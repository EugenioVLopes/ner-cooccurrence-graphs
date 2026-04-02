# Analise de Grafos de Co-ocorrencia via NER em Repositorio de Codigo-Fonte

**Disciplina:** DCA3702 - Algoritmos e Estruturas de Dados II - T01 (2026.1)
**Unidade 01 - Trabalho 01**

## Descricao

Este projeto aplica **Named Entity Recognition (NER)** sobre o codigo-fonte do
[Claude Code](https://github.com/anthropics/claude-code) para construir
**grafos de co-ocorrencia** entre entidades identificadas. A analise utiliza
conceitos de teoria de grafos estudados na disciplina, incluindo distribuicao de
grau, componentes conectados, coeficiente de agrupamento, deteccao de
comunidades e visualizacao interativa.

### Fonte de Dados

- Repositorio **claude-code** (Anthropic) — CLI oficial do Claude
- Extracao de texto a partir de: codigo TypeScript/Python, comentarios,
  docstrings e documentacao (.md)

### Visualizacoes Interativas

Explore os grafos de co-ocorrencia diretamente no navegador:

- [Grafo — Sentenca](https://eugeniovlopes.github.io/datastructure2/figures/05-pyvis/interactive_sentence.html)
- [Grafo — Paragrafo](https://eugeniovlopes.github.io/datastructure2/figures/05-pyvis/interactive_paragraph.html)
- [Grafo — K-chars (500)](https://eugeniovlopes.github.io/datastructure2/figures/05-pyvis/interactive_k_chars.html)

## Estrutura do Repositorio

```
├── analysis.py               # Metricas, visualizacoes e comunidades
├── extractor.py              # Extracao de texto do codigo-fonte
├── ner_pipeline.py           # Pipeline de NER (spaCy + regex)
├── graph_builder.py          # Construcao do grafo de co-ocorrencia
├── data/
│   ├── raw/                  # Arquivos brutos do repositorio-alvo
│   └── graphs/               # Grafos serializados (.gexf)
├── figures/
│   ├── 01-initial/           # Grafos e metricas — extracao inicial (regex)
│   ├── 02-filtered/          # Grafos apos filtragem de ruido
│   ├── 03-spacy/             # Grafos com NER via spaCy (en_core_web_lg)
│   ├── 04-louvain/           # Deteccao de comunidades Louvain
│   └── 05-pyvis/             # Visualizacoes interativas (HTML)
├── docs/                     # Relatorios de cada iteracao
├── slides/                   # Material de aula do professor
├── pyproject.toml
├── uv.lock
└── README.md
```

## Instalacao

```bash
uv sync
python -m spacy download en_core_web_lg
```

## Pipeline

### 1. Extracao de Texto (`extractor.py`)

Percorre o repositorio-alvo e extrai texto de multiplas fontes:

- **Codigo**: nomes de classes, funcoes, variaveis, imports
- **Comentarios**: linhas com `#`, `//` e blocos `""" """`
- **Documentacao**: arquivos `.md` e `.txt`

### 2. NER (`ner_pipeline.py`)

Aplica Named Entity Recognition em duas camadas:

- **spaCy** (`en_core_web_lg`) para entidades em linguagem natural
- **Regex customizado** para entidades de codigo (pacotes, classes, funcoes)
- Categorias: `LIB`, `CLASS`, `FUNC`, `PER`, `ORG`, `TECH`, `LOC`
- Filtragem de ruido: stopwords, fragmentos de path, palavras ambiguas

### 3. Construcao do Grafo (`graph_builder.py`)

Gera grafos de co-ocorrencia com tres granularidades:

- **Sentenca**: entidades na mesma sentenca
- **Paragrafo**: entidades no mesmo bloco/paragrafo
- **K-caracteres (500)**: janela deslizante de 500 caracteres

Os grafos sao serializados em formato GEXF (`data/graphs/`).

### 4. Analise (`analysis.py`)

Metricas e visualizacoes:

- Distribuicao de grau (histograma + log-log)
- Densidade da rede
- Diametro e caminho medio (maior componente)
- Componentes conectados
- Coeficiente de agrupamento e transitividade
- Centralidade (degree, betweenness, closeness, eigenvector, PageRank)
- Deteccao de comunidades (Louvain)
- Visualizacao interativa (pyvis)

## Iteracoes

| #   | Descricao                       | Doc                                         | Figuras                |
| --- | ------------------------------- | ------------------------------------------- | ---------------------- |
| 01  | Extracao inicial com regex      | [relatorio](docs/01-initial-extraction.md)  | `figures/01-initial/`  |
| 02  | Filtragem de ruido NER          | [relatorio](docs/02-filtered-extraction.md) | `figures/02-filtered/` |
| 03  | NER com spaCy (en_core_web_lg)  | [relatorio](docs/03-spacy-extraction.md)    | `figures/03-spacy/`    |
| 04  | Comunidades Louvain             | [relatorio](docs/04-louvain-communities.md) | `figures/04-louvain/`  |
| 05  | Visualizacao interativa (pyvis) | [relatorio](docs/05-pyvis-interactive.md)   | `figures/05-pyvis/`    |

## Tecnologias

- **Python 3.12+**
- **spaCy** (`en_core_web_lg`) — NER
- **NetworkX** — construcao e analise de grafos
- **python-louvain** — deteccao de comunidades
- **pyvis** — visualizacao interativa
- **matplotlib / seaborn** — visualizacoes estaticas
- **pandas / numpy** — manipulacao de dados

## Referencias

- Coscia, M. _The Atlas for the Aspiring Network Scientist_
- Huyen, C. _AI Engineering_, 2025
- NetworkX Documentation
- spaCy Documentation
