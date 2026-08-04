"""
inventar_mail_watch.py - Speichert die wöchentliche Inventarliste (xlsx-Anhang)
aus Outlook-Mails automatisch in PART_MGMT/weekly_inventorylist/, via pywin32-COM.
Outlook muss laufen.

Absender: giovanni.fiore@canon.ch und ch-sphd@canon.ch. Der Betreff variiert
stark und unvorhersehbar (mal "Inventory nnnnnnnn", mal "Inventurliste
nn.nn.nnnn", ...) - es wird deshalb NICHT nach Betreff gefiltert, sondern nach
Absender + xlsx-Anhang + Anhang-Dateiname beginnt mit "Invent" (deckt
Inventory/Inventar-/Inventurliste ab, filtert aber sonstige xlsx-Anhänge als
Rauschen raus). Mails haben meist 2 Anhänge (pdf + xlsx); nur die passende
xlsx wird gespeichert, der Dateiname wird unverändert vom Anhang übernommen
(generate_masterlist.py parst das Datum daraus).

Ruft nach jedem Poll zusätzlich generate_masterlist.py auf (im selben Ordner,
selber Prozess-Baum, kein separater Watcher nötig) - unabhängig davon ob
gerade neue Mail gefunden wurde, damit auch manuell in PART_MGMT/weekly_inventorylist/
abgelegte Dateien (z.B. eine aktualisierte Fallback-Datei) erfasst werden.
generate_masterlist.py pusht nur wenn sich masterlist.json tatsächlich
geändert hat (git-diff-Check drin) - der Aufruf ist also auch im Leerlauf
billig. Bis 2026-08-04 lief das separat über einen WSL/systemd-Dienst +
eine zweite Git-Clone unter /home/dani/inventory/ - das ist seither
konsolidiert (siehe CLAUDE.md).

Start:
    python inventar_mail_watch.py             # einmaliger Lauf (Mail-Check + Konvertierung)
    python inventar_mail_watch.py --watch 60   # Watch-Modus, alle 60 Minuten
    python inventar_mail_watch.py --dry-run    # zeigt was es täte, konvertiert/pusht nicht
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import time
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR    = Path(__file__).parent
INVENTAR_DIR  = SCRIPT_DIR.parent / "PART_MGMT" / "weekly_inventorylist"
STATE_PATH    = SCRIPT_DIR / "_inventar_mail_watch.json"

SENDERS       = ["giovanni.fiore@canon.ch", "ch-sphd@canon.ch"]
DEFAULT_FOLDER = "Inbox"
MAX_AGE_DAYS  = 60      # Backfill-Fenster beim ersten Lauf - Mails kommen woechentlich
MAX_SEEN_IDS  = 2000


# ── Outlook COM access (siehe TSM/printer_errors.py fuer die Vorlage) ──────────

def connect_outlook():
    import win32com.client
    outlook = win32com.client.Dispatch("Outlook.Application")
    last_err = None
    for delay in (0, 0.5, 1.0, 2.0, 3.0):
        if delay:
            time.sleep(delay)
        try:
            return outlook.GetNamespace("MAPI")
        except AttributeError as e:
            last_err = e
    raise RuntimeError(
        "Outlook.Application.GetNamespace nicht verfügbar nach 6.5s Warten. "
        "Outlook neustarten oder gen_py-Cache leeren: rmdir /s /q %TEMP%\\gen_py"
    ) from last_err


def resolve_folder(ns, path: str):
    if not path or path.strip().lower() == "inbox":
        return ns.GetDefaultFolder(6)  # olFolderInbox
    parts = [p.strip() for p in path.replace("\\", "/").split("/") if p.strip()]
    if parts[0].lower() == "inbox":
        folder = ns.GetDefaultFolder(6)
        parts = parts[1:]
    else:
        folder = ns.Folders.Item(1)
    for name in parts:
        folder = folder.Folders[name]
    return folder


def get_smtp_sender(item) -> str:
    try:
        pa = item.PropertyAccessor
        addr = pa.GetProperty("http://schemas.microsoft.com/mapi/proptag/0x5D01001F")
        if addr and "@" in addr:
            return addr.strip().lower()
    except Exception:
        pass
    try:
        addr = (item.SenderEmailAddress or "").strip()
        if "@" in addr:
            return addr.lower()
        sender = item.Sender
        if sender:
            try:
                eu = sender.GetExchangeUser()
                if eu and eu.PrimarySmtpAddress:
                    return eu.PrimarySmtpAddress.strip().lower()
            except Exception:
                pass
    except Exception:
        pass
    return ""


# ── State ────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"seen_ids": []}


def save_state(state: dict):
    state["seen_ids"] = state["seen_ids"][-MAX_SEEN_IDS:]
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── Attachment handling ─────────────────────────────────────────────────────

def _unique_target(inventar_dir: Path, filename: str, att_size: int) -> Path | None:
    """
    Liefert den Zielpfad fuer einen Anhang, oder None wenn eine identische
    Datei (gleicher Name + gleiche Groesse) schon existiert (Duplikat/Resend
    -> ueberspringen). Bei gleichem Namen aber anderer Groesse wird ein
    Zeitstempel-Suffix angehaengt, um kein Datenverlust durch Ueberschreiben
    zu riskieren.
    """
    safe = re.sub(r'[\\/:*?"<>|]', '_', filename).strip()
    target = inventar_dir / safe
    if not target.exists():
        return target
    if target.stat().st_size == att_size:
        return None  # identisch -> Duplikat, ueberspringen
    stem, suffix = target.stem, target.suffix
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return inventar_dir / f"{stem}__{ts}{suffix}"


def fetch_and_save(ns, inventar_dir: Path, seen_ids: list[str], dry_run: bool) -> tuple[list[str], list[str]]:
    """Neue Mails der bekannten Absender durchsuchen, xlsx-Anhaenge speichern.
    Gibt (neue seen_ids, gespeicherte Dateinamen) zurueck."""
    folder = resolve_folder(ns, DEFAULT_FOLDER)
    items = folder.Items
    items.Sort("[ReceivedTime]", True)
    cutoff = dt.datetime.now() - dt.timedelta(days=MAX_AGE_DAYS)
    try:
        cstr = cutoff.strftime("%m/%d/%Y %I:%M %p")
        items = items.Restrict(f"[ReceivedTime] >= '{cstr}'")
    except Exception:
        pass

    seen = set(seen_ids)
    senders_lc = [s.lower() for s in SENDERS]
    saved = []

    for item in items:
        try:
            if item.Class != 43:  # olMail
                continue
        except Exception:
            continue
        try:
            entry_id = item.EntryID
        except Exception:
            continue
        if not entry_id or entry_id in seen:
            continue

        sender = get_smtp_sender(item)
        if sender not in senders_lc:
            continue

        try:
            subject = item.Subject or ""
        except Exception:
            subject = ""

        seen.add(entry_id)

        try:
            atts = item.Attachments
        except Exception:
            continue

        found_xlsx = False
        for i in range(1, atts.Count + 1):
            try:
                att = atts.Item(i)
                name = att.FileName or ""
            except Exception:
                continue
            if not name.lower().endswith(".xlsx"):
                continue
            found_xlsx = True

            if not name.lower().startswith("invent"):
                print(f"  ~ ignoriert (Anhangname beginnt nicht mit 'Invent'): {name}  [{sender}]")
                continue

            try:
                att_size = att.Size
            except Exception:
                att_size = -1

            target = _unique_target(inventar_dir, name, att_size)
            if target is None:
                print(f"  = bereits vorhanden (uebersprungen): {name}  [{sender}]")
                continue

            if dry_run:
                print(f"  [dry-run] wuerde speichern: {target.name}  [{sender}] Betreff: {subject[:60]}")
            else:
                inventar_dir.mkdir(parents=True, exist_ok=True)
                att.SaveAsFile(str(target))
                print(f"  ✔ gespeichert: {target.name}  [{sender}] Betreff: {subject[:60]}")
                saved.append(target.name)

        if not found_xlsx:
            print(f"  (kein xlsx-Anhang) [{sender}] Betreff: {subject[:60]}")

    return list(seen), saved


def run_masterlist_conversion():
    """Ruft generate_masterlist.py im selben Ordner auf (Konvertierung + Push,
    pusht nur bei tatsächlicher Änderung - siehe generate_masterlist.py:git_push)."""
    script = SCRIPT_DIR / "generate_masterlist.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(SCRIPT_DIR), capture_output=True, text=True,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        print(f"⚠️  generate_masterlist.py beendete mit Exit-Code {result.returncode}", file=sys.stderr)


def run_once(dry_run: bool = False):
    state = load_state()
    print(f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] Verbinde mit Outlook ...", flush=True)
    ns = connect_outlook()
    new_seen, saved = fetch_and_save(ns, INVENTAR_DIR, state["seen_ids"], dry_run)
    if not dry_run:
        state["seen_ids"] = new_seen
        save_state(state)
    if saved:
        print(f"[{dt.datetime.now():%H:%M:%S}] {len(saved)} neue Datei(en) gespeichert: {', '.join(saved)}")
    else:
        print(f"[{dt.datetime.now():%H:%M:%S}] Keine neuen Anhaenge.")

    if not dry_run:
        run_masterlist_conversion()


def run_watch(interval_minutes: int):
    print(f"Überwache Postfach ({', '.join(SENDERS)}) alle {interval_minutes} min.")
    print(f"Ziel: {INVENTAR_DIR}  |  Ctrl+C zum Beenden.\n")
    try:
        while True:
            try:
                run_once(dry_run=False)
            except Exception as e:
                print(f"[{dt.datetime.now():%H:%M:%S}] Fehler: {e}", file=sys.stderr)
            time.sleep(interval_minutes * 60)
    except KeyboardInterrupt:
        print("\nWatcher beendet.")


def main():
    parser = argparse.ArgumentParser(description="Woechentliche Inventarliste aus Outlook-Mail speichern")
    parser.add_argument("--watch", type=int, metavar="MINUTES", default=None,
                        help="Watch-Modus, Prüfintervall in Minuten")
    parser.add_argument("--dry-run", action="store_true",
                        help="Nur anzeigen was gespeichert wuerde, nichts schreiben")
    args = parser.parse_args()

    if args.watch:
        run_watch(args.watch)
    else:
        run_once(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
