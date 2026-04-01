# 🔍 Análise de Grafos de Co-ocorrência via NER em Repositório de Código-Fonte

**Disciplina:** DCA3702 - Algoritmos e Estruturas de Dados II - T01 (2026.1)  
**Unidade 01 - Trabalho 01**

## 📋 Descrição

Este projeto aplica técnicas de **Named Entity Recognition (NER)** sobre o código-fonte de um repositório Python para construir **grafos de co-ocorrência** entre entidades identificadas. A análise utiliza conceitos de teoria de grafos estudados na disciplina, incluindo distribuição de grau, componentes conectados, coeficiente de agrupamento, entre outros.

### Fonte de Dados
- Repositório de código-fonte Python (interno)
- Extração de texto a partir de: código, comentários, docstrings, documentação (.md)

## 🏗️ Estrutura do Repositório

```
├── data/
│   ├── raw/                  # Arquivos brutos do repositório
│   ├── processed/            # Textos extraídos e entidades identificadas
│   └── graphs/               # Grafos serializados (.gexf, .graphml)
├── src/
│   ├── extractor.py          # Extração de texto do código-fonte
│   ├── ner_pipeline.py       # Pipeline de NER
│   ├── graph_builder.py      # Construção do grafo de co-ocorrência
│   └── analysis.py           # Métricas e análise do grafo
├── notebooks/
│   ├── 01_extracao.ipynb     # Extração e pré-processamento
│   ├── 02_ner.ipynb          # NER e exploração de entidades
│   ├── 03_grafo.ipynb        # Construção e visualização do grafo
│   └── 04_analise.ipynb      # Análise crítica e comparações
├── figures/                  # Figuras geradas para o relatório
├── docs/                     # Documentação adicional
├── pyproject.toml
├── uv.lock
└── README.md
```

## 🔧 Instalação

```bash
uv sync
```

## 🚀 Pipeline

### 1. Extração de Texto (`src/extractor.py`)
Percorre o repositório e extrai texto de múltiplas fontes:
- **Código**: nomes de classes, funções, variáveis, imports
- **Comentários**: linhas com `#` e blocos `""" """`
- **Docstrings**: documentação de módulos, classes e funções
- **Documentação**: arquivos `.md` e `.txt`

### 2. NER (`src/ner_pipeline.py`)
Aplica Named Entity Recognition utilizando:
- **spaCy** (modelo pt/en) para entidades em linguagem natural
- **Regex customizado** para entidades de código (nomes de pacotes, classes, funções)
- Categorias: `LIB` (biblioteca), `CLASS` (classe), `FUNC` (função), `PER` (pessoa), `ORG` (organização), `TECH` (tecnologia)

### 3. Construção do Grafo (`src/graph_builder.py`)
Gera grafos de co-ocorrência com três granularidades:
- **Sentença**: entidades na mesma sentença
- **Parágrafo**: entidades no mesmo bloco/parágrafo
- **K-caracteres**: janela deslizante de K caracteres

### 4. Análise (`src/analysis.py`)
Métricas e visualizações:
- Distribuição de grau
- Densidade da rede
- Diâmetro e caminho médio
- Componentes conectados
- Coeficiente de agrupamento (clustering)
- Centralidade (betweenness, closeness, degree)

## 📊 Comparação de Granularidades

| Métrica | Sentença | Parágrafo | K-caracteres |
|---------|----------|-----------|--------------|
| Nós     | -        | -         | -            |
| Arestas | -        | -         | -            |
| Densidade | -      | -         | -            |
| Diâmetro | -      | -         | -            |
| Clustering | -    | -         | -            |

*(Tabela preenchida após execução)*

## 🎥 Apresentação

Vídeo assíncrono (10min) disponível em: [Loom - link]

## 📚 Referências

- Coscia, M. *The Atlas for the Aspiring Network Scientist*
- Huyen, C. *AI Engineering*, 2025
- NetworkX Documentation
- spaCy Documentation
