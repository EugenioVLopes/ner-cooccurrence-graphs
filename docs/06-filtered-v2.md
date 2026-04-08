# Iteração 06 — Filtragem avançada de ruído NER

## O que mudou

Adição de filtros robustos no `ner_pipeline.py` para eliminar entidades
espúrias que o spaCy classificava incorretamente a partir de fragmentos de
código TypeScript/JavaScript.

## Problema identificado

A análise da iteração 05 revelou que o grafo de co-ocorrência continha
**centenas de nós de ruído** provenientes do spaCy, que interpretava trechos
de código como entidades nomeadas:

| Tipo de ruído | Qtd nós | Exemplos |
| --- | --- | --- |
| Fragmentos de código | 281 | `&& !`, `undefined && !`, `const wsurl = buildsdkurl(...)` |
| URLs/paths/comentários | 337 | `// suffix`, `ios/android`, `http://` |
| Números puros | 199 | `404`, `401`, `22803`, `60_000` |
| Palavras numéricas | 9 | `zero`, `non-zero`, `four`, `half` |
| PER errado (tools) | ~20 | `bash` como pessoa, `date.now`, `accesstoken` |
| ORG errado (siglas tech) | ~30 | `json`, `cli`, `sse`, `ttl`, `uuid` |
| Funções com nome <= 2 chars | 7 | `to`, `is`, `on`, `in` |

## Filtros implementados

### 1. Detector de ruído (`_is_noise()`)

Função que rejeita entidades contendo:

- Caracteres de código: `& | = { } < > ( ) $ ~ ^ ;`
- Padrões de código: `&&`, `||`, `=>`, `${}`, `.write`, `const`, `import(`, `.js`
- Números puros e HTTP status codes
- Padrões numéricos com unidades (`15s`, `300s`, `60_000`, `10 min`)
- Entidades multi-linha (quebra de linha no texto)
- Início com `//`, `/*`, `#`, `~:`, `≈`
- Entidades com menos de 3 caracteres

### 2. Reclassificação de entidades

| Entidade | spaCy dizia | Corrigido para | Razão |
| --- | --- | --- | --- |
| `json`, `xml`, `yaml`, `css`, `html`, `tsx` | ORG | TECH | São formatos/tecnologias |
| `cli`, `sse`, `ttl`, `uuid`, `auth`, `repl`, `lsp`, `wsl` | ORG | TECH | São siglas técnicas |
| `bash`, `curl`, `grep`, `npm`, `node`, `yarn` | PER | TECH | São ferramentas/comandos |

### 3. Expansão de stopwords

Adicionadas palavras numéricas (`zero`, `four`, `half`), tags de comentário
(`todo`, `fixme`), termos genéricos (`remote control`, `status code`, `post`),
e palavras de 2 letras (`to`, `is`, `on`, `in`).

### 4. Filtro no regex de funções

O padrão `function nome` agora rejeita nomes com <= 2 caracteres e nomes
presentes no STOPWORDS.

## Comparação de métricas

### Tamanho dos grafos

| Granularidade | Nós (05) | Nós (06) | Arestas (05) | Arestas (06) |
| --- | --- | --- | --- | --- |
| Sentença | 5.791 | 5.192 (-10%) | 5.947 | 5.118 (-14%) |
| Parágrafo | 7.746 | 6.644 (-14%) | 22.552 | 15.480 (-31%) |
| K-chars (500) | 7.845 | 6.742 (-14%) | 15.160 | 12.167 (-20%) |

A redução de ~31% nas arestas do parágrafo indica que muitas co-ocorrências
eram entre entidades legítimas e nós de ruído, inflando artificialmente a
conectividade.

### Métricas gerais (parágrafo)

| Métrica | 05 (com ruído) | 06 (filtrado) |
| --- | --- | --- |
| Nós | 7.746 | 6.644 |
| Arestas | 22.552 | 15.480 |
| Densidade | 0,0008 | 0,0007 |
| Diâmetro | — | 12 |
| Caminho médio | — | 3,97 |
| Clustering médio | — | 0,3663 |
| Transitividade | — | 0,1868 |
| Componentes | — | 1.220 |
| Maior componente | — | 3.809 (57%) |

### Top 10 entidades (parágrafo)

| Entidade | Tipo | Grau |
| --- | --- | --- |
| claude | LIB | 558 |
| api | TECH | 449 |
| git | TECH | 333 |
| mcp | TECH | 319 |
| anthropic | LIB | 245 |
| oauth | TECH | 229 |
| cli | TECH | 223 |
| windows | TECH | 219 |
| github | TECH | 204 |
| macos | TECH | 156 |

Nota: `cli` e `bash` agora aparecem corretamente como TECH em vez de ORG/PER.

### Comunidades Louvain (parágrafo)

| Comunidade | Nós | Tema | Membros principais |
| --- | --- | --- | --- |
| C0 | 964 | Core (API + auth + MCP) | claude, api, mcp, oauth, cli |
| C1 | 306 | Cross-platform / OS | windows, macos, linux, powershell |
| C2 | 305 | UI rendering | ink, ScrollBox, DOM, SGR |
| C3 | 294 | State e tools | AppState, AbortSignal, ToolUseContext |
| C4 | 273 | Git e integrações | git, github, bash, BashTool |

## Análise

### Qualidade do grafo

A remoção de ruído melhorou significativamente a qualidade:

- **Comunidades mais coerentes**: sem nós de lixo misturados nos clusters
- **Centralidades mais confiáveis**: as entidades mais centrais são todas
  semanticamente relevantes (claude, api, git, mcp, anthropic)
- **Densidade mais realista**: a redução de 31% nas arestas do parágrafo
  mostra que a conectividade estava inflada por fragmentos de código

### Limitações remanescentes

- **PowerShell como ORG**: o spaCy insiste em classificar como organização;
  poderia ser reclassificado para TECH
- **Entidades genéricas do spaCy**: algumas entidades como `dom`, `sgr`,
  `posix` ainda são classificadas como ORG
- O modelo `en_core_web_lg` não foi treinado para código — uma iteração futura
  com custom training resolveria esses casos restantes

## Figuras geradas

| Arquivo | Conteúdo |
| --- | --- |
| `figures/06-filtered-v2/degree_dist_*.png` | Distribuição de grau |
| `figures/06-filtered-v2/graph_viz_*.png` | Grafo colorido por tipo |
| `figures/06-filtered-v2/communities_*.png` | Grafo colorido por comunidade |
| `figures/06-filtered-v2/community_sizes_*.png` | Distribuição de tamanhos |
| `figures/06-filtered-v2/comparison_table.png` | Tabela comparativa |
| `figures/06-filtered-v2/centrality_comparison.png` | Top entidades por centralidade |
| `figures/06-filtered-v2/interactive_*.html` | Visualizações interativas (pyvis) |
