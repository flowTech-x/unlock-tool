# 🔓 MI Bootloader Unlock Tool (Android / Termux)

A **phone-only automation tool** to send Xiaomi bootloader unlock requests using **Termux**, with **4 parallel windows** and **only 2 tokens**.

✅ No PC required  
✅ Works fully on Android  
✅ Auto 4 split screens  
✅ Token reuse logic (1 & 3, 2 & 4)

---

## 📱 Requirements

- Android phone  
- Stable internet (**Wi-Fi recommended**)  
- **Termux (F-Droid version only)**  
- Firefox Browser (for cookie extraction)

❌ **Do NOT use Play Store Termux** (deprecated)

---

## 📥 Installation

### 1️⃣ Install Termux

Download from **F-Droid only**:  
👉 https://f-droid.org/packages/com.termux/

Open Termux after install.

---

### 2️⃣ Grant storage permission (one time)

```bash
termux-setup-storage

Allow permission → close Termux → open again.
Verify:

ls ~
You should see:
storage
