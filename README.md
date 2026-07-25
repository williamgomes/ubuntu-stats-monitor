# Ububtu StatsMonitor

A lightweight Ubuntu taskbar indicator that shows real-time CPU, RAM and GPU stats directly in your top panel — no bloat, no extra windows.

```
CPU 23.4% 52°  │  RAM 6.1/16G  │  GPU 45% 61°
```

![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-E95420?logo=ubuntu&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Features

- **CPU** — usage % and temperature
- **RAM** — used vs total in GiB
- **GPU** — usage % and temperature (NVIDIA and AMD supported)
- **Preferences window** — toggle each stat on/off and set the refresh interval, all saved automatically
- **Lightweight** — pure Python, no background daemons, minimal CPU overhead

---

## What it looks like

Clicking the indicator opens a dropdown with a detailed breakdown:

```
CPU  23.4%  52°C
RAM  6.10 GiB / 16 GiB
GPU  (NVIDIA) 45%  61°C
VRAM 4096 / 8192 MiB
```

The Preferences window lets you choose exactly what appears in the panel:

| Option | Default |
|---|---|
| CPU usage | ✅ on |
| CPU temperature | ✅ on |
| RAM usage | ✅ on |
| GPU usage | ✅ on |
| GPU temperature | ✅ on |
| Refresh interval | 2 seconds |

Settings are saved to `~/.config/statsmonitor/config.json` and survive reboots.

---

## Requirements

- Ubuntu 20.04 or newer (or any GNOME-based distro)
- Python 3.10+
- The **AppIndicator** GNOME Shell extension (see installation step 1 below)

### GPU support

| Brand | Method |
|---|---|
| NVIDIA | `nvidia-smi` (requires NVIDIA drivers) |
| AMD | `/sys/class/drm` sysfs (requires `amdgpu` kernel driver) |
| Intel | Not yet supported |

If no GPU is detected, the GPU section is hidden automatically.

---

## Installation

### Step 1 — Install the AppIndicator GNOME extension

On Ubuntu 24.04 and newer, AppIndicator support is not built in. You need to install the extension and log out once to activate it:

```bash
sudo apt install gnome-shell-extension-appindicator
```

Then **log out and back in**.

To confirm it's active, open the **Extensions** app and make sure *AppIndicator and KStatusNotifierItem Support* is toggled on.

### Step 2 — Clone the repo

```bash
git clone https://github.com/williamgomes/ubuntu-stats-monitor
cd ubuntu-stats-monitor
```

### Step 3 — Run the installer

```bash
bash install.sh
```

The installer will:
- Install all system dependencies (`python3-gi`, `python3-psutil`, `gir1.2-appindicator3-0.1`, `lm-sensors`)
- Copy the app to `~/.local/lib/statsmonitor/`
- Create a launcher at `~/.local/bin/statsmonitor`
- Add an autostart entry so StatsMonitor launches automatically on login
- Start StatsMonitor immediately

---

## Running manually

If you want to run StatsMonitor without installing, or to test changes:

```bash
/usr/bin/python3 src/statsmonitor.py
```

To run it in the background:

```bash
~/.local/bin/statsmonitor &
```

To stop it:

```bash
pkill -f statsmonitor.py
```

---

## Project structure

```
StatsMonitor/
├── src/
│   └── statsmonitor.py       # Main application
├── assets/
│   └── icon.svg              # Tray icon
├── snap/
│   └── snapcraft.yaml        # Snap package manifest (future)
├── bin/
│   └── launcher              # Snap launcher wrapper (future)
├── install.sh                # Local install script
├── setup.py                  # pip package definition
└── README.md
```

---

## Configuration

Preferences are saved automatically when you click **Apply** in the Preferences window. You can also edit the config file directly:

```bash
~/.config/statsmonitor/config.json
```

Example:

```json
{
  "show_cpu_usage": true,
  "show_cpu_temp": true,
  "show_ram": true,
  "show_gpu_usage": true,
  "show_gpu_temp": false,
  "refresh_interval": 2
}
```

---

## Troubleshooting

**Nothing appears in the panel**
Make sure the AppIndicator GNOME extension is installed and enabled, then log out and back in. You can verify it's active in the **Extensions** app.

**GPU section not showing**
- NVIDIA: run `nvidia-smi` in a terminal to confirm your drivers are working
- AMD: check that `/sys/class/drm/card0/device/gpu_busy_percent` exists

**Temperature not showing**
Run `sudo sensors-detect` once to configure `lm-sensors`, then restart StatsMonitor.

**`statsmonitor: command not found`**
Add `~/.local/bin` to your PATH:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
```

**Checking logs**
```bash
cat /tmp/statsmonitor.log
```

---

## Contributing

Pull requests are welcome. For major changes please open an issue first to discuss what you'd like to change.

---

## License

MIT
