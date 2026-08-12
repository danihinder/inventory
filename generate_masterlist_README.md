# generate_masterlist.py – Bedienungsanleitung

Konvertiert Inventarlisten in `data/masterlist.json` und publiziert sie automatisch auf GitHub Pages.

Seit 2026-08-04 läuft das normalerweise **vollautomatisch** über
`inventar_mail_watch.py`: das Skript wacht über Outlook, holt die
wöchentliche Inventarliste automatisch aus der Mail und ruft danach selbst
`generate_masterlist.py` auf. Diese Anleitung beschreibt trotzdem den
manuellen Aufruf von `generate_masterlist.py` — nützlich zum Testen,
Debuggen, oder falls die Mail-Automatik mal nicht laufen soll.

---

## Voraussetzungen

```bash
pip install -r requirements.txt
```

(`openpyxl` für `generate_masterlist.py`, `pywin32` zusätzlich für
`inventar_mail_watch.py` — nur unter Windows nötig, da es Outlook per COM
anspricht.)

Python 3.8+, Git (im PATH), Internetzugang für den Push.

---

## Zwei Quellen, automatisch verkettet

1. **Primärquelle:** die neueste Datei in `PART_MGMT/weekly_inventorylist/`
   (per Datum im Dateinamen erkannt — Formate wie `Inventory 28072026.xlsx`,
   `Inventarliste210726.xlsx`, `Inventurliste 21.07.2026.xlsx` werden alle
   verstanden). Spalten werden über Namen gesucht, nicht über feste Indizes,
   weil dieses Format nicht von uns kontrolliert wird.
2. **Fallback:** `Inventory value by item number, planned status, and
   age.xlsx`, liegt im selben Ordner, festes Spaltenlayout. Kommt nur zum
   Zug wenn 1) die Primärquelle fehlt oder ihr Format nicht passt, UND 2)
   diese Datei neuer ist als der bereits vorhandene `_stand` in
   `masterlist.json` — sonst passiert nichts (kein Rückschritt zu älteren
   Daten).

Schlägt die Primärquelle fehl, schreibt das Skript
`PART_MGMT/weekly_inventorylist/_masterlist_alarm.txt` (Zeitstempel + genaue
Fehlermeldung), die bestehen bleibt bis die Primärquelle wieder funktioniert.
Details siehe `CLAUDE.md` → „Masterlist-Pipeline".

---

## Manueller Aufruf

```bash
python generate_masterlist.py
```

Sucht automatisch die neueste Datei in `PART_MGMT/weekly_inventorylist/`,
konvertiert, schreibt `data/masterlist.json`, macht `git commit` + `git push`
(nur wenn sich die Ausgabe tatsächlich geändert hat).

## Automatischer Modus (Standalone-Watcher, meist nicht nötig)

```bash
python generate_masterlist.py --watch
```

Überwacht beide Quellen (Primärordner + Fallback-Datei darin) laufend und
konvertiert bei jeder erkannten Änderung. **Normalerweise überflüssig**, da
`inventar_mail_watch.py` die Konvertierung ohnehin bei jedem Mail-Poll
selbst anstösst — dieser Modus ist als eigenständiges Fallback-Werkzeug
gedacht, falls die Mail-Automatik mal nicht laufen soll.

Beenden mit `Ctrl+C`.

---

## Alle Optionen

| Option              | Beschreibung                                                                           | Default                          |
| ------------------- | --------------------------------------------------------------------------------------- | --------------------------------- |
| `--watch`           | Quellen überwachen, bei Änderung automatisch ausführen                                  | aus                                |
| `--interval N`      | Prüfintervall in Sekunden (nur mit `--watch`)                                            | `30`                               |
| `--no-push`         | Nur konvertieren, kein Git-Commit/Push                                                   | aus                                |
| `--inventar-dir PFAD` | Ordner mit den wöchentlichen Inventarlisten (Primärquelle)                            | `PART_MGMT/weekly_inventorylist/`  |
| `--input PFAD`      | Pfad zur Fallback-XLSX (nur genutzt wenn Primärquelle fehlt/kaputt UND diese Datei neuer ist als der bestehende Stand) | `<inventar-dir>/Inventory value by item number, planned status, and age.xlsx` |
| `--out PFAD`        | Alternativer Ausgabepfad für masterlist.json                                            | `data/masterlist.json`             |

**Beispiele:**

```bash
# Nur konvertieren, nicht pushen (z.B. zum Testen)
python generate_masterlist.py --no-push

# Anderen Ordner fuer die woechentlichen Listen verwenden
python generate_masterlist.py --inventar-dir "D:\Downloads\inventar-test"
```

---

## Standardpfade

| Datei                     | Pfad                                                                                                    |
| -------------------------- | -------------------------------------------------------------------------------------------------------- |
| Primärquelle (Ordner)      | `C:\sync\moebius\PART_MGMT\weekly_inventorylist\`                                                        |
| Fallback-XLSX               | `C:\sync\moebius\PART_MGMT\weekly_inventorylist\Inventory value by item number, planned status, and age.xlsx` |
| Alarm-Datei (bei Format-Problem) | `C:\sync\moebius\PART_MGMT\weekly_inventorylist\_masterlist_alarm.txt`                              |
| Ausgabe (JSON)              | `C:\sync\moebius\inventur-pwa\data\masterlist.json`                                                       |

---

## `_stand` in masterlist.json

Das Feld `_stand` gibt an, für welches Datum die Daten gelten:

- Bei der Primärquelle: das Datum, das im Dateinamen erkannt wurde (z.B.
  `Inventory 28072026.xlsx` → `2026-07-28`).
- Beim Fallback: das Datei-Änderungsdatum (mtime) der Fallback-XLSX.

Keine Rundung auf einen bestimmten Wochentag — der reine Snapshot-Zeitpunkt.

---

## Konsolenausgabe (Beispiel)

```
Lese (wöchentliche Quelle): Inventory 28072026.xlsx ...
  5,186 Datenzeilen | 60 Lager | 1621 unique Artikel
OK  Gespeichert: data/masterlist.json  (249 KB)  Quelle: weekly:Inventory 28072026.xlsx

Git: committed + pushed -> GitHub Pages wird aktualisiert.
```

Bei Fallback-Nutzung (Primärquelle kaputt, Fallback aber neuer als bestehender Stand):

```
Lese (wöchentliche Quelle): Inventorylist 28112025.xlsx ...
⚠️  Wöchentliche Quelle fehlgeschlagen: Inventorylist 28112025.xlsx: Pflichtspalten fehlen: ['min']. ...
🚨 ALARM geschrieben: .../weekly_inventorylist/_masterlist_alarm.txt
Lese (alte Quelle, Fallback): Inventory value by item number, planned status, and age.xlsx ...
  5,355 Datenzeilen | 62 Lager | 1547 unique Artikel
OK  Gespeichert: data/masterlist.json  (305 KB)  Quelle: fallback:Inventory value by item number, planned status, and age.xlsx
```

---

## Fehlerbehebung

**`⚠️ Wöchentliche Quelle fehlgeschlagen: ... Pflichtspalten fehlen: [...]`**
→ Absender hat das Exportformat geändert (Spalte umbenannt/entfernt). Prüfen
was sich geändert hat (`_masterlist_alarm.txt` zeigt die gefundenen
Spalten), ggf. `WEEKLY_COL_ALIASES` in `generate_masterlist.py` um die neue
Schreibweise ergänzen. Bis dahin läuft der Fallback automatisch (falls
aktuell genug).

**`_masterlist_alarm.txt` existiert weiterhin nach dem Fix**
→ Wird erst beim nächsten erfolgreichen Lauf der Primärquelle automatisch
gelöscht — einfach `generate_masterlist.py` erneut laufen lassen (oder
warten bis `inventar_mail_watch.py` das beim nächsten Poll erledigt).

**Fallback wird nicht verwendet, obwohl die Primärquelle kaputt ist**
→ Die Fallback-Datei ist nicht neuer als der bestehende `_stand` in
`masterlist.json` (Datei-Änderungsdatum prüfen). Das ist gewolltes
Verhalten — kein Rückschritt zu älteren Daten. Steht auch so in der
Alarm-Datei.

**`Git-Fehler: ...`**
→ Manuell pushen:

```bash
git add data/masterlist.json
git commit -m "Masterlist Update"
git push
```

**Kein Internet beim Ausführen**
→ Im `--watch`-Modus wartet das Script automatisch. Im manuellen Modus: Script nach Verbindungsaufbau erneut ausführen.

**Mail-Anhang wird von `inventar_mail_watch.py` ignoriert**
→ Nur `.xlsx`-Anhänge deren Dateiname mit `Invent` beginnt werden gespeichert
(filtert Preislisten & sonstiges Rauschen raus). Bei einem neuen, noch
unbekannten Namensmuster ggf. den Filter in `inventar_mail_watch.py`
anpassen.
