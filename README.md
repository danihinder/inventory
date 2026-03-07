# Inventory

Mobile PWA for warehouse inventory counts – runs directly in the phone browser, no app store needed.

**App URL:** `https://danihinder.github.io/inventory/`

---

## Install

**Android (Chrome):**
Address bar → ⋮ menu → "Add to Home screen"

**iOS (Safari):**
Share icon → "Add to Home Screen"

The app also works without installation directly in the browser.

---

## How to use

### 1. Load inventory file

Tap **Load Inventory File** and select the Excel file for the warehouse you are counting.
The filename must contain the warehouse code, e.g. `Inventory CHU.8678 Edubook.xlsx`.
The app detects the warehouse automatically from the filename.

### 2. Scan items

Tap **Start Scanning**. The camera opens.

- The scanner accepts only **7- or 10-digit** item numbers (Code128 and QR)
- After a successful scan: the camera closes and a quantity dialog appears
- Confirm the quantity → the scanner reopens automatically

Use the **Sound** and **Haptic** toggles in the scan dialog for beep/vibration feedback.

To enter an item number manually, use the **Manual Entry** field below the scan button.

### 3. Track progress

The progress bar and counters show:

| Field | Meaning |
|---|---|
| Counted | Items fully accounted for |
| Missing | Items still below target stock |
| Extra | Scanned items not in the inventory list |

### 4. Search

Tap **Part Search** to look up any item by text or barcode scan.
Shows item name, target stock (QOH) and already counted quantity.

### 5. Warehouse overview

Tap **Warehouse Overview** to browse all items in any warehouse with their stock levels and age.

### 6. Merge with a colleague

When multiple people are counting simultaneously:

1. Person A: go to **Merge** → tap **Show QR Code** → show the code to the colleague
2. Person B: go to **Merge** → tap **Scan QR Code** → scan Person A's code
3. The counts are merged (quantities added together)

### 7. Finish

Tap **Finish** for a summary with three collapsible lists:

| List | Content |
|---|---|
| Counted Items | All scanned items with counted quantity (editable) |
| Missing Items | Items whose counted quantity is below target stock |
| Extra Items | Scanned items not in the inventory list |

**Correction:** In the "Counted Items" list, tap any quantity to edit it directly. The summary updates immediately.

**Export:** Tap "Download filled XLSX" to get the original inventory file filled in with the counted quantities, ready to send by email.
