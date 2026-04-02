"""
analysis.py - Análise de métricas e visualização dos grafos de co-ocorrência

Implementa as métricas estudadas na disciplina:
- Distribuição de grau
- Densidade
- Diâmetro e caminho médio
- Componentes conectados
- Coeficiente de agrupamento (clustering)
- Centralidade (degree, betweenness, closeness)
"""

from collections import Counter
from typing import Optional

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import seaborn as sns


# =============================================================================
# Métricas do Grafo
# =============================================================================

def compute_metrics(G: nx.Graph) -> dict:
    """
    Calcula todas as métricas relevantes de um grafo.
    
    Returns:
        Dicionário com métricas do grafo
    """
    metrics = {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "density": nx.density(G),
    }

    # Grau
    degrees = [d for _, d in G.degree()]
    if degrees:
        metrics["avg_degree"] = np.mean(degrees)
        metrics["max_degree"] = max(degrees)
        metrics["min_degree"] = min(degrees)
        metrics["std_degree"] = np.std(degrees)

    # Componentes conectados
    if not nx.is_directed(G):
        components = list(nx.connected_components(G))
        metrics["num_components"] = len(components)
        metrics["largest_component_size"] = len(max(components, key=len)) if components else 0
        metrics["largest_component_ratio"] = (
            metrics["largest_component_size"] / G.number_of_nodes() 
            if G.number_of_nodes() > 0 else 0
        )

        # Diâmetro e caminho médio (apenas no maior componente)
        if components:
            largest_cc = G.subgraph(max(components, key=len)).copy()
            if largest_cc.number_of_nodes() > 1:
                metrics["diameter"] = nx.diameter(largest_cc)
                metrics["avg_path_length"] = nx.average_shortest_path_length(largest_cc)
            else:
                metrics["diameter"] = 0
                metrics["avg_path_length"] = 0

    # Coeficiente de agrupamento
    metrics["avg_clustering"] = nx.average_clustering(G)
    clustering_values = nx.clustering(G)
    metrics["max_clustering"] = max(clustering_values.values()) if clustering_values else 0

    # Transitividade
    metrics["transitivity"] = nx.transitivity(G)

    return metrics


def compute_centralities(G: nx.Graph) -> pd.DataFrame:
    """
    Calcula múltiplas medidas de centralidade.
    
    Returns:
        DataFrame com centralidades por nó
    """
    data = {
        "node": list(G.nodes()),
        "label": [G.nodes[n].get("label", "UNKNOWN") for n in G.nodes()],
        "count": [G.nodes[n].get("count", 0) for n in G.nodes()],
        "degree": [d for _, d in G.degree()],
        "weighted_degree": [d for _, d in G.degree(weight="weight")],
    }

    # Betweenness
    betweenness = nx.betweenness_centrality(G)
    data["betweenness"] = [betweenness[n] for n in G.nodes()]

    # Closeness
    closeness = nx.closeness_centrality(G)
    data["closeness"] = [closeness[n] for n in G.nodes()]

    # Eigenvector (pode falhar em grafos desconexos)
    try:
        eigenvector = nx.eigenvector_centrality(G, max_iter=1000)
        data["eigenvector"] = [eigenvector[n] for n in G.nodes()]
    except nx.NetworkXError:
        data["eigenvector"] = [0.0] * G.number_of_nodes()

    # PageRank
    pagerank = nx.pagerank(G)
    data["pagerank"] = [pagerank[n] for n in G.nodes()]

    df = pd.DataFrame(data).sort_values("degree", ascending=False)
    return df


# =============================================================================
# Visualizações
# =============================================================================

def plot_degree_distribution(G: nx.Graph, title: str = "", 
                              save_path: Optional[str] = None):
    """Plota distribuição de grau (linear e log-log)."""
    degrees = [d for _, d in G.degree()]
    degree_count = Counter(degrees)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Histograma
    axes[0].hist(degrees, bins=30, color="#2196F3", edgecolor="white", alpha=0.8)
    axes[0].set_xlabel("Grau (k)")
    axes[0].set_ylabel("Frequência")
    axes[0].set_title(f"Distribuição de Grau{' - ' + title if title else ''}")
    axes[0].axvline(np.mean(degrees), color="red", linestyle="--", 
                     label=f"Média: {np.mean(degrees):.1f}")
    axes[0].legend()

    # Log-Log
    k_values = sorted(degree_count.keys())
    p_values = [degree_count[k] / len(degrees) for k in k_values]
    axes[1].scatter(k_values, p_values, color="#FF5722", alpha=0.7, s=30)
    axes[1].set_xscale("log")
    axes[1].set_yscale("log")
    axes[1].set_xlabel("Grau k (log)")
    axes[1].set_ylabel("P(k) (log)")
    axes[1].set_title(f"Distribuição de Grau (log-log){' - ' + title if title else ''}")

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.show()


def plot_graph_visualization(G: nx.Graph, title: str = "",
                              max_nodes: int = 100,
                              save_path: Optional[str] = None):
    """Visualização do grafo com layout de força."""
    # Se o grafo for muito grande, pegar subgrafo dos nós mais conectados
    if G.number_of_nodes() > max_nodes:
        top_nodes = sorted(G.degree(), key=lambda x: x[1], reverse=True)[:max_nodes]
        G_sub = G.subgraph([n for n, _ in top_nodes]).copy()
    else:
        G_sub = G

    fig, ax = plt.subplots(1, 1, figsize=(16, 12))

    # Layout
    pos = nx.spring_layout(G_sub, k=2/np.sqrt(G_sub.number_of_nodes()), 
                            iterations=50, seed=42)

    # Cores por tipo de entidade
    color_map = {
        "LIB": "#2196F3",    # azul
        "CLASS": "#4CAF50",   # verde
        "FUNC": "#FF9800",    # laranja
        "PER": "#E91E63",     # rosa
        "ORG": "#9C27B0",     # roxo
        "LOC": "#F44336",     # vermelho
        "TECH": "#00BCD4",    # ciano
        "MISC": "#795548",    # marrom
        "UNKNOWN": "#9E9E9E", # cinza
    }

    node_colors = [
        color_map.get(G_sub.nodes[n].get("label", "UNKNOWN"), "#9E9E9E")
        for n in G_sub.nodes()
    ]

    # Tamanho proporcional ao grau
    degrees = dict(G_sub.degree())
    node_sizes = [max(degrees[n] * 50, 100) for n in G_sub.nodes()]

    # Peso das arestas
    edge_weights = [G_sub[u][v].get("weight", 1) for u, v in G_sub.edges()]
    max_weight = max(edge_weights) if edge_weights else 1
    edge_widths = [0.5 + 2 * (w / max_weight) for w in edge_weights]

    # Desenhar
    nx.draw_networkx_edges(G_sub, pos, alpha=0.2, width=edge_widths, 
                            edge_color="#cccccc", ax=ax)
    nx.draw_networkx_nodes(G_sub, pos, node_color=node_colors, 
                            node_size=node_sizes, alpha=0.8, ax=ax)

    # Labels apenas para nós com grau alto
    avg_degree = np.mean(list(degrees.values()))
    labels = {n: n for n in G_sub.nodes() if degrees[n] > avg_degree}
    nx.draw_networkx_labels(G_sub, pos, labels, font_size=8, 
                             font_weight="bold", ax=ax)

    # Legenda
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=color, label=label)
        for label, color in color_map.items()
        if any(G_sub.nodes[n].get("label") == label for n in G_sub.nodes())
    ]
    ax.legend(handles=legend_elements, loc="upper left", fontsize=9)

    ax.set_title(f"Grafo de Co-ocorrência{' - ' + title if title else ''}", 
                  fontsize=14, fontweight="bold")
    ax.axis("off")

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.show()


def plot_comparison_table(metrics_dict: dict[str, dict], 
                           save_path: Optional[str] = None):
    """
    Plota tabela comparativa entre granularidades.
    
    Args:
        metrics_dict: Dict com {granularity: metrics}
    """
    df = pd.DataFrame(metrics_dict).T
    
    # Selecionar métricas principais
    cols = ["nodes", "edges", "density", "avg_degree", "diameter", 
            "avg_path_length", "avg_clustering", "num_components",
            "largest_component_ratio", "transitivity"]
    cols = [c for c in cols if c in df.columns]
    
    df_display = df[cols].round(4)
    df_display.index.name = "Granularidade"
    
    # Renomear colunas para português
    rename = {
        "nodes": "Nós", "edges": "Arestas", "density": "Densidade",
        "avg_degree": "Grau Médio", "diameter": "Diâmetro",
        "avg_path_length": "Caminho Médio", "avg_clustering": "Clustering Médio",
        "num_components": "Componentes", "largest_component_ratio": "Maior Comp. (%)",
        "transitivity": "Transitividade",
    }
    df_display = df_display.rename(columns=rename)
    
    fig, ax = plt.subplots(figsize=(14, 3))
    ax.axis("off")
    
    table = ax.table(
        cellText=df_display.values,
        colLabels=df_display.columns,
        rowLabels=df_display.index,
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.5)
    
    # Estilizar header
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#2196F3")
            cell.set_text_props(color="white", fontweight="bold")
        elif col == -1:
            cell.set_facecolor("#E3F2FD")
            cell.set_text_props(fontweight="bold")
    
    plt.title("Comparação de Métricas por Granularidade", 
              fontsize=14, fontweight="bold", pad=20)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.show()
    
    return df_display


def plot_centrality_comparison(centralities_dict: dict[str, pd.DataFrame],
                                top_n: int = 15,
                                save_path: Optional[str] = None):
    """Compara top entidades por centralidade entre granularidades."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    for ax, (granularity, df) in zip(axes, centralities_dict.items()):
        top = df.head(top_n)
        colors = [
            {"LIB": "#2196F3", "CLASS": "#4CAF50", "FUNC": "#FF9800",
             "PER": "#E91E63", "ORG": "#9C27B0", "TECH": "#00BCD4"
            }.get(label, "#9E9E9E")
            for label in top["label"]
        ]
        
        ax.barh(range(len(top)), top["degree"], color=colors, alpha=0.8)
        ax.set_yticks(range(len(top)))
        ax.set_yticklabels(top["node"], fontsize=8)
        ax.set_xlabel("Grau")
        ax.set_title(f"Top {top_n} - {granularity.capitalize()}")
        ax.invert_yaxis()
    
    plt.suptitle("Entidades Mais Conectadas por Granularidade", 
                  fontsize=14, fontweight="bold")
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.show()


# =============================================================================
# Relatório Completo
# =============================================================================

def full_analysis(graphs: dict[str, nx.Graph], 
                   output_dir: str = "figures") -> dict:
    """
    Executa análise completa e gera todas as figuras.
    
    Args:
        graphs: Dict com {granularity: nx.Graph}
        output_dir: Diretório para salvar figuras
    
    Returns:
        Dict com métricas comparativas
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    all_metrics = {}
    all_centralities = {}
    
    for name, G in graphs.items():
        print(f"\n{'='*60}")
        print(f"📊 Análise: {name}")
        print(f"{'='*60}")
        
        # Métricas
        metrics = compute_metrics(G)
        all_metrics[name] = metrics
        
        for k, v in metrics.items():
            if isinstance(v, float):
                print(f"  {k}: {v:.4f}")
            else:
                print(f"  {k}: {v}")
        
        # Centralidades
        centralities = compute_centralities(G)
        all_centralities[name] = centralities
        
        print(f"\n  Top 10 entidades por grau:")
        for _, row in centralities.head(10).iterrows():
            print(f"    [{row['label']}] {row['node']} (grau: {row['degree']})")
        
        # Figuras individuais
        plot_degree_distribution(G, title=name, 
                                  save_path=f"{output_dir}/degree_dist_{name}.png")
        plot_graph_visualization(G, title=name, 
                                  save_path=f"{output_dir}/graph_viz_{name}.png")
    
    # Comparações
    plot_comparison_table(all_metrics, 
                           save_path=f"{output_dir}/comparison_table.png")
    plot_centrality_comparison(all_centralities, 
                                save_path=f"{output_dir}/centrality_comparison.png")
    
    return {"metrics": all_metrics, "centralities": all_centralities}


if __name__ == "__main__":
    from graph_builder import load_graph
    import sys
    
    graph_dir = sys.argv[1] if len(sys.argv) > 1 else "data/graphs"
    
    graphs = {}
    for name in ["sentence", "paragraph", "k_chars"]:
        path = f"{graph_dir}/graph_{name}.gexf"
        try:
            graphs[name] = load_graph(path)
            print(f"✅ Carregado: {path}")
        except FileNotFoundError:
            print(f"⚠️  Não encontrado: {path}")
    
    if graphs:
        full_analysis(graphs)
