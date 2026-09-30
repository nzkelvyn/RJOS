#!/usr/bin/env bash
# =============================================================================
# RJOS — mkiso.sh
# Gera a imagem ISO bootável do RJOS
# Uso: sudo ./scripts/mkiso.sh
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log_info()    { echo -e "${CYAN}[INFO]${NC} $*"; }
log_ok()      { echo -e "${GREEN}[OK]${NC}   $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_section() { echo -e "\n${BOLD}${CYAN}══════ $* ══════${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

ROOTFS_DIR="$PROJECT_ROOT/build/rootfs"
ISO_STAGING="$PROJECT_ROOT/build/iso-staging"
ISO_OUTPUT="$PROJECT_ROOT/build/RJOS.iso"

check_root() {
  [[ $EUID -ne 0 ]] && { log_error "Execute como root: sudo ./scripts/mkiso.sh"; exit 1; }
}

check_deps() {
  local deps=(mksquashfs xorriso grub-mkrescue mformat)
  local missing=()
  for dep in "${deps[@]}"; do
    if ! command -v "$dep" &>/dev/null; then
      missing+=("$dep")
    fi
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    log_error "Dependências faltando para gerar a ISO: ${missing[*]}"
    echo ""
    echo "Instale no host com:"
    echo "  sudo apt install -y squashfs-tools xorriso grub-pc-bin grub-efi-amd64-bin mtools"
    exit 1
  fi
  log_ok "Dependências da ISO verificadas"
}

check_rootfs() {
  [[ ! -d "$ROOTFS_DIR/bin" ]] && {
    log_error "Rootfs não encontrado. Execute primeiro: sudo ./scripts/build.sh"
    exit 1
  }
  log_ok "Rootfs encontrado"
}

create_squashfs() {
  log_section "Criando squashfs (filesystem comprimido)"

  mkdir -p "$ISO_STAGING/live"

  log_info "Comprimindo rootfs com mksquashfs (xz)..."
  log_info "Isso pode levar vários minutos..."

  mksquashfs "$ROOTFS_DIR" "$ISO_STAGING/live/filesystem.squashfs" \
    -comp xz \
    -Xbcj x86 \
    -b 1M \
    -noappend \
    -wildcards \
    -ef "$SCRIPT_DIR/squashfs-excludes.txt" 2>/dev/null || \
  mksquashfs "$ROOTFS_DIR" "$ISO_STAGING/live/filesystem.squashfs" \
    -comp xz \
    -b 1M \
    -noappend

  local size
  size=$(du -sh "$ISO_STAGING/live/filesystem.squashfs" | cut -f1)
  log_ok "Squashfs criado: $size"
}

copy_kernel() {
  log_section "Copiando kernel e initramfs"

  mkdir -p "$ISO_STAGING/boot"

  # Encontra o kernel mais recente no rootfs
  local vmlinuz
  vmlinuz=$(ls "$ROOTFS_DIR/boot/vmlinuz-"* | sort -V | tail -1)

  local initrd
  initrd=$(ls "$ROOTFS_DIR/boot/initrd.img-"* | sort -V | tail -1)

  cp "$vmlinuz" "$ISO_STAGING/boot/vmlinuz"
  cp "$initrd"  "$ISO_STAGING/boot/initrd.img"

  log_ok "Kernel: $(basename "$vmlinuz")"
  log_ok "initrd: $(basename "$initrd")"
}

create_grub_config() {
  log_section "Configurando GRUB da ISO"

  mkdir -p "$ISO_STAGING/boot/grub"

  cat > "$ISO_STAGING/boot/grub/grub.cfg" << 'EOF'
# RJOS GRUB Configuration
set default=0
set timeout=5

# Cores RJOS
set color_normal=light-gray/black
set color_highlight=white/blue

# Resolução
set gfxmode=1920x1080x32,1280x720x32,auto
set gfxpayload=keep
terminal_output gfxterm

menuentry "RJOS — Iniciar Sistema" {
    linux   /boot/vmlinuz boot=live quiet splash rjos.live=1
    initrd  /boot/initrd.img
}

menuentry "RJOS — Modo Seguro (sem gráficos)" {
    linux   /boot/vmlinuz boot=live nomodeset rjos.safe=1
    initrd  /boot/initrd.img
}

menuentry "RJOS — Com Terminal de Debug" {
    linux   /boot/vmlinuz boot=live rjos.debug=1
    initrd  /boot/initrd.img
}

menuentry "Verificar memória (memtest)" --class memtest {
    linux16 /boot/memtest86+.bin
}
EOF

  log_ok "grub.cfg criado"
}

build_iso() {
  log_section "Gerando ISO com xorriso"

  xorriso -as mkisofs \
    -iso-level 3 \
    -full-iso9660-filenames \
    -volid "RJOS_LIVE" \
    -output "$ISO_OUTPUT" \
    -eltorito-boot boot/grub/i386-pc/eltorito.img \
      -no-emul-boot \
      -boot-load-size 4 \
      -boot-info-table \
      --eltorito-catalog boot/grub/boot.cat \
    --grub2-boot-info \
    --grub2-mbr /usr/lib/grub/i386-pc/boot_hybrid.img \
    -partition_offset 16 \
    --mbr-force-bootable \
    -append_partition 2 28732ac11ff8d211ba4b00a0c93ec93b \
      /usr/lib/grub/x86_64-efi/cdboot.efi \
    -appended_part_as_gpt \
    -iso_mbr_part_type a2a0d0ebe5b9334487c068b6b72699c7 \
    -m "--interval:appended_partition_2:all::" \
    -m "--interval:local_fs:x86-sys:" \
    "$ISO_STAGING" 2>/dev/null || \
  grub-mkrescue \
    --output="$ISO_OUTPUT" \
    --modules="linux normal iso9660 all_video boot lvm" \
    "$ISO_STAGING" -- \
    -volid "RJOS_LIVE"

  local iso_size
  iso_size=$(du -sh "$ISO_OUTPUT" | cut -f1)
  log_ok "ISO gerada: $ISO_OUTPUT ($iso_size)"
}

main() {
  check_root
  check_deps
  check_rootfs

  rm -rf "$ISO_STAGING"
  mkdir -p "$ISO_STAGING"

  create_squashfs
  copy_kernel
  create_grub_config

  # Instala grub na staging
  grub-mkstandalone \
    --format=i386-pc \
    --output="$ISO_STAGING/boot/grub/i386-pc/eltorito.img" \
    --install-modules="linux normal iso9660 all_video boot lvm" \
    --modules="linux normal iso9660 all_video boot lvm" \
    --locales="" \
    --themes="" \
    "boot/grub/grub.cfg=$ISO_STAGING/boot/grub/grub.cfg" 2>/dev/null || true

  build_iso

  echo ""
  log_section "ISO pronta!"
  echo ""
  echo -e "  Arquivo: ${BOLD}$ISO_OUTPUT${NC}"
  echo ""
  echo "  Testar no QEMU:"
  echo "    ./scripts/run.sh"
  echo ""
  echo "  Gravar em pendrive:"
  echo "    sudo dd if=$ISO_OUTPUT of=/dev/sdX bs=4M status=progress"
}

main "$@"
