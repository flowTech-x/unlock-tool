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
https://f-droid.org/packages/com.termux/

Open Termux after install.

---

### 2️⃣ Grant storage permission (one time)

```bash
termux-setup-storage
```
Allow permission → close Termux → open again.

Verify:
```bash
ls ~
```

You should see:

storage

3️⃣ Go to internal storage
```bash
cd ~/storage/shared
```
```bash
mkdir script
```
```bash
cd script
```
4️⃣ Clone the repository
```bash
pkg install git -y
```
```bash
git clone https://github.com/flowTech-x/unlock-tool.git
```
```bash
cd unlock-tool
```


Check files:
```bash
ls
```


Expected:

script.py
start_4.sh
token.txt
timeshift.txt

5️⃣ Install dependencies
```bash
pkg install python tmux -y
```
```bash
pip install requests ntplib pytz urllib3 icmplib colorama
```
🔐 Getting Xiaomi Token (Phone Only)
Use Firefox + Cookie Editor

Install Firefox Browser
Create a App Clone of Firefox Browser

Login Mi Account in Both Main Firefox and Clone One
👉India Mi Community Link - https://new-ams.c.mi.com/global/forum-type/Redmi%20Phone
👉Global Mi Community Link - https://c.mi.com/global/


Install Cookie-Editor addon
👉 https://addons.mozilla.org/firefox/addon/cookie-editor/

Open Cookie-Editor

Search for:

new_bbs_serviceToken


Copy VALUE only

🗝️ Add Tokens (Only 2 Lines)

Open token file:
```bash
nano token.txt
```

Paste:

TOKEN_ACCOUNT_1
TOKEN_ACCOUNT_2


Save:

CTRL + O → Enter
CTRL + X

🔁 Token Mapping Logic
Slot	Token Used
1	Token line 1
2	Token line 2
3	Token line 1
4	Token line 2

➡️ No need to paste the same token multiple times.

▶️ Run the Tool (IMPORTANT)

⚠️ Android shared storage is noexec, so do NOT use ./

✅ Correct command:
```bash
bash start_4.sh
```


or
```bash
ash start_4.sh
```

🖥️ What Happens Next

tmux opens automatically

Screen splits into 4 boxes

Each box runs the script

Each box asks:

[Slot number (1-4)]:

Enter:

Box 1 → 1

Box 2 → 2

Box 3 → 3

Box 4 → 4

📊 Live Logs

Each box shows:

Beijing time (NTP or system fallback)

Waiting status

Request send time

API response

🧠 Notes & Tips

Wi-Fi recommended (mobile data may block NTP)

If NTP fails, script automatically uses system time

Do NOT close Termux while running

Detach tmux safely:

CTRL + B → D


Re-attach:

tmux attach

❗ Common Errors & Fixes
❌ permission denied

✅ Use:

bash start_4.sh

❌ Cookie expired

✅ Re-login on mi.com → copy token again

❌ Time sync failed

✅ Already handled (system time fallback)

⚠️ Disclaimer

This project is for educational purposes only.
Unlocking bootloaders may violate manufacturer policies.
Use at your own risk.

⭐ Support

If this tool helped you:

Star the repo ⭐

Share with others

Report issues via GitHub

📌 Maintained by

flowTech-x
