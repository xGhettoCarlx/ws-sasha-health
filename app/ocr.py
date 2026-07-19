"""Grok Vision OCR adapter for medical document analysis.

Uses xAI Grok Vision models via OpenAI-compatible chat/completions endpoint.
Handles image encoding, API retry, and JSON normalisation into AnalysisSchema.
"""

import base64
import json
import logging
import mimetypes
import re
import time
from pathlib import Path

import httpx

from app.config import get_settings
from app.schemas.analysis import AnalysisSchema, ParameterItem

logger = logging.getLogger(__name__)

# Max uncompressed image size (10 MB)
MAX_IMAGE_BYTES = 10 * 1024 * 1024

# Supported MIME types (per xAI docs: jpg/jpeg, png)
SUPPORTED_MIME_TYPES = {"image/jpeg", "image/png"}

# System prompt for medical document OCR
OCR_SYSTEM_PROMPT = (
    "You are a medical document OCR engine. "
    "Extract structured data from medical documents precisely. "
    "Always return valid JSON with no extra commentary."
)

# User prompt requesting specific JSON structure
OCR_USER_PROMPT = (
    "Extract all medical data from this document. "
    "Return JSON with exactly these fields:\n"
    '- test_name: string (test/analysis name, e.g. "Биохимический анализ крови")\n'
    '- date: string (ISO date YYYY-MM-DD if found, else "")\n'
    '- institution: string (clinic/hospital name if found, else "")\n'
    "- parameters: array of {name, value, unit, ref_range} "
    "(each measured parameter)\n"
    '- conclusion: string (clinical conclusion if found, else "")\n\n'
    "IMPORTANT: Return ONLY the JSON object. No markdown, no explanation."
)


class GrokVisionOCR:
    """OCR adapter using xAI Grok Vision models.

    Sends medical document images to Grok Vision and returns structured
    ``AnalysisSchema`` objects with extracted test parameters, institution,
    and clinical conclusions.

    Usage::

        ocr = GrokVisionOCR(api_key="xai-...")
        result = await ocr.analyze_image("blood_test.jpg")
        print(result.test_name, len(result.parameters))
        await ocr.close()
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "grok-4.3",
        base_url: str = "https://api.x.ai/v1",
        max_retries: int = 3,
        base_delay: float = 1.0,
        request_timeout: float = 30.0,
    ):
        """Initialise OCR adapter.

        Args:
            api_key: xAI API key. Falls back to ``XAI_API_KEY`` from config.
            model: Grok model identifier (default: ``grok-4.3``).
            base_url: xAI API base URL.
            max_retries: Number of retry attempts on transient errors.
            base_delay: Initial backoff delay in seconds (doubles each retry).
            request_timeout: Timeout per request in seconds.
        """
        self.api_key: str | None = api_key or get_settings().XAI_API_KEY
        self.model = model
        self.base_url = base_url
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.request_timeout = request_timeout
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze_image(self, image_path: str) -> AnalysisSchema:
        """Analyze a medical document image using Grok Vision OCR.

        Args:
            image_path: Path to the image file (JPEG or PNG).

        Returns:
            AnalysisSchema with extracted test name, parameters,
            institution, conclusion, and metadata.

        Raises:
            FileNotFoundError: Image file doesn't exist.
            ValueError: Image too large or unsupported format.
            RuntimeError: All API attempts exhausted without success.
        """
        mime_type, image_data_url = self._encode_image(image_path)

        logger.info("Grok OCR: processing %s (%s)", image_path, mime_type)

        raw_response = await self._call_grok_api(image_data_url, mime_type)
        result = self._normalize_results(raw_response)

        logger.info(
            "Grok OCR: done — test_name=%r params=%d tier=%s",
            result.test_name,
            len(result.parameters),
            result.trust_tier,
        )
        return result

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Internal: image encoding
    # ------------------------------------------------------------------

    def _encode_image(self, image_path: str) -> tuple[str, str]:
        """Read image file and return ``(mime_type, data_url)``.

        Validates file existence, size, and supported format.

        Returns:
            Tuple of ``(mime_type, "data:<mime>;base64,<b64>")``.
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        file_size = path.stat().st_size
        if file_size > MAX_IMAGE_BYTES:
            raise ValueError(
                f"Image too large: {file_size} bytes "
                f"(max {MAX_IMAGE_BYTES:,})"
            )

        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type not in SUPPORTED_MIME_TYPES:
            # Default fallback — xAI accepts jpeg/png
            mime_type = "image/png"

        with open(path, "rb") as fh:
            image_data = fh.read()

        b64 = base64.b64encode(image_data).decode("utf-8")
        data_url = f"data:{mime_type};base64,{b64}"
        return mime_type, data_url

    # ------------------------------------------------------------------
    # Internal: API call with retry
    # ------------------------------------------------------------------

    async def _call_grok_api(
        self, image_data_url: str, mime_type: str
    ) -> dict:
        """Call xAI chat/completions endpoint with exponential-backoff retry.

        Retries: ``self.max_retries`` attempts (default 3).
        Delays: 1s → 2s → 4s (base × 2^(attempt-1)).
        Timeout: ``self.request_timeout`` per request (default 30s).

        Returns:
            ``{"raw_content": "<response text>"}``.

        Raises:
            RuntimeError: All retry attempts exhausted.
        """
        payload = self._build_payload(image_data_url, mime_type)
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                client = await self._get_client()
                resp = await client.post("/chat/completions", json=payload)
                resp.raise_for_status()
                data = resp.json()
                content_text = self._extract_content(data)
                return {"raw_content": content_text}
            except (
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.ReadError,
                httpx.HTTPStatusError,
            ) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "Grok API attempt %d/%d failed (%s). Retrying in %.0fs…",
                        attempt,
                        self.max_retries,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "Grok API: all %d attempts exhausted. Last: %s",
                        self.max_retries,
                        exc,
                    )
            except Exception as exc:
                # Non-transient errors — don't retry
                raise RuntimeError(f"Grok API unrecoverable error: {exc}") from exc

        raise RuntimeError(
            f"Grok API call failed after {self.max_retries} attempts. "
            f"Last error: {last_error}"
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Return (lazily created) httpx AsyncClient."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.request_timeout),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    def _build_payload(
        self, image_data_url: str, mime_type: str
    ) -> dict:
        """Construct the OpenAI-compatible request payload."""
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": OCR_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_data_url},
                        },
                        {"type": "text", "text": OCR_USER_PROMPT},
                    ],
                },
            ],
            "max_tokens": 500,
        }

    @staticmethod
    def _extract_content(response_data: dict) -> str:
        """Extract text content from chat/completions response."""
        choices = response_data.get("choices", [])
        if not choices:
            raise ValueError("Empty choices in API response")
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if not content:
            raise ValueError("Empty content in API response")
        return content

    # ------------------------------------------------------------------
    # Internal: response normalisation
    # ------------------------------------------------------------------

    def _normalize_results(self, raw_response: dict) -> AnalysisSchema:
        """Parse raw OCR output into a validated ``AnalysisSchema``.

        Handles:
        - JSON wrapped in markdown fences (`` ```json … ``` ``)
        - Plain JSON objects or arrays
        - Non-JSON / unparseable responses (fallback with ``trust_tier="unverified"``)
        - Russian-equivalent field names as fallback
        """
        raw_text: str = raw_response.get("raw_content", "")

        # --- Step 1: strip markdown fences ---
        cleaned = self._strip_json_fences(raw_text)

        # --- Step 2: try JSON parse ---
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning(
                "Grok OCR: non-JSON response. First 200 chars: %r",
                raw_text[:200],
            )
            return self._fallback_schema(raw_text, "Unparseable JSON response")

        if not isinstance(parsed, dict):
            logger.warning(
                "Grok OCR: response is %s, not dict", type(parsed).__name__
            )
            return self._fallback_schema(raw_text, f"Expected dict, got {type(parsed).__name__}")

        # --- Step 3: build schema from parsed dict ---
        return self._build_schema(parsed, raw_text)

    def _strip_json_fences(self, text: str) -> str:
        """Remove markdown code fences from a string."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            # Remove opening fence: ```json or ```
            cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
            # Remove closing fence
            cleaned = re.sub(r"\n?\s*```\s*$", "", cleaned)
        return cleaned.strip()

    def _fallback_schema(
        self, raw_text: str, reason: str
    ) -> AnalysisSchema:
        """Return a minimal schema for unparseable OCR output."""
        return AnalysisSchema(
            test_name="Unknown",
            date="",
            trust_tier="unverified",
            source=f"Grok Vision OCR ({reason})",
            content=raw_text,
            tags=["ocr_fallback"],
            parameters=[],
        )

    def _build_schema(
        self, parsed: dict, raw_text: str
    ) -> AnalysisSchema:
        """Build ``AnalysisSchema`` from a successfully parsed dictionary.

        Supports both English and Russian field names.
        """
        # --- test_name ---
        test_name = parsed.get("test_name") or parsed.get("название_теста") or "Unknown"

        # --- date ---
        date = parsed.get("date") or parsed.get("дата") or ""

        # --- institution ---
        institution: str | None = parsed.get("institution") or parsed.get("учреждение") or None

        # --- parameters ---
        raw_params = parsed.get("parameters") or parsed.get("параметры") or []
        parameters: list[ParameterItem] = []
        if isinstance(raw_params, list):
            for item in raw_params:
                if not isinstance(item, dict):
                    continue
                param = ParameterItem(
                    name=str(item.get("name") or item.get("название") or ""),
                    value=str(item.get("value") or item.get("значение") or ""),
                    unit=item.get("unit") or item.get("единица"),
                    ref_range=(
                        item.get("ref_range")
                        or item.get("реф_диапазон")
                        or item.get("норма")
                    ),
                    trust_tier="unverified",
                    date=date,
                )
                parameters.append(param)

        # --- conclusion ---
        conclusion: str | None = parsed.get("conclusion") or parsed.get("заключение") or None

        return AnalysisSchema(
            test_name=test_name,
            date=date or "",
            institution=institution,
            equipment=parsed.get("equipment"),
            parameters=parameters,
            conclusion=conclusion,
            recommendations=parsed.get("recommendations"),
            trust_tier="unverified",
            source="Grok Vision OCR",
            content=raw_text,
        )
