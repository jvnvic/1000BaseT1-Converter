#!/usr/bin/env bash
set -e

PY_PREFIX="/opt/python311"
PY_VERSION="3.11.14"
VENV_DIR="$HOME/.ledfx"
SERVICE_NAME="ledfx.service"

echo "[*] Updating apt…"
sudo apt update

echo "[*] Installing build prerequisites for Python…"
sudo apt install -y \
  build-essential pkg-config wget curl git gcc \
  libssl-dev zlib1g-dev \
  libncurses-dev \
  libreadline-dev libsqlite3-dev \
  libgdbm-dev libbz2-dev \
  libexpat1-dev liblzma-dev \
  tk-dev libffi-dev uuid-dev \
  portaudio19-dev pulseaudio avahi-daemon cmake python3-pip \
  libavcodec-dev libavformat-dev libavutil-dev libswresample-dev \
  libsndfile1-dev libsamplerate0-dev

# try to install libaubio-dev if it exists in the repo
if apt-cache show libaubio-dev >/dev/null 2>&1; then
  echo "[*] Installing libaubio-dev…"
  sudo apt install -y libaubio-dev
else
  echo "[!] libaubio-dev package not found in your repos, continuing without it."
fi

# ---------------------------------------------------------------------
# Step 1: ensure python 3.11 exists at /opt/python311
# ---------------------------------------------------------------------
if [ ! -x "$PY_PREFIX/bin/python3.11" ]; then
  echo "[*] Python 3.11 not found in $PY_PREFIX, building from source…"
  cd /tmp
  wget "https://www.python.org/ftp/python/${PY_VERSION}/Python-${PY_VERSION}.tgz"
  tar xvf "Python-${PY_VERSION}.tgz"
  cd "Python-${PY_VERSION}"

  ./configure --prefix="$PY_PREFIX" --enable-optimizations --with-lto
  make -j"$(nproc)"
  sudo make altinstall

  echo "[+] Installed Python 3.11 to $PY_PREFIX"
else
  echo "[*] Found existing $PY_PREFIX/bin/python3.11, skipping build."
fi

# ---------------------------------------------------------------------
# Step 2: create venv using our python3.11
# ---------------------------------------------------------------------
echo "[*] Creating LEDFX venv at $VENV_DIR using $PY_PREFIX/bin/python3.11 …"
"$PY_PREFIX/bin/python3.11" -m venv "$VENV_DIR"

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

echo "[*] Upgrading pip/setuptools/wheel in venv…"
pip install --upgrade pip setuptools wheel

# ---------------------------------------------------------------------
# Step 3: install ledfx from PyPI
# ---------------------------------------------------------------------
echo "[*] Installing LEDFX from PyPI…"
pip install ledfx

echo "[+] LEDFX installed in venv $VENV_DIR"

# ---------------------------------------------------------------------
# Step 4: create systemd service
# ---------------------------------------------------------------------
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"
LED_USER="$(id -un)"
LED_HOME="$HOME"
LED_EXEC="$VENV_DIR/bin/ledfx"

echo "[*] Creating systemd service at $SERVICE_FILE …"
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=LedFx Daemon
After=network.target sound.target

[Service]
Type=simple
User=${LED_USER}
WorkingDirectory=${LED_HOME}
ExecStart=${LED_EXEC}
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "[*] Reloading systemd and enabling service…"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"

echo
echo "=============================================================="
echo " LEDFX install finished."
echo
echo " - Python 3.11: $PY_PREFIX/bin/python3.11"
echo " - venv:        $VENV_DIR"
echo " - run manual:  source $VENV_DIR/bin/activate && ledfx --open-ui"
echo " - service:     sudo systemctl status $SERVICE_NAME"
echo "=============================================================="
