#!/usr/bin/env bash
# =============================================================================
# RJOS — chroot.sh
# Entra no rootfs do RJOS para configuração e testes manuais
# Uso: sudo ./scripts/chroot.sh [comando]
# =============================================================================

set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; NC='\033[0m'; BOLD='\033[1m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ROOTFS="$PROJECT_ROOT/build/rootfs"

if [[ $EUID -ne 0 ]]; then
  echo -e "${RED}[ERROR]${NC} Execute como root: sudo ./scripts/chroot.sh"
  exit 1
fi

if [[ ! -d "$ROOTFS/bin" ]]; then
  echo -e "${RED}[ERROR]${NC} Rootfs não encontrado em $ROOTFS"
  echo "Execute primeiro: sudo ./scripts/build.sh"
  exit 1
fi

# ─── Monta sistemas de arquivos ──────────────────────────────────────────────
mount_fs() {
  mount --bind /proc     "$ROOTFS/proc"     2>/dev/null || true
  mount --bind /sys      "$ROOTFS/sys"      2>/dev/null || true
  mount --bind /dev      "$ROOTFS/dev"      2>/dev/null || true
  mount --bind /dev/pts  "$ROOTFS/dev/pts"  2>/dev/null || true
  mount --bind /run      "$ROOTFS/run"      2>/dev/null || true
  cp /etc/resolv.conf "$ROOTFS/etc/resolv.conf" 2>/dev/null || true
}

umount_fs() {
  umount "$ROOTFS/run"      2>/dev/null || true
  umount "$ROOTFS/dev/pts"  2>/dev/null || true
  umount "$ROOTFS/dev"      2>/dev/null || true
  umount "$ROOTFS/sys"      2>/dev/null || true
  umount "$ROOTFS/proc"     2>/dev/null || true
}

trap 'echo ""; echo -e "${YELLOW}[WARN]${NC} Saindo do chroot..."; umount_fs' EXIT

mount_fs

echo ""
echo -e "${BOLD}${CYAN}  RJOS Chroot${NC}"
echo -e "  Rootfs: $ROOTFS"
echo ""

if [[ $# -gt 0 ]]; then
  # Executa comando específico
  echo -e "${CYAN}[INFO]${NC} Executando: $*"
  chroot "$ROOTFS" /bin/bash -c "$*"
else
  # Shell interativo
  echo -e "${CYAN}[INFO]${NC} Shell interativo. Digite 'exit' para sair."
  echo ""
  chroot "$ROOTFS" /bin/bash --login
fi
