# Inventur Scanner

Barcode-Scanner für Lagerinventuren – läuft direkt im Handy-Browser, kein App-Store nötig.

**App-URL:** `https://danihinder.github.io/inventur-pwa/`

---

## App installieren

**Android (Chrome):**
Adressleiste → ⋮ Menü → „Zum Startbildschirm hinzufügen"

**iOS (Safari):**
Teilen-Symbol → „Zum Home-Bildschirm"

Die App funktioniert auch ohne Installation direkt im Browser.

---

## Bedienung

### 1. Inventurdatei laden

Auf dem Tab **Inventur** die Excel-Datei für das zu zählende Lager auswählen.
Der Dateiname muss die Lagerkennung enthalten, z.B. `Inventory CHU.8678 Edubook.xlsx`.
Die App erkennt das Lager automatisch aus dem Dateinamen.

### 2. Artikel scannen

Auf **Scannen starten** tippen. Die Kamera öffnet sich.

- Der Scanner erkennt nur **7- oder 10-stellige** Artikelnummern (Code128)
- Nach erfolgreichem Scan: Kamera schliesst sich, Mengendialog erscheint
- Menge bestätigen → Scanner öffnet sich automatisch wieder

Im Scan-Dialog gibt es einen Schalter für **Ton** (Beep) und **Haptik** (Vibration, nur Android) bei erfolgreichem Scan.

Alternativ können Artikelnummern auch über **Manuelle Eingabe** eingetippt werden.

### 3. Fortschritt verfolgen

Oben auf dem Inventur-Tab wird der Fortschritt als Stückzahl und Balken angezeigt:

| Feld | Bedeutung |
|---|---|
| Gezählt Stk. | Anzahl bereits vollständig erfasster Stücke |
| Fehlend Stk. | Noch ausstehende Stücke laut Sollbestand |
| Extra Stk. | Gescannte Stücke die nicht in der Inventurliste stehen |

### 4. Suche

Im Tab **Suche** kann nach Artikeln gesucht werden – per Texteingabe oder Barcode-Scan.
Zeigt Artikelname, Sollbestand (QOH) und bereits gezählte Menge.

### 5. Mit Kollegen zusammenführen (Merge)

Wenn mehrere Personen gleichzeitig zählen:

1. Person A: Tab **Merge** → **QR-Code anzeigen** → Code dem Kollegen zeigen
2. Person B: Tab **Merge** → **QR-Code scannen** → QR-Code von Person A scannen
3. Die Zählstände werden zusammengeführt (Mengen addiert)

### 6. Abschluss

Der Tab **Abschluss** zeigt eine Zusammenfassung und drei aufklappbare Listen:

| Liste | Inhalt |
|---|---|
| Gezählte Artikel | Alle erfassten Artikel mit gezählter Menge (editierbar) |
| Fehlende Artikel | Artikel deren gezählte Menge unter dem Sollbestand liegt |
| Extra-Artikel | Gescannte Artikel die nicht in der Inventurliste stehen |

**Korrektur:** In der Liste „Gezählte Artikel" kann die Menge direkt angepasst werden – einfach den Wert antippen, ändern und Feld verlassen. Die Auswertung aktualisiert sich sofort.

**Export:** Mit „Ausgefüllte XLSX herunterladen" wird die originale Inventurdatei mit den gezählten Mengen ausgefüllt und kann per Mail verschickt werden.

---

## Dateien

| Datei | Zweck |
|---|---|
| `index.html` | Die komplette App (kein Build-Schritt nötig) |
| `manifest.json` | PWA-Metadaten (Name, Icon, Display-Mode) |
| `sw.js` | Service Worker (Offline-Cache, automatische Updates) |
| `data/masterlist.json` | Alle Teile + QOH-Sollbestand je Lager |
| `generate_masterlist.py` | Erzeugt masterlist.json aus der Stammdaten-XLSX |
