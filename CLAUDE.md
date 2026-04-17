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
| `generate_masterlist.py` | Konvertiert Masterlist-XLSX → masterlist.json + auto git push |

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
  "_w": { "CHU.8678": "Edubook", "CHU.1234": "Anderer Standort" },
  "i": {
    "1070128700": {
      "n": "BELT-TIMING-1830-2MR09",
      "l": { "CHU.8678": {"min": 1, "qoh": 2} }
    }
  }
}
```

Wird erzeugt von `generate_masterlist.py` aus `PART_MGMT/input/Inventory value by item number…xlsx`.
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

## Linux/WSL Setup (auf Windows-Rechnern mit WSL)

`generate_masterlist.py` läuft auf Linux via Wrapper-Script und systemd-Service:

- **`~/masterlist_watch.sh`** — ruft das Script mit dem Windows-Pfad auf:
  ```
  --input "/mnt/c/sync/moebius/PART_MGMT/input/Inventory value by item number, planned status, and age.xlsx" --watch
  ```
- **systemd-Service** `masterlist-watch` — startet automatisch beim Ubuntu-Start
- Logs: `journalctl -u masterlist-watch -f`

Bei neuem Linux-Rechner: `masterlist_watch.sh` erstellen, systemd-Service einrichten (siehe git history oder frag Claude).

---

## Bekannte Einschränkungen / Offene Punkte

- QR-Merge hat 2953-Zeichen-Limit → bei vielen Artikeln zu klein
- iOS: AudioContext muss via User-Gesture erzeugt werden (Toggle-Button im Scanner-Modal)
- Kein Multi-Lager in einer Session (immer ein XLSX = ein Lager)
