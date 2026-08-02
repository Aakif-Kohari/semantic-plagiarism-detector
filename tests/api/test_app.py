import io
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.api.app import app, get_expected_bearer_token

client = TestClient(app)

def test_scan_missing_content_type():
    expected_token = get_expected_bearer_token()
    response = client.post(
        "/api/v1/scan",
        headers={"Authorization": f"Bearer {expected_token}"},
        content=b""
    )
    assert response.status_code == 415
    assert response.json()["detail"] == "Unsupported Media Type: Request must be multipart/form-data"


def test_scan_invalid_content_type():
    expected_token = get_expected_bearer_token()
    response = client.post(
        "/api/v1/scan",
        headers={
            "Authorization": f"Bearer {expected_token}",
            "Content-Type": "application/json"
        },
        json={"filename": "test.txt"}
    )
    assert response.status_code == 415
    assert response.json()["detail"] == "Unsupported Media Type: Request must be multipart/form-data"


@patch("src.api.app.get_corpus_documents_with_embeddings")
@patch("src.api.app.embed_chunks")
def test_scan_valid_multipart(mock_embed, mock_corpus):
    import numpy as np
    mock_embed.return_value = np.ones((1, 384), dtype=np.float32)
    mock_corpus.return_value = {}
    
    expected_token = get_expected_bearer_token()
    sample_content = b"Some valid content here."
    
    response = client.post(
        "/api/v1/scan",
        headers={"Authorization": f"Bearer {expected_token}"},
        files={"file": ("essay.txt", io.BytesIO(sample_content), "text/plain")},
    )
    
    assert response.status_code == 200
