# Relatório 04 — Detecção de Comunidades (Louvain)

## O que mudou

- Adicionada detecção de comunidades com algoritmo de Louvain (`python-louvain`)
  ao `analysis.py`.
- Novas visualizações: grafo colorido por comunidade e distribuição de tamanhos.
- `full_analysis()` agora inclui comunidades automaticamente.

## Resultados por granularidade

### Sentença

- **1.521 comunidades** | Modularity: **0,8538**
- Alta modularidade indica estrutura de comunidades muito bem definida,
  mas muitas comunidades pequenas (grafo esparso).

| Comunidade | Nós | Tema                         | Membros principais                            |
|------------|-----|------------------------------|-----------------------------------------------|
| C0         | 490 | API e autenticação           | api, claude, oauth, anthropic, cli            |
| C1         | 273 | MCP (Model Context Protocol) | mcp, zod, json, ScopedMcpServerConfig         |
| C2         | 250 | Cross-platform / OS          | windows, macos, linux, powershell, wsl        |
| C3         | 208 | UI (React/Ink)               | react, ink, repl, ansi, tsx                   |
| C4         | 175 | Git e integrações            | git, github, rest, gitlab                     |

### Parágrafo

- **1.367 comunidades** | Modularity: **0,7252**
- Modularity menor que sentença — chunks maiores mesclam mais entidades,
  gerando comunidades menos separadas.

| Comunidade | Nós   | Tema                         | Membros principais                            |
|------------|-------|------------------------------|-----------------------------------------------|
| C0         | 1.296 | Core (API + auth + MCP)      | claude, api, mcp, oauth, cli                  |
| C1         | 691   | Git e cross-platform         | git, windows, github, powershell, macos       |
| C2         | 391   | UI rendering                 | ink, ScrollBox, DOM, SGR, ScrollTop           |
| C3         | 354   | State e tools                | AppState, AbortSignal, ToolUseContext, AgentTool |
| C4         | 226   | Misc / temporal              | java, utc, month                              |

### K-chars (500)

- **1.408 comunidades** | Modularity: **0,7435**

| Comunidade | Nós | Tema                         | Membros principais                            |
|------------|-----|------------------------------|-----------------------------------------------|
| C0         | 991 | Core (API + git)             | claude, api, git, cli, github                 |
| C1         | 509 | Cross-platform / shell       | windows, macos, powershell, linux, BashTool   |
| C2         | 410 | Autenticação                 | oauth, jwt, 401, axios                        |
| C3         | 312 | MCP                          | mcp, ScopedMcpServerConfig, lsp               |
| C4         | 301 | UI rendering                 | ink, ScrollBox, SGR, DOM, ANSI                |

## Análise dos clusters temáticos

### Clusters consistentes entre granularidades

Independente da granularidade, os mesmos temas emergem:

1. **Core / API** — `claude`, `api`, `anthropic`, `cli`. O núcleo da
   aplicação: comunicação com a API da Anthropic.

2. **MCP (Model Context Protocol)** — `mcp`, `zod`, `ScopedMcpServerConfig`.
   Subsistema de integração com servidores MCP para ferramentas externas.

3. **Cross-platform / OS** — `windows`, `macos`, `linux`, `powershell`, `wsl`.
   Camada de compatibilidade multi-plataforma.

4. **UI (React/Ink)** — `react`, `ink`, `ScrollBox`, `ANSI`, `SGR`.
   Interface de terminal construída com Ink (React para CLI).

5. **Git** — `git`, `github`, `gitlab`, `rest`.
   Integração com controle de versão.

6. **Autenticação** — `oauth`, `jwt`, `anthropic`.
   Subsistema de login e tokens.

### Separação por granularidade

- **Sentença** produz a melhor separação temática (modularity 0,85) — cada
  cluster é mais focado, mas perde conexões entre subsistemas.
- **Parágrafo** mescla temas no cluster C0 (API + MCP + auth juntos) — reflete
  que esses subsistemas são mencionados juntos nos mesmos blocos de código.
- **K-chars** fica entre os dois, com OAuth se separando como cluster próprio.

### Insight arquitetural

A detecção de comunidades revela a arquitetura do Claude Code:
- Um **core** de API/auth fortemente conectado
- **Subsistemas satélite** (MCP, UI, Git, OS) com interfaces claras
- A camada de **UI** é surpreendentemente isolada — pouca co-ocorrência com
  a camada de API, sugerindo boa separação de responsabilidades.

## Figuras geradas

| Arquivo                                  | Conteúdo                               |
|------------------------------------------|----------------------------------------|
| `figures/04-louvain/communities_*.png`   | Grafo colorido por comunidade Louvain  |
| `figures/04-louvain/community_sizes_*.png` | Distribuição de tamanhos             |
| `figures/04-louvain/degree_dist_*.png`   | Distribuição de grau                   |
| `figures/04-louvain/graph_viz_*.png`     | Grafo colorido por tipo de entidade    |
| `figures/04-louvain/comparison_table.png`| Tabela comparativa                     |
| `figures/04-louvain/centrality_comparison.png` | Top entidades por centralidade   |
