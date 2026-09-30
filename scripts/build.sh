#!/usr/bin/env bash
# =============================================================================
# RJOS — build.sh
# Script principal de build da distribuição RJOS
# Cria o rootfs completo do sistema usando debootstrap
#
# Uso: sudo ./scripts/build.sh [--skip-debootstrap] [--skip-packages]
# =============================================================================

set -euo pipefail

# ─── Cores para output ───────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log_info()    { echo -e "${CYAN}[INFO]${NC} $*"; }
log_ok()      { echo -e "${GREEN}[OK]${NC}   $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_section() { echo -e "\n${BOLD}${CYAN}══════ $* ══════${NC}"; }

# ─── Configuração ────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

ROOTFS_DIR="$PROJECT_ROOT/build/rootfs"
CACHE_DIR="$PROJECT_ROOT/build/cache"
CONFIG_DIR="$PROJECT_ROOT/config"

DEBIAN_SUITE="bookworm"        # Debian 12 Stable
DEBIAN_MIRROR="http://deb.debian.org/debian"
ARCH="amd64"

SKIP_DEBOOTSTRAP=false
SKIP_PACKAGES=false

# ─── Parse argumentos ────────────────────────────────────────────────────────
for arg in "$@"; do
  case $arg in
    --skip-debootstrap) SKIP_DEBOOTSTRAP=true ;;
    --skip-packages)    SKIP_PACKAGES=true ;;
    --help|-h)
      echo "Uso: sudo ./scripts/build.sh [opções]"
      echo "  --skip-debootstrap   Pula etapa debootstrap (usa rootfs existente)"
      echo "  --skip-packages      Pula instalação de pacotes"
      exit 0
      ;;
  esac
done

# ─── Verificações iniciais ────────────────────────────────────────────────────
banner() {
  echo -e "${CYAN}"
  echo "  ██████╗      ██╗ ██████╗ ███████╗"
  echo "  ██╔══██╗     ██║██╔═══██╗██╔════╝"
  echo "  ██████╔╝     ██║██║   ██║███████╗"
  echo "  ██╔══██╗██   ██║██║   ██║╚════██║"
  echo "  ██║  ██║╚█████╔╝╚██████╔╝███████║"
  echo "  ╚═╝  ╚═╝ ╚════╝  ╚═════╝ ╚══════╝"
  echo -e "${NC}"
  echo "  RJOS Build System — Fase 1"
  echo "  Base: Debian $DEBIAN_SUITE ($ARCH)"
  echo ""
}

check_root() {
  if [[ $EUID -ne 0 ]]; then
    log_error "Este script deve ser executado como root (sudo ./scripts/build.sh)"
    exit 1
  fi
}

check_host_os() {
  if [[ ! -f /etc/os-release ]]; then
    log_error "Sistema host não identificado. Execute em Linux ou WSL2."
    exit 1
  fi
  # shellcheck source=/dev/null
  source /etc/os-release
  log_info "Host: $PRETTY_NAME"
}

check_deps() {
  log_section "Verificando dependências do host"

  local deps=(
    debootstrap
    chroot
    mount
    umount
    mknod
    xorriso
    mksquashfs
    grub-mkrescue
    mformat
  )

  local missing=()
  for dep in "${deps[@]}"; do
    if command -v "$dep" &>/dev/null; then
      log_ok "$dep"
    else
      log_warn "Faltando: $dep"
      missing+=("$dep")
    fi
  done

  if [[ ${#missing[@]} -gt 0 ]]; then
    log_error "Dependências faltando: ${missing[*]}"
    echo ""
    echo "Instale no host com:"
    echo "  sudo apt install -y debootstrap xorriso squashfs-tools grub-pc-bin grub-efi-amd64-bin mtools"
    exit 1
  fi

  log_ok "Todas as dependências encontradas"
}

# ─── Criação da estrutura de diretórios ──────────────────────────────────────
create_build_dirs() {
  log_section "Criando estrutura de build"

  mkdir -p "$ROOTFS_DIR"
  mkdir -p "$CACHE_DIR/apt"
  mkdir -p "$PROJECT_ROOT/build/iso"
  mkdir -p "$PROJECT_ROOT/build/iso/boot/grub"
  mkdir -p "$PROJECT_ROOT/build/iso/live"

  log_ok "Diretórios criados"
}

# ─── debootstrap: Cria rootfs mínimo Debian ──────────────────────────────────
run_debootstrap() {
  if [[ "$SKIP_DEBOOTSTRAP" == true ]]; then
    log_warn "Pulando debootstrap (--skip-debootstrap)"
    return
  fi

  log_section "Executando debootstrap (Debian $DEBIAN_SUITE)"
  log_info "Isso pode levar alguns minutos..."

  # Pacotes mínimos incluídos no first stage
  local include_pkgs="systemd,systemd-sysv,dbus,udev,locales,ca-certificates,apt"

  debootstrap \
    --arch="$ARCH" \
    --include="$include_pkgs" \
    --cache-dir="$CACHE_DIR/apt" \
    "$DEBIAN_SUITE" \
    "$ROOTFS_DIR" \
    "$DEBIAN_MIRROR"

  log_ok "Rootfs base criado em $ROOTFS_DIR"
}

# ─── Montagem de sistemas de arquivos para chroot ────────────────────────────
mount_chroot() {
  log_info "Montando sistemas de arquivos para chroot..."

  mountpoint -q "$ROOTFS_DIR/proc" || mount --bind /proc  "$ROOTFS_DIR/proc"
  mountpoint -q "$ROOTFS_DIR/sys" || mount --bind /sys   "$ROOTFS_DIR/sys"
  mountpoint -q "$ROOTFS_DIR/dev" || mount --bind /dev   "$ROOTFS_DIR/dev"
  mountpoint -q "$ROOTFS_DIR/dev/pts" || mount --bind /dev/pts "$ROOTFS_DIR/dev/pts"

  # Copiar resolv.conf para o chroot ter internet
  cp /etc/resolv.conf "$ROOTFS_DIR/etc/resolv.conf"

  log_ok "Montagens realizadas"
}

umount_chroot() {
  log_info "Desmontando sistemas de arquivos..."

  # Usar -l (lazy) para desocupar mesmo com processos ou referências
  umount -l "$ROOTFS_DIR/dev/pts" 2>/dev/null || true
  umount -l "$ROOTFS_DIR/dev"     2>/dev/null || true
  umount -l "$ROOTFS_DIR/sys"     2>/dev/null || true
  umount -l "$ROOTFS_DIR/proc"    2>/dev/null || true

  log_ok "Desmontagens realizadas"
}

# ─── Executa comando dentro do chroot ────────────────────────────────────────
chroot_exec() {
  chroot "$ROOTFS_DIR" /bin/bash -c "$*"
}

chroot_script() {
  # Copia e executa um script dentro do chroot
  local script_content="$1"
  local tmp_script="/tmp/rjos_chroot_script.sh"

  echo "#!/bin/bash" > "$ROOTFS_DIR/$tmp_script"
  echo "set -euo pipefail" >> "$ROOTFS_DIR/$tmp_script"
  echo "$script_content" >> "$ROOTFS_DIR/$tmp_script"
  chmod +x "$ROOTFS_DIR/$tmp_script"

  chroot "$ROOTFS_DIR" /bin/bash "$tmp_script"
  rm -f "$ROOTFS_DIR/$tmp_script"
}

# ─── Configuração base do sistema ────────────────────────────────────────────
configure_base_system() {
  log_section "Configurando sistema base"

  # hostname
  echo "rjos" > "$ROOTFS_DIR/etc/hostname"

  # hosts
  cat > "$ROOTFS_DIR/etc/hosts" << 'EOF'
127.0.0.1   localhost
127.0.1.1   rjos
::1         localhost ip6-localhost ip6-loopback
ff02::1     ip6-allnodes
ff02::2     ip6-allrouters
EOF

  # fstab mínimo (será expandido pelo instalador)
  cat > "$ROOTFS_DIR/etc/fstab" << 'EOF'
# RJOS fstab
# <device>   <mount>   <type>   <options>   <dump>   <pass>
proc         /proc     proc     defaults    0        0
sysfs        /sys      sysfs   defaults    0        0
devpts       /dev/pts  devpts  defaults    0        0
tmpfs        /tmp      tmpfs   defaults    0        0
EOF

  # locale
  echo "en_US.UTF-8 UTF-8" >> "$ROOTFS_DIR/etc/locale.gen"
  echo "pt_BR.UTF-8 UTF-8" >> "$ROOTFS_DIR/etc/locale.gen"

  log_ok "Sistema base configurado"
}

# ─── Instala pacotes essenciais ──────────────────────────────────────────────
install_packages() {
  if [[ "$SKIP_PACKAGES" == true ]]; then
    log_warn "Pulando instalação de pacotes (--skip-packages)"
    return
  fi

  log_section "Instalando pacotes essenciais"

  # Atualiza sources.list com contrib e non-free-firmware
  cat > "$ROOTFS_DIR/etc/apt/sources.list" << EOF
deb $DEBIAN_MIRROR $DEBIAN_SUITE main contrib non-free non-free-firmware
deb $DEBIAN_MIRROR $DEBIAN_SUITE-updates main contrib non-free non-free-firmware
deb http://security.debian.org/debian-security $DEBIAN_SUITE-security main contrib non-free non-free-firmware
EOF

  chroot_script "
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq

    # Geração de locales
    apt-get install -y locales
    locale-gen en_US.UTF-8 pt_BR.UTF-8
    update-locale LANG=en_US.UTF-8

    # Kernel Linux, initramfs e live boot
    apt-get install -y linux-image-amd64 linux-headers-amd64 grub-pc grub-efi-amd64-bin initramfs-tools live-boot

    # Systemd completo
    apt-get install -y systemd-timesyncd dbus

    # Rede
    apt-get install -y network-manager iproute2 iputils-ping curl wget \
      wireless-tools wpasupplicant rfkill net-tools

    # Firmware Wi-Fi e hardware
    apt-get install -y firmware-linux firmware-linux-nonfree \
      firmware-iwlwifi firmware-realtek firmware-atheros firmware-misc-nonfree || true

    # Áudio
    apt-get install -y pipewire pipewire-pulse wireplumber \
      alsa-utils pulseaudio-utils

    # Ferramentas essenciais
    apt-get install -y bash bash-completion sudo \
      coreutils util-linux e2fsprogs fdisk \
      nano vim-tiny less file htop

    # Git e ferramentas de desenvolvimento + Python
    apt-get install -y git build-essential gcc make \
      pkg-config python3 python3-pip python3-gi python3-gi-cairo

    # Suporte a Flatpak
    apt-get install -y flatpak

    # Utilitários do sistema
    apt-get install -y acpid pm-utils upower \
      lm-sensors pciutils usbutils

    # Fonts
    apt-get install -y fonts-inter fonts-jetbrains-mono \
      fonts-noto fonts-noto-color-emoji

    # Limpeza do cache APT
    apt-get clean
    rm -rf /var/lib/apt/lists/*
  "

  log_ok "Pacotes instalados"
}

# ─── Configura Wayland e Ambiente Gráfico ────────────────────────────────────
install_graphics() {
  log_section "Instalando componentes gráficos"

  chroot_script "
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq

    # Wayland e utilitários
    apt-get install -y wayland-protocols libwayland-dev \
      libwayland-client0 libwayland-server0

    # wlroots (base do compositor)
    apt-get install -y libwlroots-dev || apt-get install -y libwlroots11

    # GTK4 toolkit e dependências Python dos apps RJOS
    apt-get install -y libgtk-4-dev libgtk-4-1 \
      libadwaita-1-dev libadwaita-1-0 \
      gir1.2-gtk-4.0 gir1.2-adw-1 \
      python3-gi python3-gi-cairo

    # Layer shell para painel
    apt-get install -y gtk4-layer-shell-dev gir1.2-gtklayershell-0.1 || true

    # VTE para terminal
    apt-get install -y libvte-2.91-gtk4-dev gir1.2-vte-3.91 || \
      apt-get install -y libvte-2.91-dev gir1.2-vte-2.91 || true

    # Mesa (OpenGL/EGL para Wayland)
    apt-get install -y mesa-vulkan-drivers mesa-va-drivers \
      libgl1-mesa-dri libgles2-mesa-dev libegl1-mesa-dev

    # Seat/session management
    apt-get install -y seatd libseat-dev

    # Display login manager alternativo (greetd)
    apt-get install -y greetd || true

    # Polkit para elevação de privilégios
    apt-get install -y polkit

    # Utilitários do desktop Wayland
    apt-get install -y swaybg mako-notifier wl-clipboard brightnessctl || true

    # Flatpak portal (para apps Flatpak funcionarem no Wayland)
    apt-get install -y xdg-desktop-portal xdg-desktop-portal-wlr || true

    apt-get clean
    rm -rf /var/lib/apt/lists/*
  "

  log_ok "Componentes gráficos instalados"
}

# ─── Cria usuário padrão ──────────────────────────────────────────────────────
create_user() {
  log_section "Criando usuário padrão"

  local username="rjos"
  local fullname="RJOS User"

  chroot_script "
    # Cria usuário
    id -u $username &>/dev/null || useradd \
      --create-home \
      --shell /bin/bash \
      --comment '$fullname' \
      --groups audio,video,netdev,plugdev,bluetooth,sudo \
      $username

    # Senha padrão: 'rjos' (usuário deverá alterar)
    echo '$username:rjos' | chpasswd

    # Configura sudo sem senha para grupo sudo (modo live/instalação)
    echo '%sudo ALL=(ALL) ALL' > /etc/sudoers.d/sudo-group
    chmod 440 /etc/sudoers.d/sudo-group

    # Diretórios pessoais padrão XDG
    mkdir -p /home/$username/{Desktop,Downloads,Documents,Pictures,Music,Videos}
    chown -R $username:$username /home/$username

    # Configurar ambiente básico do usuário
    cat > /home/$username/.bashrc << 'BASHRC'
# RJOS .bashrc
export XDG_SESSION_TYPE=wayland
export XDG_CURRENT_DESKTOP=RJOS
export MOZ_ENABLE_WAYLAND=1
export QT_QPA_PLATFORM=wayland

# Prompt personalizado RJOS
PS1='\[\033[01;36m\]\u\[\033[00m\]@\[\033[01;34m\]\h\[\033[00m\]:\[\033[01;32m\]\w\[\033[00m\]\$ '

alias ls='ls --color=auto'
alias ll='ls -alFh'
alias la='ls -A'
alias grep='grep --color=auto'
alias ..='cd ..'
BASHRC
    chown $username:$username /home/$username/.bashrc
  "

  log_ok "Usuário '$username' criado (senha: rjos)"
}

# ─── Configura systemd ────────────────────────────────────────────────────────
configure_systemd() {
  log_section "Configurando systemd"

  # Copia units customizadas do projeto para o rootfs
  if [[ -d "$CONFIG_DIR/systemd/system" ]]; then
    cp -r "$CONFIG_DIR/systemd/system/." "$ROOTFS_DIR/etc/systemd/system/"
  fi

  chroot_script "
    # Habilita serviços essenciais
    systemctl enable NetworkManager
    systemctl enable systemd-timesyncd
    systemctl enable systemd-resolved

    # Habilita PipeWire (via user service)
    # Será ativado por socket no login do usuário
    systemctl --global enable pipewire.socket pipewire-pulse.socket wireplumber.service

    # Se greetd disponível, use para login gráfico
    if systemctl list-unit-files | grep -q greetd; then
      systemctl enable greetd
    else
      # Fallback: login via getty no TTY1 que inicia Wayland
      systemctl enable getty@tty1
    fi

    # Configura target padrão como graphical
    systemctl set-default graphical.target
  "

  log_ok "systemd configurado"
}

# ─── Configura GRUB ───────────────────────────────────────────────────────────
configure_grub() {
  log_section "Configurando GRUB"

  # Configuração do GRUB
  cat > "$ROOTFS_DIR/etc/default/grub" << 'EOF'
GRUB_DEFAULT=0
GRUB_TIMEOUT=5
GRUB_TIMEOUT_STYLE=menu
GRUB_DISTRIBUTOR="RJOS"
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
GRUB_CMDLINE_LINUX=""
GRUB_TERMINAL_OUTPUT="gfxterm"
GRUB_GFXMODE="1920x1080x32,1280x720x32,auto"
GRUB_GFXPAYLOAD_LINUX=keep
EOF

  # Copia tema GRUB se existir
  if [[ -d "$PROJECT_ROOT/desktop/themes/grub" ]]; then
    mkdir -p "$ROOTFS_DIR/boot/grub/themes"
    cp -r "$PROJECT_ROOT/desktop/themes/grub" "$ROOTFS_DIR/boot/grub/themes/rjos"
    echo 'GRUB_THEME="/boot/grub/themes/rjos/theme.txt"' >> "$ROOTFS_DIR/etc/default/grub"
  fi

  log_ok "GRUB configurado"
}

# ─── Instala binários RJOS compilados ────────────────────────────────────────
install_rjos_binaries() {
  log_section "Instalando binários RJOS"

  local bin_dir="$PROJECT_ROOT/build/rjos-bin"

  # CLI rjos
  if [[ -f "$PROJECT_ROOT/system/rjos-cli/rjos" ]]; then
    install -m 755 "$PROJECT_ROOT/system/rjos-cli/rjos" "$ROOTFS_DIR/usr/local/bin/rjos"
    log_ok "rjos CLI instalado"
  else
    # Instala versão bash do CLI (pré-compilação)
    install -m 755 "$SCRIPT_DIR/rjos-bootstrap.sh" "$ROOTFS_DIR/usr/local/bin/rjos" 2>/dev/null || \
      log_warn "rjos CLI não compilado ainda (execute: cd system/rjos-cli && make)"
  fi

  # Compositor
  if [[ -f "$PROJECT_ROOT/desktop/compositor/build/rjos-compositor" ]]; then
    install -m 755 "$PROJECT_ROOT/desktop/compositor/build/rjos-compositor" \
      "$ROOTFS_DIR/usr/local/bin/rjos-compositor"
    log_ok "rjos-compositor instalado"
  else
    log_warn "rjos-compositor não compilado ainda (Fase 2)"
  fi

  # Shell (painel)
  if [[ -f "$PROJECT_ROOT/desktop/shell/build/rjos-shell" ]]; then
    install -m 755 "$PROJECT_ROOT/desktop/shell/build/rjos-shell" \
      "$ROOTFS_DIR/usr/local/bin/rjos-shell"
    log_ok "rjos-shell instalado"
  else
    log_warn "rjos-shell não compilado ainda (Fase 2)"
  fi

  # Tema GTK
  if [[ -d "$PROJECT_ROOT/desktop/themes/rjos" ]]; then
    mkdir -p "$ROOTFS_DIR/usr/share/themes/RJOS"
    cp -r "$PROJECT_ROOT/desktop/themes/rjos/." "$ROOTFS_DIR/usr/share/themes/RJOS/"
    log_ok "Tema RJOS instalado"
  fi

  # Ícones
  if [[ -d "$PROJECT_ROOT/icons" ]]; then
    mkdir -p "$ROOTFS_DIR/usr/share/icons/RJOS"
    cp -r "$PROJECT_ROOT/icons/." "$ROOTFS_DIR/usr/share/icons/RJOS/"
    log_ok "Ícones RJOS instalados"
  fi

  # Wallpapers
  if [[ -d "$PROJECT_ROOT/desktop/wallpapers" ]]; then
    mkdir -p "$ROOTFS_DIR/usr/share/rjos/wallpapers"
    cp -r "$PROJECT_ROOT/desktop/wallpapers/." "$ROOTFS_DIR/usr/share/rjos/wallpapers/"
    log_ok "Wallpapers instalados"
  fi

  # Instala todos os apps e módulos Python da shell
  if [[ -f "$SCRIPT_DIR/install-apps.sh" ]]; then
    bash "$SCRIPT_DIR/install-apps.sh" "$ROOTFS_DIR"
  fi
}

# ─── Limpeza final do rootfs ──────────────────────────────────────────────────
cleanup_rootfs() {
  log_section "Limpando rootfs"

  chroot_script "
    # Remove cache APT
    apt-get clean
    rm -rf /var/lib/apt/lists/*
    rm -rf /tmp/*
    rm -rf /var/tmp/*

    # Remove arquivos de log desnecessários
    find /var/log -type f -delete

    # Remove resolv.conf temporário (será gerido pelo NetworkManager)
    rm -f /etc/resolv.conf
    ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf
  "

  log_ok "Rootfs limpo"
}

# ─── Main ─────────────────────────────────────────────────────────────────────
main() {
  banner
  check_root
  check_host_os
  check_deps
  create_build_dirs

  # Trap para garantir desmontagem em caso de erro
  trap 'log_error "Build falhou. Desmontando..."; umount_chroot; exit 1' ERR

  run_debootstrap
  configure_base_system
  mount_chroot

  install_packages
  install_graphics
  create_user
  configure_systemd
  configure_grub
  install_rjos_binaries
  cleanup_rootfs

  umount_chroot

  log_section "Build concluído!"
  log_ok "Rootfs em: $ROOTFS_DIR"
  log_info "Próximos passos:"
  echo "  1. Gerar ISO:    sudo ./scripts/mkiso.sh"
  echo "  2. Testar QEMU:  ./scripts/run.sh"
  echo "  3. Chroot:       sudo ./scripts/chroot.sh"
}

main "$@"
