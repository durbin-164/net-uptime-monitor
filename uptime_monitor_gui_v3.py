import subprocess
import platform
import time
import datetime
import threading
import tkinter as tk
from tkinter import scrolledtext
import pygame
import re

# --- Configuration ---
TARGETS = {
    "8.8.8.8": "Google DNS",
    "1.1.1.1": "Cloudflare DNS",
    "4.2.2.1": "Level3 DNS"
}
PING_INTERVAL = 5  # seconds
FAILURE_THRESHOLD = 3
LOG_FILE = "net_uptime_gui_log.txt"
IS_WINDOWS = platform.system().lower() == "windows"

# Sound
pygame.mixer.init()
net_up_sound = pygame.mixer.Sound("sounds/button-2.wav")
net_down_sound = pygame.mixer.Sound("sounds/button-3.wav")

#Font
# emoji_font = None
# system = platform.system().lower()
# if system == "windows":
#     emoji_font = ("Segoe UI Emoji", 16)
# elif system == "darwin":  # macOS
#     emoji_font = ("Apple Color Emoji", 16)
# else:
#     # Linux fallback, you may need to install Noto Color Emoji font
#     emoji_font = ("Noto Color Emoji", 16)

# # emoji_font = ("Noto Color Emoji", "DejaVu Sans", 16)

# print("emoji font",emoji_font)


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
    
def get_ping_time(host):
    IS_WINDOWS = platform.system().lower() == "windows"
    try:
        if IS_WINDOWS:
            # Windows ping output looks like: "Minimum = 20ms, Maximum = 20ms, Average = 20ms"
            output = subprocess.check_output(["ping", "-n", "1", host], text=True, stderr=subprocess.DEVNULL)
            # Find Average time in output
            match = re.search(r"Average = (\d+)ms", output)
            if match:
                return int(match.group(1))
        else:
            # Linux/macOS
            output = subprocess.check_output(["ping", "-c", "1", "-W", "1", host], text=True, stderr=subprocess.DEVNULL)
            # Find 'time=XX ms' in output
            match = re.search(r"time=([\d\.]+) ms", output)
            if match:
                return float(match.group(1))
    except subprocess.CalledProcessError:
        return None

def get_default_gateway():
    try:
        if IS_WINDOWS:
            output = subprocess.check_output("ipconfig", text=True)
            for line in output.splitlines():
                if "Default Gateway" in line and ":" in line:
                    return line.split(":")[1].strip()
        else:
            output = subprocess.check_output(["ip", "route"], text=True)
            for line in output.splitlines():
                if line.startswith("default"):
                    parts = line.split()
                    return parts[2]
    except Exception as e:
        print(e)
        return None

def update_server_statuses():
    for ip, label in target_labels.items():
        ping_time = get_ping_time(ip)
        # print(f"{ip}: time: {ping_time}")
        # if is_reachable(ip):
        if ping_time and ping_time < 300:
            # label.config(text=f"[🟢] {ip} ({TARGETS[ip]})", fg="green", font=emoji_font)
            label.config(text=f"[{ping_time}] {ip} ({TARGETS[ip]})", fg="green")
        else:
            # label.config(text=f"[🔴] {ip} ({TARGETS[ip]})", fg="red", font=emoji_font)
            label.config(text=f"[{ping_time}] {ip} ({TARGETS[ip]})", fg="red")
    root.after(PING_INTERVAL * 1000, update_server_statuses)

# Adding log seach

from tkinter import simpledialog, messagebox

def load_filtered_log():
    date_str = simpledialog.askstring("Filter Log", "Enter date (YYYY-MM-DD):")
    if not date_str:
        return

    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        messagebox.showerror("Error", "Log file not found.")
        return

    filtered = [line for line in lines if line.startswith(f"[{date_str}")]
    if not filtered:
        messagebox.showinfo("No Logs", f"No logs found for {date_str}")
        return

    show_log_popup(filtered)

def show_log_popup(lines):
    popup = tk.Toplevel(root)
    popup.title("Filtered Log View")
    popup.geometry("600x400")

    text_area = scrolledtext.ScrolledText(popup, wrap=tk.WORD, font=("Consolas", 10))
    text_area.pack(expand=True, fill="both")

    text_area.insert(tk.END, "".join(lines))
    text_area.config(state="disabled")

# log search

def monitor():
    in_outage = False
    outage_start = None
    gateway = get_default_gateway() or "192.168.0.1"
    log_event(f"Detected gateway: {gateway}")

    while True:
        if not is_reachable(gateway):
            log_event("LAN issue: Gateway unreachable")
            status_var.set("⚠️ Gateway Down")
            net_down_sound.play()
            time.sleep(PING_INTERVAL)
            continue

        failures = sum(1 for t in TARGETS if not is_reachable(t))

        if failures >= FAILURE_THRESHOLD:
            if not in_outage:
                in_outage = True
                outage_start = datetime.datetime.now()
                log_event("🔴 Internet DOWN")
                status_var.set("🔴 DOWN")
                net_down_sound.play()

        else:
            if in_outage:
                in_outage = False
                duration = datetime.datetime.now() - outage_start
                log_event(f"🟢 Internet RESTORED after {duration}")
                net_up_sound.play()

            status_var.set("🟢 UP")

        time.sleep(PING_INTERVAL)

# --- GUI Setup ---
root = tk.Tk()
root.title("Net Uptime Monitor (Python)")
root.geometry("640x500")

status_var = tk.StringVar(value="Checking...")

tk.Label(root, text="Internet Status:", font=("Arial", 14)).pack(pady=5)
tk.Label(root, textvariable=status_var, font=("Arial", 16), fg="blue").pack()

tk.Label(root, text="Server Status:", font=("Arial", 12, "bold")).pack(pady=5)

target_labels = {}
for ip in TARGETS:
    lbl = tk.Label(root, text=f"[...] {ip} ({TARGETS[ip]})", font=("Arial", 11))
    lbl.pack()
    target_labels[ip] = lbl

log_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, state='disabled', font=("Consolas", 10), height=12)
log_text.pack(expand=True, fill='both', padx=10, pady=10)
# for log seach
tk.Button(root, text="📂 Load Filtered Log", command=load_filtered_log).pack(pady=5)

# --- Start Threads ---
threading.Thread(target=monitor, daemon=True).start()
root.after(1000, update_server_statuses)

# --- Run App ---
root.mainloop()
