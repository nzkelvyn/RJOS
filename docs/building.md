# RJOS — Guia de Build

## Pré-requisitos

O build do RJOS **deve ser feito em Linux** (Ubuntu/Debian host, ou WSL2 no Windows):

```bash
# Instala dependências no host
sudo apt install \
  debootstrap \
  qemu-system-x86 qemu-utils \
  xorriso squashfs-tools \
  grub-pc-bin grub-efi-amd64-bin \
  meson ninja-build gcc make pkg-config \
  libwlroots-dev libgtk-4-dev libadwaita-1-dev \
  libvte-2.91-gtk4-dev \
  python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-vte-3.91 \
  git
```

## Workflow de build

### 1. Fase 1 — Build do sistema base

```bash
# Constrói o rootfs completo (requer sudo)
sudo ./scripts/build.sh

# Instala os apps RJOS no rootfs
sudo ./scripts/install-apps.sh

# Entra no chroot para testes manuais
sudo ./scripts/chroot.sh
```

### 2. Fase 2 — Build do compositor (wlroots)

```bash
cd desktop/compositor

# Configura com meson
meson setup build

# Compila
cd build && ninja

# Instala no rootfs
sudo cp build/rjos-compositor ../../build/rootfs/usr/local/bin/
```

### 3. Gerar ISO

```bash
sudo ./scripts/mkiso.sh
```

### 4. Testar no QEMU

```bash
# Com ISO (não persiste)
./scripts/run.sh --iso

# Com disco persistente (recomendado após instalar)
./scripts/run.sh

# Com KVM (aceleração — apenas Linux)
./scripts/run.sh --kvm

# Com menos RAM (512MB)
./scripts/run.sh --ram 512
```

## No Windows (WSL2)

1. Instale WSL2 com Ubuntu: `wsl --install`
2. Dentro do WSL2, clone o repositório
3. Execute os scripts normalmente
4. O arquivo `RJOS.iso` gerado fica acessível em `/mnt/c/Users/.../RJOS/build/`
5. Abra o QEMU diretamente no Windows apontando para a ISO

## Estrutura de arquivos após o build

```
build/
├── rootfs/          ← Sistema Debian personalizado
│   ├── bin/
│   ├── etc/
│   ├── usr/
│   │   ├── local/bin/rjos         ← CLI
│   │   ├── local/bin/rjos-shell   ← Desktop shell
│   │   ├── local/bin/rjos-terminal
│   │   ├── local/bin/rjos-files
│   │   ├── local/bin/rjos-settings
│   │   └── local/bin/rjos-compositor
│   └── ...
├── iso-staging/     ← Staging da ISO
├── RJOS.iso         ← ISO final bootável
└── rjos-disk.img    ← Disco QEMU (16GB)
```

## Uso de RAM

O RJOS foi projetado para rodar em **≤ 1GB de RAM**:

| Componente         | RAM aprox. |
|--------------------|-----------|
| Kernel Linux       | ~30 MB     |
| systemd            | ~15 MB     |
| NetworkManager     | ~10 MB     |
| PipeWire           | ~10 MB     |
| rjos-compositor    | ~20 MB     |
| rjos-shell         | ~25 MB     |
| rjos-terminal      | ~20 MB     |
| Firefox (Flatpak)  | ~200-400 MB |
| **Total base**     | **~130 MB** |
| **Com navegador**  | **~500-700 MB** |

## Credenciais padrão (Live/teste)

- **Usuário:** `rjos`
- **Senha:** `rjos`
- **Root:** `sudo` com a senha acima

## Atalhos do compositor

| Atalho            | Ação                        |
|-------------------|----------------------------|
| `Super + T`       | Abre terminal               |
| `Super + F`       | Abre gerenciador de arquivos|
| `Super + Space`   | Abre launcher               |
| `Super + Q`       | Fecha janela                |
| `Super + M`       | Maximiza janela             |
| `Super + Tab`     | Alterna janelas             |
| `Super + ←`       | Janela na metade esquerda   |
| `Super + →`       | Janela na metade direita    |
| `Super + Shift+E` | Encerra compositor          |

## rjos CLI

```bash
# Instalar pacote (APT ou Flatpak automático)
sudo rjos install firefox

# Atualizar sistema
sudo rjos update
sudo rjos upgrade

# Info do sistema
rjos sysinfo

# Pesquisar
rjos search vlc
```
