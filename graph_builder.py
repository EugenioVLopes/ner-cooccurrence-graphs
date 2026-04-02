"""
graph_builder.py - Construção de grafos de co-ocorrência de entidades

Suporta três granularidades de co-ocorrência:
- Sentença: entidades que aparecem na mesma sentença
- Parágrafo: entidades no mesmo bloco/parágrafo
- K-caracteres: janela deslizante de K caracteres
"""

import re
from dataclasses import dataclass
from itertools import combinations
from typing import Optional

import networkx as nx

from ner_pipeline import Entity, NERPipeline
from extractor import ExtractedText


@dataclass
class CoOccurrenceConfig:
    """Configuração para construção do grafo."""
    granularity: str = "sentence"  # 'sentence', 'paragraph', 'k_chars'
    k_chars: int = 500  # tamanho da janela para k_chars
    min_weight: int = 1  # peso mínimo para incluir aresta
    normalize_names: bool = True  # normalizar nomes das entidades


def split_into_sentences(text: str) -> list[str]:
    """Divide texto em sentenças."""
    # Padrão simples para divisão por sentença
    sentences = re.split(r'[.!?\n]+', text)
    return [s.strip() for s in sentences if len(s.strip()) > 5]


def split_into_paragraphs(text: str) -> list[str]:
    """Divide texto em parágrafos."""
    paragraphs = re.split(r'\n\s*\n|\n(?=\s*(?:class |def |#))', text)
    return [p.strip() for p in paragraphs if len(p.strip()) > 5]


def split_into_k_chars(text: str, k: int = 500, overlap: int = 100) -> list[str]:
    """Divide texto em janelas de K caracteres com sobreposição."""
    windows = []
    start = 0
    while start < len(text):
        end = min(start + k, len(text))
        windows.append(text[start:end])
        start += k - overlap
    return windows


def build_cooccurrence_graph(
    texts: list[ExtractedText],
    pipeline: NERPipeline,
    config: Optional[CoOccurrenceConfig] = None,
) -> nx.Graph:
    """
    Constrói o grafo de co-ocorrência de entidades.
    
    Args:
        texts: Lista de textos extraídos
        pipeline: Pipeline de NER configurado
        config: Configuração de granularidade
    
    Returns:
        Grafo NetworkX com entidades como nós e co-ocorrências como arestas
    """
    if config is None:
        config = CoOccurrenceConfig()

    G = nx.Graph()
    G.graph["granularity"] = config.granularity
    G.graph["k_chars"] = config.k_chars if config.granularity == "k_chars" else None

    # Selecionar função de divisão
    if config.granularity == "sentence":
        split_fn = split_into_sentences
    elif config.granularity == "paragraph":
        split_fn = split_into_paragraphs
    elif config.granularity == "k_chars":
        split_fn = lambda t: split_into_k_chars(t, k=config.k_chars)
    else:
        raise ValueError(f"Granularidade desconhecida: {config.granularity}")

    # Processar cada texto
    for extracted in texts:
        chunks = split_fn(extracted.text)

        for chunk in chunks:
            # Extrair entidades do chunk
            entities = pipeline.extract(chunk, extracted.source_file)

            if len(entities) < 2:
                continue

            # Adicionar nós com atributos
            for entity in entities:
                name = entity.normalized if config.normalize_names else entity.text
                if not G.has_node(name):
                    G.add_node(name, 
                               label=entity.label,
                               count=0,
                               source_files=set())
                G.nodes[name]["count"] += 1
                G.nodes[name]["source_files"].add(extracted.source_file)

            # Adicionar arestas (co-ocorrência)
            unique_entities = list(set(
                e.normalized if config.normalize_names else e.text 
                for e in entities
            ))

            for e1, e2 in combinations(sorted(unique_entities), 2):
                if G.has_edge(e1, e2):
                    G[e1][e2]["weight"] += 1
                else:
                    G.add_edge(e1, e2, weight=1)

    # Filtrar arestas com peso mínimo
    if config.min_weight > 1:
        edges_to_remove = [
            (u, v) for u, v, d in G.edges(data=True) 
            if d["weight"] < config.min_weight
        ]
        G.remove_edges_from(edges_to_remove)

    # Remover nós isolados após filtragem
    isolated = list(nx.isolates(G))
    G.remove_nodes_from(isolated)

    # Converter sets para listas para serialização
    for node in G.nodes:
        if isinstance(G.nodes[node].get("source_files"), set):
            G.nodes[node]["source_files"] = ", ".join(sorted(G.nodes[node]["source_files"]))

    return G


def build_all_granularities(
    texts: list[ExtractedText],
    pipeline: NERPipeline,
    k_chars: int = 500,
) -> dict[str, nx.Graph]:
    """
    Constrói grafos para todas as granularidades para comparação.
    
    Returns:
        Dict com chaves 'sentence', 'paragraph', 'k_chars'
    """
    graphs = {}

    for granularity in ["sentence", "paragraph", "k_chars"]:
        config = CoOccurrenceConfig(
            granularity=granularity,
            k_chars=k_chars,
        )
        print(f"🔨 Construindo grafo ({granularity})...")
        G = build_cooccurrence_graph(texts, pipeline, config)
        graphs[granularity] = G
        print(f"   → {G.number_of_nodes()} nós, {G.number_of_edges()} arestas")

    return graphs


def save_graph(G: nx.Graph, filepath: str, format: str = "gexf"):
    """Salva o grafo em arquivo."""
    if format == "gexf":
        nx.write_gexf(G, filepath)
    elif format == "graphml":
        nx.write_graphml(G, filepath)
    elif format == "json":
        import json
        from networkx.readwrite import json_graph
        data = json_graph.node_link_data(G)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
    else:
        raise ValueError(f"Formato desconhecido: {format}")
    print(f"💾 Grafo salvo em: {filepath}")


def load_graph(filepath: str, format: str = "gexf") -> nx.Graph:
    """Carrega um grafo de arquivo."""
    if format == "gexf":
        return nx.read_gexf(filepath)
    elif format == "graphml":
        return nx.read_graphml(filepath)
    elif format == "json":
        import json
        from networkx.readwrite import json_graph
        with open(filepath, "r") as f:
            data = json.load(f)
        return json_graph.node_link_graph(data)
    else:
        raise ValueError(f"Formato desconhecido: {format}")


if __name__ == "__main__":
    # Exemplo de uso rápido
    import argparse
    from extractor import extract_repository, load_jsonl_extractions

    parser = argparse.ArgumentParser(description="Constrói grafos de co-ocorrência")
    parser.add_argument("repo_path", help="Caminho do repositório")
    parser.add_argument(
        "--input-jsonl",
        dest="input_jsonl",
        help="Arquivo JSONL gerado pelo extractor.py para pular a etapa de extração",
    )
    args = parser.parse_args()

    repo_path = args.repo_path

    # Extração
    if args.input_jsonl:
        print("📂 Carregando extrações do JSONL...")
        extraction = load_jsonl_extractions(args.input_jsonl, repo_path=repo_path)
    else:
        print("📂 Extraindo texto do repositório...")
        extraction = extract_repository(repo_path)
    print(f"   → {len(extraction.texts)} blocos extraídos")

    # NER + Grafo
    pipeline = NERPipeline(use_spacy=True)
    graphs = build_all_granularities(extraction.texts, pipeline)

    # Salvar
    for name, G in graphs.items():
        save_graph(G, f"data/graphs/graph_{name}.gexf")
