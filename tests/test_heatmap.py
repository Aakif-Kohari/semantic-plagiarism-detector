import matplotlib.pyplot as plt
import numpy as np


def test_similarity_heatmap_visual():
    """Verify that the similarity matrix heatmap renders without error."""
    fig, ax = plt.subplots(figsize=(6, 6))

    # Dummy similarity matrix for testing visual output
    matrix = np.array(
        [[1.0, 0.85, 0.20], [0.85, 1.0, 0.15], [0.20, 0.15, 1.0]]
    )
    labels = ["Doc 1", "Doc 2", "Doc 3"]

    cax = ax.matshow(matrix, cmap="YlOrRd")
    fig.colorbar(cax)

    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45)
    ax.set_yticklabels(labels)
    ax.set_title("Similarity Heatmap")

    # Verify figure rendered without errors
    assert fig is not None
    assert len(fig.axes) >= 1
    plt.close(fig)