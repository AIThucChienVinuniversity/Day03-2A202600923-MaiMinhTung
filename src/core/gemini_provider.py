import os
import time
from typing import Dict, Any, Optional, Generator

import google.generativeai as genai

from src.core.llm_provider import LLMProvider


class GeminiProvider(LLMProvider):
    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        api_key: Optional[str] = None
    ):
        """
        Gemini LLM provider.

        API key priority:
        1. api_key passed from main.py
        2. GEMINI_API_KEY environment variable
        3. GOOGLE_API_KEY environment variable
        """

        api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
        )

        if not api_key:
            raise ValueError(
                "Missing Gemini API key. "
                "Please set GEMINI_API_KEY or GOOGLE_API_KEY in .env "
                "or pass api_key from main.py."
            )

        super().__init__(model_name=model_name, api_key=api_key)

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a full response from Gemini.

        Return format:
        {
            "content": str,
            "usage": dict,
            "latency_ms": int,
            "provider": "google",
            "model": str
        }
        """

        start_time = time.time()

        full_prompt = self._build_prompt(
            prompt=prompt,
            system_prompt=system_prompt
        )

        try:
            response = self.model.generate_content(full_prompt)

            content = self._extract_text(response)
            usage = self._extract_usage(response)

            latency_ms = int((time.time() - start_time) * 1000)

            return {
                "content": content,
                "usage": usage,
                "latency_ms": latency_ms,
                "provider": "google",
                "model": self.model_name
            }

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)

            return {
                "content": f"Gemini API error: {str(e)}",
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                },
                "latency_ms": latency_ms,
                "provider": "google",
                "model": self.model_name,
                "error": str(e)
            }

    def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Stream response text from Gemini.
        """

        full_prompt = self._build_prompt(
            prompt=prompt,
            system_prompt=system_prompt
        )

        try:
            response = self.model.generate_content(
                full_prompt,
                stream=True
            )

            for chunk in response:
                text = self._extract_text(chunk)
                if text:
                    yield text

        except Exception as e:
            yield f"Gemini API stream error: {str(e)}"

    def _build_prompt(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Build prompt for Gemini.

        In this lab, we prepend system instructions manually.
        """

        if system_prompt:
            return f"""System:
{system_prompt}

User:
{prompt}
"""

        return prompt

    def _extract_text(self, response: Any) -> str:
        """
        Safely extract text from Gemini response.
        """

        try:
            text = getattr(response, "text", "")
            if text:
                return text
        except Exception:
            pass

        try:
            candidates = getattr(response, "candidates", [])
            if not candidates:
                return ""

            parts = candidates[0].content.parts
            texts = []

            for part in parts:
                part_text = getattr(part, "text", "")
                if part_text:
                    texts.append(part_text)

            return "\n".join(texts).strip()

        except Exception:
            return ""

    def _extract_usage(self, response: Any) -> Dict[str, int]:
        """
        Safely extract token usage from Gemini response.
        """

        usage_metadata = getattr(response, "usage_metadata", None)

        if usage_metadata is None:
            return {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }

        return {
            "prompt_tokens": getattr(
                usage_metadata,
                "prompt_token_count",
                0
            ),
            "completion_tokens": getattr(
                usage_metadata,
                "candidates_token_count",
                0
            ),
            "total_tokens": getattr(
                usage_metadata,
                "total_token_count",
                0
            )
        }