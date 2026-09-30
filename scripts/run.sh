#!/usr/bin/env bash
# =============================================================================
# RJOS — run.sh
# Executa o RJOS no QEMU para testes
# Uso: ./scripts/run.sh [--iso] [--ram 1024] [--cpus 2] [--kvm]
# =============================================================================

set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ─── Defaults ────────────────────────────────────────────────────────────────
RAM_MB=1024          # 1GB RAM (target mínimo recomendado)
CPUS=2
DISK_IMG="$PROJECT_ROOT/build/rjos-disk.img"
DISK_SIZE="16G"
ISO_PATH="$PROJECT_ROOT/build/RJOS.iso"
USE_ISO=false
USE_KVM=false
DISPLAY_BACKEND="gtk"   # gtk, sdl, vnc

# ─── Parse args ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --iso)          USE_ISO=true ;;
    --ram)          RAM_MB="$2"; shift ;;
    --cpus)         CPUS="$2"; shift ;;
    --kvm)          USE_KVM=true ;;
    --sdl)          DISPLAY_BACKEND="sdl" ;;
    --gtk)          DISPLAY_BACKEND="gtk" ;;
    --vnc)          DISPLAY_BACKEND="vnc" ;;
    --help|-h)
      echo "Uso: ./scripts/run.sh [opções]"
      echo "  --iso          Iniciar da ISO (modo Live)"
      echo "  --ram MB       RAM em MB (padrão: 1024)"
      echo "  --cpus N       Número de CPUs (padrão: 2)"
      echo "  --kvm          Usar aceleração KVM por hardware"
      echo "  --gtk          Usar backend GTK para o display (padrão)"
      echo "  --sdl          Usar backend SDL para o display"
      echo "  --vnc          Usar VNC como display"
      exit 0
      ;;
    *) echo "Opção desconhecida: $1"; exit 1 ;;
  esac
  shift
done

# ─── Verificações ─────────────────────────────────────────────────────────────
check_qemu() {
  local qemu_bin="qemu-system-x86_64"
  if ! command -v "$qemu_bin" &>/dev/null; then
    echo -e "${RED}[ERROR]${NC} QEMU não encontrado."
    echo "Instale: sudo apt install qemu-system-x86 qemu-utils"
    exit 1
  fi
  echo -e "${GREEN}[OK]${NC}   QEMU: $(qemu-system-x86_64 --version | head -1)"
}

create_disk() {
  if [[ ! -f "$DISK_IMG" ]]; then
    echo -e "${CYAN}[INFO]${NC} Criando disco virtual: $DISK_SIZE"
    mkdir -p "$(dirname "$DISK_IMG")"
    qemu-img create -f qcow2 "$DISK_IMG" "$DISK_SIZE" >/dev/null
    echo -e "${GREEN}[OK]${NC}   Disco criado: $DISK_IMG"
  else
    local size
    size=$(du -sh "$DISK_IMG" | cut -f1)
    echo -e "${GREEN}[OK]${NC}   Disco existente: $DISK_IMG ($size)"
  fi
}

main() {
  echo -e "${BOLD}${CYAN}"
  echo "  ██████╗      ██╗ ██████╗ ███████╗"
  echo "  ██╔══██╗     ██║██╔═══██╗██╔════╝"
  echo "  ██████╔╝     ██║██║   ██║███████╗"
  echo "  ██╔══██╗██   ██║██║   ██║╚════██║"
  echo "  ██║  ██║╚█████╔╝╚██████╔╝███████║"
  echo "  ╚═╝  ╚═╝ ╚════╝  ╚═════╝ ╚══════╝"
  echo -e "${NC}"
  echo "  RJOS QEMU Runner"
  echo "  RAM: ${RAM_MB}MB | CPUs: ${CPUS} | KVM: ${USE_KVM}"
  echo ""

  check_qemu
  create_disk

  local -a args=(
    -m "${RAM_MB}M"
    -smp "cpus=${CPUS}"
    -machine q35
    -drive "file=${DISK_IMG},format=qcow2,if=virtio"
    -device virtio-vga
    -device nec-usb-xhci
    -device usb-tablet
    -netdev "user,id=net0,hostfwd=tcp::2222-:22"
    -device "virtio-net-pci,netdev=net0"
  )

  # Aceleração KVM
  if [[ "$USE_KVM" == true ]] && [[ -w /dev/kvm ]]; then
    args+=(-enable-kvm -cpu host)
  else
    args+=(-cpu qemu64)
  fi

  # Boot por ISO ou Disco
  if [[ "$USE_ISO" == true ]]; then
    if [[ ! -f "$ISO_PATH" ]]; then
      echo -e "${RED}[ERROR]${NC} ISO não encontrada: $ISO_PATH"
      echo "Execute primeiro: sudo ./scripts/make-iso.sh"
      exit 1
    fi
    args+=(
      -drive "file=${ISO_PATH},media=cdrom,readonly=on"
      -boot "order=d,once=d"
    )
  else
    args+=(-boot "order=c")
  fi

  # Display
  if [[ "$DISPLAY_BACKEND" == "vnc" ]]; then
    args+=(-display vnc=:1)
    echo -e "${CYAN}[INFO]${NC} VNC ativo em :1 (porta 5901)"
  else
    args+=(-display "${DISPLAY_BACKEND}")
  fi

  echo -e "${CYAN}[INFO]${NC} Iniciando QEMU..."
  echo ""

  qemu-system-x86_64 "${args[@]}" || {
    echo ""
    echo -e "${YELLOW}[WARN]${NC} Falha na inicialização gráfica. Tentando com display padrão..."
    qemu-system-x86_64 -m "${RAM_MB}M" -smp "${CPUS}" -machine q35 \
      -vga std \
      -drive "file=${ISO_PATH},media=cdrom,readonly=on" \
      -boot order=d
  }
}

main "$@"
