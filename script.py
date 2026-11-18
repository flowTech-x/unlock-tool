#!/usr/bin/env python3

# =====================================================================
# MI Bootloader Unlock Tool  -  Improved Edition
# Original: github.com/flowTech-x/unlock-tool
# =====================================================================

# =========================
# CONFIG
# =========================
SKIP_TIMING        = False   # False=auto-wait for next Beijing midnight
MANUAL_FIRE_HOUR   = 0       # Used only if SKIP_TIMING = True
MANUAL_FIRE_MIN    = 0
MANUAL_FIRE_SEC    = 0
OFFSET_MS          = 120     # Fire this many ms BEFORE midnight
BURST_INTERVAL_MS  = 50      # Gap between burst shots
BURST_COUNT        = 20      # Number of rapid shots per session (was 10)
RETRY_ON_FAIL      = True    # Retry the full burst next midnight if quota missed
LOG_FILE           = "unlock_log.txt"  # Set to None to disable file logging

# =========================
# BOOTSTRAP INSTALLS
# =========================
import subprocess, sys, os, time, json, hashlib, random, linecache, signal, re
from datetime import datetime, timezone, timedelta

def _install(pkg):
    print(f"[setup] Installing {pkg}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", pkg])

for _p in ("ntplib", "pytz", "urllib3", "colorama"):
    try:
        __import__(_p)
    except ImportError:
        _install(_p)

import ntplib, pytz, urllib3
from colorama import init, Fore, Style

# =========================
# SETUP
# =========================
init(autoreset=True)
G  = Fore.GREEN
Y  = Fore.YELLOW
R  = Fore.RED
B  = Fore.BLUE
C  = Fore.CYAN
M  = Fore.MAGENTA
GB = Style.BRIGHT + Fore.GREEN
YB = Style.BRIGHT + Fore.YELLOW
RB = Style.BRIGHT + Fore.RED
CB = Style.BRIGHT + Fore.CYAN

TZ_BJ = pytz.timezone("Asia/Shanghai")

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def signal_handler(sig, frame):
    print(f"\n{Y}[!] Ctrl+C — clean exit")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# =========================
# LOGGING
# =========================
_log_lines = []

def log(msg: str, color: str = ""):
    """Print with color and optionally write to log file (stripped of ANSI)."""
    print(f"{color}{msg}{Fore.RESET}" if color else msg)
    if LOG_FILE:
        clean = re.sub(r"\x1b\[[0-9;]*m", "", msg)
        ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {clean}\n")

# =========================
# BEIJING TIME
# =========================
def beijing_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(TZ_BJ)

def show_clock(label: str = "BEIJING"):
    bt = beijing_now()
    print(f"{B}[{label}] {bt.strftime('%H:%M:%S.%f')[:-3]}{Fore.RESET}")

# =========================
# TOKEN LOADING
# =========================
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.txt")

def load_tokens() -> list:
    """Load all non-empty tokens from token.txt."""
    if not os.path.exists(TOKEN_FILE):
        log(f"token.txt not found at: {TOKEN_FILE}", RB)
        sys.exit(1)
    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        tokens = [line.strip() for line in f if line.strip()]
    return tokens

def validate_token_format(token: str) -> bool:
    """Rough sanity check: token should be a URL-encoded string ≥50 chars."""
    return len(token) >= 50

# =========================
# USER INPUT / STARTUP
# =========================
def select_token(tokens: list) -> tuple:
    """Display token menu and return (token_num, token_value)."""
    n = len(tokens)
    clear()
    show_clock("STARTUP")
    print(f"\n{CB}╔══════════════════════════════════════╗")
    print(f"{CB}║   MI Bootloader Unlock Tool           ║")
    print(f"{CB}╚══════════════════════════════════════╝{Fore.RESET}\n")
    print(f"{Y}  Tokens loaded: {G}{n}{Fore.RESET}")
    for i, tok in enumerate(tokens, 1):
        preview = tok[:12] + "..." + tok[-8:] if len(tok) > 20 else tok
        valid   = f"{G}✓" if validate_token_format(tok) else f"{R}✗ (too short!)"
        print(f"    {Y}[{i}]{Fore.RESET} {preview}  {valid}")
    print()

    while True:
        try:
            choice = input(f"{G}  Select token number (1-{n}): {Fore.RESET}").strip()
            idx    = int(choice)
            if 1 <= idx <= n:
                return idx, tokens[idx - 1]
        except (ValueError, KeyboardInterrupt):
            pass
        print(f"  {R}Invalid — enter a number between 1 and {n}")

# =========================
# NTP SYNC
# =========================
NTP_SERVERS = [
    "ntp0.ntp-servers.net",
    "ntp1.ntp-servers.net",
    "ntp2.ntp-servers.net",
    "time.cloudflare.com",
    "pool.ntp.org",
]

def get_ntp_beijing() -> tuple:
    """Return (synced beijing datetime, local monotonic timestamp)."""
    c = ntplib.NTPClient()
    for srv in NTP_SERVERS:
        try:
            r  = c.request(srv, version=3, timeout=3)
            bt = datetime.fromtimestamp(r.tx_time, timezone.utc).astimezone(TZ_BJ)
            log(f"[NTP ✓] {srv}  →  {bt.strftime('%H:%M:%S.%f')[:-3]}", G)
            return bt, time.monotonic()
        except Exception:
            pass
    log("[NTP ✗] All NTP servers failed — using system clock (less accurate)", Y)
    bt = beijing_now()
    return bt, time.monotonic()

def synced_now(start_bt: datetime, start_mono: float) -> datetime:
    """Return current Beijing time computed from NTP anchor + elapsed monotonic time."""
    return start_bt + timedelta(seconds=(time.monotonic() - start_mono))

# =========================
# TARGET / COUNTDOWN
# =========================
def get_target(start_bt: datetime) -> datetime:
    if SKIP_TIMING:
        t = start_bt.replace(hour=MANUAL_FIRE_HOUR,
                              minute=MANUAL_FIRE_MIN,
                              second=MANUAL_FIRE_SEC,
                              microsecond=0)
        log(f"[MANUAL] Target: {t.strftime('%H:%M:%S Beijing')}", Y)
        return t
    t = (start_bt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    log(f"[AUTO]   Target midnight: {t.strftime('%Y-%m-%d %H:%M:%S Beijing')}", Y)
    return t

def countdown(start_bt: datetime, start_mono: float, target: datetime):
    """Blocking countdown with live display. Returns when target is reached."""
    log("Waiting for target — press Ctrl+C to exit", Y)
    last_print = 0
    while True:
        now  = synced_now(start_bt, start_mono)
        diff = (target - now).total_seconds()
        if time.monotonic() - last_print >= 1:
            h, rem = divmod(int(diff), 3600)
            m, s   = divmod(rem, 60)
            print(f"\r{B}  ⏳ {h:02d}h {m:02d}m {s:02d}s  │  {now.strftime('%H:%M:%S.%f')[:-3]} BJT   {Fore.RESET}", end="", flush=True)
            last_print = time.monotonic()
        if diff <= 0.01:
            print()
            break
        elif diff > 0.1:
            time.sleep(min(diff - 0.05, 0.5))
        else:
            time.sleep(0.0001)

# =========================
# API CONSTANTS & SESSION
# =========================
URL_STATUS = "https://sgp-api.buy.mi.com/bbs/api/global/user/bl-switch/state"
URL_APPLY  = "https://sgp-api.buy.mi.com/bbs/api/global/apply/bl-auth"
UA         = "okhttp/4.12.0"

def gen_device_id() -> str:
    return hashlib.sha1(f"{random.random()}-{time.monotonic()}".encode()).hexdigest().upper()

class Session:
    def __init__(self):
        self.http = urllib3.PoolManager(
            maxsize=20,
            retries=urllib3.Retry(total=0),
            timeout=urllib3.Timeout(connect=2.0, read=5.0),
        )

    def _cookie(self, token: str, device_id: str) -> dict:
        return {"Cookie": f"new_bbs_serviceToken={token};versionCode=500411;versionName=5.4.11;deviceId={device_id};",
                "User-Agent": UA}

    def status(self, token: str, device_id: str):
        try:
            r    = self.http.request("GET", URL_STATUS, headers=self._cookie(token, device_id))
            data = json.loads(r.data.decode("utf-8"))
            r.release_conn()
            return data
        except KeyboardInterrupt:
            raise
        except Exception as e:
            return {"_error": str(e)}

    def apply(self, token: str, device_id: str):
        h = self._cookie(token, device_id)
        h.update({"Content-Type": "application/json",
                   "Content-Length": "16",
                   "Connection": "keep-alive",
                   "Accept-Encoding": "gzip"})
        try:
            r    = self.http.request("POST", URL_APPLY, headers=h, body=b'{"is_retry":true}', preload_content=False)
            data = json.loads(r.data.decode("utf-8"))
            r.release_conn()
            return data
        except KeyboardInterrupt:
            raise
        except Exception as e:
            return {"_error": str(e)}

# =========================
# STATUS CHECK
# =========================
def check_status(session: Session, token: str, device_id: str) -> bool:
    data = session.status(token, device_id)
    if "_error" in data:
        log(f"[Status] Network error: {data['_error']}", R)
        return False
    code = data.get("code")
    if code == 100004:
        log("[Status] ❌  Token expired — please refresh your cookie", RB)
        sys.exit(1)
    if code != 0:
        log(f"[Status] Unexpected code {code}: {data.get('msg','')}", R)
        return False
    info   = data.get("data", {})
    is_pass = info.get("is_pass")
    button  = info.get("button_state")
    deadline = info.get("deadline_format", "")

    if is_pass == 1:
        log("[Status] ✅  Already APPROVED — unlock is active!", GB)
        sys.exit(0)
    elif is_pass == 4 and button == 1:
        log("[Status] ✅  READY — eligible to claim quota tonight", GB)
        return True
    elif is_pass == 4 and button == 0:
        log(f"[Status] ⏳  Cooldown — unlock quota locked until: {deadline}", Y)
        return False
    else:
        log(f"[Status] ❓  Unknown state  is_pass={is_pass}  button={button}", R)
        return False

# =========================
# BURST FIRE
# =========================
def handle_resp(resp: dict, shot: int) -> bool:
    if "_error" in resp:
        log(f"  [{shot}/{BURST_COUNT}] ⚠  {resp['_error']}", Y)
        return False
    if resp.get("code") != 0:
        log(f"  [{shot}/{BURST_COUNT}] ❌  API code {resp.get('code')}  {resp.get('msg','')}", R)
        return False
    result   = resp.get("data", {}).get("apply_result")
    deadline = resp.get("data", {}).get("deadline_format", "")
    if result == 1:
        log(f"  [{shot}/{BURST_COUNT}] 🎉  APPROVED!", GB)
        return True
    elif result == 3:
        log(f"  [{shot}/{BURST_COUNT}] ⏳  QUOTA FULL — {deadline}", Y)
        return False
    elif result == 4:
        log(f"  [{shot}/{BURST_COUNT}] ⛔  BLOCKED — {deadline}", R)
        return False
    else:
        log(f"  [{shot}/{BURST_COUNT}] ❓  apply_result={result}  raw={resp}", R)
        return False

def burst(session: Session, token: str, device_id: str,
          start_bt: datetime, start_mono: float, target: datetime) -> bool:
    log(f"\n{GB}🚀  BURST FIRING — {BURST_COUNT} shots @ {BURST_INTERVAL_MS}ms intervals\n", GB)
    success = False
    for i in range(BURST_COUNT):
        shot_target = target + timedelta(milliseconds=i * BURST_INTERVAL_MS)
        # Precision wait for this specific shot
        while True:
            diff = (shot_target - synced_now(start_bt, start_mono)).total_seconds()
            if diff <= 0:
                break
            time.sleep(diff * 0.8)
        fire_time = beijing_now()
        resp      = session.apply(token, device_id)
        t_str     = fire_time.strftime("%H:%M:%S.%f")[:-3]
        if resp:
            print(f"  {B}@{t_str}{Fore.RESET} ", end="")
            if handle_resp(resp, i + 1):
                success = True
                break
        else:
            log(f"  [{i+1}/{BURST_COUNT}] ⚠  No response @{t_str}", Y)
    return success

# =========================
# WINDOWS TOAST NOTIFICATION
# =========================
def _notify(title: str, msg: str):
    """Non-blocking Windows 10/11 toast notification (silent if unsupported)."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBeep(0)   # simple beep
    except Exception:
        pass
    try:
        ps = (
            f"[void][System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');"
            f"$n=New-Object System.Windows.Forms.NotifyIcon;"
            f"$n.Icon=[System.Drawing.SystemIcons]::Information;"
            f"$n.Visible=$true;"
            f"$n.ShowBalloonTip(8000,'{title}','{msg}',"
            f"[System.Windows.Forms.ToolTipIcon]::Info);"
            f"Start-Sleep 10; $n.Dispose()"
        )
        subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps])
    except Exception:
        pass

# =========================
# MAIN
# =========================
def main():
    tokens            = load_tokens()
    token_num, token  = select_token(tokens)

    if not validate_token_format(token):
        log(f"\n⚠  Token #{token_num} looks very short — it may be invalid or truncated.", Y)
        input("   Press Enter to continue anyway, or Ctrl+C to exit...")

    log(f"\n{Y}  Checking account status with Xiaomi servers...", Y)
    device_id = gen_device_id()
    session   = Session()

    if not check_status(session, token, device_id):
        log("Account is not ready. Exiting.", R)
        sys.exit(1)

    # --- NTP sync ---
    print()
    start_bt, start_mono = get_ntp_beijing()
    target               = get_target(start_bt)

    # --- Countdown ---
    fire_target = target - timedelta(milliseconds=OFFSET_MS)
    print()
    countdown(start_bt, start_mono, fire_target)

    # --- Burst ---
    success = burst(session, token, device_id, start_bt, start_mono, target)

    # --- Result ---
    print()
    if success:
        log("✅  Unlock quota claimed! Open the Mi Unlock app to proceed.", GB)
        _notify("MI Unlock Tool", f"Token #{token_num}: APPROVED! Open Mi Unlock app.")
    else:
        log("❌  Burst complete — quota not claimed this round.", RB)
        log(f"   Next window: 00:00:00 Beijing tomorrow (21:30 IST)", Y)
        _notify("MI Unlock Tool", f"Token #{token_num}: Missed quota. Try again tomorrow.")

        if RETRY_ON_FAIL:
            log(f"\n  Auto-retry enabled — waiting for NEXT midnight burst...\n", C)
            main_loop(session, token, token_num, device_id)

def main_loop(session, token, token_num, device_id):
    """Keep retrying each midnight until approved."""
    attempt = 1
    while True:
        attempt += 1
        log(f"\n{CB}  ─── Attempt #{attempt} ───\n", CB)
        start_bt, start_mono = get_ntp_beijing()
        target               = get_target(start_bt)
        fire_target          = target - timedelta(milliseconds=OFFSET_MS)
        countdown(start_bt, start_mono, fire_target)
        success = burst(session, token, device_id, start_bt, start_mono, target)
        if success:
            log("✅  Approved on attempt #{attempt}!", GB)
            _notify("MI Unlock Tool", f"Token #{token_num}: APPROVED on attempt #{attempt}!")
            break
        log(f"❌  Attempt #{attempt} missed. Retrying tomorrow.", Y)

if __name__ == "__main__":
    main()
