#!/usr/bin/env bash
# StatsMonitor — local installer (no Snap required).
# Usage:  bash install.sh

set -euo pipefail

INSTALL_DIR="$HOME/.local/lib/statsmonitor"
BIN_DIR="$HOME/.local/bin"
AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/statsmonitor.desktop"

echo "=== StatsMonitor installer ==="

# ── Dependencies ──────────────────────────────────────────────────────────────
echo "→ Installing system dependencies…"
sudo apt-get update -qq
sudo apt-get install -y \
    python3 \
    python3-gi \
    python3-gi-cairo \
    python3-psutil \
    gir1.2-gtk-3.0 \
    gir1.2-appindicator3-0.1 \
    lm-sensors

# ── Copy application files ────────────────────────────────────────────────────
echo "→ Installing application to $INSTALL_DIR …"
mkdir -p "$INSTALL_DIR"
cp -r src/. "$INSTALL_DIR/"

# ── Create launcher in PATH ───────────────────────────────────────────────────
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/statsmonitor" << 'EOF'
#!/usr/bin/env bash
exec /usr/bin/python3 "$HOME/.local/lib/statsmonitor/statsmonitor.py" "$@"
EOF
chmod +x "$BIN_DIR/statsmonitor"

echo "→ Launcher written to $BIN_DIR/statsmonitor"

# ── Autostart entry ───────────────────────────────────────────────────────────
mkdir -p "$AUTOSTART_DIR"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=StatsMonitor
Comment=CPU, GPU & RAM usage in the taskbar
Exec=$BIN_DIR/statsmonitor
Icon=utilities-system-monitor
StartupNotify=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
EOF

echo "→ Autostart entry written to $DESKTOP_FILE"

# ── GNOME extension reminder ──────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  IMPORTANT — AppIndicator GNOME extension                          ║"
echo "║                                                                      ║"
echo "║  On GNOME Shell (Ubuntu 17.10+) you need the extension:            ║"
echo "║  'AppIndicator and KStatusNotifierItem Support'                     ║"
echo "║                                                                      ║"
echo "║  Install via terminal:                                              ║"
echo "║  sudo apt install gnome-shell-extension-appindicator               ║"
echo "║                                                                      ║"
echo "║  Then log out and back in to activate it.                          ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "✓ Installation complete! Starting StatsMonitor now…"

# ── Launch ────────────────────────────────────────────────────────────────────
nohup "$BIN_DIR/statsmonitor" &>/tmp/statsmonitor.log &
echo "  PID $! — logs at /tmp/statsmonitor.log"
echo ""
echo "  StatsMonitor will auto-start with your next login."
echo "  To stop it:  pkill -f statsmonitor.py"