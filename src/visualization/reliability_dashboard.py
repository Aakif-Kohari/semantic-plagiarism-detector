# semantic-plagiarism-detector/src/visualization/reliability_dashboard.py

import plotly.express as px
import plotly.graph_objects as go
from typing import List

def generate_reviewer_agreement_heatmap(agreement_matrix: List[List[float]], reviewer_labels: List[str]) -> go.Figure:
    """
    Generates a Plotly heatmap displaying pairwise or committee reviewer agreement scores.
    """
    fig = px.imshow(
        agreement_matrix,
        x=reviewer_labels,
        y=reviewer_labels,
        color_continuousScale="Greens",
        labels=dict(x="Reviewer", y="Reviewer", color="Kappa Score"),
        title="Inter-Rater Reliability & Reviewer Agreement Heatmap"
    )
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Segoe UI", size=12)
    )
    return fig
