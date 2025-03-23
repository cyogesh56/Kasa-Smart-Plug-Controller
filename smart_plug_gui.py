import tkinter as tk
import json      # For reading/writing configuration files in JSON format
import os        # To check for file existence
import asyncio   # For asynchronous tasks
import threading # For running async loops in separate threads
import psutil    # For battery info and process checking
import time      
from kasa import Discover         # To discover smart plugs on the network
from kasa.iot import IotPlug        # To control individual plug sockets
import autostart_helper           # Our helper module for autostart functionality

# Config File Location
CONFIG_FILE = "config.json"

def load_config():
    """
    Load configuration settings from a JSON file. If the file exists, load the user's settings,
    ensure that all required keys are present, and write back any updates.
    """
    default_config = {
        "ip_address": "10.0.0.67",
        "plug_number": 0,
        "battery_threshold": 20,
        "apps": ["chrome.exe", "notepad.exe"],
        "check_interval": 10
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as file:
                user_config = json.load(file)
            for key, default_value in default_config.items():
                if key not in user_config:
                    print(f"⚠️ Missing `{key}` in config.json. Using default: {default_value}")
                    user_config[key] = default_value
            with open(CONFIG_FILE, "w") as file:
                json.dump(user_config, file, indent=4)
            return user_config
        except json.JSONDecodeError:
            print("❌ Error: Invalid JSON format in config.json. Loading default settings.")
            return default_config
    return default_config

config = load_config()

# --------------------------
# Collapsible Pane for Settings
# --------------------------
class CollapsiblePane(tk.Frame):
    def __init__(self, parent, title="", subtext="", *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self._is_open = True
        # Header inside the pane's border
        self.header_frame = tk.Frame(self, bg="lightgray")
        self.header_frame.pack(fill="x")
        # Left side: icon, title and sub-label
        header_left = tk.Frame(self.header_frame, bg="lightgray")
        header_left.pack(side="left", fill="x", expand=True)
        self.title_label = tk.Label(header_left, text=title, font=("Arial", 12, "bold"), bg="lightgray")
        self.title_label.pack(anchor="w")
        if subtext:
            self.sub_label = tk.Label(header_left, text=subtext, font=("Arial", 10, "italic"), bg="lightgray")
            self.sub_label.pack(anchor="w")
        # Right side: Toggle button using the requested icons (⇱ for collapse, ⇲ for expand)
        self.toggle_button = tk.Button(self.header_frame, text="⇱", command=self.toggle, font=("Arial", 12), bd=2)
        self.toggle_button.pack(side="right")
        # Container for the collapsible content
        self.container = tk.Frame(self, relief="sunken", borderwidth=1)
        self.container.pack(fill="both", expand=True)

    def toggle(self):
        if self._is_open:
            self.container.forget()
            self.toggle_button.config(text="⇲")
        else:
            self.container.pack(fill="both", expand=True)
            self.toggle_button.config(text="⇱")
        self._is_open = not self._is_open

# --------------------------
# Main Application
# --------------------------
class SmartPlugApp:
    """
    SmartPlugApp encapsulates the Smart Plug Controller's UI and functionality.
    The UI has four sections:
      • Settings (collapsible): "⚙️ Configuration" with sub-label "Get started with one-time configuration"
      • Controls: "👆 Controls" with sub-label "Monitoring and Manual Control"
      • Info: "ℹ️ Information" showing battery and app running status
      • Output: Status messages (with "Status Output:" left-aligned)
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Plug Controller")
        self.running = False         # For monitoring loop
        self.plug = None             # Plug instance (re-discovered as needed)
        self.last_status = None
        self._toggle_in_progress = False
        self.manual_override = False
        self.monitor_task = None
        self.last_plug_state = None  # Holds last reported plug state (True/False)
        self.last_app_names = []     # Holds last reported app status (list) for logging

        # Set up system tray functionality.
        self.tray_icon = None
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        # Create a dedicated async event loop for all async operations.
        if os.name == 'nt':
            self.async_loop = asyncio.ProactorEventLoop()
        else:
            self.async_loop = asyncio.new_event_loop()
        threading.Thread(target=self.run_async_loop, args=(self.async_loop,), daemon=True).start()

        # Schedule continuous Info updates every 1 second.
        asyncio.run_coroutine_threadsafe(self.info_update_loop(), self.async_loop)

        # ===== SETTINGS SECTION (Collapsible) =====
        self.settings_pane = CollapsiblePane(root, title="⚙️ Configuration", subtext="Get started with one-time configuration")
        self.settings_pane.pack(fill="both", expand=True, padx=10, pady=5)
        self.settings_frame = self.settings_pane.container

        tk.Label(self.settings_frame, text="Smart Plug IP Address:").grid(row=0, column=0, sticky="w")
        self.ip_entry = tk.Entry(self.settings_frame, width=20, font=("Arial", 12))
        self.ip_entry.insert(0, config["ip_address"])
        self.ip_entry.grid(row=0, column=1, sticky="w", padx=5, pady=2, ipady=4)

        tk.Label(self.settings_frame, text="Plug Number (0-2):").grid(row=1, column=0, sticky="w")
        self.plug_number = tk.Spinbox(self.settings_frame, from_=0, to=2, width=5, font=("Arial", 12))
        self.plug_number.delete(0, tk.END)
        self.plug_number.insert(0, config["plug_number"])
        self.plug_number.grid(row=1, column=1, sticky="w", padx=5, pady=2, ipady=4)

        tk.Label(self.settings_frame, text="Battery Threshold (%):").grid(row=2, column=0, sticky="w")
        self.battery_threshold = tk.Spinbox(self.settings_frame, from_=1, to=100, width=5, font=("Arial", 12))
        self.battery_threshold.delete(0, tk.END)
        self.battery_threshold.insert(0, config["battery_threshold"])
        self.battery_threshold.grid(row=2, column=1, sticky="w", padx=5, pady=2, ipady=4)

        tk.Label(self.settings_frame, text="Monitored Apps (comma-separated .exe names):").grid(row=3, column=0, sticky="w")
        self.app_entry = tk.Entry(self.settings_frame, width=30, font=("Arial", 12))
        self.app_entry.insert(0, ",".join(config["apps"]))
        self.app_entry.grid(row=3, column=1, sticky="w", padx=5, pady=2, ipady=4)

        tk.Button(self.settings_frame, text="Save Configuration", command=self.save_config, font=("Arial", 12))\
            .grid(row=4, column=0, columnspan=2, pady=5, ipady=4)
        
        # New: Autostart service section inside Settings
        tk.Label(self.settings_frame, text="Set-up always-on service:", font=("Arial", 12)).grid(row=5, column=0, sticky="w", pady=2)
        self.autostart_button = tk.Button(self.settings_frame, text="Start on boot", font=("Arial", 12), command=self.toggle_autostart)
        self.autostart_button.grid(row=5, column=1, sticky="w", padx=5, pady=2, ipady=4)
        if autostart_helper.is_autostart_enabled():
            self.autostart_button.config(text="Stop on boot")
        else:
            self.autostart_button.config(text="Start on boot")

        # ===== CONTROLS SECTION =====
        self.controls_frame = tk.LabelFrame(root, padx=10, pady=10)
        self.controls_frame.pack(fill="both", expand=True, padx=10, pady=5)
        # Header inside Controls frame
        self.controls_header = tk.Frame(self.controls_frame)
        self.controls_header.pack(fill="x", padx=10, pady=2, anchor="w")
        tk.Label(self.controls_header, text="👆", font=("Arial", 12)).pack(side="left")
        tk.Label(self.controls_header, text="Controls", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        tk.Label(self.controls_header, text="Monitoring and Manual Control", font=("Arial", 10, "italic")).pack(side="left", padx=5)
        self.controls_content = tk.Frame(self.controls_frame)
        self.controls_content.pack(fill="both", expand=True)
        self.monitor_button = tk.Button(self.controls_content, text="Start Monitoring", command=self.toggle_monitoring,
                                        width=20, font=("Arial", 12))
        self.monitor_button.grid(row=0, column=0, padx=5, pady=5, ipady=4)
        self.toggle_power_button = tk.Button(self.controls_content, text="Toggle Power", command=self.toggle_power,
                                             width=20, font=("Arial", 12))
        self.toggle_power_button.grid(row=0, column=1, padx=5, pady=5, ipady=4)

        # ===== INFO SECTION =====
        self.info_frame = tk.LabelFrame(root, padx=10, pady=10)
        self.info_frame.pack(fill="both", expand=True, padx=10, pady=5)
        # Header inside Info frame
        self.info_header = tk.Frame(self.info_frame)
        self.info_header.pack(fill="x", padx=10, pady=2, anchor="w")
        tk.Label(self.info_header, text="ℹ️", font=("Arial", 12)).pack(side="left")
        tk.Label(self.info_header, text="Information", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        self.info_content = tk.Frame(self.info_frame)
        self.info_content.pack(fill="both", expand=True)
        self.battery_static_label = tk.Label(self.info_content, text="🔋 Battery Status:", font=("Arial", 12))
        self.battery_static_label.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.battery_dynamic_label = tk.Label(self.info_content, text="--%", font=("Arial", 12))
        self.battery_dynamic_label.grid(row=0, column=1, padx=5, pady=2, sticky="w")
        self.app_static_label = tk.Label(self.info_content, text="💻 App(s) Running:", font=("Arial", 12))
        self.app_static_label.grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.app_dynamic_label = tk.Label(self.info_content, text="No", font=("Arial", 12))
        self.app_dynamic_label.grid(row=1, column=1, padx=5, pady=2, sticky="w")

        # ===== OUTPUT SECTION =====
        tk.Label(root, text="Status Output:", anchor="w").pack(fill="x", padx=10, pady=2)
        self.output_text = tk.Text(root, height=12, width=60)
        self.output_text.pack(padx=10, pady=5)
        self.log("Ready to control the Smart Plug.")
        if autostart_helper.is_autostart_enabled():
            self.log("Autostart is enabled; starting monitoring automatically.")
            self.start_monitoring()
            self.monitor_button.config(text="Stop Monitoring")
            self.autostart_button.config(text="Stop on boot")
        else:
            self.autostart_button.config(text="Start on boot")

    def run_async_loop(self, loop):
        """Run the dedicated asynchronous event loop."""
        asyncio.set_event_loop(loop)
        loop.run_forever()

    def log(self, message):
        """Log a message to the output text area."""
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)

    def save_config(self):
        """Save settings from the UI to the configuration file and update in-memory config."""
        new_config = {
            "ip_address": self.ip_entry.get(),
            "plug_number": int(self.plug_number.get()),
            "battery_threshold": int(self.battery_threshold.get()),
            "apps": [app.strip() for app in self.app_entry.get().split(",") if app.strip()],
            "check_interval": 10
        }
        with open(CONFIG_FILE, "w") as file:
            json.dump(new_config, file, indent=4)
        global config
        config = new_config
        self.log("✅ Configuration saved successfully!")
        if autostart_helper.is_autostart_enabled():
            self.autostart_button.config(text="Stop on boot")
        else:
            self.autostart_button.config(text="Start on boot")

    def toggle_autostart(self):
        """Toggle the always-on service using the helper module."""
        if autostart_helper.is_autostart_enabled():
            if autostart_helper.disable_autostart():
                self.log("Autostart disabled.")
                self.autostart_button.config(text="Start on boot")
            else:
                self.log("Error disabling autostart.")
        else:
            if autostart_helper.enable_autostart():
                self.log("Autostart enabled.")
                self.autostart_button.config(text="Stop on boot")
            else:
                self.log("Error enabling autostart.")

    async def discover_plug(self):
        """Discover the smart plug using the provided IP address."""
        self.log("🔄 Discovering smart plugs...")
        try:
            plug = await Discover.discover_single(self.ip_entry.get())
            await plug.update()
            self.log(f"✅ Found device: {plug.alias}")
            return plug
        except Exception as e:
            self.log(f"❌ Error discovering plug: {e}")
            return None

    async def toggle_manual(self):
        """
        Toggle the power state of the smart plug.
        Always re-discovers the plug so subsequent toggles work reliably.
        Prevents overlapping toggles and closes the plug connection after toggling.
        """
        if self._toggle_in_progress:
            self.log("Toggle already in progress.")
            return
        self._toggle_in_progress = True
        self.manual_override = True
        try:
            self.log("🔄 Discovering smart plugs...")
            self.plug = await Discover.discover_single(self.ip_entry.get())
            await self.plug.update()
            self.log(f"✅ Found device: {self.plug.alias}")

            plug_index = int(self.plug_number.get())
            if hasattr(self.plug, "children") and self.plug.children:
                child_plug = self.plug.children[plug_index]
                await child_plug.update()
                if child_plug.is_on:
                    desired_state = False
                    await child_plug.turn_off()
                else:
                    desired_state = True
                    await child_plug.turn_on()
                await asyncio.sleep(0.5)
                await child_plug.update()
                self.log(f"✅ Plug {plug_index} is now {'ON' if desired_state else 'OFF'}.")
            else:
                self.log("❌ No child sockets detected. This may not be a power strip!")
        except Exception as e:
            self.log(f"❌ Error: {e}")
            self.plug = None
        finally:
            try:
                if self.plug and hasattr(self.plug, "close"):
                    await self.plug.close()
            except Exception as e2:
                self.log(f"❌ Error closing plug: {e2}")
            self._toggle_in_progress = False
            self.manual_override = False

    def toggle_power(self):
        """Schedule the manual toggle coroutine on the shared async loop."""
        asyncio.run_coroutine_threadsafe(self.toggle_manual(), self.async_loop)

    def update_info(self, battery, charging, app_running):
        """Update the Info section labels."""
        if charging:
            self.battery_dynamic_label.config(text=f"⚡ {battery}%")
        else:
            self.battery_dynamic_label.config(text=f"{battery}%")
        if app_running:
            self.app_dynamic_label.config(text="Yes", bg="#71d17c")
        else:
            self.app_dynamic_label.config(text="No", bg=self.root.cget("bg"))

    async def info_update_loop(self):
        """Continuously update the Info section every second."""
        while True:
            battery = psutil.sensors_battery()
            if battery is not None:
                battery_level = battery.percent
                charging = battery.power_plugged
            else:
                battery_level = 0
                charging = False
            app_running = self.is_app_running()
            self.root.after(0, lambda: self.update_info(battery_level, charging, app_running))
            await asyncio.sleep(1)

    async def control_smart_plug(self):
        """
        Main control loop: periodically checks battery level and monitored apps,
        then toggles the plug accordingly.
        Skips automatic control if manual override is active.
        (Battery and app info are updated exclusively via info_update_loop.)
        """
        self.plug = await self.discover_plug()
        if not self.plug:
            return

        plug_index = int(self.plug_number.get())
        if not (hasattr(self.plug, "children") and self.plug.children):
            self.log("❌ No child sockets detected. This may not be a power strip!")
            return

        child_plug = self.plug.children[plug_index]
        if self.last_plug_state is None:
            self.last_plug_state = child_plug.is_on
        if self.last_app_names is None:
            self.last_app_names = []
        while self.running:
            if self.manual_override:
                await asyncio.sleep(config["check_interval"])
                continue
            try:
                await child_plug.update()
                battery = psutil.sensors_battery()
                if battery is None:
                    self.log("❌ No battery information available.")
                    await asyncio.sleep(config["check_interval"])
                    continue
                battery_level = battery.percent
                # Check app status (we revert to generic messages)
                app_running = self.is_app_running()
                if self.last_app_names != app_running:
                    if app_running:
                        self.log("✅ User-specified app(s) are running.")
                    else:
                        self.log("✅ User-specified app(s) are closed.")
                    self.last_app_names = app_running

                if app_running:
                    desired_state = True
                elif battery_level < config["battery_threshold"]:
                    desired_state = True
                elif battery_level >= 100:
                    desired_state = False
                else:
                    desired_state = child_plug.is_on

                if desired_state != child_plug.is_on and self.last_plug_state != desired_state:
                    if desired_state:
                        await child_plug.turn_on()
                        self.log(f"✅ Plug {plug_index} turned ON (Condition met).")
                    else:
                        await child_plug.turn_off()
                        self.log(f"✅ Plug {plug_index} turned OFF (Condition met).")
                    self.last_plug_state = desired_state
                await asyncio.sleep(config["check_interval"])
            except Exception as e:
                self.log(f"❌ Error: {e}")
                await asyncio.sleep(config["check_interval"])

    def start_monitoring(self):
        """Start the monitoring loop by scheduling the control coroutine on the shared async loop."""
        if not self.running:
            self.running = True
            self.monitor_task = asyncio.run_coroutine_threadsafe(self.control_smart_plug(), self.async_loop)
            self.log("🔄 Monitoring started...")

    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.running = False
        self.manual_override = False
        self.log("🛑 Monitoring stopped.")

    def toggle_monitoring(self):
        """Toggle between starting and stopping the monitoring loop and update the button label."""
        if self.running:
            self.stop_monitoring()
            self.monitor_button.config(text="Start Monitoring")
        else:
            self.start_monitoring()
            self.monitor_button.config(text="Stop Monitoring")

    def is_app_running(self):
        """Check if any monitored application is running (case-insensitive)."""
        monitored_apps = [app.lower() for app in config["apps"]]
        for proc in psutil.process_iter(['name']):
            name = proc.info['name']
            if name and name.lower() in monitored_apps:
                return True
        return False

    # --------------------------
    # System Tray (Background Service) Support
    # --------------------------
    def hide_window(self):
        """Hide the main window and create a system tray icon."""
        self.root.withdraw()
        self.create_tray_icon()

    def show_window(self):
        """Show the main window and remove the system tray icon."""
        self.root.deiconify()
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None

    def create_tray_icon(self):
        """Create a system tray icon with menu options to Show and Exit."""
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
            image = Image.open(icon_path)
        except Exception as e:
            print("Error loading tray icon:", e)
            return

        menu = pystray.Menu(
            pystray.MenuItem("Show", lambda: self.show_window()),
            pystray.MenuItem("Exit", lambda: self.exit_app())
        )
        self.tray_icon = pystray.Icon("Smart Plug Controller", image, "Smart Plug Controller", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def exit_app(self):
        """Stop the tray icon and exit the application."""
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()

if __name__ == "__main__":
    import sys
    from PIL import Image
    import pystray
    root = tk.Tk()
    if sys.platform.startswith("win"):
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        try:
            root.iconbitmap(icon_path)
        except Exception as e:
            try:
                icon_path_png = os.path.join(os.path.dirname(__file__), "icon.png")
                icon_image = tk.PhotoImage(file=icon_path_png)
                root.iconphoto(True, icon_image)
            except Exception as e2:
                print("Failed to set icon:", e, e2)
    elif sys.platform == "darwin":
        icon_path_png = os.path.join(os.path.dirname(__file__), "icon.png")
        icon_image = tk.PhotoImage(file=icon_path_png)
        root.iconphoto(True, icon_image)
    app = SmartPlugApp(root)
    root.protocol("WM_DELETE_WINDOW", app.hide_window)
    app.monitor_button.config(command=app.toggle_monitoring)
    root.mainloop()
    app.async_loop.stop()  # Stop the async loop when the GUI is closed.
