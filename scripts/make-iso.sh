#!/usr/bin/env bash
# =============================================================================
# RJOS — make-iso.sh
# Finaliza a instalação dos binários/apps no rootfs e gera a imagem ISO bootável
# Uso: sudo ./scripts/make-iso.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

[[ $EUID -ne 0 ]] && { echo -e "\033[0;31m[ERROR]\033[0m Execute como root: sudo ./scripts/make-iso.sh"; exit 1; }

echo -e "\033[0;36m[1/2] Finalizando configuração do rootfs e instalando apps RJOS...\033[0m"
bash "$SCRIPT_DIR/build.sh" --skip-debootstrap

echo -e "\033[0;36m[2/2] Gerando imagem ISO bootável (RJOS.iso)...\033[0m"
bash "$SCRIPT_DIR/mkiso.sh"

# Ajusta permissões para o usuário original poder rodar a ISO sem sudo
if [[ -n "${SUDO_USER:-}" ]]; then
  chown "$SUDO_USER:$SUDO_USER" "$PROJECT_ROOT/build/RJOS.iso" 2>/dev/null || true
  chown "$SUDO_USER:$SUDO_USER" "$PROJECT_ROOT/build" 2>/dev/null || true
fi
chmod 777 "$PROJECT_ROOT/build" 2>/dev/null || true

echo ""
echo -e "\033[0;32m════════════════════════════════════════════════════════════════════\033[0m"
echo -e "\033[1;32m  ISO gerada com sucesso: $PROJECT_ROOT/build/RJOS.iso\033[0m"
echo -e "\033[0;32m════════════════════════════════════════════════════════════════════\033[0m"
echo ""
echo -e "Para rodar na máquina virtual agora:"
echo -e "  \033[1;36m./scripts/run.sh --iso --kvm\033[0m"
echo ""
