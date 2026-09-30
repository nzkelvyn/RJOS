# RJOS — Guia de Desenvolvimento e Fluxo Git

Este documento define o padrão oficial de governança, branching, versionamento e commits para o projeto **RJOS (Rio de Janeiro Operating System)**.

---

## 1. Estrutura de Branches

O desenvolvimento do RJOS segue um modelo estruturado para garantir estabilidade, isolamento e rastreabilidade:

```
feature/* ──► demo ──► release/* ──► main
  ▲                                    │
  └───────────── hotfix/* ◄────────────┘
```

### Branches Principais

| Branch | Finalidade | Regras |
|---|---|---|
| `main` | Código estável de produção / releases oficiais. | Nunca commit diretamente. Recebe merges apenas de `release/*` ou `hotfix/*`. |
| `demo` | Ambiente de integração contínua e testes de novas features. | Ponto de encontro para validação de funcionalidades antes de uma release. |

### Feature Branches (`feature/*`)

Cada funcionalidade isolada possui sua própria branch:

| Branch | Área / Responsabilidade |
|---|---|
| `feature/desktop` | Shell GTK4, Wayland compositor (wlroots), dock, painel, temas, wallpapers e terminal |
| `feature/settings` | Painel de configurações (`rjos-settings`) e motor de personalização (`rjos-theme`) |
| `feature/explorer` | Gerenciador de arquivos (`rjos-files`) e integração com sistema de arquivos |
| `feature/login` | Gerenciador de display e greeter (`rjos-greeter`), sessão greetd/PAM |
| `feature/hardware` | Detecção de hardware, drivers, CPU, memória e sensores |
| `feature/input` | Teclados, layouts ABNT2, mouses, touchpads e atalhos globais |
| `feature/network` | Gerenciamento de Wi-Fi, Ethernet, conexões VPN e NetworkManager |
| `feature/audio` | Servidor de som PipeWire / PulseAudio, controle de volume e perfis |
| `feature/battery` | Leitura UPower, status de carregamento, consumo e perfis de energia |
| `feature/bluetooth` | Integração BlueZ, pareamento e dispositivos de áudio/periféricos |
| `feature/power` | Suspensão, hibernação, gerenciamento de energia e diálogo de desligamento |
| `feature/notifications` | Daemon de notificações (Desktop Notifications Spec) e central de avisos |
| `feature/update-system` | Atualizações de pacotes do sistema e patches de segurança |
| `feature/rjpm` | Gerenciador de pacotes RJOS (RJOS Package Manager) |
| `feature/installer` | Instalador do sistema para disco rígido / SSD |
| `feature/recovery` | Ambiente de recuperação, fallback de boot e snapshots |
| `feature/security` | AppArmor, regras Polkit, firewall (UFW) e integridade do sistema |

---

## 2. Padrão de Commits (Conventional Commits)

Todos os commits devem ser atômicos e seguir a convenção de commits semânticos:

```
<tipo>(<escopo>): <descrição no imperativo e em minúsculas>
```

### Tipos Permitidos
- `feat`: Nova funcionalidade.
- `fix`: Correção de bug.
- `refactor`: Refatoração interna que não altera comportamento.
- `style`: Ajustes visuais, formatação, espaçamento, CSS.
- `docs`: Documentação.
- `chore`: Tarefas de build, scripts de empacotamento, `.gitignore`.
- `perf`: Melhoria de performance ou consumo de recursos.

### Exemplos Válidos
```bash
feat(battery): adiciona leitura de nível via upower
feat(network): adiciona detecção de redes wi-fi
feat(desktop): implementa dock com indicador de app ativo
style(desktop): padroniza paleta oficial azul oceano e carvão
fix(settings): corrige persistência de tema no arquivo de configuração
docs(git): adiciona guia de fluxo de desenvolvimento
```

Evitar mensagens genéricas como `update`, `changes`, `fixes`, `teste`.

---

## 3. Padrão de Versionamento e Tags

O projeto adota **Semantic Versioning (SemVer)**: `MAJOR.MINOR.PATCH`

- **PATCH** (`0.1.0` → `0.1.1`): Correções de bugs e pequenos ajustes.
- **MINOR** (`0.1.1` → `0.2.0`): Novas funcionalidades sem quebrar compatibilidade.
- **MAJOR** (`0.x` → `1.0.0`): Marco estável de lançamento oficial do sistema.

### Tags de Releases e Features

Tags representam marcos concluídos e testados, nunca commits intermediários:
- Tags de Release do Sistema: `rjos-0.1.0-demo`, `rjos-0.2.0`, `rjos-1.0.0`
- Tags de Feature Concluída: `rjos-battery-0.1.0`, `rjos-desktop-0.1.0`, etc.

---

## 4. Fluxo de Integração e Releases

```
[Desenvolvimento na feature/*]
            │
            ▼
[Testes unitários e verificação local]
            │
            ▼
[Merge para a branch demo]
            │
            ▼
[Testes de integração e build de ISO]
            │
            ▼
[Criação da branch release/x.y.z]
            │
            ▼
[Validação final e testes com usuários]
            │
            ▼
[Merge para main + Tag rjos-x.y.z]
```

### Regras de Ouro
1. **Nunca faça merge sem testes**: Build, dependências e ausência de regressões devem ser verificados antes de integrar à `demo` ou `main`.
2. **Não altere histórico publicado**: Proibido `git reset --hard`, `git push --force` ou exclusão de histórico em branches compartilhadas.
3. **Hotfixes**: Para problemas críticos em produção, crie `hotfix/nome-do-problema` a partir da `main`. Após corrigir e testar, faça merge em `main` e propague para `demo`.
