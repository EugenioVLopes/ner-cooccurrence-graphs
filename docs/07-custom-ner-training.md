# Iteração 07 — Treinamento de NER customizado com spaCy

## O que mudou

Substituição do modelo NER genérico (`en_core_web_lg`) por um modelo spaCy
**fine-tunado** em labels específicos de software: `LIB`, `CLASS`, `FUNC`,
`TECH`, além de `PER`, `ORG`, `LOC` preservados do modelo base para evitar
_catastrophic forgetting_. Também foi otimizado o pipeline de construção de
grafo para usar `nlp.pipe` em batch.

## Motivação

A iteração 06 limpou o ruído do spaCy genérico, mas algumas limitações
permaneciam:

- `PowerShell`, `dom`, `sgr` continuavam marcados como `ORG`
- Bibliotecas pouco conhecidas (`scrollbox`, `ansi`, `zod`) só apareciam
  quando listadas no dicionário `KNOWN_LIBRARIES`
- O regex era rígido: só captura padrões explícitos (`import X from`,
  `class X`) e não generaliza para menções contextuais

A solução é treinar o próprio modelo a reconhecer entidades de código a
partir de exemplos reais.

## Arquivos criados/modificados

| Arquivo                     | Ação                                                                                              |
| --------------------------- | ------------------------------------------------------------------------------------------------- |
| `generate_training_data.py` | **Novo** — gera DocBin silver-labeled                                                             |
| `configs/config.cfg`        | **Novo** — config spaCy v3 (tok2vec + NER)                                                        |
| `Makefile`                  | **Novo** — targets `training-data`, `train`, `evaluate`                                           |
| `ner_pipeline.py`           | **Modificado** — parâmetros `custom_model` e `use_regex_fallback`; `extract_batch` usa `nlp.pipe` |
| `graph_builder.py`          | **Modificado** — coleta chunks antes e chama `extract_batch` uma vez                              |
| `.gitignore`                | **Modificado** — ignora `data/training/*.spacy` e `models/`                                       |

## Pipeline de treinamento

### 1. Geração de dados silver (`generate_training_data.py`)

- Lê `data/graphs/restored-src-extracted.jsonl` (78.526 blocos)
- Para cada bloco ≥ 50 chars:
  - Roda `extract_code_entities()` (regex + dicionário) → spans com labels
    `LIB`, `CLASS`, `FUNC`, `TECH`
  - Roda `en_core_web_lg` → spans com labels `PER`, `ORG`, `LOC`
    (preservados para evitar esquecimento catastrófico)
  - Re-localiza offsets para entradas de dicionário via `\b<termo>\b`
  - Resolve sobreposições com `spacy.util.filter_spans` (mantém o maior)
- Filtra docs vazios, divide 80/20, serializa em `DocBin`

**Saída:**

- `data/training/train.spacy` — 13.428 docs
- `data/training/dev.spacy` — 3.357 docs
- ~23.500 entidades totais distribuídas:

| Label | Quantidade |
| ----- | ---------- |
| ORG   | 7.105      |
| TECH  | 6.172      |
| FUNC  | 4.144      |
| LIB   | 3.245      |
| PER   | 1.374      |
| CLASS | 855        |
| LOC   | 605        |

### 2. Configuração de treino (`configs/config.cfg`)

- Base: `python -m spacy init config --pipeline ner --lang en`
- `[paths] vectors = "en_core_web_lg"` — transfere embeddings estáticos
- Pipeline: `["tok2vec", "ner"]` — cabeças frescas (não reaproveita NER do base)
- `max_epochs = 20`, `patience = 1600`, `eval_frequency = 400`
- `batch_size` com scheduler `compounding.v1` (100 → 3000)
- Optimizer: Adam com `learn_rate = 0.001`, `L2 = 0.01`

### 3. Makefile

Targets principais:

```make
training-data: gera .spacy
train:         spacy train configs/config.cfg → models/custom-ner
evaluate:      spacy evaluate → models/custom-ner/metrics.json
clean-training: remove binários gerados
```

## Métricas do modelo (dev set)

Avaliação após `make train` (em `models/custom-ner/metrics.json`):

| Label     | Precision | Recall    | F1        |
| --------- | --------- | --------- | --------- |
| **FUNC**  | 0,993     | 0,982     | **0,987** |
| **LIB**   | 0,988     | 0,968     | **0,978** |
| **TECH**  | 0,925     | 0,925     | **0,925** |
| **CLASS** | 0,913     | 0,926     | **0,919** |
| **ORG**   | 0,823     | 0,788     | **0,805** |
| **PER**   | 0,673     | 0,637     | **0,655** |
| **LOC**   | 0,588     | 0,407     | **0,481** |
| **Geral** | **0,892** | **0,866** | **0,879** |

**Observações:**

- Labels de código (`FUNC`, `LIB`, `TECH`, `CLASS`) ficam acima de 0,90 —
  confirma que o silver labeling do regex é de boa qualidade para esses tipos
- `ORG`, `PER`, `LOC` ficam abaixo porque os exemplos vêm do próprio
  `en_core_web_lg`, então o modelo só aprende a replicar (e às vezes errar)
  o que o base já fazia
- `LOC` tem o menor F1 (0,48) — entidades geográficas são raras em código e
  tendem a ser ruído (nomes de cidades em comentários/docs)
- Velocidade: **5510 palavras/s** — adequado para processar o repositório

## Otimização: batch real com `nlp.pipe`

O `graph_builder.py` original chamava `pipeline.extract(chunk)` em loop,
executando `nlp(text)` individualmente para cada chunk. Com 138k chunks de
sentença isso levaria horas.

**Refatoração:**

1. `ner_pipeline.py` — `extract_batch()` agora:
   - Coleta textos truncados
   - Usa `self.nlp.pipe(texts, batch_size=64)` (batching real)
   - Aplica regex por item em paralelo
2. `graph_builder.py` — `build_cooccurrence_graph()` agora:
   - Achata todos os chunks antes do processamento
   - Faz uma única chamada a `extract_batch`
   - Itera sobre os resultados para construir o grafo

Resultado: as 3 granularidades processam em **poucos minutos** em vez de
uma hora.

## Métricas do grafo (iter-07 vs iter-06)

### Tamanho

| Granularidade | Nós (06) | Nós (07) | Δ    | Arestas (06) | Arestas (07) | Δ    |
| ------------- | -------- | -------- | ---- | ------------ | ------------ | ---- |
| Sentença      | 1.887    | 1.520    | −19% | 2.696        | 2.292        | −15% |
| Parágrafo     | 3.132    | 2.519    | −20% | 9.109        | 7.095        | −22% |
| K-chars (500) | 3.145    | 2.510    | −20% | 6.899        | 5.568        | −19% |

A redução (~20%) vem do modelo ter aprendido a **não** rotular fragmentos
genéricos que o regex capturava às cegas via dicionário.

### Parágrafo (grafo principal)

| Métrica              | 06 (filtrado) | 07 (custom NER) |
| -------------------- | ------------- | --------------- |
| Nós                  | 3.132         | 2.519           |
| Arestas              | 9.109         | 7.095           |
| Densidade            | 0,0019        | 0,0022          |
| Grau médio           | —             | 5,63            |
| Diâmetro             | 11            | 12              |
| Caminho médio        | 3,71          | 3,66            |
| Clustering médio     | 0,53          | 0,50            |
| Transitividade       | 0,14          | 0,13            |
| Componentes          | ~120          | 83              |
| Maior componente (%) | 84%           | 86%             |
| Comunidades Louvain  | —             | 128             |
| Modularity           | —             | 0,628           |

**Destaques:**

- **Menos componentes** (83 vs ~120): remoção de entidades espúrias que
  formavam ilhas
- **Densidade ligeiramente maior** (0,0022 vs 0,0019): mesmo tendo menos nós
  e arestas, a proporção é maior — o grafo é mais "concentrado"
- **Maior componente cobre 86%**: melhor conectividade global
- **Clustering mantido alto** (0,50): a estrutura de vizinhança coesa
  persistiu

### Top 10 entidades por grau (parágrafo)

| Entidade  | Tipo | Grau (07) | Grau (06) |
| --------- | ---- | --------- | --------- |
| claude    | LIB  | 423       | 496       |
| api       | TECH | 334       | 400       |
| git       | TECH | 252       | 296       |
| mcp       | TECH | 233       | 266       |
| windows   | TECH | 173       | 195       |
| cli       | TECH | 171       | 191       |
| anthropic | LIB  | 166       | 189       |
| oauth     | TECH | 158       | 204       |
| github    | TECH | 155       | 183       |
| macos     | TECH | 123       | 145       |

O ranking é praticamente idêntico ao da iter-06, confirmando que o modelo
aprendeu os termos certos como centrais. Os graus absolutos diminuíram
proporcionalmente à poda de ruído.

### Comunidades Louvain (parágrafo, iter-07)

| Comunidade | Nós | Tema                    | Membros principais                       |
| ---------- | --- | ----------------------- | ---------------------------------------- |
| C0         | 613 | Core Claude + CLI + MCP | claude, api, mcp, oauth, cli             |
| C1         | 255 | Cross-platform OS       | windows, macos, linux, powershell, wsl   |
| C2         | 214 | UI rendering            | ink, react, scrollbox, ansi, dom         |
| C3         | 198 | Git + networking        | git, github, dns, docker, unc            |
| C4         | 152 | Feature flags + auth    | growthbook, axios, cse, ttl, accesstoken |

As comunidades permanecem temáticas e coerentes. A iter-07 captura novas
entidades (`ansi`, `dom`, `unc`, `cse`) que o dicionário do iter-06 não
incluía.

### Comparativo entre granularidades (iter-07)

| Granularidade | Nós   | Arestas | Densidade | Clustering | Modularity | Comunidades |
| ------------- | ----- | ------- | --------- | ---------- | ---------- | ----------- |
| sentence      | 1.520 | 2.292   | 0,0020    | 0,287      | 0,752      | 114         |
| paragraph     | 2.519 | 7.095   | 0,0022    | 0,500      | 0,628      | 128         |
| k_chars       | 2.510 | 5.568   | 0,0018    | 0,465      | 0,655      | 131         |

- **sentence**: grafo mais esparso, modularity mais alto (0,75) porque
  janelas pequenas capturam co-ocorrências mais específicas
- **paragraph**: melhor equilíbrio — alto clustering, mais conexões
- **k_chars**: intermediário; janela fixa gera co-ocorrências artificiais
  entre entidades de tópicos distintos, reduzindo clustering

## Limitações do silver labeling

O modelo foi treinado com anotações geradas automaticamente, não revisadas
manualmente. Isso implica:

1. **Tetos de performance herdados do regex**: o modelo não aprende
   entidades que o regex/dicionário nunca marcou
2. **Propagação de erros**: se o regex confunde `node` (ferramenta) com
   `node` (nó de grafo), o modelo herda a confusão
3. **Viés de cobertura**: labels com muitos exemplos (`TECH`, `ORG`)
   aprendem melhor; `LOC` (605 exemplos) tem F1 apenas 0,48

Para uma iteração futura, um conjunto **gold** anotado manualmente em
~500 blocos traria ganhos reais, especialmente para `CLASS` e `FUNC` onde
o contexto importa muito.

## Figuras geradas

| Arquivo                                                    | Conteúdo                                |
| ---------------------------------------------------------- | --------------------------------------- |
| `figures/07-custom-ner-training/degree_dist_*.png`         | Distribuição de grau                    |
| `figures/07-custom-ner-training/graph_viz_*.png`           | Grafo colorido por tipo                 |
| `figures/07-custom-ner-training/communities_*.png`         | Grafo colorido por comunidade           |
| `figures/07-custom-ner-training/community_sizes_*.png`     | Tamanhos de comunidades                 |
| `figures/07-custom-ner-training/comparison_table.png`      | Tabela comparativa entre granularidades |
| `figures/07-custom-ner-training/centrality_comparison.png` | Top entidades por centralidade          |
| `figures/07-custom-ner-training/interactive_*.html`        | Visualizações interativas (pyvis)       |
| `figures/07-custom-ner-training/metrics.json`              | Métricas numéricas exportadas           |

## Reprodução

```bash
# 1. Gerar dados silver
make training-data

# 2. Treinar (50 min em CPU)
make train

# 3. Avaliar no dev set
make evaluate

# 4. Gerar grafos com modelo custom
uv run python graph_builder.py data/raw/claude-code-sourcemap \
  --input-jsonl data/graphs/restored-src-extracted.jsonl \
  --custom-model models/custom-ner/model-best \
  --output-dir data/graphs/07-custom

# 5. Analisar
uv run python -c "
from graph_builder import load_graph
from analysis import full_analysis
graphs = {n: load_graph(f'data/graphs/07-custom/graph_{n}.gexf')
          for n in ['sentence','paragraph','k_chars']}
full_analysis(graphs, output_dir='figures/07-custom-ner-training')
"
```
