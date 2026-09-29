# RJOS — A Linux Distribution Built From Scratch

<div align="center">

```
██████╗      ██╗ ██████╗ ███████╗
██╔══██╗     ██║██╔═══██╗██╔════╝
██████╔╝     ██║██║   ██║███████╗
██╔══██╗██   ██║██║   ██║╚════██║
██║  ██║╚█████╔╝╚██████╔╝███████║
╚═╝  ╚═╝ ╚════╝  ╚═════╝ ╚══════╝
```

**Uma distribuição Linux com identidade própria**

![Status](https://img.shields.io/badge/status-Phase%201%20%E2%80%94%20Base-blue)
![Base](https://img.shields.io/badge/base-Debian%20Stable-red)
![Display](https://img.shields.io/badge/display-Wayland-purple)
![Compositor](https://img.shields.io/badge/compositor-wlroots-cyan)

</div>

---

## O que é o RJOS?

RJOS é uma distribuição Linux construída do zero com identidade visual e experiência próprias.
Não é um reskin de outra distro — é uma distribuição montada peça a peça com controle total sobre cada camada.

## Stack Tecnológico

| Camada | Tecnologia |
|--------|-----------|
| Base | Debian (debootstrap) |
| Kernel | Linux 6.x |
| Init | systemd |
| Áudio | PipeWire + WirePlumber |
| Rede | NetworkManager |
| Display | Wayland |
| Compositor | wlroots (C) |
| Toolkit | GTK4 |
| Tema | CSS GTK4 personalizado |

## Início Rápido

```bash
# Construir o sistema (requer Linux/WSL2 com dependências)
./scripts/build.sh

# Executar no QEMU
./scripts/run.sh

# Gerar ISO
./scripts/mkiso.sh

# Limpar build
./scripts/clean.sh
```

## Fases do Projeto

- [x] **Fase 0** — Análise e arquitetura
- [ ] **Fase 1** — Base: kernel, boot, terminal, rede
- [ ] **Fase 2** — Desktop: Wayland, compositor, janelas
- [ ] **Fase 3** — Apps: terminal, files, settings, browser
- [ ] **Fase 4** — Sistema: updates, users, security
- [ ] **Fase 5** — Identidade visual completa
- [ ] **Fase 6** — ISO, instalador, documentação

## Estrutura do Projeto

```
RJOS/
├── build/          # Artefatos de build
├── config/         # Configurações do sistema
├── desktop/        # Compositor, shell, temas
├── apps/           # Aplicativos nativos
├── system/         # Ferramentas de sistema
├── icons/          # Ícones RJOS
├── installer/      # Instalador gráfico
├── scripts/        # Scripts de build
└── docs/           # Documentação
```

## Requisitos para Build

O build do RJOS deve ser feito em um host Linux (ou WSL2 no Windows):

```bash
# Ubuntu/Debian host
sudo apt install debootstrap qemu-system-x86 xorriso \
  squashfs-tools meson ninja-build gcc pkg-config \
  libwlroots-dev libgtk-4-dev git
```

## Documentação

- [Arquitetura](docs/architecture.md)
- [Como buildar](docs/building.md)
- [Desenvolvimento de apps](docs/developing.md)

---

<div align="center">
RJOS — Construído com ❤️ e muito código C
</div>
