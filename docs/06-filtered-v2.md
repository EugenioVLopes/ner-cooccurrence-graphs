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

### 5. Filtro de prefixos em português

O extractor gera descrições como `"Função getSkills"` e `"Parâmetros FpsMetrics"`.
O spaCy interpretava essas frases como entidades (ORG/PER). Adicionado filtro
para rejeitar entidades que começam com `função`, `parâmetros`, `classe`, `método`
ou `retorna`.

### 6. Restrição do regex CamelCase

O padrão que capturava qualquer `PascalCase` como CLASS gerava milhares de nós
para classes internas sem valor semântico (`ProcessUserInputBaseResult`,
`FilterToolProgressMessages`). Agora só captura CamelCase precedido por
palavras-chave de declaração: `class`, `interface`, `type`, `extends`,
`implements`, `new`, `import`.

### 7. Remoção de ilhas (componentes pequenos)

Adicionado `min_component_size=3` ao `CoOccurrenceConfig` no `graph_builder.py`.
Componentes conectados com menos de 3 nós são removidos do grafo, eliminando
pares isolados que não contribuem para a análise de co-ocorrência.

## Comparação de métricas

### Tamanho dos grafos

| Granularidade | Nós (05) | Nós (06) | Arestas (05) | Arestas (06) |
| --- | --- | --- | --- | --- |
| Sentença | 5.791 | 1.907 (-67%) | 5.947 | 2.748 (-54%) |
| Parágrafo | 7.746 | 3.163 (-59%) | 22.552 | 9.211 (-59%) |
| K-chars (500) | 7.845 | 3.156 (-60%) | 15.160 | 6.926 (-54%) |

A redução drástica se deve a três fatores combinados: filtragem de ruído do
spaCy, restrição do CamelCase, e remoção de componentes pequenos. As entidades
restantes são semanticamente relevantes.

### Métricas gerais (parágrafo)

| Métrica | 05 (com ruído) | 06 (filtrado) |
| --- | --- | --- |
| Nós | 7.746 | 3.163 |
| Arestas | 22.552 | 9.211 |
| Densidade | 0,0008 | 0,0018 |
| Diâmetro | — | 11 |
| Caminho médio | — | 3,71 |
| Clustering médio | — | 0,5253 |
| Transitividade | — | 0,1446 |
| Componentes | — | 121 |
| Maior componente | — | 2.664 (84%) |

Destaques:
- **Densidade dobrou** (0,0008 → 0,0018): grafo mais conectado sem ruído
- **Clustering subiu** (→ 0,53): vizinhança dos nós é mais coesa
- **Maior componente cobre 84%** do grafo (vs ~57% antes)
- **Apenas 121 componentes** (vs ~1.200 antes)

### Top 10 entidades (parágrafo)

| Entidade | Tipo | Grau |
| --- | --- | --- |
| claude | LIB | 496 |
| api | TECH | 400 |
| git | TECH | 296 |
| mcp | TECH | 266 |
| oauth | TECH | 204 |
| windows | TECH | 195 |
| cli | TECH | 191 |
| anthropic | LIB | 189 |
| github | TECH | 183 |
| macos | TECH | 145 |

Nota: `cli` e `bash` agora aparecem corretamente como TECH em vez de ORG/PER.

### Comunidades Louvain (parágrafo)

| Comunidade | Nós | Tema | Membros principais |
| --- | --- | --- | --- |
| C0 | 432 | Git e cross-platform | git, windows, powershell, github, macos |
| C1 | 428 | Core CLI + MCP | claude, mcp, cli, repl, lsp |
| C2 | 282 | Autenticação | oauth, growthbook, ttl, jwt, ccr |
| C3 | 281 | API e linguagens | api, anthropic, python, javascript |
| C4 | 267 | UI rendering | ink, react, scrollbox, chalk, sgr |

## Análise

### Qualidade do grafo

A remoção de ruído melhorou significativamente a qualidade:

- **Comunidades mais coerentes**: sem nós de lixo misturados nos clusters
- **Centralidades mais confiáveis**: as entidades mais centrais são todas
  semanticamente relevantes (claude, api, git, mcp, anthropic)
- **Grafo mais denso e conexo**: remoção de ilhas resultou em 84% dos nós
  no componente principal (vs ~57% antes)
- **Clustering alto** (0,53): indica que vizinhos tendem a estar conectados
  entre si — estrutura de comunidades real, não artefato

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
