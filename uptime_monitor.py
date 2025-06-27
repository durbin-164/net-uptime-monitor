import subprocess
import time
import datetime
import threading

# List of reliable hosts to ping (Google DNS, Cloudflare, Level 3)
TARGETS = ["8.8.8.8", "1.1.1.1", "4.2.2.1"]

# Configuration
PING_INTERVAL = 5  # seconds
FAILURE_THRESHOLD = 3  # all targets must fail
LOG_FILE = "net_uptime_log.txt"
GATEWAY_IP = "192.168.0.1"  # Adjust to your local gateway

def log_event(event: str):
    with open(LOG_FILE, "a") as f:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {event}\n")

def is_reachable(ip: str) -> bool:
    try:
        subprocess.check_output(["ping", "-c", "1", "-W", "1", ip], stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def monitor_connection():
    in_outage = False
    outage_start = None

    while True:
        failures = 0

        # Check gateway first to rule out LAN issues
        if not is_reachable(GATEWAY_IP):
            log_event("LAN disconnected or Gateway unreachable.")
            time.sleep(PING_INTERVAL)
            continue

        # Check internet hosts
        for target in TARGETS:
            if not is_reachable(target):
                failures += 1

        if failures >= FAILURE_THRESHOLD:
            if not in_outage:
                in_outage = True
                outage_start = datetime.datetime.now()
                log_event("Internet connection DOWN")
                print("🔴 Internet connection DOWN")
        else:
            if in_outage:
                in_outage = False
                outage_end = datetime.datetime.now()
                duration = outage_end - outage_start
                log_event(f"Internet connection RESTORED (downtime: {duration})")
                print(f"🟢 Internet connection RESTORED (downtime: {duration})")

        time.sleep(PING_INTERVAL)

# Run the monitoring in a background thread
monitor_thread = threading.Thread(target=monitor_connection)
monitor_thread.daemon = True
monitor_thread.start()

# Keep the main program running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nExiting...")

