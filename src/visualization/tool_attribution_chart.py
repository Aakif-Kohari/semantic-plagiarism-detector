# semantic-plagiarism-detector/src/visualization/tool_attribution_chart.py

import plotly.express as px
import plotly.graph_objects as go
from typing import Dict

def generate_tool_probability_chart(probabilities: Dict[str, float]) -> go.Figure:
    """
    Generates a Plotly probability chart showing the likelihood of specific paraphrasing tool usage.
    """
    tools = list(probabilities.keys())
    probs = list(probabilities.values())

    fig = px.bar(
        x=tools,
        y=probs,
        labels={"x": "Paraphrasing Tool / Engine", "y": "Probability Likelihood"},
        title="Automated Paraphrase Tool Fingerprinting & Attribution",
        color=probs,
        color_continuousScale="Viridis"
    )
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Segoe UI", size=12),
        yaxis=dict(range=[0, 1])
    )
    return fig
