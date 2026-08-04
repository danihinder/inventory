# CLAUDE.md – Inventur Scanner PWA

## Projektübersicht

Mobile PWA für Lagerinventuren bei Canon Schweiz AG.
Mitarbeiter scannen Barcodes mit dem Handy, vergleichen mit der Inventurliste (XLSX) und exportieren das Ergebnis.

**Live-URL:** `https://danihinder.github.io/inventory/`
**Deployment:** GitHub Pages (automatisch bei Push auf main)
**Build-Nummer:** steht in `const BUILD` in `index.html`; der Header liest sie daraus und zeigt sie an.

---

## Architektur-Entscheid: Single-File PWA

Die gesamte App steckt in **`index.html`** (~1300 Zeilen, kein Build-Schritt).
Bewusste Entscheidung: kein Node.js, kein npm, kein Framework — direkt im Browser lauffähig, auch offline.

| Datei | Zweck |
|---|---|
| `index.html` | Komplette App (HTML + CSS + JS) |
| `manifest.json` | PWA-Metadaten (Icon als inline SVG data-URI) |
| `sw.js` | Service Worker, Cache-Name = `inventur-v<Build>` |
| `data/masterlist.json` | Stammdaten: Artikelname + QOH/MIN je Lager |
| `generate_masterlist.py` | Konvertiert Inventarliste(n) → masterlist.json + auto git push (Pipeline s.u.) |
| `inventar_mail_watch.py` | Windows/Outlook: speichert wöchentliche Inventarliste aus Mail-Anhang, ruft danach `generate_masterlist.py` auf (gesamte Pipeline in einem Prozess) |

---

## State-Objekt `S`

Zentraler App-Zustand (global in `index.html`):

```js
const S = {
  ml:       null,   // masterlist.json (geladen beim Start von GitHub Pages)
  inv:      null,   // [{tag, item, bez, sub, row}] – aus XLSX geladen
  wh:       null,   // "CHU.8678" – aus Dateiname geparst
  whName:   null,   // "Edubook" – aus Dateiname geparst
  fname:    null,   // originaler Dateiname
  fdata:    null,   // ArrayBuffer der XLSX (für Export)
  fdataB64: null,   // base64 von fdata (für localStorage)
  scanned:  {},     // {itemNr: anzahl}
}
```

Persistenz: `localStorage` Key `inventur_v1` (JSON), wird bei jedem `saveSession()` geschrieben.

---

## masterlist.json Format

```json
{
  "_generated": "2026-02-26",
  "_stand": "2026-07-28",
  "_source": "weekly:Inventory 28072026.xlsx",
  "_w": { "CHU.8678": "Edubook", "CHU.1234": "Anderer Standort" },
  "i": {
    "1070128700": {
      "n": "BELT-TIMING-1830-2MR09",
      "l": { "CHU.8678": {"min": 1, "qoh": 2, "a": 3} }
    }
  }
}
```

`l.<lager>.a` = Age-Rank (0–5, siehe `parse_age_rank`), `l.<lager>.v` = Preis
(TOTAL STOCK VALUE) — beide optional, `index.html` fällt bei Fehlen sauber auf
neutrale Darstellung zurück (`ageClass` → `''`, Preis → `—`).

Wird erzeugt von `generate_masterlist.py`, siehe „Masterlist-Pipeline" unten.
SW-Strategie: **Network-first** (immer aktuellste Daten, Fallback Cache).

---

## CDN-Abhängigkeiten (fest versioniert)

- **zxing-wasm** `@2.1.2` – Barcode-Decoder (C++-ZXing als WebAssembly).
  **Nur auf iOS geladen**, weil iOS Safari keinen nativen `BarcodeDetector` hat.
  Auf Android läuft der native `BarcodeDetector` (ML-Kit) — der ist bereits gut getuned
  und kennt keine `tryHarder`-Option. Die Zweigentscheidung steckt im `<script type="module">`
  im Head; `window.scannerReady` exponiert `{mode: 'native' | 'wasm', ...}`.
- **SheetJS** `xlsx-0.20.3` – XLSX lesen + schreiben im Browser
- **QRCode.js** `1.0.0` via cdnjs – QR-Code generieren (Merge-Funktion)

Alle werden vom SW gecacht (best-effort). Transitive Deps des zxing-wasm
(share.js, `zxing_reader.wasm`, ~500 KB) cachen beim ersten Scan via fetch-Handler →
**erste iOS-Nutzung braucht Online-Verbindung**.

### Scanner-Engine-Details
- Auf iOS: eigener Tick-Loop (~13 Hz) zeichnet jedes Tick das Video-Frame auf ein
  Canvas (max. 1280-px-Kante) und ruft `readBarcodes(imgData, {tryHarder, tryRotate,
  tryInvert, tryDownscale, maxNumberOfSymbols: 1})`. `tryHarder` ist CPU-intensiv,
  deshalb gedrosselt.
- False-Positives aus `tryHarder` (z.B. 2-Zeichen-Geistermatches aus Kantenrauschen)
  werden vom `isInventoryCode`-Filter in der Scan-Loop abgefangen — Loop läuft weiter
  statt sich zu beenden (Regression-Schutz, Build 63).
- Torch + Zoom: via `track.getCapabilities()` und `applyConstraints({advanced: […]})`.
  Capability-gated (Buttons sichtbar nur wenn die Kamera es meldet). Auf iOS Safari
  ist Torch wankelig — fehlgeschlagene Toggles erscheinen in der Debug-Zeile.
- **Kamera-Auswahl (Android, Build 70):** Android-Phones haben oft mehrere Rückkameras
  (Haupt/Ultraweit/Tele/Macro). Chrome wählt bei `facingMode: 'environment'` +
  1920×1080 zufällig eine davon — oft die Ultraweit mit schlechter Nah-Fokussierung.
  Wir enumerieren mit `enumerateDevices()` und defaulten auf **Index 0 der Back-Cams**
  (= meist Hauptlinse, zuverlässig getestet auf Samsung Galaxy). `📷 N/M`-Button im
  Scanner lässt durch alle Linsen zyklen; Auswahl in localStorage `inventur_cam_idx`.
- Fokus: `focusDistance: min` wird versucht (Build 69), hilft auf einigen Phones als
  Macro-Erzwingung — aber der Kamera-Wechsel wirkt stärker.

---

## Barcode-Filter

Nur **7- oder 10-stellige Zahlen** werden akzeptiert: `/^(\d{7}|\d{10})$/`
Gilt für Hauptscanner, Suchscanner und manuelle Eingabe.

Doppelscan-Schutz: gleicher Code innerhalb 2500ms wird ignoriert.

---

## Expert Mode

Aktivierung: **7× Tap auf das Build-Label** im Header → PIN-Dialog → `675756`
Deaktivierung: erneut 7× Tap (kein PIN nötig).

Gespeichert in `localStorage` Key `inventur_expert`.

Expert-only Elemente:
- Qty-Modal: "MIN laut System" + "QOH laut System" (im Normalmodus versteckt, damit Techniker nicht einfach den Sollbestand einträgt)
- Qty-Modal Normal: 1-spaltig (nur "Bisher gezählt"); Expert: 3-spaltig
- Fortschrittsbalken-Text: nur Expert zeigt "X von Y Stk. korrekt im Lager"
- Abschluss: QOH-Spalte in "Gezählte Artikel"
- Abschluss: "Noch fehlend"-Spalte in "Fehlende Artikel"
- Abschluss: Liste "Überbestand" (Inventarteile wo gezählt > QOH; nur bei bekanntem QOH)

---

## Merge-Funktion (QR-Code)

Person A zeigt QR-Code (`showExportQR`), Person B scannt ihn (`startQRImport`).
Payload: `GZ:<gzip+base64>` (Fallback `RAW:<base64>`), enthält `S.scanned` als JSON.
QR-Limit: 2953 Zeichen. Bei grösserem Datenbestand → manuelles Teilen nötig.
Merge-Logik: Mengen werden **addiert** (kein Überschreiben).

---

## Service Worker

- Cache-Name muss bei **jedem Deployment hochgezählt** werden: `inventur-v<N>` (idealerweise gleich wie `BUILD`)
- `skipWaiting` im Install → neuer SW übernimmt sofort
- `controllerchange` → App lädt automatisch neu (Session bleibt via localStorage)
- **Auto-Update** (Build 68): Beim Page-Load und alle 10 Min ruft der Client `reg.update()`,
  damit iOS Safari nicht tagelang auf alter Version hängenbleibt
- **Manueller Update-Button** (⟳ im Header, nur Expert-Mode): ruft `reg.update()` und
  postet `{type:'SKIP_WAITING'}` an einen wartenden Worker

---

## Fehlend-Logik

`deficit = max(0, target - gezählt)`
`target = QOH aus masterlist (wenn vorhanden) sonst 1`

Artikel gilt als "vollständig" wenn deficit = 0.

---

## XLSX-Export (`downloadXLSX`)

- Liest original XLSX aus `S.fdata` (oder `S.fdataB64`)
- Schreibt gezählte Menge in Spalte `Gezählt`
- Extra-Artikel (nicht in Inventurliste) werden **am Ende angehängt**
- Ausgabename: `<Originalname>_ausgefüllt.xlsx`

---

## Deployment-Workflow

1. `index.html` ändern + `const BUILD` hochzählen (Header-Label liest daraus)
2. `sw.js`: `CACHE_NAME = 'inventur-v<N+1>'` hochzählen (selbe Nummer wie BUILD)
3. `git commit` + `git push` → GitHub Pages aktualisiert automatisch (ca. 1 Min)
4. Clients kriegen das Update binnen ~10 Sek nach dem nächsten Page-Reload,
   dank `reg.update()`. Falls jemand hängt: ⟳-Button im Header (Expert-Mode).
5. Masterlist-Update (separat): `python generate_masterlist.py` → commitet + pusht automatisch

---

## Masterlist-Pipeline (seit 2026-08-04)

Zwei Quellen, automatisch verkettet mit Fallback + Alarm:

1. **Primärquelle: wöchentliche Inventarliste** (`PART_MGMT/weekly_inventorylist/*.xlsx`) —
   kommt per Mail von `giovanni.fiore@canon.ch` bzw. `ch-sphd@canon.ch`, wird von
   `inventar_mail_watch.py` (Outlook-COM, Windows-seitig) automatisch als
   xlsx-Anhang dort gespeichert. Betreff/Dateiname variieren stark und
   unvorhersehbar ("Inventory 28072026", "Inventurliste 21.07.2026", ...) —
   `generate_masterlist.py` sucht sich selbst die *neueste Datei per Datum im
   Dateinamen* (`parse_snapshot_date`, mehrere Formate) und liest Spalten *per
   Name* (nicht per fixem Index), weil dieses Format nicht von uns kontrolliert
   wird und schon mehrfach leicht variiert hat (Spaltenreihenfolge, fehlende
   Spalten). Diese Quelle hat **keine Preisspalte** (bewusst kein Problem, siehe
   masterlist.json-Format oben) und keine feste Spaltenanzahl.
2. **Fallback: alte Quelle** `Inventory value by item number, planned status,
   and age.xlsx` — liegt seit 2026-08-04 im **selben Ordner**
   (`PART_MGMT/weekly_inventorylist/`, nicht mehr `PART_MGMT/input/`), fester Dateiname
   und festes Spaltenlayout (`COL_*`-Konstanten), ein einzelner
   Datenlieferant, inkl. Preis. `find_latest_weekly_file` erkennt sie am
   festen Namen und wertet sie nie als wöchentlichen Snapshot.

**Wann greift der Fallback:** Nur wenn 1) die wöchentliche Liste fehlt oder
ihr Spaltenlayout nicht mehr zu den Pflichtspalten (`WEEKLY_REQUIRED_COLS`)
passt, UND 2) die Fallback-Datei (per Datei-Änderungsdatum) **neuer** ist als
der `_stand` der bereits vorhandenen `masterlist.json`
(`read_existing_stand`). Ist die Fallback-Datei nicht neuer (z.B. eine alte,
liegengebliebene Kopie) — **passiert nichts**: `masterlist.json` bleibt
byte-identisch unverändert, kein Commit, kein Push, kein Rückschritt zu
älteren Daten. Genauso wenn gar keine Fallback-Datei existiert.

**Alarm-Mechanismus:** In jedem dieser Fehlerfälle schreibt
`generate_masterlist.py` eine `PART_MGMT/weekly_inventorylist/_masterlist_alarm.txt` mit
Zeitstempel, genauer Fehlermeldung und was daraufhin passiert ist (Fallback
genutzt / Fallback zu alt / kein Fallback). Die Alarm-Datei bleibt bestehen
bis die wöchentliche Quelle wieder erfolgreich gelesen wird (dann automatisch
gelöscht). Wird der Fallback tatsächlich verwendet, landet zusätzlich ein
Hinweis in der Commit-Message ("... (Fallback: alte Quelle wg.
Format-Problem)").

**`inventar_mail_watch.py`** (Windows, `pywin32`, Outlook muss laufen):
sucht neue Mails der beiden Absender, speichert nur `.xlsx`-Anhänge (der
mitgeschickte `.pdf`-Anhang wird ignoriert) unter Originalname in
`PART_MGMT/weekly_inventorylist/`. Dedup über Outlook-`EntryID` in
`_inventar_mail_watch.json`. Ruft danach **selbst** `generate_masterlist.py`
im selben Ordner auf (Konvertierung + Push) — bei jedem Poll, nicht nur wenn
neue Mail gefunden wurde, damit auch manuell abgelegte Dateien erfasst
werden; das ist billig, weil `generate_masterlist.py` nur pusht wenn sich
`masterlist.json` tatsächlich geändert hat. Start: `inventar_mail_watch.bat`
(eigener `.venv` via `_venv.bat`/`requirements.txt`, analog zu
`TSM/printer_errors_watch.bat`) — idealerweise per Verknüpfung in
`shell:startup`, dann läuft es automatisch mit jedem Login mit.

Damit läuft die **gesamte Pipeline in einem einzigen Windows-Prozess**, in
genau dem Ordner (`/mnt/c/sync/moebius/inventur-pwa/`), den auch Claude Code
normalerweise bearbeitet — kein separater Watcher, keine zweite Git-Clone.

## Frühere Architektur (bis 2026-08-04, retired)

Bis 2026-08-04 lief die Konvertierung als **separater WSL/systemd-Dienst**
(`masterlist-watch`, via `~/masterlist_watch.sh` mit `--watch`), der aus
einer **eigenen WSL-nativen Git-Clone** unter `/home/dani/inventory/` (nicht
`/mnt/c/sync/moebius/inventur-pwa/`) lief. Das führte wiederholt zu
Verwirrung, weil Änderungen am Skript erst nach `git pull` in dieser zweiten
Clone + Service-Neustart wirksam wurden. Mit `inventar_mail_watch.py`, das
seither die Konvertierung selbst anstösst (s.o.), wurde dieser Dienst
überflüssig und deaktiviert. Falls hier künftig doch wieder ein WSL-seitiger
Watcher gebraucht wird (z.B. als unabhängiger Fallback falls der
Windows-Prozess mal nicht läuft): `generate_masterlist.py --watch` existiert
unverändert und funktioniert weiterhin eigenständig, sollte dann aber direkt
aus `/mnt/c/sync/moebius/inventur-pwa/` laufen statt aus einer zweiten Clone.

---

## Netzwerk-Umgebung (Dev-Rechner mit Cisco Umbrella)

Dieser Rechner filtert GitHub über einen **Cisco-Umbrella-DNS-Filter** (siehe `/sync/CLAUDE.md` → „Environment: Network"). Relevanz für dieses Projekt:

- **Publish-Weg unbetroffen:** `generate_masterlist.py` und `git push` laufen über **SSH zu `github.com`** (echte IP, kein TLS-Cert-Trust) → funktioniert klaglos.
- **Daten-Laden meist OK, selten flaky:** Die PWA zieht `data/masterlist.json` von ihrer eigenen Origin `danihinder.github.io`. **`*.github.io` ist NICHT hart blockiert** (löst auf echte Pages-IP `185.199.x.x` auf, Fetch getestet HTTP 200). Nur wenn die PWA **im Browser auf diesem Rechner** getestet wird, können vereinzelt **transiente DNS-Aussetzer** (`getaddrinfo failed`) das Laden kurz stören — kein Dauerblock, meist beim Reload weg. Endnutzer auf anderen Netzen (Handy etc.) sind ohnehin nicht betroffen.
- **Hart blockiert ist nur `raw.githubusercontent.com`** (`146.112.x.x` → `CERTIFICATE_VERIFY_FAILED`) — nutzt dieses Projekt nicht.

**Fallback, falls github.io hier je zu unzuverlässig wird:** masterlist.json stattdessen vom freien `api.github.com`-Contents-Endpoint laden — es ist ein Cross-Origin-Fetch, aber api.github.com sendet CORS-Header:

```js
fetch("https://api.github.com/repos/danihinder/inventory/contents/data/masterlist.json?ref=main",
      { headers: { Accept: "application/vnd.github.raw+json" } })  // → JSON roh, ETag/304, public = ohne Token (60/h pro IP)
```

Referenz: `TSM/dartagnan.py` `_run_masterlist_fetch` wurde 2026-07-13 aus Robustheitsgründen genau so umgestellt (Python-Seite).

## Bekannte Einschränkungen / Offene Punkte

- QR-Merge hat 2953-Zeichen-Limit → bei vielen Artikeln zu klein
- iOS: AudioContext muss via User-Gesture erzeugt werden (Toggle-Button im Scanner-Modal)
- Kein Multi-Lager in einer Session (immer ein XLSX = ein Lager)
