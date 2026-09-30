#!/usr/bin/env bash
# =============================================================================
# RJOS — clean.sh
# Remove artefatos de build
# Uso: ./scripts/clean.sh [--all] [--rootfs] [--iso] [--disk]
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

CLEAN_ROOTFS=false
CLEAN_ISO=false
CLEAN_DISK=false
CLEAN_ALL=false
CLEAN_CACHE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all)    CLEAN_ALL=true ;;
    --rootfs) CLEAN_ROOTFS=true ;;
    --iso)    CLEAN_ISO=true ;;
    --disk)   CLEAN_DISK=true ;;
    --cache)  CLEAN_CACHE=true ;;
    --help|-h)
      echo "Uso: ./scripts/clean.sh [opções]"
      echo "  --all     Remove tudo (rootfs, ISO, disco, cache)"
      echo "  --rootfs  Remove apenas o rootfs"
      echo "  --iso     Remove apenas a ISO"
      echo "  --disk    Remove apenas o disco QEMU"
      echo "  --cache   Remove cache APT"
      exit 0
      ;;
    *) echo "Opção desconhecida: $1"; exit 1 ;;
  esac
  shift
done

# Se nenhuma opção, mostra menu interativo
if [[ "$CLEAN_ALL" == false && "$CLEAN_ROOTFS" == false && \
      "$CLEAN_ISO" == false && "$CLEAN_DISK" == false && "$CLEAN_CACHE" == false ]]; then
  echo ""
  echo -e "${BOLD}RJOS — Limpeza de Build${NC}"
  echo ""
  echo "O que deseja remover?"
  echo "  1) Apenas a ISO (build/RJOS.iso)"
  echo "  2) Apenas o disco QEMU (build/rjos-disk.img)"
  echo "  3) Rootfs + ISO (mantém cache APT)"
  echo "  4) Tudo (rootfs, ISO, disco, cache) — rebuild completo"
  echo "  5) Cancelar"
  echo ""
  read -rp "Escolha [1-5]: " choice

  case "$choice" in
    1) CLEAN_ISO=true ;;
    2) CLEAN_DISK=true ;;
    3) CLEAN_ROOTFS=true; CLEAN_ISO=true ;;
    4) CLEAN_ALL=true ;;
    5) echo "Cancelado."; exit 0 ;;
    *) echo "Opção inválida."; exit 1 ;;
  esac
fi

# ─── Garante desmontagem do rootfs ───────────────────────────────────────────
ensure_unmounted() {
  local rootfs="$PROJECT_ROOT/build/rootfs"
  for mp in dev/pts dev sys proc; do
    if mountpoint -q "$rootfs/$mp" 2>/dev/null; then
      echo -e "${YELLOW}[WARN]${NC} Desmontando $rootfs/$mp..."
      umount "$rootfs/$mp" || true
    fi
  done
}

echo ""

if [[ "$CLEAN_ALL" == true ]] || [[ "$CLEAN_ROOTFS" == true ]]; then
  if [[ -d "$PROJECT_ROOT/build/rootfs" ]]; then
    ensure_unmounted
    echo -e "${CYAN}[INFO]${NC} Removendo rootfs..."
    rm -rf "$PROJECT_ROOT/build/rootfs"
    echo -e "${GREEN}[OK]${NC}   rootfs removido"
  fi
fi

if [[ "$CLEAN_ALL" == true ]] || [[ "$CLEAN_ISO" == true ]]; then
  if [[ -f "$PROJECT_ROOT/build/RJOS.iso" ]]; then
    rm -f "$PROJECT_ROOT/build/RJOS.iso"
    echo -e "${GREEN}[OK]${NC}   RJOS.iso removida"
  fi
  if [[ -d "$PROJECT_ROOT/build/iso-staging" ]]; then
    rm -rf "$PROJECT_ROOT/build/iso-staging"
    echo -e "${GREEN}[OK]${NC}   iso-staging removido"
  fi
fi

if [[ "$CLEAN_ALL" == true ]] || [[ "$CLEAN_DISK" == true ]]; then
  if [[ -f "$PROJECT_ROOT/build/rjos-disk.img" ]]; then
    rm -f "$PROJECT_ROOT/build/rjos-disk.img"
    echo -e "${GREEN}[OK]${NC}   rjos-disk.img removido"
  fi
fi

if [[ "$CLEAN_ALL" == true ]] || [[ "$CLEAN_CACHE" == true ]]; then
  if [[ -d "$PROJECT_ROOT/build/cache" ]]; then
    rm -rf "$PROJECT_ROOT/build/cache"
    echo -e "${GREEN}[OK]${NC}   cache APT removido"
  fi
fi

# Limpa builds compilados dos apps
echo -e "${CYAN}[INFO]${NC} Limpando builds compilados..."
find "$PROJECT_ROOT/desktop" "$PROJECT_ROOT/apps" "$PROJECT_ROOT/system" \
  -name "build" -type d -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_ROOT" -name "*.o" -o -name "*.so" -o -name "*.a" \
  2>/dev/null | grep -v ".git" | xargs rm -f 2>/dev/null || true

echo ""
echo -e "${GREEN}[OK]${NC}   Limpeza concluída"
echo ""
echo "Para rebuild completo:"
echo "  sudo ./scripts/build.sh"
