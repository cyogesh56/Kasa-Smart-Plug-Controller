🤖 # Smart Plug Controller GUI App

> **Note:** This application and its source code were generated using AI assistance. Always review and test thoroughly before deploying or using in critical applications.

> **Also:** I have bare-minimum knowledge of Python and have created this as a hobby project. If you have knowledge of Python, I welcome you to improve the UX and functionalities.

## Overview

The **Smart Plug Controller GUI** is a Python-based, user-friendly graphical application designed to manage and automate smart plug devices effortlessly. Built using Tkinter for simplicity, this tool allows users to control their smart plugs manually or automatically based on system battery levels and application usage.

---

## Features

- **Easy Configuration:** Modify settings such as IP address, plug index, battery threshold, and monitored applications directly through the intuitive GUI.
- **Automatic Monitoring:** Continuously checks your system battery status and specified applications, automatically toggling the smart plug as needed.
- **Manual Control:** Quickly switch plug states via a visual toggle in the GUI.
- **Real-time Status Updates:** Provides clear, detailed logs and notifications about plug status, battery levels, and monitored applications.
- **Persistent Settings:** User configurations are saved in a JSON file, ensuring your settings persist between sessions.
- **Start/Stop on System Boot:** If you enable Start on boot, it will add the app to your startup apps and whenever your system boots, it will start monitoring automatically.
- **System Tray Support:** When you close the app, it closes to system tray so you can open it faster and check the status. Only drawback for now is that you have to exit it from system tray.

---

## Installation & Usage

### Requirements

Before using the app, ensure Python and the following dependencies are installed:

```sh
pip install python-kasa psutil pyinstaller
```

### Instructions & Usage

- For fast and easy usage, download the "Smart Plug Controller.exe" from the releases and configure it accordingly (see Configuration section).
- If you would like to build it by yourself see the information below:

### Building and Running the Application

To build and run this application yourself, follow these steps:

1. Clone this repository:

```sh
git clone https://github.com/your-repository-link.git
cd your-repository-folder
```

2. Install required dependencies:

```sh
pip install python-kasa psutil pyinstaller
```

3. Run the main application:

```sh
python smart_plug_gui.py
```

### Building a Windows Executable

To create a standalone executable for Windows, follow these steps:

1. Ensure `pyinstaller` is installed:

```sh
pip install pyinstaller
```

2. Navigate to the project folder and ensure you have the icons (whatever icon you want to use) as "icon.ico" and "icon.png" in the same folder as smart\_*plug\_*gui.py
3. &#x20;Then run the following command:

```sh
pyinstaller --onefile --noconsole --name "Smart Plug Controller" --icon "icon.ico" --add-data "autostart_helper.py;." --add-data "config.json;." --add-data "icon.png;." smart_plug_gui.py
```

3. Once complete, locate the executable in the `dist` folder.

### Configuration

When launching for the first time:

- Input your smart plug's IP address.
- Select the appropriate plug number (for multi-socket smart plugs).
- Set the battery threshold percentage.
- Specify applications to monitor (comma-separated list of `.exe` filenames).
- Save the configuration.

### Operation

- **Start Monitoring**: Begins automatic checking based on your configuration.
- **Stop Monitoring**: Stops the automatic checks, returning manual control.
- **Toggle Switch**: Manually turn your smart plug on or off.
- **Start/Stop on boot:** Adds the app to your startup applications, so whenever the system boots, the app will open and start monitoring.

---

## Important Considerations

- This application is specifically configured to work with TP-Link Kasa smart plugs. Compatibility with other brands may vary.
- Ensure your smart plug is accessible on the network with the provided IP address.
- The monitored applications list should reflect exact `.exe` filenames as they appear in system processes.
- Always test your configuration to verify that the app behaves as expected.

---

## Contributions

Feel free to fork this repository and submit pull requests for enhancements or fixes. Ensure changes are well-tested and documented.

---

## License

This project is open-source and available under the MIT License.

