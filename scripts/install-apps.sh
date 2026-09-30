#!/usr/bin/env bash
# =============================================================================
# RJOS — install-apps.sh
# Instala os apps Python do RJOS no rootfs
# Cria wrappers /usr/local/bin/* que chamam os scripts Python
# Uso: sudo ./scripts/install-apps.sh [ROOTFS_DIR]
# =============================================================================

set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; NC='\033[0m'; BOLD='\033[1m'
info() { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC}   $*"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ROOTFS="${1:-$PROJECT_ROOT/build/rootfs}"

[[ $EUID -ne 0 ]] && { echo "Execute como root"; exit 1; }
[[ ! -d "$ROOTFS/usr" ]] && { echo "Rootfs não encontrado: $ROOTFS"; exit 1; }

info "Instalando apps RJOS em $ROOTFS"

# ─── Diretórios de destino ────────────────────────────────────────────────────
RJOS_APP_DIR="$ROOTFS/usr/lib/rjos"
mkdir -p "$RJOS_APP_DIR"

# ─── Função para instalar app Python ──────────────────────────────────────────
install_python_app() {
  local src="$1"
  local dest_name="$2"
  local wrapper_name="$3"

  if [[ ! -f "$src" ]]; then
    echo "  Pulando (não encontrado): $src"
    return
  fi

  # Copia script para /usr/lib/rjos/
  cp "$src" "$RJOS_APP_DIR/$dest_name"
  chmod 755 "$RJOS_APP_DIR/$dest_name"

  # Cria wrapper em /usr/local/bin/
  cat > "$ROOTFS/usr/local/bin/$wrapper_name" << EOF
#!/bin/bash
export PYTHONDONTWRITEBYTECODE=1
exec python3 /usr/lib/rjos/$dest_name "\$@"
EOF
  chmod 755 "$ROOTFS/usr/local/bin/$wrapper_name"
  ok "$wrapper_name"
}

# ─── Instala apps ─────────────────────────────────────────────────────────────
echo ""
info "Apps da desktop shell:"

# Copia todos os módulos Python da shell (quick_settings, context_menu, desktop_icons, wallpaper_manager)
for pyfile in "$PROJECT_ROOT"/desktop/shell/*.py; do
  if [[ -f "$pyfile" ]]; then
    base=$(basename "$pyfile")
    cp "$pyfile" "$RJOS_APP_DIR/$base"
    chmod 755 "$RJOS_APP_DIR/$base"
  fi
done

install_python_app \
  "$PROJECT_ROOT/desktop/shell/rjos-shell.py" \
  "rjos-shell.py" \
  "rjos-shell"

# Greeter de login se existir
if [[ -f "$PROJECT_ROOT/desktop/login/rjos-greeter.py" ]]; then
  install_python_app \
    "$PROJECT_ROOT/desktop/login/rjos-greeter.py" \
    "rjos-greeter.py" \
    "rjos-greeter"
fi

# Dock RJOS se existir
if [[ -f "$PROJECT_ROOT/desktop/dock/rjos-dock.py" ]]; then
  install_python_app \
    "$PROJECT_ROOT/desktop/dock/rjos-dock.py" \
    "rjos-dock.py" \
    "rjos-dock"
fi

echo ""
info "Aplicativos:"

install_python_app \
  "$PROJECT_ROOT/apps/terminal/rjos-terminal.py" \
  "rjos-terminal.py" \
  "rjos-terminal"

install_python_app \
  "$PROJECT_ROOT/apps/files/rjos-files.py" \
  "rjos-files.py" \
  "rjos-files"

install_python_app \
  "$PROJECT_ROOT/apps/settings/rjos-settings.py" \
  "rjos-settings.py" \
  "rjos-settings"

# ─── Módulo de tema compartilhado ─────────────────────────────────────────────
if [[ -f "$PROJECT_ROOT/desktop/themes/rjos_theme.py" ]]; then
  cp "$PROJECT_ROOT/desktop/themes/rjos_theme.py" "$RJOS_APP_DIR/rjos_theme.py"
  chmod 644 "$RJOS_APP_DIR/rjos_theme.py"
  ok "rjos_theme.py (tokens)"
fi

# ─── Wallpapers Oficiais ──────────────────────────────────────────────────────
if [[ -d "$PROJECT_ROOT/desktop/wallpapers" ]]; then
  mkdir -p "$ROOTFS/usr/share/backgrounds/rjos"
  cp -r "$PROJECT_ROOT/desktop/wallpapers/." "$ROOTFS/usr/share/backgrounds/rjos/"
  ok "Wallpapers RJOS instalados em /usr/share/backgrounds/rjos"
fi

# ─── CLI rjos ─────────────────────────────────────────────────────────────────
echo ""
info "CLI:"

if [[ -f "$PROJECT_ROOT/system/rjos-cli/rjos" ]]; then
  install -m 755 "$PROJECT_ROOT/system/rjos-cli/rjos" \
    "$ROOTFS/usr/local/bin/rjos"
  ok "rjos CLI"
fi

# ─── rjos-theme (motor de temas em tempo real) ────────────────────────────────
if [[ -f "$PROJECT_ROOT/system/rjos-theme/rjos-theme" ]]; then
  install -m 755 "$PROJECT_ROOT/system/rjos-theme/rjos-theme" \
    "$ROOTFS/usr/local/bin/rjos-theme"
  ok "rjos-theme"
fi

# ─── Aplica tema padrão no rootfs (gera o CSS override inicial) ───────────────
if [[ -x "$ROOTFS/usr/local/bin/rjos-theme" ]]; then
  # Cria config padrão
  mkdir -p "$ROOTFS/etc/skel/.config/rjos"
  cat > "$ROOTFS/etc/skel/.config/rjos/theme.json" << 'EOF'
{
  "accent": "ocean",
  "style": "dark",
  "font": "Inter 13",
  "mono_font": "JetBrains Mono 12",
  "transparency": true,
  "animations": true
}
EOF
  ok "Config de tema padrão criada"
fi

# ─── Tema GTK ─────────────────────────────────────────────────────────────────
echo ""
info "Tema GTK4:"

if [[ -d "$PROJECT_ROOT/desktop/themes/rjos" ]]; then
  mkdir -p "$ROOTFS/usr/share/themes/RJOS"
  cp -r "$PROJECT_ROOT/desktop/themes/rjos/." "$ROOTFS/usr/share/themes/RJOS/"
  ok "Tema RJOS"
fi

# ─── Configura tema padrão via gsettings ──────────────────────────────────────
cat > "$ROOTFS/etc/dconf/db/site.d/rjos-defaults" << 'EOF'
[org/gnome/desktop/interface]
gtk-theme='RJOS'
color-scheme='prefer-dark'
font-name='Inter 13'
monospace-font-name='JetBrains Mono 12'
icon-theme='hicolor'
cursor-theme='Adwaita'
cursor-size=24
EOF

# ─── Arquivo .desktop para apps ───────────────────────────────────────────────
echo ""
info "Arquivos .desktop:"

mkdir -p "$ROOTFS/usr/share/applications"

# Terminal
cat > "$ROOTFS/usr/share/applications/rjos-terminal.desktop" << 'EOF'
[Desktop Entry]
Version=1.0
Name=Terminal
Name[pt_BR]=Terminal
Comment=Terminal RJOS
Exec=rjos-terminal
Icon=utilities-terminal
Terminal=false
Type=Application
Categories=System;TerminalEmulator;
StartupNotify=true
EOF

# Files
cat > "$ROOTFS/usr/share/applications/rjos-files.desktop" << 'EOF'
[Desktop Entry]
Version=1.0
Name=Arquivos
Name[pt_BR]=Arquivos
Comment=Gerenciador de arquivos RJOS
Exec=rjos-files %u
Icon=system-file-manager
Terminal=false
Type=Application
Categories=System;FileManager;
MimeType=inode/directory;
StartupNotify=true
EOF

# Settings
cat > "$ROOTFS/usr/share/applications/rjos-settings.desktop" << 'EOF'
[Desktop Entry]
Version=1.0
Name=Configurações
Name[pt_BR]=Configurações
Comment=Configurações do sistema RJOS
Exec=rjos-settings
Icon=preferences-system
Terminal=false
Type=Application
Categories=Settings;
StartupNotify=true
EOF

ok "Arquivos .desktop criados"

echo ""
ok "Instalação dos apps RJOS concluída!"
