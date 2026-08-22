import plotly.graph_objects as go

def generate_evolution_heatmap(diff_tokens: list[dict], block_size: int = 50) -> go.Figure:
    """
    Aggregates granular tokens into chunk blocks to graph an evolution map layout.
    Values represent modification density (Deletions/Additions = 1, Unchanged = 0).
    """
    chunks = [diff_tokens[i:i + block_size] for i in range(0, len(diff_tokens), block_size)]
    
    density_scores = []
    chunk_labels = []
    
    for idx, chunk in enumerate(chunks):
        changes = sum(1 for t in chunk if t["action"] in ["added", "deleted"])
        score = (changes / len(chunk)) * 100 if len(chunk) > 0 else 0
        density_scores.append(score)
        chunk_labels.append(f"Block {idx + 1}")

    # Build Plotly visual layout matrix maps
    fig = go.Figure(data=go.Heatmap(
        z=[density_scores],
        x=chunk_labels,
        y=["Modification Density"],
        colorscale="YlOrRd",
        zmin=0,
        zmax=100,
        colorbar=dict(title="Change %", titleside="top")
    ))

    fig.update_layout(
        title="Document Evolution & Edit Density Map",
        xaxis_title="Sequential Document Text Blocks",
        yaxis_title="",
        height=250,
        margin=dict(l=40, r=40, t=60, b=40),
        template="plotly_white"
    )
    
    return fig
