# Relatório 05 — Visualização Interativa (pyvis)

## O que mudou

- Adicionada função `build_pyvis_graph()` ao `analysis.py`.
- `full_analysis()` agora gera HTMLs interativos para cada granularidade.
- Novas visualizações em `figures/05-pyvis/`.

## Como funciona

### Seleção de nós

Para manter a visualização responsiva, apenas os **300 nós mais conectados**
(por grau) são incluídos. Isso preserva os hubs centrais e suas conexões
enquanto elimina nós periféricos de baixo grau.

### Codificação visual

| Atributo     | Codificação                                    |
|-------------|------------------------------------------------|
| **Cor**     | Comunidade Louvain (paleta de 20 cores)        |
| **Forma**   | Tipo de entidade: LIB=●, TECH=◆, CLASS=▲, FUNC=■, ORG=★, PER=▽, LOC=⬡ |
| **Tamanho** | Proporcional ao grau (8–60px)                  |
| **Aresta**  | Largura proporcional ao peso de co-ocorrência  |

### Interatividade

- **Hover**: tooltip com nome, tipo, grau, comunidade e contagem
- **Drag**: arrastar nós para reorganizar o layout
- **Zoom**: scroll para aproximar/afastar
- **Select menu**: filtrar por atributo
- **Filter menu**: buscar nós específicos
- **Física**: simulação Barnes-Hut com gravidade -3000

## Resultados por granularidade

### Sentença (300 nós / 5.791 total)

- Grafo mais esparso — nós de mesmo tema ficam agrupados mas com poucos
  links entre clusters.
- Comunidades visualmente bem separadas.
- Arquivo: 2.5 MB (mais arestas entre top-300 hubs).

### Parágrafo (300 nós / 7.746 total)

- Grafo mais denso — muitas co-ocorrências em blocos maiores.
- Cluster central (API + MCP + auth) domina o centro.
- Arquivo: 655 KB.

### K-chars 500 (300 nós / 7.845 total)

- Intermediário entre sentença e parágrafo.
- Boa separação de subsistemas (OAuth, UI, Git como clusters distintos).
- Arquivo: 284 KB.

## Análise

### Valor da interatividade

As visualizações estáticas (PNG) das iterações anteriores limitavam a
exploração: nós se sobrepunham e labels ficavam ilegíveis em grafos grandes.
O pyvis resolve isso com:

1. **Zoom seletivo** — explorar regiões específicas do grafo
2. **Drag & drop** — separar nós sobrepostos manualmente
3. **Tooltips** — consultar atributos sem poluir a visualização
4. **Busca** — localizar entidades específicas pelo nome

### Observações dos grafos interativos

- **`claude`** aparece como hub central em todas as granularidades, confirmando
  seu papel como entidade mais conectada do codebase.
- Os subsistemas satélite (MCP, UI, Git, OS) formam "ilhas" visíveis
  conectadas ao core por pontes específicas.
- A granularidade **parágrafo** produz o grafo mais informativo para
  exploração interativa — densidade suficiente para ver relações,
  sem o ruído excessivo de k-chars.

## Figuras geradas

| Arquivo                                        | Conteúdo                              |
|------------------------------------------------|---------------------------------------|
| `figures/05-pyvis/interactive_sentence.html`   | Grafo interativo — sentença           |
| `figures/05-pyvis/interactive_paragraph.html`  | Grafo interativo — parágrafo          |
| `figures/05-pyvis/interactive_k_chars.html`    | Grafo interativo — k-chars (500)      |
