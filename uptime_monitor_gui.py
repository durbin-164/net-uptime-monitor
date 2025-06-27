import subprocess
import platform
import time
import datetime
import threading
import tkinter as tk
from tkinter import scrolledtext

# --- Configuration ---
TARGETS = ["8.8.8.8", "1.1.1.1", "4.2.2.1"]
PING_INTERVAL = 5  # seconds
FAILURE_THRESHOLD = 3
LOG_FILE = "net_uptime_gui_log.txt"
IS_WINDOWS = platform.system().lower() == "windows"

# --- Functions ---
def log_event(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    with open(LOG_FILE, "a") as f:
        f.write(log_entry)
    gui_log(log_entry)

def gui_log(text):
    log_text.config(state='normal')
    log_text.insert(tk.END, text)
    log_text.yview(tk.END)
    log_text.config(state='disabled')

def is_reachable(host):
    try:
        if IS_WINDOWS:
            subprocess.check_output(["ping", "-n", "1", "-w", "1000", host],
                                    stderr=subprocess.DEVNULL,
                                    stdin=subprocess.DEVNULL)
        else:
            subprocess.check_output(["ping", "-c", "1", "-W", "1", host],
                                    stderr=subprocess.DEVNULL,
                                    stdin=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        log_event("Ping command not found. Ensure it's installed.")
        return False

def get_default_gateway():
    try:
        if IS_WINDOWS:
            output = subprocess.check_output("ipconfig", text=True)
            for line in output.splitlines():
                if "Default Gateway" in line and ":" in line:
                    return line.split(":")[1].strip()
        else:
            output = subprocess.check_output("ip route", text=True)
            for line in output.splitlines():
                if line.startswith("default"):
                    parts = line.split()
                    return parts[2]
    except Exception:
        return None

def monitor():
    in_outage = False
    outage_start = None
    print(get_default_gateway())
    gateway = get_default_gateway() or "192.168.0.1"
    log_event(f"Detected gateway: {gateway}")

    while True:
        if not is_reachable(gateway):
            log_event("LAN issue: Gateway unreachable")
            time.sleep(PING_INTERVAL)
            continue

        failures = sum(1 for t in TARGETS if not is_reachable(t))

        if failures >= FAILURE_THRESHOLD:
            if not in_outage:
                in_outage = True
                outage_start = datetime.datetime.now()
                log_event("🔴 Internet DOWN")
                status_var.set("🔴 DOWN")
        else:
            if in_outage:
                in_outage = False
                duration = datetime.datetime.now() - outage_start
                log_event(f"🟢 Internet RESTORED after {duration}")
                status_var.set("🟢 UP")
            elif status_var.get() != "🟢 UP":
                status_var.set("🟢 UP")

        time.sleep(PING_INTERVAL)

# --- GUI Setup ---
root = tk.Tk()
root.title("Net Uptime Monitor (Python)")
root.geometry("600x400")

status_var = tk.StringVar(value="Checking...")

tk.Label(root, text="Internet Status:", font=("Arial", 14)).pack(pady=5)
tk.Label(root, textvariable=status_var, font=("Arial", 16), fg="blue").pack()

log_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, state='disabled', font=("Consolas", 10))
log_text.pack(expand=True, fill='both', padx=10, pady=10)

# --- Start Monitor Thread ---
threading.Thread(target=monitor, daemon=True).start()

# --- Run ---
root.mainloop()
