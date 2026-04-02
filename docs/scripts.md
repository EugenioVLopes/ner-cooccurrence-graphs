# Documentação dos Scripts

## extractor.py

Extrai texto estruturado de repositórios TypeScript. Percorre a árvore de
diretórios e processa arquivos `.ts`, `.tsx` e documentação (`.md`, `.txt`,
`.rst`).

### Estruturas extraídas de TypeScript

| Tipo        | O que captura                                |
| ----------- | -------------------------------------------- |
| `import`    | `import ... from 'pkg'` e `import 'pkg'`     |
| `code`      | Classes, interfaces, types, enums exportados |
| `code`      | `function` e `const fn = () =>` exportados   |
| `comment`   | Comentários de linha (`//`)                  |
| `docstring` | Blocos `/** ... */` e `/* ... */` (JSDoc)    |
| `markdown`  | Seções divididas por headers `#`             |

### Classes e dataclasses

- **`ExtractedText`** — bloco de texto com metadados (`text`, `source_file`,
  `source_type`, `line_start`, `line_end`).
- **`RepoExtraction`** — resultado completo da extração. Propriedades:
  `all_text`, `by_type`. Método `save_jsonl()` para persistir.

### Funções principais

- `extract_typescript(source_code, filepath)` — regex-based extraction de um
  arquivo TS/TSX.
- `extract_markdown(filepath)` — divide markdown por seções (`#`).
- `extract_repository(repo_path, extensions=None)` — pipeline principal.
  Default: `.ts`, `.tsx`, `.md`, `.txt`, `.rst`.
- `load_jsonl_extractions(input_path, repo_path)` — carrega extrações salvas em
  JSONL.

### CLI

```bash
uv run python extractor.py <repo_path> [--out-jsonl <output.jsonl>]
```

---

## ner_pipeline.py

Pipeline de Named Entity Recognition combinando spaCy (opcional) com extração
customizada via regex e dicionários.

### Categorias de entidades

| Label   | Descrição                       | Fonte              |
| ------- | ------------------------------- | ------------------ |
| `LIB`   | Biblioteca/pacote npm           | regex + dicionário |
| `CLASS` | Classe ou tipo CamelCase        | regex              |
| `FUNC`  | Função                          | regex              |
| `TECH`  | Tecnologia (linguagem, DB, etc) | dicionário         |
| `PER`   | Pessoa                          | spaCy              |
| `ORG`   | Organização                     | spaCy              |
| `LOC`   | Localização                     | spaCy              |
| `MISC`  | Outros                          | spaCy              |

### Dicionários

- **`KNOWN_LIBRARIES`** — ~60 pacotes npm (react, zod, prisma, anthropic, etc).
- **`KNOWN_TECH`** — ~50 tecnologias (typescript, docker, postgresql, llm, etc).

### Classe `NERPipeline`

- `__init__(spacy_model, use_spacy)` — carrega modelo spaCy (opcional).
- `extract(text, source_file)` — extrai e deduplica entidades de um texto.
- `extract_batch(texts)` — extrai de múltiplos textos.
- `summarize(entities)` — contagens e top entidades.

### CLI

```bash
uv run python ner_pipeline.py  # roda exemplo embutido
```

---

## graph_builder.py

Constrói grafos de co-ocorrência de entidades NER usando NetworkX.

### Granularidades

| Granularidade | Divisão                           | Parâmetro     |
| ------------- | --------------------------------- | ------------- |
| `sentence`    | Por `.`, `!`, `?`, `\n`           | —             |
| `paragraph`   | Por linhas em branco / `class`    | —             |
| `k_chars`     | Janela deslizante de K caracteres | `k_chars=500` |

### Funções principais

- `build_cooccurrence_graph(texts, pipeline, config)` — constrói um grafo para
  uma granularidade.
- `build_all_granularities(texts, pipeline, k_chars)` — constrói os 3 grafos.
- `save_graph(G, filepath, format)` — salva em GEXF, GraphML ou JSON.
- `load_graph(filepath, format)` — carrega grafo salvo.

### Atributos dos nós

- `label` — tipo da entidade (LIB, CLASS, FUNC, TECH, etc).
- `count` — frequência de aparição.
- `source_files` — arquivos onde a entidade aparece.

### Atributos das arestas

- `weight` — frequência de co-ocorrência.

### CLI

```bash
uv run python graph_builder.py <repo_path> [--input-jsonl <extractions.jsonl>]
```

---

## analysis.py

Métricas de grafos e visualizações para análise comparativa.

### Métricas (`compute_metrics`)

- Nós, arestas, densidade
- Grau médio, máximo, mínimo, desvio padrão
- Componentes conectados e tamanho do maior componente
- Diâmetro e caminho médio (no maior componente)
- Coeficiente de agrupamento médio e máximo
- Transitividade

### Centralidades (`compute_centralities`)

Retorna DataFrame com: degree, weighted_degree, betweenness, closeness,
eigenvector, pagerank.

### Visualizações

- `plot_degree_distribution` — histograma + log-log.
- `plot_graph_visualization` — layout de força colorido por tipo de entidade.
- `plot_comparison_table` — tabela comparativa entre granularidades.
- `plot_centrality_comparison` — barras horizontais top-N por grau.
- `full_analysis(graphs, output_dir)` — roda tudo e salva em `figures/`.

### CLI

```bash
uv run python analysis.py [data/graphs]
```
