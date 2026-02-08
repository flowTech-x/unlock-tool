#!/usr/bin/env python3

# =========================
# CONFIG - BEIJING TIMES ONLY
# =========================
SKIP_TIMING = False          # False=next midnight, True=manual
MANUAL_FIRE_HOUR = 19        # Beijing hour
MANUAL_FIRE_MIN = 37         # Beijing minute  
MANUAL_FIRE_SEC = 0          # Beijing second
OFFSET_MS = 120              # First shot Xms BEFORE midnight
BURST_INTERVAL_MS = 50       # 50ms between shots

# =========================
# IMPORTS
# =========================
import subprocess, sys, os, time, json, hashlib, random, linecache, signal
from datetime import datetime, timezone, timedelta
import ntplib, pytz, urllib3
from colorama import init, Fore, Style

# =========================
# AUTO INSTALL
# =========================
def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

for p in ("ntplib", "pytz", "urllib3", "colorama"):
    try: __import__(p)
    except: install(p)

# =========================
# SETUP
# =========================
init(autoreset=True)
G, Y, R, B, GB = Fore.GREEN, Fore.YELLOW, Fore.RED, Fore.BLUE, Style.BRIGHT + Fore.GREEN
def clear(): os.system("cls" if os.name == "nt" else "clear")

clear()

# Ctrl+C handler
def signal_handler(sig, frame):
    print(f'\n{R}[!] Interrupted - Clean exit'); sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

# =========================
# BEIJING TIME
# =========================
def show_beijing_time():
    beijing = datetime.now(timezone.utc).astimezone(pytz.timezone("Asia/Shanghai"))
    print(f'{B}[BEIJING] {beijing.strftime("%H:%M:%S.%f")[:-3]}{Fore.RESET}')

# =========================
# USER INPUT
# =========================
show_beijing_time()
slot = int(input(f'{G}[Slot 1-4]: '))
token_num = 1 if slot in (1, 3) else 2 if slot in (2, 4) else None
if not token_num: print(f'{R}Invalid slot'); sys.exit(1)

clear(); show_beijing_time()
print(f'{GB}Token #{token_num}')
token = linecache.getline("token.txt", token_num).strip()
if not token: print(f'{R}No token'); sys.exit(1)

# =========================
# CONSTANTS
# =========================
URL_STATUS = "https://sgp-api.buy.mi.com/bbs/api/global/user/bl-switch/state"
URL_APPLY = "https://sgp-api.buy.mi.com/bbs/api/global/apply/bl-auth"
UA = "okhttp/4.12.0"
NTP_SERVERS = ["ntp0.ntp-servers.net", "ntp1.ntp-servers.net", "ntp2.ntp-servers.net"]

# =========================
# HELPERS
# =========================
def gen_device_id(): return hashlib.sha1(f"{random.random()}-{time.time()}".encode()).hexdigest().upper()

def get_ntp_beijing():
    tz = pytz.timezone("Asia/Shanghai"); c = ntplib.NTPClient()
    for s in NTP_SERVERS:
        try:
            r = c.request(s, version=3, timeout=3)
            bt = datetime.fromtimestamp(r.tx_time, timezone.utc).astimezone(tz)
            print(f'{G}[NTP] {bt.strftime("%H:%M:%S.%f")[:-3]}{Fore.RESET}'); return bt
        except: pass
    bt = datetime.now(timezone.utc).astimezone(tz)
    print(f'{Y}[SYS] {bt.strftime("%H:%M:%S.%f")[:-3]}{Fore.RESET}'); return bt

def synced_time(start_bt, start_ts): 
    return start_bt + timedelta(seconds=(time.time() - start_ts))

# =========================
# PERFECT TIMING
# =========================
def get_target(start_bt):
    if SKIP_TIMING:
        target = start_bt.replace(hour=MANUAL_FIRE_HOUR, minute=MANUAL_FIRE_MIN, 
                                second=MANUAL_FIRE_SEC, microsecond=0)
        print(f'{Y}[MANUAL] {target.strftime("%H:%M:%S Beijing")}')
        return target
    target = (start_bt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    print(f'{Y}[AUTO] Midnight target: {target.strftime("%H:%M:%S Beijing")}')
    return target

def wait_target(start_bt, start_ts, target):
    print(f'{Y}Waiting for exact target...'); last_show = 0
    while True:
        now = synced_time(start_bt, start_ts)
        diff = (target - now).total_seconds()
        if time.time() - last_show > 1: 
            show_beijing_time(); last_show = time.time()
        if diff > 0.01: 
            time.sleep(min(diff-0.005, 0.1))
        elif diff > 0: 
            time.sleep(0.0001)
        else: 
            break

# =========================
# HTTP SESSION
# =========================
class Session:
    def __init__(self):
        self.http = urllib3.PoolManager(
            maxsize=10, 
            retries=urllib3.Retry(total=1, backoff_factor=0),
            timeout=urllib3.Timeout(connect=2.0, read=5.0)
        )
    
    def request(self, method, url, headers=None, body=None):
        try:
            h = headers or {}
            if method == 'POST':
                body = body or b'{"is_retry":true}'
                h.update({
                    'Content-Type': 'application/json',
                    'Content-Length': str(len(body)),
                    'User-Agent': UA,
                    'Connection': 'keep-alive',
                    'Accept-Encoding': 'gzip'
                })
            return self.http.request(method, url, headers=h, body=body, preload_content=False)
        except KeyboardInterrupt: raise
        except: print(f'{R}[HTTP ERR]'); return None

# =========================
# STATUS & FIRE
# =========================
def check_status(session, token, device_id):
    h = {"Cookie": f"new_bbs_serviceToken={token};versionCode=500411;versionName=5.4.11;deviceId={device_id};"}
    r = session.request('GET', URL_STATUS, headers=h)
    if not r: return False
    try:
        data = json.loads(r.data.decode('utf-8')); r.release_conn()
        if data.get("code") == 100004: print(f'{R}Token expired!'); sys.exit(1)
        info = data.get("data", {})
        is_pass, button = info.get("is_pass"), info.get("button_state")
        print(f'{G}[Status]: ', end='')
        if is_pass == 4 and button == 1: print(f'{GB}READY!'); return True
        elif is_pass == 1: print(f'{GB}Already approved!'); sys.exit(0)
        else: print(f'{R}Not ready'); sys.exit(1)
    except: return False

def fire(session, token, device_id):
    h = {"Cookie": f"new_bbs_serviceToken={token};versionCode=500411;versionName=5.4.11;deviceId={device_id};"}
    try:
        r = session.request("POST", URL_APPLY, headers=h)
        if not r: return None
        data = json.loads(r.data.decode('utf-8')); r.release_conn()
        return data
    except KeyboardInterrupt: raise
    except: return None

def handle_resp(resp):
    if resp.get("code") != 0: print(f'{R}❌ API ERR'); return False
    result = resp.get("data", {}).get("apply_result")
    deadline = resp.get("data", {}).get("deadline_format", "")
    if result == 1: print(f'{GB}✅ APPROVED! 🎉'); return True
    elif result == 3: print(f'{Y}⏳ QUOTA: {deadline}'); return False
    elif result == 4: print(f'{R}⛔ BLOCKED: {deadline}'); return False
    else: print(f'{R}❓ {resp}'); return False

# =========================
# MAIN - PERFECT STAGGERED BURST
# =========================
def main():
    device_id = gen_device_id()
    session = Session()
    
    print(f'{Y}🔍 Checking status...'); clear()
    if not check_status(session, token, device_id): return
    
    start_bt = get_ntp_beijing()
    start_ts = time.time()
    target = get_target(start_bt)
    
    # Wait for EXACT target time (midnight/OFFSET_MS)
    wait_target(start_bt, start_ts, target - timedelta(milliseconds=OFFSET_MS))
    
    clear(); show_beijing_time()
    print(f'{GB}🚀 PRECISE 10x BURST STARTS NOW!{Fore.RESET}\n')
    
    success = False
    try:
        for i in range(10):
            # PERFECT TIMING: shot i fires at target + (i * 50ms)
            shot_target = target + timedelta(milliseconds=i * BURST_INTERVAL_MS)
            
            # Wait precisely for THIS shot's exact time
            while True:
                shot_time = synced_time(start_bt, start_ts)
                diff = (shot_target - shot_time).total_seconds()
                if diff <= 0: break
                time.sleep(diff * 0.8)  # Micro-sleep
            
            # FIRE at EXACT millisecond
            now_beijing = datetime.now(timezone.utc).astimezone(pytz.timezone("Asia/Shanghai"))
            print(f'[{i+1}/10] ', end='')
            resp = fire(session, token, device_id)
            
            if resp:
                print(f'{B}@{now_beijing.strftime("%H:%M:%S.%f")}{Fore.RESET} ', end='')
                if handle_resp(resp):
                    success = True
                    print(f'\n{GB}🎉 SUCCESS on shot {i+1}!')
                    break
            
    except KeyboardInterrupt: 
        print(f'\n{Y}[!] Burst interrupted')
    
    if not success:
        print(f'{R}\n❌ Burst complete - No approval')
    print(f'{Y}[*] Next quota: 00:00 Beijing tomorrow')

if __name__ == "__main__": main()
