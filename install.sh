#!/usr/bin/env bash
# ==============================================================================
# Automated Enterprise Installer for NetworkingAgent Enterprise (Linux / macOS)
# ==============================================================================

set -euo pipefail

INSTALL_DIR="${HOME}/.local/share/networking-agent"
BIN_DIR="${HOME}/.local/bin"
APP_SOURCE_DIR="${INSTALL_DIR}/app"
VENV_DIR="${INSTALL_DIR}/venv"

echo ""
echo "================================================================="
echo "   NetworkingAgent Enterprise v2.1.0 - Automated POSIX Setup    "
echo "   Autonomous & Closed-Loop Network Assistant (Textual TUI)     "
echo "================================================================="
echo ""

# 1. Prerequisites check
echo "[*] Checking Python and uv availability..."
if command -v uv &> /dev/null; then
    INSTALLER="uv"
elif command -v python3 &> /dev/null; then
    INSTALLER="python"
else
    echo "[!] Neither uv nor Python 3 was found. Attempting to install uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="${HOME}/.local/bin:${PATH}"
    if command -v uv &> /dev/null; then
        INSTALLER="uv"
    else
        echo "[ERROR] Please install Python 3.12+ or uv manually."
        exit 1
    fi
fi

# 2. Directory setup
mkdir -p "${INSTALL_DIR}"
mkdir -p "${BIN_DIR}"

# 3. Source setup (local or remote clone)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${SCRIPT_DIR}/pyproject.toml" ]]; then
    echo "[*] Installing from local repository: ${SCRIPT_DIR}..."
    rm -rf "${APP_SOURCE_DIR}"
    mkdir -p "${APP_SOURCE_DIR}"
    cp -R "${SCRIPT_DIR}/." "${APP_SOURCE_DIR}/"
else
    echo "[*] Cloning NetworkingAgent from GitHub..."
    rm -rf "${APP_SOURCE_DIR}"
    git clone --depth 1 https://github.com/GuifMur98/networkingAgent.git "${APP_SOURCE_DIR}"
fi

cd "${APP_SOURCE_DIR}"

# 4. Virtual environment & dependencies
if [[ "${INSTALLER}" == "uv" ]]; then
    echo "[*] Creating virtual environment with uv..."
    uv venv "${VENV_DIR}"
    VENV_PYTHON="${VENV_DIR}/bin/python"
    uv pip install --python "${VENV_PYTHON}" -e .
else
    echo "[*] Creating virtual environment with python3 venv..."
    python3 -m venv "${VENV_DIR}"
    VENV_PYTHON="${VENV_DIR}/bin/python"
    "${VENV_PYTHON}" -m pip install --upgrade pip
    "${VENV_PYTHON}" -m pip install -e .
fi

# 5. Launcher script
LAUNCHER="${BIN_DIR}/networking-agent"
cat << EOF > "${LAUNCHER}"
#!/usr/bin/env bash
export NETWORKING_AGENT_HOME="${INSTALL_DIR}"
exec "${VENV_PYTHON}" "${APP_SOURCE_DIR}/main.py" "\$@"
EOF
chmod +x "${LAUNCHER}"

echo "[+] Created launcher: ${LAUNCHER}"

# 6. Ensure ~/.local/bin is in PATH
if [[ ":$PATH:" != *":${BIN_DIR}:"* ]]; then
    echo "[!] ${BIN_DIR} is not in your current PATH."
    SHELL_RC=""
    if [[ -n "${BASH_VERSION:-}" ]]; then
        SHELL_RC="${HOME}/.bashrc"
    elif [[ -n "${ZSH_VERSION:-}" ]]; then
        SHELL_RC="${HOME}/.zshrc"
    fi

    if [[ -n "${SHELL_RC}" && -f "${SHELL_RC}" ]]; then
        echo "export PATH=\"${BIN_DIR}:\$PATH\"" >> "${SHELL_RC}"
        echo "[+] Added ${BIN_DIR} to ${SHELL_RC}."
    fi
fi

# 7. Uninstaller script
UNINSTALLER="${INSTALL_DIR}/uninstall.sh"
cat << EOF > "${UNINSTALLER}"
#!/usr/bin/env bash
echo "[*] Uninstalling NetworkingAgent Enterprise..."
rm -rf "${INSTALL_DIR}"
rm -f "${LAUNCHER}"
echo "[+] NetworkingAgent successfully removed."
EOF
chmod +x "${UNINSTALLER}"

echo ""
echo "================================================================="
echo " [SUCCESS] NetworkingAgent Enterprise v2.1.0 installed!          "
echo "================================================================="
echo " To start the agent, run:"
echo "    networking-agent"
echo ""
echo " Uninstaller located at: ${UNINSTALLER}"
echo ""
