
def test_embed_empty_text_returns_zero_vector():
    from embeddings import embed
    vec = embed("")
    assert len(vec) == 0 or all(v == 0.0 for v in vec), "empty input should return empty or zero vector"
