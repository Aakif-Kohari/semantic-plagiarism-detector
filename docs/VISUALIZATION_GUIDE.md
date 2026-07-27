# Visualization Customization Guide

## Overview

All chart-drawing code lives in `src/visualization/`:

| File | Library | What it draws |
|---|---|---|
| `heatmap.py` | Matplotlib/Seaborn + Plotly | Similarity matrix heatmaps (static PNG and interactive), chunk-level comparison heatmap |
| `network_graph.py` | NetworkX + Plotly | Document plagiarism network graph |
| `analytics.py` | Plotly Express/Graph Objects | Dashboard charts (trend lines, bar charts, histograms) |

These functions are pure: they take data in and return a `Figure` object out. They don't read Streamlit session state directly — the app layer (`app/streamlit_app.py`) calls them and passes in whatever theme/config values are needed.

## How Theming Works

The app has a `Light`/`Dark` theme system defined in `app/theme.py`:

- `THEMES` is a dict of two palettes (`"Light"`, `"Dark"`), each mapping token names (`background`, `ink`, `danger`, `warning`, `success`, etc.) to hex colors.
- `get_colors()` returns the currently active palette as a plain `dict`.
- The visualization functions accept this dict through a `theme_colors: Optional[dict]` parameter and pull individual tokens out with `.get("token_name", "#fallback")`.

This means a visualization function never hardcodes "Light mode" or "Dark mode" — it just asks for a token (like `"danger"`) and lets the caller decide what that token currently means.

### The token contract

If you add a new visualization or extend an existing one, use these token names so it stays consistent with the rest of the app:

- `background`, `surface`, `card` — backgrounds
- `ink`, `muted` — text colors
- `accent` — brand/highlight color
- `border` — borders/gridlines
- `danger`, `warning`, `success` — severity colors (used for high/medium/low similarity)
- `danger_soft`, `warning_soft`, `success_soft`, `neutral_soft` — light background tints for badges/pills

Do not invent new token names inside a single chart function — add the token to both palettes in `THEMES` (`app/theme.py`) first, so Light and Dark both define it.

## Extending Each File

### `heatmap.py`

Two entry points draw the main similarity matrix:

- `plot_similarity_heatmap(...)` — Matplotlib/Seaborn, used for the high-res PNG download.
- `plot_similarity_heatmap_plotly(...)` — Plotly, used for the interactive on-screen version.

Both currently use a **module-level constant** for the colormap:

```python
_CMAP = "RdYlGn_r"
```

This is used directly inside `sns.heatmap(..., cmap=_CMAP)` and `go.Heatmap(..., colorscale="RdYlGn_r")`. Neither function currently accepts a `cmap` argument — the colormap is fixed at the module level, not passed in per-call.

Theme colors (background/ink/etc.) are applied conditionally with `if theme_colors:` blocks that style the figure background, axis text color, and legend — see lines 75–83 and 140–146 in `plot_similarity_heatmap`.

`plot_chunk_similarity_comparison(...)` (the two-document chunk-level heatmap) reuses the same `_CMAP` constant and a similar `if theme_colors:` block.

### `network_graph.py`

`plot_similarity_network(...)` builds a graph with NetworkX (`nx.spring_layout` for node positions) and renders it with Plotly `go.Figure`.

Coloring logic here is threshold-based rather than a single palette lookup:

- **Edges** are colored by similarity severity (lines ~92–98): `>= 0.90` uses `theme_colors["danger"]`, `>= 0.75` uses `theme_colors["warning"]`, otherwise `theme_colors["success"]` — each with a hardcoded hex fallback if `theme_colors` is `None`.
- **Nodes** are colored by document class tags (e.g. `#class_A`, `#class_B`) when tag metadata is provided via `document_tags` (or fetched from database). Each unique class tag is mapped to a discrete color from a high-contrast palette. If no document tags exist, node colors fall back to connection degree (degree `0` → success, degree `1` → warning, degree `2+` → danger).

If you want to change these severity cutoffs, they are separate from `PLAGIARISM_THRESHOLD` in `src/core/similarity.py` — the `0.90`/`0.75` values are local to this function.

### `analytics.py`

Four chart functions live here: `plot_high_severity_trends`, `plot_most_plagiarized_documents`, `plot_similarity_distribution`, `plot_document_sizes`.

Unlike `heatmap.py` and `network_graph.py`, **none of these currently accept a `theme_colors` parameter**. Their colors are hardcoded per-trace, e.g.:

```python
fig.update_traces(
    line=dict(color="#ff4b4b", width=3), marker=dict(size=8, color="#ff4b4b")
)
```

So today, dashboard charts do not follow the Light/Dark theme the way the heatmap and network graph do. This is the main gap to be aware of if you're asked to make analytics charts theme-aware — see "Known Gaps" below.

## Adding a New Chart

1. Add your function to the relevant file (or a new file if it's a new category of chart) under `src/visualization/`.
2. Give it a `theme_colors: Optional[dict] = None` parameter if it should respect Light/Dark mode, and pull colors via `theme_colors.get("token", "#fallback")` so it still works if `None` is passed.
3. Export it from `src/visualization/__init__.py` (add it to both the `from .module import ...` line and the `__all__` list) so it can be imported as `from src.visualization import your_function`.
4. Call it from `app/streamlit_app.py`, passing `theme_colors=get_colors()` if applicable.
5. Add a test under `tests/` (see `tests/test_heatmap.py` and `tests/visualization/test_network_graph.py` for existing patterns) and, if it's a Matplotlib figure, consider a baseline image test like `tests/baseline/test_similarity_heatmap_visual.png`.

## Chart Customization Examples

### Choosing a heatmap colormap

`plot_similarity_heatmap`, `plot_similarity_heatmap_plotly`, and `plot_chunk_similarity_comparison` all accept a `colormap_name` argument. Pick any of `UI_COLORMAP_OPTIONS` (`"Viridis"`, `"Plasma"`, `"Coolwarm"`, `"YlOrRd"`):

```python
from src.visualization.heatmap import plot_similarity_heatmap

fig = plot_similarity_heatmap(
    similarity_df,
    colormap_name="Plasma",  # try "Viridis", "Coolwarm", or "YlOrRd" too
)
```

### Overriding theme colors for a single chart

Every visualization function accepts a `theme_colors` dict. You don't have to use `get_colors()` from `app/theme.py` — pass a custom dict to preview a one-off palette:

```python
custom_theme = {
    "background": "#1A1A2E",
    "surface": "#16213E",
    "ink": "#EAEAEA",
    "danger": "#FF6B6B",
    "warning": "#FFD93D",
    "success": "#6BCB77",
}

fig = plot_similarity_heatmap(similarity_df, theme_colors=custom_theme)
```

### Adding a permanent app-wide theme

To make a new palette selectable app-wide (not just for one chart), add it to `THEMES` in `app/theme.py`, following the same token names used by `"Light"` and `"Dark"`:

```python
THEMES["HighContrast"] = {
    "background": "#000000",
    "surface": "#111111",
    "card": "#000000",
    "ink": "#FFFFFF",
    "muted": "#AAAAAA",
    "accent": "#00FFC2",
    "border": "#333333",
    "input": "#000000",
    "danger": "#FF0033",
    "danger_soft": "#330000",
    "warning": "#FFEE00",
    "warning_soft": "#332B00",
    "success": "#00FF66",
    "success_soft": "#003311",
    "neutral_soft": "#1A1A1A",
}
```

Once added, `set_theme("HighContrast")` makes it available through `get_colors()`, and every chart that accepts `theme_colors=get_colors()` will pick it up automatically.

## Known Gaps (useful context for future work)
- **`heatmap.py` colormap is not overridable per-call.** `app/streamlit_app.py` calls `plot_similarity_heatmap(..., cmap=heatmap_cmap, ...)` in one place (search for `# Dynamic colormap support`), but `plot_similarity_heatmap`'s signature has no `cmap` parameter — it only has `theme_colors`, not a colormap override. As written, that call site would raise a `TypeError` if it executes, since `cmap` isn't a valid keyword argument for the function. Adding a `cmap: str = _CMAP` parameter to `plot_similarity_heatmap` (and using it in place of the hardcoded `_CMAP` inside the function) would resolve this.
- **`plot_similarity_distribution` and `plot_document_sizes` are not exported** from `src/visualization/__init__.py`. They're defined in `analytics.py` but must currently be imported as `from src.visualization.analytics import plot_similarity_distribution` rather than `from src.visualization import plot_similarity_distribution`.
- **`analytics.py` charts don't take `theme_colors`.** Their colors are hardcoded hex strings, so they won't shift with the Light/Dark toggle the way `heatmap.py` and `network_graph.py` do.