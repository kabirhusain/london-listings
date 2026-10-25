#!/usr/bin/env bash
# Install (or update) the systemd user timer that runs scripts/20261024_run_local.sh
# every day at 05:30 London time, half an hour before the GitHub run.
#
#   scripts/20261024_install_timer.sh            install or update, and enable
#   scripts/20261024_install_timer.sh --remove   disable and delete
#
# The service unit is generated with this repo's current path, so if you move
# the folder, just run this again.
set -euo pipefail

NAME=london-listings-local
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

command -v systemctl >/dev/null || { echo "systemctl not found; use cron instead (see the README)." >&2; exit 1; }

if [[ "${1:-}" == "--remove" ]]; then
  systemctl --user disable --now "$NAME.timer" 2>/dev/null || true
  rm -f "$UNIT_DIR/$NAME.service" "$UNIT_DIR/$NAME.timer"
  systemctl --user daemon-reload
  echo "Removed the $NAME timer."
  exit 0
fi

chmod +x "$REPO/scripts/20261024_run_local.sh"
mkdir -p "$UNIT_DIR"

# systemd treats % as a specifier, so escape it in the path.
SD_REPO="${REPO//%/%%}"

cat > "$UNIT_DIR/$NAME.service" <<EOF
[Unit]
Description=Collect London listings for venues that block GitHub, and push them
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$SD_REPO
ExecStart=/usr/bin/env bash "$SD_REPO/scripts/20261024_run_local.sh"
EOF

cat > "$UNIT_DIR/$NAME.timer" <<EOF
[Unit]
Description=Daily local listings run, before the 06:00 GitHub run

[Timer]
OnCalendar=*-*-* 05:30:00 Europe/London
# Run a missed job at next boot/wake (e.g. the laptop was off at 05:30).
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
EOF

systemd-analyze --user verify "$UNIT_DIR/$NAME.service" "$UNIT_DIR/$NAME.timer"
systemctl --user daemon-reload
systemctl --user enable --now "$NAME.timer"

echo
systemctl --user list-timers "$NAME.timer" --no-pager
echo
echo "Installed. Repo: $REPO"
echo "  Run it now:   systemctl --user start $NAME.service"
echo "  Logs:         journalctl --user -u $NAME"
echo "  Remove:       $0 --remove"
if [[ "$(loginctl show-user "$USER" --property=Linger --value 2>/dev/null)" != "yes" ]]; then
  echo
  echo "Note: user timers only run while you're logged in. To run even when logged out:"
  echo "  sudo loginctl enable-linger $USER"
fi
