#!/usr/bin/env bash
# =============================================================================
# RJOS — run.sh
# Executa o RJOS no QEMU para testes
# Uso: ./scripts/run.sh [--iso] [--ram 512] [--kvm]
# =============================================================================

set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ─── Defaults ────────────────────────────────────────────────────────────────
RAM_MB=1024          # 1GB RAM (nosso target máximo)
CPUS=2
DISK_IMG="$PROJECT_ROOT/build/rjos-disk.img"
DISK_SIZE="16G"
ISO_PATH="$PROJECT_ROOT/build/RJOS.iso"
USE_ISO=false
USE_KVM=false
DISPLAY_BACKEND="sdl"   # sdl, gtk, vnc, spice

# ─── Parse args ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --iso)          USE_ISO=true ;;
    --ram)          RAM_MB="$2"; shift ;;
    --cpus)         CPUS="$2"; shift ;;
    --kvm)          USE_KVM=true ;;
    --vnc)          DISPLAY_BACKEND="vnc" ;;
    --spice)        DISPLAY_BACKEND="spice" ;;
    --help|-h)
      echo "Uso: ./scripts/run.sh [opções]"
      echo "  --iso          Iniciar da ISO (sem disco persistente)"
      echo "  --ram MB       RAM em MB (padrão: 1024)"
      echo "  --cpus N       Número de CPUs (padrão: 2)"
      echo "  --kvm          Usar KVM (aceleração hardware — Linux apenas)"
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

# ─── Cria disco virtual se não existir ───────────────────────────────────────
create_disk() {
  if [[ ! -f "$DISK_IMG" ]]; then
    echo -e "${CYAN}[INFO]${NC} Criando disco virtual: $DISK_SIZE"
    qemu-img create -f qcow2 "$DISK_IMG" "$DISK_SIZE"
    echo -e "${GREEN}[OK]${NC}   Disco criado: $DISK_IMG"
  else
    local size
    size=$(du -sh "$DISK_IMG" | cut -f1)
    echo -e "${GREEN}[OK]${NC}   Disco existente: $DISK_IMG ($size)"
  fi
}

# ─── Monta argumentos do QEMU ────────────────────────────────────────────────
build_qemu_args() {
  local args=()

  # CPU e memória
  args+=(-m "${RAM_MB}M")
  args+=(-smp "cpus=${CPUS}")

  # CPU type: mais compatível
  args+=(-cpu host 2>/dev/null || -cpu qemu64)

  # KVM (aceleração)
  if [[ "$USE_KVM" == true ]]; then
    args+=(-enable-kvm -machine q35,accel=kvm)
  else
    args+=(-machine q35)
  fi

  # Disco
  args+=(
    -drive "file=${DISK_IMG},format=qcow2,if=virtio,cache=writeback"
  )

  # ISO
  if [[ "$USE_ISO" == true ]]; then
    if [[ ! -f "$ISO_PATH" ]]; then
      echo -e "${RED}[ERROR]${NC} ISO não encontrada: $ISO_PATH"
      echo "Execute primeiro: sudo ./scripts/mkiso.sh"
      exit 1
    fi
    args+=(
      -drive "file=${ISO_PATH},media=cdrom,readonly=on"
      -boot "order=d"
    )
  else
    args+=(-boot "order=c")
  fi

  # Placa de vídeo (virtio-gpu para Wayland)
  args+=(
    -device "virtio-gpu-gl"
    -display "${DISPLAY_BACKEND},gl=on" 2>/dev/null || \
    args+=(-vga virtio -display "${DISPLAY_BACKEND}")
  )

  # Rede (bridged virtio — acesso à internet)
  args+=(
    -netdev "user,id=net0,hostfwd=tcp::2222-:22"
    -device "virtio-net-pci,netdev=net0"
  )

  # Áudio (PipeWire/PulseAudio via QEMU)
  args+=(
    -audiodev "pa,id=snd0"
    -device "virtio-sound-pci,audiodev=snd0" 2>/dev/null || true
  )

  # USB
  args+=(
    -device "nec-usb-xhci,id=usb"
    -device "usb-tablet"
  )

  # Memória compartilhada (para melhor performance gráfica)
  args+=(
    -object "memory-backend-memfd,id=mem,size=${RAM_MB}M,share=on"
    -numa "node,memdev=mem"
  ) 2>/dev/null || true

  # Debug serial (opcional)
  args+=(
    -serial "mon:stdio"
  )

  echo "${args[@]}"
}

# ─── Main ────────────────────────────────────────────────────────────────────
main() {
  echo -e "${BOLD}${CYAN}"
  echo "  ██████╗      ██╗ ██████╗ ███████╗"
  echo "  ██╔══██╗     ██║██╔═══██╗██╔════╝"
  echo "  ██████╔╝     ██║██║   ██║███████╗"
  echo "  ██╔══██╗██   ██║██║   ██║╚════██║"
  echo "  ██║  ██║╚█████╔╝╚██████╔╝███████║"
  echo -e "${NC}"
  echo "  RJOS QEMU Runner"
  echo "  RAM: ${RAM_MB}MB | CPUs: ${CPUS} | KVM: ${USE_KVM}"
  echo ""

  check_qemu
  create_disk

  local qemu_args
  qemu_args="-m ${RAM_MB}M -smp ${CPUS} -machine q35"

  # KVM
  [[ "$USE_KVM" == true ]] && qemu_args+=" -enable-kvm -cpu host" || qemu_args+=" -cpu qemu64"

  # Disco
  qemu_args+=" -drive file=${DISK_IMG},format=qcow2,if=virtio"

  # ISO
  if [[ "$USE_ISO" == true ]]; then
    [[ ! -f "$ISO_PATH" ]] && { echo -e "${RED}[ERROR]${NC} ISO não encontrada. Execute: sudo ./scripts/mkiso.sh"; exit 1; }
    qemu_args+=" -drive file=${ISO_PATH},media=cdrom,readonly=on -boot order=d,once=d"
  fi

  # GPU virtio (melhor para Wayland)
  qemu_args+=" -device virtio-gpu-gl -display ${DISPLAY_BACKEND},gl=on"

  # Rede com acesso à internet
  qemu_args+=" -netdev user,id=net0,hostfwd=tcp::2222-:22 -device virtio-net-pci,netdev=net0"

  # USB e tablet (mouse preciso)
  qemu_args+=" -device nec-usb-xhci -device usb-tablet"

  # Áudio
  qemu_args+=" -audiodev pa,id=audio0 -device intel-hda -device hda-duplex,audiodev=audio0" 2>/dev/null || true

  echo -e "${CYAN}[INFO]${NC} Iniciando QEMU..."
  echo ""

  # shellcheck disable=SC2086
  qemu-system-x86_64 $qemu_args || {
    echo ""
    echo -e "${YELLOW}[WARN]${NC} Falha com GPU virtio. Tentando com VGA padrão..."
    qemu_args="${qemu_args/-device virtio-gpu-gl -display ${DISPLAY_BACKEND},gl=on/-vga virtio -display ${DISPLAY_BACKEND}}"
    # shellcheck disable=SC2086
    qemu-system-x86_64 $qemu_args
  }
}

main "$@"
