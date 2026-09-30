# 🚀 RJOS 0.1.2 - Foundation Update

O RJOS atingiu um de seus maiores marcos com a versão **0.1.2 — Foundation Update**. Esta atualização constrói o alicerce para tornar o RJOS não apenas uma interface visual customizada, mas um sistema operacional verdadeiramente resiliente, conectado e autossuficiente.

---

## 🌟 Destaques da Atualização (Focos Principais)

### 1. Desktop Moderno e Unificado
- **Linguagem Visual 100% Integrada:** Os componentes de sistema agora falam a mesma língua. O `Quick Settings`, `App Launcher`, `Wallpaper Manager` e o `Desktop Icons` foram reescritos para utilizar nativamente as variáveis do `rjos_theme.py`.
- **Efeitos Premium:** O *glassmorphism* (fundo translúcido com desfoque) e bordas suaves foram aplicados globalmente a janelas utilitárias, garantindo consistência com o Topbar.

### 2. Sistema de Atualizações Online
- **Recebimento OTA (Over-The-Air):** O RJOS não depende mais de reinstalações da ISO inteira para receber pacotes! O novo módulo `rjos-update-daemon` faz a varredura automática através da rede.
- **Update Center (GUI):** O usuário agora possui um painel gráfico construído em GTK4 amigável e nativo para descobrir, ler o *changelog* e aprovar as instalações de novas versões através do botão "Atualizar".
- **Integração Online:** A origem do sistema consome diretamente o endpoint estático publicado em `https://nzkelvyn.github.io/RJOS/updates`, permitindo distribuir pacotes em larga escala com custo zero de infraestrutura.

### 3. Infraestrutura A/B e Rollback (Snapshots)
- **Segurança de Atualização:** Implementada a abstração (através do `rjpm.py` e `snapshot.py`) para atualizações transacionais.
- O sistema tira um Snapshot antes de invocar o `apt` local; caso um update falhe na rede, o rollback é instantaneamente acionado para evitar "telas pretas" (Kernel Panic) ou falhas no compositor wlroots.
- Base estrutural pronta para cenários de **Imutabilidade de Partições (A/B)** no bootloader.

### 4. Diagnósticos e Pre-Flight
- Implementada a arquitetura inteligente de *Pre-Flight Checks*. O RJOS analisa a saúde do computador e bloqueia atualizações perigosas avisando o usuário se:
  - O HD tiver menos de 1GB de espaço livre.
  - O notebook estiver desplugado e com menos de 20% de bateria.
  - A conexão com a internet atual for provida por ancoragem móvel (4G/5G).

---

## 🛠️ O Que Vem a Seguir?
Com a fundação criada, a Próxima Fase abordará componentes massivos para a usabilidade de Desktop do dia a dia:
1. **Loja de Aplicativos (App Store):** Integradora de Flatpak para aplicativos seguros de usabilidade geral.
2. **Gerenciador de Arquivos RJOS:** Um navegador de pastas moderno em GTK4/Adwaita.
3. **Módulo de Configurações do Sistema (Settings):** Expansão do Quick Settings para painel global de rede, displays e contas de usuário.
