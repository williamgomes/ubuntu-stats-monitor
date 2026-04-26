#!/usr/bin/env python3
"""
StatsMonitor — CPU, GPU & RAM usage + temperature in the Ubuntu taskbar.
"""

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")

from gi.repository import Gtk, AppIndicator3, GLib

import json
import os
import subprocess
import psutil
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ─── Paths ────────────────────────────────────────────────────────────────────

CONFIG_DIR  = os.path.expanduser("~/.config/statsmonitor")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
ICON_PATH   = os.path.join(os.path.dirname(__file__), "icon.svg")
APP_ID      = "statsmonitor"

# ─── Default config ───────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "show_cpu_usage":   True,
    "show_cpu_temp":    True,
    "show_ram":         True,
    "show_gpu_usage":   True,
    "show_gpu_temp":    True,
    "refresh_interval": 2,        # seconds
}

# ─── Config helpers ───────────────────────────────────────────────────────────

def load_config() -> dict:
    try:
        with open(CONFIG_FILE) as f:
            data = json.load(f)
        # Fill in any missing keys from defaults
        return {**DEFAULT_CONFIG, **data}
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_CONFIG.copy()


def save_config(cfg: dict):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

# ─── Hardware helpers ─────────────────────────────────────────────────────────

def _cpu_percent() -> float:
    return psutil.cpu_percent(interval=None)


def _cpu_temp() -> float | None:
    try:
        all_temps = psutil.sensors_temperatures()
    except AttributeError:
        return None
    for key in ("coretemp", "k10temp", "cpu_thermal", "cpu-thermal",
                "acpitz", "zenpower", "it8686", "nct6775"):
        entries = all_temps.get(key, [])
        if entries:
            for e in entries:
                if "package" in e.label.lower() or "tdie" in e.label.lower():
                    return e.current
            return entries[0].current
    return None


def _ram_info() -> tuple[float, float]:
    m = psutil.virtual_memory()
    gib = 1024 ** 3
    return m.used / gib, m.total / gib


def _nvidia_info() -> dict | None:
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,temperature.gpu,"
                "memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            timeout=2,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        return None

    first_line = out.splitlines()[0]
    parts = [p.strip() for p in first_line.split(",")]
    try:
        return {
            "vendor":        "nvidia",
            "usage":         float(parts[0]),
            "temp":          float(parts[1]),
            "mem_used_mib":  float(parts[2]),
            "mem_total_mib": float(parts[3]),
        }
    except (ValueError, IndexError):
        return None


def _amd_info() -> dict | None:
    base = "/sys/class/drm"
    if not os.path.isdir(base):
        return None
    for card in sorted(os.listdir(base)):
        if not card.startswith("card") or card.count("-") > 0:
            continue
        dev = os.path.join(base, card, "device")
        busy_path = os.path.join(dev, "gpu_busy_percent")
        if not os.path.exists(busy_path):
            continue
        try:
            usage = float(_sysfs_read(busy_path))
        except (TypeError, ValueError):
            continue
        temp      = _amd_temp(dev)
        mem_used  = _sysfs_read(os.path.join(dev, "mem_info_vram_used"))
        mem_total = _sysfs_read(os.path.join(dev, "mem_info_vram_total"))
        try:
            mib = 1024 ** 2
            mem_used_mib  = int(mem_used)  / mib if mem_used  else None
            mem_total_mib = int(mem_total) / mib if mem_total else None
        except ValueError:
            mem_used_mib = mem_total_mib = None
        return {
            "vendor":        "amd",
            "usage":         usage,
            "temp":          temp,
            "mem_used_mib":  mem_used_mib,
            "mem_total_mib": mem_total_mib,
        }
    return None


def _amd_temp(dev_path: str) -> float | None:
    hwmon_base = os.path.join(dev_path, "hwmon")
    if not os.path.isdir(hwmon_base):
        return None
    for hw in os.listdir(hwmon_base):
        temp_raw = _sysfs_read(os.path.join(hwmon_base, hw, "temp1_input"))
        if temp_raw:
            try:
                return float(temp_raw) / 1000.0
            except ValueError:
                pass
    return None


def _sysfs_read(path: str) -> str | None:
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


def _gpu_info() -> dict | None:
    return _nvidia_info() or _amd_info()

# ─── Label builder ────────────────────────────────────────────────────────────

def _temp_str(t: float | None) -> str:
    return f" {t:.0f}°" if t is not None else ""


def build_label(cfg: dict, cpu_pct: float, cpu_temp: float | None,
                ram_used: float, ram_total: float, gpu: dict | None) -> str:
    parts: list[str] = []

    # CPU
    if cfg["show_cpu_usage"] or cfg["show_cpu_temp"]:
        cpu_str = "CPU"
        if cfg["show_cpu_usage"]:
            cpu_str += f" {cpu_pct:.1f}%"
        if cfg["show_cpu_temp"] and cpu_temp is not None:
            cpu_str += _temp_str(cpu_temp)
        parts.append(cpu_str)

    # RAM
    if cfg["show_ram"]:
        parts.append(f"RAM {ram_used:.1f}/{ram_total:.0f}G")

    # GPU
    if cfg["show_gpu_usage"] or cfg["show_gpu_temp"]:
        if gpu:
            gpu_str = "GPU"
            if cfg["show_gpu_usage"]:
                gpu_str += f" {gpu['usage']:.0f}%"
            if cfg["show_gpu_temp"] and gpu.get("temp") is not None:
                gpu_str += _temp_str(gpu["temp"])
            parts.append(gpu_str)

    return "  │  ".join(parts) if parts else "–"

# ─── Preferences dialog ───────────────────────────────────────────────────────

class PreferencesDialog(Gtk.Dialog):
    def __init__(self, parent_cfg: dict):
        super().__init__(title="StatsMonitor — Preferences")
        self.set_border_width(12)
        self.set_resizable(False)
        self.add_buttons(
            "_Cancel", Gtk.ResponseType.CANCEL,
            "_Apply",  Gtk.ResponseType.APPLY,
        )
        self.set_default_response(Gtk.ResponseType.APPLY)

        box = self.get_content_area()
        box.set_spacing(6)

        # ── Section: What to display ──────────────────────────────────────────
        box.pack_start(self._section_label("Display"), False, False, 4)

        self._checks = {}
        options = [
            ("show_cpu_usage", "CPU usage"),
            ("show_cpu_temp",  "CPU temperature"),
            ("show_ram",       "RAM usage"),
            ("show_gpu_usage", "GPU usage"),
            ("show_gpu_temp",  "GPU temperature"),
        ]
        for key, label in options:
            cb = Gtk.CheckButton(label=label)
            cb.set_active(parent_cfg.get(key, True))
            cb.set_margin_start(12)
            box.pack_start(cb, False, False, 0)
            self._checks[key] = cb

        # ── Section: Refresh interval ─────────────────────────────────────────
        box.pack_start(self._section_label("Refresh interval"), False, False, 8)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hbox.set_margin_start(12)

        self._spin = Gtk.SpinButton()
        self._spin.set_range(1, 60)
        self._spin.set_increments(1, 5)
        self._spin.set_value(parent_cfg.get("refresh_interval", 2))
        self._spin.set_numeric(True)

        hbox.pack_start(self._spin, False, False, 0)
        hbox.pack_start(Gtk.Label(label="seconds"), False, False, 0)
        box.pack_start(hbox, False, False, 0)

        box.show_all()

    def _section_label(self, text: str) -> Gtk.Label:
        lbl = Gtk.Label()
        lbl.set_markup(f"<b>{text}</b>")
        lbl.set_halign(Gtk.Align.START)
        return lbl

    def get_config(self) -> dict:
        cfg = {key: cb.get_active() for key, cb in self._checks.items()}
        cfg["refresh_interval"] = int(self._spin.get_value())
        return cfg

# ─── AppIndicator ─────────────────────────────────────────────────────────────

class StatsMonitor:
    def __init__(self):
        self.cfg = load_config()

        # Use the SVG icon if it exists, otherwise fall back to a system icon
        icon = ICON_PATH if os.path.isfile(ICON_PATH) else "utilities-system-monitor"

        self.indicator = AppIndicator3.Indicator.new(
            APP_ID,
            icon,
            AppIndicator3.IndicatorCategory.SYSTEM_SERVICES,
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        # Warm up psutil CPU counter (first call always returns 0.0)
        psutil.cpu_percent(interval=None)

        self._timeout_id = None
        self._build_menu()
        self._update()
        self._schedule()

    # ── Scheduling ────────────────────────────────────────────────────────────

    def _schedule(self):
        if self._timeout_id:
            GLib.source_remove(self._timeout_id)
        interval_ms = self.cfg["refresh_interval"] * 1000
        self._timeout_id = GLib.timeout_add(interval_ms, self._update)

    # ── Menu ──────────────────────────────────────────────────────────────────

    def _build_menu(self):
        menu = Gtk.Menu()

        self._detail_item = Gtk.MenuItem(label="Loading…")
        self._detail_item.set_sensitive(False)
        menu.append(self._detail_item)

        menu.append(Gtk.SeparatorMenuItem())

        prefs = Gtk.MenuItem(label="⚙  Preferences")
        prefs.connect("activate", self._on_prefs)
        menu.append(prefs)

        quit_item = Gtk.MenuItem(label="✕  Quit")
        quit_item.connect("activate", self._on_quit)
        menu.append(quit_item)

        menu.show_all()
        self.indicator.set_menu(menu)

    # ── Update loop ───────────────────────────────────────────────────────────

    def _update(self) -> bool:
        cpu_pct          = _cpu_percent()
        cpu_temp         = _cpu_temp()
        ram_used, ram_total = _ram_info()
        gpu              = _gpu_info()

        label = build_label(self.cfg, cpu_pct, cpu_temp, ram_used, ram_total, gpu)
        self.indicator.set_label(label, "")

        # Detailed breakdown in the dropdown
        detail_lines = []
        if self.cfg["show_cpu_usage"] or self.cfg["show_cpu_temp"]:
            cpu_line = "CPU"
            if self.cfg["show_cpu_usage"]:
                cpu_line += f"  {cpu_pct:.1f}%"
            if self.cfg["show_cpu_temp"] and cpu_temp is not None:
                cpu_line += f"  {cpu_temp:.0f}°C"
            detail_lines.append(cpu_line)

        if self.cfg["show_ram"]:
            detail_lines.append(f"RAM  {ram_used:.2f} GiB / {ram_total:.0f} GiB")

        if gpu and (self.cfg["show_gpu_usage"] or self.cfg["show_gpu_temp"]):
            vendor   = gpu["vendor"].upper()
            gpu_line = f"GPU  ({vendor})"
            if self.cfg["show_gpu_usage"]:
                gpu_line += f"  {gpu['usage']:.0f}%"
            if self.cfg["show_gpu_temp"] and gpu.get("temp") is not None:
                gpu_line += f"  {gpu['temp']:.0f}°C"
            detail_lines.append(gpu_line)
            if gpu.get("mem_used_mib") and gpu.get("mem_total_mib"):
                detail_lines.append(
                    f"VRAM  {gpu['mem_used_mib']:.0f} / {gpu['mem_total_mib']:.0f} MiB"
                )

        self._detail_item.set_label("\n".join(detail_lines) if detail_lines else "Nothing selected")

        return True   # keep the GLib timeout alive

    # ── Preferences ───────────────────────────────────────────────────────────

    def _on_prefs(self, _):
        dlg = PreferencesDialog(self.cfg)
        response = dlg.run()
        if response == Gtk.ResponseType.APPLY:
            new_cfg = dlg.get_config()
            interval_changed = new_cfg["refresh_interval"] != self.cfg["refresh_interval"]
            self.cfg = new_cfg
            save_config(self.cfg)
            self._update()
            if interval_changed:
                self._schedule()
        dlg.destroy()

    def _on_quit(self, _):
        Gtk.main_quit()


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    app = StatsMonitor()   # noqa: F841
    Gtk.main()


if __name__ == "__main__":
    main()