import sys
import os

# Windows implementation using winreg:
if sys.platform == "win32":
    import winreg

    def enable_autostart():
        try:
            # Use the absolute path to your executable.
            exe_path = os.path.abspath(sys.argv[0])
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                     r"Software\Microsoft\Windows\CurrentVersion\Run",
                                     0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(reg_key, "SmartPlugController", 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(reg_key)
            return True
        except Exception as e:
            print("Error enabling autostart on Windows:", e)
            return False

    def disable_autostart():
        try:
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                     r"Software\Microsoft\Windows\CurrentVersion\Run",
                                     0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(reg_key, "SmartPlugController")
            winreg.CloseKey(reg_key)
            return True
        except Exception as e:
            print("Error disabling autostart on Windows:", e)
            return False

    def is_autostart_enabled():
        try:
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                     r"Software\Microsoft\Windows\CurrentVersion\Run",
                                     0, winreg.KEY_READ)
            value, regtype = winreg.QueryValueEx(reg_key, "SmartPlugController")
            winreg.CloseKey(reg_key)
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            print("Error checking autostart on Windows:", e)
            return False

# macOS implementation using a LaunchAgent plist:
elif sys.platform == "darwin":
    import plistlib

    def enable_autostart():
        try:
            plist_path = os.path.expanduser("~/Library/LaunchAgents/com.smartplug.controller.plist")
            exe_path = os.path.abspath(sys.argv[0])
            plist_content = {
                "Label": "com.smartplug.controller",
                "ProgramArguments": [exe_path],
                "RunAtLoad": True,
                "KeepAlive": False
            }
            with open(plist_path, "wb") as fp:
                plistlib.dump(plist_content, fp)
            return True
        except Exception as e:
            print("Error enabling autostart on macOS:", e)
            return False

    def disable_autostart():
        try:
            plist_path = os.path.expanduser("~/Library/LaunchAgents/com.smartplug.controller.plist")
            if os.path.exists(plist_path):
                os.remove(plist_path)
            return True
        except Exception as e:
            print("Error disabling autostart on macOS:", e)
            return False

    def is_autostart_enabled():
        plist_path = os.path.expanduser("~/Library/LaunchAgents/com.smartplug.controller.plist")
        return os.path.exists(plist_path)
else:
    # For other platforms, you could raise NotImplementedError or simply return False.
    def enable_autostart():
        raise NotImplementedError("Autostart not implemented on this platform.")

    def disable_autostart():
        raise NotImplementedError("Autostart not implemented on this platform.")

    def is_autostart_enabled():
        return False
