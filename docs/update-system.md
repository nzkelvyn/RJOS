# Sistema de Atualização do RJOS

## Arquitetura
O sistema de atualização do RJOS é desenhado para ser modular, descentralizado e integrado. 

A arquitetura atual possui os seguintes componentes principais:
1. **rjos-update-daemon**: Executa em background, gerenciado pelo systemd, verificando periodicamente se há atualizações.
2. **rjos-update (CLI)**: Permite ao usuário verificar, visualizar informações, instalar atualizações e consultar o histórico.
3. **rjos-update-center (GUI)**: Interface amigável no Desktop baseada em GTK4 que apresenta as atualizações, o changelog e permite a instalação de forma suave.
4. **rjpm (RJOS Package Manager)**: O backend abstrato de gerenciamento de pacotes (atualmente fazendo chamadas a `apt`, preparado para uma evolução futura).

## Fluxo (Update Flow)
1. O timer do systemd aciona o daemon.
2. O daemon consulta o metadata YAML no servidor HTTP remoto.
3. As versões são comparadas de forma semântica (0.1.1 < 0.1.2).
4. O usuário é notificado.
5. O usuário abre o Update Center e clica em Atualizar.
6. O Update Center delega para a CLI e, subsequentemente, para o `rjpm`.
7. O histórico é atualizado no cache local.

## Canais (Channels) e Metadata
Suportamos atualmente canais `stable` e `demo`. 
O metadata está estruturado em arquivos `.yaml` (`latest.yaml`, e `releases/{version}.yaml`). 

## Segurança e Performance
O sistema não baixa ISOs completas. Apenas os pacotes que foram atualizados via `rjpm` são modificados. Nenhum código arbitrário do YAML é executado; o YAML apenas instrui o frontend de pacote.
O daemon usa timers, garantindo baixo consumo de CPU e banda.

## Futuro (Repositório APT)
A estrutura de abstração do `UpdateSource` está preparada para suportar `AptUpdateSource` ou repositórios mais sofisticados no futuro (como repo.rjos.org).
