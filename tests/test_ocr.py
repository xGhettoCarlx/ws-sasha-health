"""Tests for app.ocr — GrokVisionOCR adapter."""

import base64
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from app.ocr import (
    MAX_IMAGE_BYTES,
    OCR_SYSTEM_PROMPT,
    OCR_USER_PROMPT,
    GrokVisionOCR,
)
from app.schemas.analysis import AnalysisSchema

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_image_png(tmp_path: Path, content: bytes = b"\x89PNG\r\n\x1a\nmock") -> Path:
    """Create a minimal fake PNG file on disk."""
    path = tmp_path / "test_image.png"
    path.write_bytes(content)
    return path


def _b64_png(content: bytes = b"\x89PNG\r\n\x1a\nmock") -> str:
    """Return a data URL for a fake PNG."""
    b64 = base64.b64encode(content).decode()
    return f"data:image/png;base64,{b64}"


def _mock_httpx_response(content: str, status: int = 200) -> Mock:
    """Build a Mock httpx.Response with chat/completions shape."""
    resp = Mock(spec=httpx.Response)
    resp.status_code = status
    resp.json.return_value = {
        "choices": [
            {"message": {"role": "assistant", "content": content}}
        ]
    }
    resp.raise_for_status = Mock()
    return resp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ocr_instance():
    """GrokVisionOCR instance with a fake API key (no real calls)."""
    return GrokVisionOCR(api_key="xai-test-key", model="grok-4.3")


@pytest.fixture
def sample_png(tmp_path):
    return _make_image_png(tmp_path)


# ---------------------------------------------------------------------------
# Tests: _encode_image
# ---------------------------------------------------------------------------


class TestEncodeImage:
    def test_encodes_valid_png(self, ocr_instance, sample_png):
        mime, data_url = ocr_instance._encode_image(str(sample_png))
        assert mime == "image/png"
        assert data_url.startswith("data:image/png;base64,")
        # Decode and verify original bytes
        b64_part = data_url.split(",", 1)[1]
        decoded = base64.b64decode(b64_part)
        assert decoded == b"\x89PNG\r\n\x1a\nmock"

    def test_raises_on_missing_file(self, ocr_instance):
        with pytest.raises(FileNotFoundError):
            ocr_instance._encode_image("/nonexistent/path.png")

    def test_raises_on_oversized_image(self, ocr_instance, tmp_path):
        big = tmp_path / "big.png"
        big.write_bytes(b"x" * (MAX_IMAGE_BYTES + 1))
        with pytest.raises(ValueError, match="Image too large"):
            ocr_instance._encode_image(str(big))

    def test_max_size_exactly_ok(self, ocr_instance, tmp_path):
        ok = tmp_path / "max.png"
        ok.write_bytes(b"x" * MAX_IMAGE_BYTES)
        mime, data_url = ocr_instance._encode_image(str(ok))
        assert mime == "image/png"


# ---------------------------------------------------------------------------
# Tests: _call_grok_api (with httpx mock)
# ---------------------------------------------------------------------------


class TestCallGrokApi:
    async def test_successful_call_returns_raw_content(self, ocr_instance, sample_png):
        _, data_url = ocr_instance._encode_image(str(sample_png))

        expected_json = json.dumps(
            {
                "test_name": "Blood Test",
                "date": "2026-01-15",
                "institution": "Clinic A",
                "parameters": [
                    {
                        "name": "Hemoglobin",
                        "value": "14.5",
                        "unit": "g/dL",
                        "ref_range": "12-16",
                    }
                ],
                "conclusion": "Normal",
            }
        )

        mock_response = _mock_httpx_response(expected_json)
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        ocr_instance._client = mock_client

        result = await ocr_instance._call_grok_api(data_url, "image/png")
        assert "raw_content" in result
        assert result["raw_content"] == expected_json

        # Verify the payload was built correctly
        args, kwargs = mock_client.post.call_args
        assert args[0] == "/chat/completions"
        sent_payload = kwargs["json"]
        assert sent_payload["model"] == "grok-4.3"
        assert sent_payload["messages"][0]["role"] == "system"
        assert sent_payload["messages"][0]["content"] == OCR_SYSTEM_PROMPT
        assert sent_payload["max_tokens"] == 500

    async def test_retry_on_timeout_then_succeeds(self, ocr_instance, sample_png):
        """First two calls timeout, third succeeds."""
        _, data_url = ocr_instance._encode_image(str(sample_png))

        mock_client = AsyncMock()
        # Fails twice, succeeds on third
        mock_client.post.side_effect = [
            httpx.TimeoutException("timeout"),
            httpx.TimeoutException("timeout"),
            _mock_httpx_response(json.dumps({"test_name": "X", "date": "2026-01-01"})),
        ]

        ocr_instance._client = mock_client
        ocr_instance.max_retries = 3
        ocr_instance.base_delay = 0.01  # fast in tests

        result = await ocr_instance._call_grok_api(data_url, "image/png")
        assert result["raw_content"] == json.dumps({"test_name": "X", "date": "2026-01-01"})
        assert mock_client.post.call_count == 3

    async def test_all_retries_exhausted_raises(self, ocr_instance, sample_png):
        """All three attempts fail → RuntimeError."""
        _, data_url = ocr_instance._encode_image(str(sample_png))

        mock_client = AsyncMock()
        mock_client.post.side_effect = [
            httpx.TimeoutException("t1"),
            httpx.ConnectError("c2"),
            httpx.ReadError("r3"),
        ]

        ocr_instance._client = mock_client
        ocr_instance.max_retries = 3
        ocr_instance.base_delay = 0.01

        with pytest.raises(RuntimeError, match="failed after 3 attempts"):
            await ocr_instance._call_grok_api(data_url, "image/png")

    async def test_http_error_retried(self, ocr_instance, sample_png):
        """HTTP 500 is retried, then succeeds."""
        _, data_url = ocr_instance._encode_image(str(sample_png))

        err_resp = Mock(spec=httpx.Response)
        err_resp.status_code = 500
        err_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "server error", request=Mock(), response=err_resp
        )

        mock_client = AsyncMock()
        mock_client.post.side_effect = [
            httpx.HTTPStatusError("500", request=Mock(), response=err_resp),
            _mock_httpx_response(json.dumps({"test_name": "Ok"})),
        ]

        ocr_instance._client = mock_client
        ocr_instance.max_retries = 3
        ocr_instance.base_delay = 0.01

        result = await ocr_instance._call_grok_api(data_url, "image/png")
        assert result["raw_content"] == json.dumps({"test_name": "Ok"})
        assert mock_client.post.call_count == 2


# ---------------------------------------------------------------------------
# Tests: _normalize_results
# ---------------------------------------------------------------------------


class TestNormalizeResults:
    def test_valid_json_parsed_correctly(self, ocr_instance):
        raw = {
            "raw_content": json.dumps(
                {
                    "test_name": "Биохимический анализ",
                    "date": "2026-06-15",
                    "institution": "Городская больница №5",
                    "parameters": [
                        {
                            "name": "Белок общий",
                            "value": "76.0",
                            "unit": "г/л",
                            "ref_range": "65-85",
                        },
                        {
                            "name": "Глюкоза",
                            "value": "5.2",
                            "unit": "ммоль/л",
                            "ref_range": "3.3-5.5",
                        },
                    ],
                    "conclusion": "Показатели в норме",
                }
            )
        }
        result = ocr_instance._normalize_results(raw)

        assert isinstance(result, AnalysisSchema)
        assert result.test_name == "Биохимический анализ"
        assert result.date == "2026-06-15"
        assert result.institution == "Городская больница №5"
        assert result.conclusion == "Показатели в норме"
        assert result.trust_tier == "unverified"
        assert result.source == "Grok Vision OCR"
        assert len(result.parameters) == 2
        assert result.parameters[0].name == "Белок общий"
        assert result.parameters[0].value == "76.0"
        assert result.parameters[0].unit == "г/л"
        assert result.parameters[0].ref_range == "65-85"
        assert result.parameters[1].name == "Глюкоза"

    def test_json_with_markdown_fences(self, ocr_instance):
        """Response wrapped in ```json ... ``` fences."""
        raw = {
            "raw_content": """```json
{
    "test_name": "Анализ мочи",
    "date": "2026-05-10",
    "parameters": [
        {"name": "pH", "value": "5.5", "unit": "", "ref_range": "5.0-7.0"}
    ],
    "conclusion": "Норма"
}
```"""
        }
        result = ocr_instance._normalize_results(raw)
        assert result.test_name == "Анализ мочи"
        assert result.date == "2026-05-10"
        assert len(result.parameters) == 1
        assert result.parameters[0].name == "pH"

    def test_markdown_fences_with_newlines(self, ocr_instance):
        """Fences on their own lines with extra whitespace."""
        raw = {
            "raw_content": """```json

{"test_name": "X", "date": "2026-01-01"}

```
"""
        }
        result = ocr_instance._normalize_results(raw)
        assert result.test_name == "X"

    def test_unparseable_json_fallback(self, ocr_instance):
        """Non-JSON text → fallback schema with raw text."""
        raw = {
            "raw_content": "Sorry, I could not read this document clearly."
        }
        result = ocr_instance._normalize_results(raw)
        assert result.test_name == "Unknown"
        assert result.trust_tier == "unverified"
        assert result.content == "Sorry, I could not read this document clearly."
        assert result.tags == ["ocr_fallback"]
        assert result.parameters == []
        assert "Unparseable" in (result.source or "")

    def test_json_array_instead_of_object(self, ocr_instance):
        """Array response → fallback."""
        raw = {"raw_content": '[{"test_name": "A"}]'}
        result = ocr_instance._normalize_results(raw)
        assert result.test_name == "Unknown"
        assert "Expected dict" in (result.source or "")

    def test_empty_string_fallback(self, ocr_instance):
        raw = {"raw_content": ""}
        result = ocr_instance._normalize_results(raw)
        assert result.test_name == "Unknown"
        assert result.content == ""

    def test_russian_field_names(self, ocr_instance):
        """Russian keys as fallback when English keys missing."""
        raw = {
            "raw_content": json.dumps(
                {
                    "название_теста": "ОАК",
                    "дата": "2026-04-01",
                    "учреждение": "Поликлиника №1",
                    "параметры": [
                        {
                            "название": "Лейкоциты",
                            "значение": "6.2",
                            "единица": "10^9/л",
                            "норма": "4.0-9.0",
                        }
                    ],
                    "заключение": "Без патологий",
                },
                ensure_ascii=False,
            )
        }
        result = ocr_instance._normalize_results(raw)
        assert result.test_name == "ОАК"
        assert result.date == "2026-04-01"
        assert result.institution == "Поликлиника №1"
        assert result.conclusion == "Без патологий"
        assert len(result.parameters) == 1
        assert result.parameters[0].name == "Лейкоциты"
        assert result.parameters[0].value == "6.2"
        assert result.parameters[0].unit == "10^9/л"
        assert result.parameters[0].ref_range == "4.0-9.0"

    def test_mixed_english_russian_keys(self, ocr_instance):
        """English keys take priority; Russian used as fallback."""
        raw = {
            "raw_content": json.dumps(
                {
                    "test_name": "MRI",
                    "название_теста": "МРТ (should be ignored)",
                    "дата": "2026-03-03",
                    "institution": "Center",
                    "учреждение": "should be ignored",
                },
                ensure_ascii=False,
            )
        }
        result = ocr_instance._normalize_results(raw)
        assert result.test_name == "MRI"  # English wins
        assert result.institution == "Center"  # English wins
        assert result.date == "2026-03-03"

    def test_missing_optional_fields(self, ocr_instance):
        """Only test_name present — all other fields get defaults."""
        raw = {"raw_content": json.dumps({"test_name": "Simple"})}
        result = ocr_instance._normalize_results(raw)
        assert result.test_name == "Simple"
        assert result.date == ""
        assert result.institution is None
        assert result.conclusion is None
        assert result.parameters == []

    def test_parameter_with_minimal_fields(self, ocr_instance):
        """Parameter with only name and value."""
        raw = {
            "raw_content": json.dumps(
                {
                    "test_name": "T",
                    "parameters": [{"name": "P", "value": "10"}],
                }
            )
        }
        result = ocr_instance._normalize_results(raw)
        assert len(result.parameters) == 1
        assert result.parameters[0].name == "P"
        assert result.parameters[0].value == "10"
        assert result.parameters[0].unit is None
        assert result.parameters[0].ref_range is None

    def test_parameter_skips_non_dict_entries(self, ocr_instance):
        """Non-dict items in parameters array are skipped."""
        raw = {
            "raw_content": json.dumps(
                {
                    "test_name": "T",
                    "parameters": [
                        "bad_string",
                        123,
                        {"name": "Valid", "value": "ok"},
                        None,
                    ],
                }
            )
        }
        result = ocr_instance._normalize_results(raw)
        assert len(result.parameters) == 1
        assert result.parameters[0].name == "Valid"


# ---------------------------------------------------------------------------
# Tests: analyze_image (integration-style with mocks)
# ---------------------------------------------------------------------------


class TestAnalyzeImage:
    async def test_full_pipeline_success(self, ocr_instance, sample_png):
        """End-to-end: image → encode → API → normalize."""
        good_json = json.dumps(
            {
                "test_name": "Full pipeline",
                "date": "2026-07-01",
                "institution": "Hospital",
                "parameters": [
                    {
                        "name": "WBC",
                        "value": "7.0",
                        "unit": "K/uL",
                        "ref_range": "4.0-11.0",
                    }
                ],
                "conclusion": "OK",
            }
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = _mock_httpx_response(good_json)
        ocr_instance._client = mock_client

        result = await ocr_instance.analyze_image(str(sample_png))
        assert result.test_name == "Full pipeline"
        assert result.date == "2026-07-01"
        assert result.institution == "Hospital"
        assert result.trust_tier == "unverified"
        assert result.source == "Grok Vision OCR"
        assert len(result.parameters) == 1

    async def test_fallback_on_bad_json(self, ocr_instance, sample_png):
        """Unparseable response → fallback schema returned."""
        mock_client = AsyncMock()
        mock_client.post.return_value = _mock_httpx_response(
            "Not JSON at all, just text"
        )
        ocr_instance._client = mock_client

        result = await ocr_instance.analyze_image(str(sample_png))
        assert result.test_name == "Unknown"
        assert result.trust_tier == "unverified"
        assert "Not JSON at all, just text" in (result.content or "")
        assert "ocr_fallback" in result.tags
        assert result.parameters == []

    async def test_close_cleans_up_client(self, ocr_instance, sample_png):
        """close() sets _client to None and calls aclose."""
        _, data_url = ocr_instance._encode_image(str(sample_png))

        mock_client = AsyncMock()
        mock_client.post.return_value = _mock_httpx_response(
            json.dumps({"test_name": "T"})
        )
        ocr_instance._client = mock_client

        await ocr_instance.close()
        mock_client.aclose.assert_awaited_once()
        assert ocr_instance._client is None

    async def test_analyze_after_close_recreates_client(self, ocr_instance, sample_png):
        """After close(), next analyze_image() lazily creates new client."""
        # Do one call, then close
        mock1 = AsyncMock()
        mock1.post.return_value = _mock_httpx_response(
            json.dumps({"test_name": "First"})
        )
        ocr_instance._client = mock1
        await ocr_instance.analyze_image(str(sample_png))
        await ocr_instance.close()

        # Now another analyze_image — should create new client
        mock2 = AsyncMock()
        mock2.post.return_value = _mock_httpx_response(
            json.dumps({"test_name": "Second"})
        )
        ocr_instance._client = mock2

        result = await ocr_instance.analyze_image(str(sample_png))
        assert result.test_name == "Second"
        # Original mock should be closed, new one not yet
        mock1.aclose.assert_awaited_once()


# ---------------------------------------------------------------------------
# Tests: constructor / config integration
# ---------------------------------------------------------------------------


class TestConstructor:
    def test_explicit_api_key_used(self, ocr_instance):
        assert ocr_instance.api_key == "xai-test-key"

    def test_default_model_is_grok_4_3(self):
        ocr = GrokVisionOCR(api_key="k")
        assert ocr.model == "grok-4.3"

    def test_custom_params_passed_through(self):
        ocr = GrokVisionOCR(
            api_key="k",
            model="grok-custom",
            max_retries=5,
            base_delay=2.0,
            request_timeout=15.0,
        )
        assert ocr.model == "grok-custom"
        assert ocr.max_retries == 5
        assert ocr.base_delay == 2.0
        assert ocr.request_timeout == 15.0


# ---------------------------------------------------------------------------
# Tests: prompt constant integrity
# ---------------------------------------------------------------------------


class TestPrompts:
    def test_system_prompt_mentions_ocr(self):
        assert "OCR" in OCR_SYSTEM_PROMPT
        assert "JSON" in OCR_SYSTEM_PROMPT

    def test_user_prompt_contains_expected_fields(self):
        assert "test_name" in OCR_USER_PROMPT
        assert "date" in OCR_USER_PROMPT
        assert "institution" in OCR_USER_PROMPT
        assert "parameters" in OCR_USER_PROMPT
        assert "conclusion" in OCR_USER_PROMPT
        assert "JSON" in OCR_USER_PROMPT
