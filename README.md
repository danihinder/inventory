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

### 3. Part Search →

Tap **Part Search →** to look up any item by text or barcode scan.
Shows which warehouses carry the part and their current stock levels.

### 4. Warehouse overview

Tap **Warehouse Overview** to browse all items in any warehouse with their stock levels and age.

### 5. Merge with a colleague

When multiple people are counting simultaneously:

1. Person A: go to **Merge** → tap **Show QR Code** → show the code to the colleague
2. Person B: go to **Merge** → tap **Scan QR Code** → scan Person A's code
3. The counts are merged (quantities added together)

### 6. Export

Once counting is done, the main page shows the list of all counted items.

Tap **Download filled XLSX** to get the original inventory file filled in with the counted quantities, ready to send by email.

Tap **Start New Inventory** to reset and begin a new count.


<img width="30%" height="2036" alt="grafik" src="https://github.com/user-attachments/assets/2542d00f-db7b-4ce6-b180-b362411000bb" />
<img width="30%" height="2286" alt="grafik" src="https://github.com/user-attachments/assets/82a19913-5d63-4421-96ca-e329ba42c420" />
<img width="30%" height="2286" alt="grafik" src="https://github.com/user-attachments/assets/2fffacce-e33b-42c1-ac27-844ede6e4110" />
<img width="30%" height="2286" alt="grafik" src="https://github.com/user-attachments/assets/2ad6863d-6a7d-4cf6-b15d-8cc07743e0f9" />
<img width="30%" height="2226" alt="grafik" src="https://github.com/user-attachments/assets/a9d33fcb-b75b-4c09-95f1-1974d7a32f43" />






