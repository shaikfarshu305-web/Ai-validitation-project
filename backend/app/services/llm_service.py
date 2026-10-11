import os
import json
import re
import asyncio
import logging
from typing import Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    Unified LLM Service — async-first with sync fallback.
    Supports: OpenAI, Google Gemini, local NLP fallback.
    Uses async httpx for non-blocking concurrent agent calls.
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.openai_key = settings.OPENAI_API_KEY
        self.gemini_key = settings.GEMINI_API_KEY
        self.temperature = settings.LLM_TEMPERATURE
        # Shared async client for connection-pooling across all agent calls
        self._async_client: Optional[httpx.AsyncClient] = None

    def is_external_available(self) -> bool:
        if self.provider == "openai" and self.openai_key:
            return True
        if self.provider == "gemini" and self.gemini_key:
            return True
        return False

    def get_async_client(self) -> httpx.AsyncClient:
        """Return a shared persistent async HTTP client (connection pooling)."""
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(timeout=25.0)
        return self._async_client

    # ── Async interface (used by parallel orchestrator) ──────────────────────

    async def query_async(
        self,
        prompt: str,
        system_prompt: str = "You are a professional AI evaluation judge.",
    ) -> str:
        """Async LLM query — non-blocking, safe for asyncio.gather."""
        if self.provider == "openai" and self.openai_key:
            try:
                return await self._call_openai_async(prompt, system_prompt)
            except Exception as e:
                logger.warning(f"OpenAI async call failed: {e}. Falling back.")

        if self.provider == "gemini" and self.gemini_key:
            try:
                return await self._call_gemini_async(prompt, system_prompt)
            except Exception as e:
                logger.warning(f"Gemini async call failed: {e}. Falling back.")

        return ""  # triggers local semantic fallback in each agent

    # ── Sync interface (backward-compat for direct calls) ────────────────────

    def query(
        self,
        prompt: str,
        system_prompt: str = "You are a professional AI evaluation judge.",
    ) -> str:
        """Sync wrapper — runs async query in current event loop if possible."""
        if self.provider == "openai" and self.openai_key:
            try:
                return self._call_openai_sync(prompt, system_prompt)
            except Exception as e:
                logger.warning(f"OpenAI sync call failed: {e}. Falling back.")

        if self.provider == "gemini" and self.gemini_key:
            try:
                return self._call_gemini_sync(prompt, system_prompt)
            except Exception as e:
                logger.warning(f"Gemini sync call failed: {e}. Falling back.")

        return ""

    # ── Async HTTP implementations ────────────────────────────────────────────

    async def _call_openai_async(self, prompt: str, system_prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt + " Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
        }
        client = self.get_async_client()
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    async def _call_gemini_async(self, prompt: str, system_prompt: str) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_MODEL}:generateContent?key={self.gemini_key}"
        )
        full_prompt = (
            f"{system_prompt}\n\nPlease respond in valid JSON format only.\n\nTask:\n{prompt}"
        )
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": self.temperature,
                "responseMimeType": "application/json",
            },
        }
        client = self.get_async_client()
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

    # ── Sync HTTP implementations (fallback) ─────────────────────────────────

    def _call_openai_sync(self, prompt: str, system_prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt + " Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
        }
        with httpx.Client(timeout=25.0) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    def _call_gemini_sync(self, prompt: str, system_prompt: str) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_MODEL}:generateContent?key={self.gemini_key}"
        )
        full_prompt = (
            f"{system_prompt}\n\nPlease respond in valid JSON format only.\n\nTask:\n{prompt}"
        )
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": self.temperature,
                "responseMimeType": "application/json",
            },
        }
        with httpx.Client(timeout=25.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


llm_service = LLMService()
