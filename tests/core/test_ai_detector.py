"""
test_ai_detector.py
-------------------
Tests for AI-generated text detection functionality.

Includes tests for:
- Probability detection batch and single text functions
- Confidence tier categorization
- Document-level AI detection statistics
- Text perplexity scoring helper (Issue #1154)
"""

import math
from unittest.mock import MagicMock, patch
import pytest

from src.core.ai_detector import (
    calculate_text_perplexity,
    categorize_ai_probability,
    detect_ai_generated_text,
    detect_ai_probability,
    detect_ai_probability_batch,
    detect_document_ai_probability,
    detect_documents_ai_probability,
)


def test_categorize_ai_probability_boundaries():
    """Verify that the confidence categorization partitions the [0,1] range correctly."""
    assert categorize_ai_probability(0.85) == "High Probability"
    assert categorize_ai_probability(0.80) == "High Probability"
    assert categorize_ai_probability(0.79) == "Moderate Probability"
    assert categorize_ai_probability(0.65) == "Moderate Probability"
    assert categorize_ai_probability(0.50) == "Moderate Probability"
    assert categorize_ai_probability(0.49) == "Low Probability"
    assert categorize_ai_probability(0.20) == "Low Probability"
    assert categorize_ai_probability(0.00) == "Low Probability"


@pytest.fixture(autouse=True)
def mock_transformers_pipeline():
    """Autouse fixture to mock Hugging Face pipeline across all tests in this module."""
    with patch("transformers.pipeline") as mock_pipe:
        mock_classifier = MagicMock()
        # Mock pipeline output format: [{'label': 'Fake', 'score': 0.85}]
        mock_classifier.return_value = [[{"label": "Fake", "score": 0.85}]]
        mock_pipe.return_value = mock_classifier
        yield mock_pipe


def test_detect_ai_probability_empty_text():
    """Test that empty text returns 0.0 probability."""
    result = detect_ai_probability("")
    assert result == 0.0


def test_detect_ai_probability_none():
    """Test that None input returns 0.0 probability."""
    result = detect_ai_probability(None)
    assert result == 0.0


def test_detect_ai_probability_whitespace_only():
    """Test that whitespace-only text returns 0.0 probability."""
    result = detect_ai_probability("   \n\t  ")
    assert result == 0.0


def test_detect_ai_probability_batch_empty():
    """Test that empty list returns empty list."""
    result = detect_ai_probability_batch([])
    assert result == []


def test_detect_document_ai_probability_empty():
    """Test that empty chunks return zero probabilities."""
    result = detect_document_ai_probability([])
    assert result["overall"] == 0.0
    assert result["max"] == 0.0
    assert result["chunk_scores"] == []


def test_detect_documents_ai_probability_empty():
    """Test that empty dict returns empty dict."""
    result = detect_documents_ai_probability({})
    assert result == {}


def test_detect_documents_ai_probability_single_doc():
    """Test AI detection with a single document."""
    chunked_docs = {
        "test_doc.txt": ["This is a test chunk of text.", "Another test chunk here."]
    }
    result = detect_documents_ai_probability(chunked_docs)

    assert "test_doc.txt" in result
    assert "overall" in result["test_doc.txt"]
    assert "max" in result["test_doc.txt"]
    assert "chunk_scores" in result["test_doc.txt"]
    assert len(result["test_doc.txt"]["chunk_scores"]) == 2
    assert 0.0 <= result["test_doc.txt"]["overall"] <= 1.0
    assert 0.0 <= result["test_doc.txt"]["max"] <= 1.0


def test_detect_ai_probability_batch_mixed():
    """Test batch detection with mixed empty and non-empty texts."""
    texts = ["Some text", "", None, "More text"]
    result = detect_ai_probability_batch(texts)

    assert len(result) == 4
    assert result[1] == 0.0  # Empty string
    assert result[2] == 0.0  # None
    assert 0.0 <= result[0] <= 1.0
    assert 0.0 <= result[3] <= 1.0


def test_detect_ai_generated_text_empty():
    """Verify that empty text returns low confidence default dictionary."""
    res = detect_ai_generated_text("")
    assert res["ai_probability"] == 0.0
    assert res["confidence_tier"] == "low"
    assert res["perplexity_score"] == 150.0


def test_detect_ai_generated_text_whitespace():
    """Verify that whitespace-only text returns low confidence default dictionary."""
    res = detect_ai_generated_text("   \n\t  ")
    assert res["ai_probability"] == 0.0
    assert res["confidence_tier"] == "low"
    assert res["perplexity_score"] == 150.0


def test_detect_ai_generated_text_tiers():
    """Verify that confidence categorizations partition correctly."""
    with patch("src.core.ai_detector.detect_ai_probability") as mock_prob:
        # High confidence AI (>= 0.75)
        mock_prob.return_value = 0.85
        res = detect_ai_generated_text("Test AI text")
        assert res["ai_probability"] == 0.85
        assert res["confidence_tier"] == "high"
        assert res["perplexity_score"] == float(150.0 - 110.0 * 0.85)

        # Medium confidence (0.40 <= prob < 0.75)
        mock_prob.return_value = 0.55
        res = detect_ai_generated_text("Test medium text")
        assert res["ai_probability"] == 0.55
        assert res["confidence_tier"] == "medium"
        assert res["perplexity_score"] == float(150.0 - 110.0 * 0.55)

        # Low confidence (< 0.40)
        mock_prob.return_value = 0.25
        res = detect_ai_generated_text("Test human text")
        assert res["ai_probability"] == 0.25
        assert res["confidence_tier"] == "low"
        assert res["perplexity_score"] == float(150.0 - 110.0 * 0.25)


# ─── Tests for calculate_text_perplexity (Issue #1154) ──────────────────────────


def test_calculate_text_perplexity_empty_string():
    """Empty string must return the default perplexity score of 0.0."""
    result = calculate_text_perplexity("")
    assert result == 0.0


def test_calculate_text_perplexity_none_input():
    """None input must return the default perplexity score of 0.0."""
    result = calculate_text_perplexity(None)
    assert result == 0.0


def test_calculate_text_perplexity_whitespace_only():
    """Whitespace-only text must return the default perplexity score of 0.0."""
    result = calculate_text_perplexity("   \n\t  ")
    assert result == 0.0


def test_calculate_text_perplexity_returns_float():
    """The return type must always be a float."""
    result = calculate_text_perplexity("This is a valid sentence for testing.")
    assert isinstance(result, float)


def test_calculate_text_perplexity_with_fallback_model():
    """When model is in fallback mode, return default perplexity score."""
    with patch("src.core.ai_detector._get_model_and_tokenizer") as mock_loader:
        mock_loader.return_value = ("fallback", "fallback")
        result = calculate_text_perplexity("Some text to evaluate.")
        assert result == 0.0


def test_calculate_text_perplexity_with_mock_model():
    """Verify perplexity calculation with a mocked transformer model and tokenizer."""
    mock_model = MagicMock()
    mock_tokenizer = MagicMock()

    # Mock the model config to provide a max_length value
    mock_config = MagicMock()
    mock_config.max_position_embeddings = 512
    mock_model.config = mock_config

    # Mock the tokenizer output with tensors that simulate tokenized input
    mock_input_ids = MagicMock()
    mock_input_ids.to = MagicMock(return_value=mock_input_ids)

    mock_attention_mask = MagicMock()
    mock_attention_mask.to = MagicMock(return_value=mock_attention_mask)

    mock_tokenizer.return_value = {
        "input_ids": mock_input_ids,
        "attention_mask": mock_attention_mask,
    }

    # Mock the model output with a specific loss value
    # loss = ln(perplexity), so perplexity = exp(loss)
    # If we want perplexity = 50.0, loss = ln(50) ≈ 3.912
    mock_loss_value = math.log(50.0)
    mock_outputs = MagicMock()
    mock_outputs.loss = MagicMock()
    mock_outputs.loss.item = MagicMock(return_value=mock_loss_value)

    # The float() call on loss will use the item() value
    # We need to mock __float__ on the loss tensor
    type(mock_outputs.loss).__float__ = MagicMock(return_value=mock_loss_value)

    mock_model.return_value = mock_outputs
    mock_model.to = MagicMock(return_value=mock_model)

    with patch(
        "src.core.ai_detector._get_model_and_tokenizer",
        return_value=(mock_model, mock_tokenizer),
    ):
        # Reset the global model/tokenizer to force re-loading
        import src.core.ai_detector as module

        original_model = module._model
        original_tokenizer = module._tokenizer
        module._model = mock_model
        module._tokenizer = mock_tokenizer

        try:
            result = calculate_text_perplexity(
                "The quick brown fox jumps over the lazy dog."
            )
            # Result should be a float value
            assert isinstance(result, float)
            # Perplexity should be >= 0
            assert result >= 0.0
        finally:
            # Restore original globals
            module._model = original_model
            module._tokenizer = original_tokenizer


def test_calculate_text_perplexity_handles_exception_gracefully():
    """If the model throws an unexpected error, return default perplexity score."""
    with patch("src.core.ai_detector._get_model_and_tokenizer") as mock_loader:
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_loader.return_value = (mock_model, mock_tokenizer)

        # Make the tokenizer raise an exception to simulate a failure
        mock_tokenizer.side_effect = RuntimeError("Simulated tokenizer failure")

        import src.core.ai_detector as module

        original_model = module._model
        original_tokenizer = module._tokenizer
        module._model = mock_model
        module._tokenizer = mock_tokenizer

        try:
            result = calculate_text_perplexity("Some text that will fail tokenization.")
            assert result == 0.0
        finally:
            module._model = original_model
            module._tokenizer = original_tokenizer


def test_calculate_text_perplexity_value_error_handling():
    """ValueError during perplexity computation must return the default score."""
    with patch("src.core.ai_detector._get_model_and_tokenizer") as mock_loader:
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_loader.return_value = (mock_model, mock_tokenizer)

        # Make the tokenizer raise ValueError
        mock_tokenizer.side_effect = ValueError("Text too short to tokenize")

        import src.core.ai_detector as module

        original_model = module._model
        original_tokenizer = module._tokenizer
        module._model = mock_model
        module._tokenizer = mock_tokenizer

        try:
            result = calculate_text_perplexity("ab")
            assert result == 0.0
        finally:
            module._model = original_model
            module._tokenizer = original_tokenizer


def test_calculate_text_perplexity_non_string_input():
    """Non-string inputs must return the default perplexity score."""
    assert calculate_text_perplexity(123) == 0.0
    assert calculate_text_perplexity([]) == 0.0
    assert calculate_text_perplexity({}) == 0.0
    assert calculate_text_perplexity(True) == 0.0


def test_calculate_text_perplexity_long_text():
    """Very long text should be handled gracefully with truncation."""
    long_text = "This is a sentence. " * 500
    result = calculate_text_perplexity(long_text)
    assert isinstance(result, float)
    assert result >= 0.0


def test_calculate_text_perplexity_returns_non_negative():
    """Perplexity must always be a non-negative value."""
    with patch("src.core.ai_detector._get_model_and_tokenizer") as mock_loader:
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()

        mock_config = MagicMock()
        mock_config.max_position_embeddings = 512
        mock_model.config = mock_config

        mock_input_ids = MagicMock()
        mock_input_ids.to = MagicMock(return_value=mock_input_ids)
        mock_attention_mask = MagicMock()
        mock_attention_mask.to = MagicMock(return_value=mock_attention_mask)

        mock_tokenizer.return_value = {
            "input_ids": mock_input_ids,
            "attention_mask": mock_attention_mask,
        }

        # Create a loss that yields a positive perplexity
        mock_loss_value = 3.0  # exp(3.0) ≈ 20.09
        mock_outputs = MagicMock()
        mock_outputs.loss = MagicMock()
        type(mock_outputs.loss).__float__ = MagicMock(return_value=mock_loss_value)

        mock_model.return_value = mock_outputs
        mock_model.to = MagicMock(return_value=mock_model)

        mock_loader.return_value = (mock_model, mock_tokenizer)

        import src.core.ai_detector as module

        original_model = module._model
        original_tokenizer = module._tokenizer
        module._model = mock_model
        module._tokenizer = mock_tokenizer

        try:
            result = calculate_text_perplexity("A reasonable length text for analysis.")
            assert result >= 0.0
        finally:
            module._model = original_model
            module._tokenizer = original_tokenizer


def test_calculate_text_perplexity_clamps_large_values():
    """Extremely large perplexity values must be clamped to prevent overflow."""
    with patch("src.core.ai_detector._get_model_and_tokenizer") as mock_loader:
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()

        mock_config = MagicMock()
        mock_config.max_position_embeddings = 512
        mock_model.config = mock_config

        mock_input_ids = MagicMock()
        mock_input_ids.to = MagicMock(return_value=mock_input_ids)
        mock_attention_mask = MagicMock()
        mock_attention_mask.to = MagicMock(return_value=mock_attention_mask)

        mock_tokenizer.return_value = {
            "input_ids": mock_input_ids,
            "attention_mask": mock_attention_mask,
        }

        # Create a very large loss value: exp(100) would overflow
        # The function should clamp it to 10000.0
        mock_loss_value = 100.0
        mock_outputs = MagicMock()
        mock_outputs.loss = MagicMock()
        type(mock_outputs.loss).__float__ = MagicMock(return_value=mock_loss_value)

        mock_model.return_value = mock_outputs
        mock_model.to = MagicMock(return_value=mock_model)

        mock_loader.return_value = (mock_model, mock_tokenizer)

        import src.core.ai_detector as module

        original_model = module._model
        original_tokenizer = module._tokenizer
        module._model = mock_model
        module._tokenizer = mock_tokenizer

        try:
            result = calculate_text_perplexity(
                "Text with extreme perplexity potential."
            )
            assert result <= 10000.0
            assert result >= 0.0
        finally:
            module._model = original_model
            module._tokenizer = original_tokenizer


def test_calculate_text_perplexity_none_loss():
    """If model returns None for loss, return default perplexity score."""
    with patch("src.core.ai_detector._get_model_and_tokenizer") as mock_loader:
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()

        mock_config = MagicMock()
        mock_config.max_position_embeddings = 512
        mock_model.config = mock_config

        mock_input_ids = MagicMock()
        mock_input_ids.to = MagicMock(return_value=mock_input_ids)
        mock_attention_mask = MagicMock()
        mock_attention_mask.to = MagicMock(return_value=mock_attention_mask)

        mock_tokenizer.return_value = {
            "input_ids": mock_input_ids,
            "attention_mask": mock_attention_mask,
        }

        # Model returns None loss
        mock_outputs = MagicMock()
        mock_outputs.loss = None

        mock_model.return_value = mock_outputs
        mock_model.to = MagicMock(return_value=mock_model)

        mock_loader.return_value = (mock_model, mock_tokenizer)

        import src.core.ai_detector as module

        original_model = module._model
        original_tokenizer = module._tokenizer
        module._model = mock_model
        module._tokenizer = mock_tokenizer

        try:
            result = calculate_text_perplexity("Text where loss is None.")
            assert result == 0.0
        finally:
            module._model = original_model
            module._tokenizer = original_tokenizer
