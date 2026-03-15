# CLAUDE.md – Inventur Scanner PWA

## Projektübersicht

Mobile PWA für Lagerinventuren bei Canon Schweiz AG.
Mitarbeiter scannen Barcodes mit dem Handy, vergleichen mit der Inventurliste (XLSX) und exportieren das Ergebnis.

**Live-URL:** `https://danihinder.github.io/inventory/`
**Deployment:** GitHub Pages (automatisch bei Push auf main)
**Aktueller Build:** 60

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

- **ZXing** `@0.18.6` – Barcode/QR-Scanner (Code128 + QR auf iOS & Android)
- **SheetJS** `xlsx-0.20.3` – XLSX lesen + schreiben im Browser
- **QRCode.js** `1.0.0` via cdnjs – QR-Code generieren (Merge-Funktion)

Alle drei werden vom SW gecacht (best-effort).

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

- Cache-Name muss bei **jedem Deployment hochgezählt** werden: `inventur-v<N>`
- `skipWaiting` im Install → neuer SW übernimmt sofort
- `controllerchange` → App lädt automatisch neu (Session bleibt via localStorage)

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

1. `index.html` ändern
2. `sw.js`: `CACHE_NAME = 'inventur-v<N+1>'` hochzählen
3. `git commit` + `git push` → GitHub Pages aktualisiert automatisch
4. Masterlist-Update (separat): `python generate_masterlist.py` → commitet + pusht automatisch

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
