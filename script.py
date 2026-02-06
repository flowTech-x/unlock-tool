#!/usr/bin/env python3

# =========================
# CONFIG
# =========================

SKIP_TIMING = True      # ← change to False for real 00:00 hit
OFFSET_MS = 120         # Mobile-safe offset (80–120ms recommended)

# =========================
# IMPORTS
# =========================

import subprocess, sys, os, time, json, hashlib, random, linecache
from datetime import datetime, timezone, timedelta

import ntplib, pytz, urllib3
from colorama import init, Fore, Style

# =========================
# AUTO INSTALL
# =========================

def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

for p in ("ntplib", "pytz", "urllib3", "colorama"):
    try:
        __import__(p)
    except ImportError:
        install(p)

# =========================
# COLORS
# =========================

init(autoreset=True)
G = Fore.GREEN
Y = Fore.YELLOW
R = Fore.RED
B = Fore.BLUE
GB = Style.BRIGHT + Fore.GREEN

os.system("cls" if os.name == "nt" else "clear")

# =========================
# USER INPUT
# =========================

slot = int(input(G + "[Slot number (1-4)]: " + Fore.RESET))
token_number = 1 if slot in (1, 3) else 2 if slot in (2, 4) else None

if not token_number:
    print(R + "Invalid slot")
    sys.exit(1)

os.system("cls" if os.name == "nt" else "clear")

print(GB + f"ARU_FHL_v070425_token_#{token_number}")

token = linecache.getline("token.txt", token_number).strip()
if not token:
    print(R + "Invalid token line")
    sys.exit(1)

# =========================
# CONSTANTS
# =========================

NTP_SERVERS = [
    "ntp0.ntp-servers.net",
    "ntp1.ntp-servers.net",
    "ntp2.ntp-servers.net"
]

URL_APPLY = "https://sgp-api.buy.mi.com/bbs/api/global/apply/bl-auth"
UA = "okhttp/4.12.0"

# =========================
# HELPERS
# =========================

def generate_device_id():
    seed = f"{random.random()}-{time.time()}"
    return hashlib.sha1(seed.encode()).hexdigest().upper()

def get_ntp_beijing():
    tz = pytz.timezone("Asia/Shanghai")
    c = ntplib.NTPClient()

    for s in NTP_SERVERS:
        try:
            r = c.request(s, version=3, timeout=2)
            bt = datetime.fromtimestamp(r.tx_time, timezone.utc).astimezone(tz)
            print(G + "[Beijing time - NTP]: " + Fore.RESET + bt.strftime("%H:%M:%S.%f"))
            return bt
        except:
            pass

    bt = datetime.now(timezone.utc).astimezone(tz)
    print(Y + "[Beijing time - SYSTEM]: " + Fore.RESET + bt.strftime("%H:%M:%S.%f"))
    return bt

def synced_time(start_bt, start_ts):
    return start_bt + timedelta(seconds=(time.time() - start_ts))

def wait_for_midnight(start_bt, start_ts):
    target = (start_bt + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(milliseconds=OFFSET_MS)

    print(Y + "🎯 Target fire time: " + Fore.RESET + target.strftime("%H:%M:%S.%f"))

    while True:
        now = synced_time(start_bt, start_ts)
        diff = (target - now).total_seconds()

        if diff > 0.01:
            time.sleep(diff - 0.005)
        elif diff > 0:
            pass
        else:
            break

# =========================
# HTTP SESSION
# =========================

class HTTP11Session:
    def __init__(self):
        self.http = urllib3.PoolManager(
            maxsize=10,
            retries=True,
            timeout=urllib3.Timeout(connect=2.0, read=15.0)
        )

    def request(self, method, url, headers=None, body=None):
        try:
            return self.http.request(
                method, url,
                headers=headers,
                body=body,
                preload_content=False
            )
        except Exception as e:
            print(R + "[Network error] " + str(e))
            return None

# =========================
# APPLY + HANDLE
# =========================

def send_apply(session, token, device_id):
    headers = {
        "Cookie": (
            f"new_bbs_serviceToken={token};"
            f"versionCode=500411;"
            f"versionName=5.4.11;"
            f"deviceId={device_id};"
        ),
        "User-Agent": UA,
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip"
    }

    r = session.request(
        "POST",
        URL_APPLY,
        headers=headers,
        body=b'{"is_retry":true}'
    )

    if not r:
        return None

    data = json.loads(r.data.decode())
    r.release_conn()
    return data

def handle_response(resp):
    code = resp.get("code")
    data = resp.get("data", {})
    apply = data.get("apply_result")
    deadline = data.get("deadline_format")

    if code != 0:
        print(R + "❌ API ERROR:", resp)
        return

    if apply == 1:
        print(GB + "✅ APPROVED — unlock granted")
    elif apply == 3:
        print(Y + f"⏳ LIMIT REACHED — try again at {deadline}")
    elif apply == 4:
        print(R + f"⛔ BLOCKED — until {deadline}")
    else:
        print(R + "⚠️ UNKNOWN RESPONSE:", resp)

# =========================
# MAIN
# =========================

def main():
    device_id = generate_device_id()
    session = HTTP11Session()

    start_bt = get_ntp_beijing()
    start_ts = time.time()

    if SKIP_TIMING:
        print(Y + "\n[TEST MODE] Timing skipped — sending immediately\n" + Fore.RESET)
    else:
        wait_for_midnight(start_bt, start_ts)

    now = synced_time(start_bt, start_ts)
    print(G + "[Request @] " + Fore.RESET + now.strftime("%H:%M:%S.%f"))

    resp = send_apply(session, token, device_id)
    if resp:
        print(B + "[Response]: " + Fore.RESET + str(resp))
        handle_response(resp)

# =========================
# ENTRY
# =========================

if __name__ == "__main__":
    main()
