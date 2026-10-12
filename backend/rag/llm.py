"""Fournisseurs LLM : API compatible OpenAI (DeepSeek en V0) et repli sur un second fournisseur."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

import httpx

from backend.rag.interfaces import LLMProvider, LLMUnavailableError
from backend.rag.types import LLMCompletion

logger = logging.getLogger(__name__)


class OpenAICompatibleLLM:
    """Client `POST /chat/completions` en mode JSON.

    `extra_body` porte les paramètres propres au fournisseur. Pour DeepSeek :
    `{"thinking": {"type": "disabled"}}`, car le mode réflexion est actif par défaut.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_s: float = 60.0,
        temperature: float = 0.0,
        max_tokens: int = 1500,
        extra_body: Mapping[str, Any] | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.name = model
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._extra_body = dict(extra_body or {})
        self._client = client or httpx.Client(
            base_url=base_url,
            timeout=timeout_s,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    def complete_json(self, system: str, user: str) -> LLMCompletion:
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            **self._extra_body,
        }
        try:
            response = self._client.post("chat/completions", json=body)
        except httpx.HTTPError as error:
            raise LLMUnavailableError(f"{self.name} : {error!r}") from error
        if response.status_code >= 400:
            raise LLMUnavailableError(f"{self.name} : HTTP {response.status_code} {response.text[:300]}")

        try:
            payload = response.json()
            choice = payload["choices"][0]
            text = choice["message"]["content"] or ""
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise LLMUnavailableError(f"{self.name} : réponse au format inattendu") from error
        if choice.get("finish_reason") == "length":
            raise LLMUnavailableError(f"{self.name} : réponse tronquée (max_tokens atteint)")

        usage = payload.get("usage") or {}
        return LLMCompletion(
            text=text,
            model=payload.get("model") or self._model,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )

    def close(self) -> None:
        self._client.close()


class FallbackLLM:
    """Essaie chaque fournisseur dans l'ordre jusqu'au premier qui répond."""

    def __init__(self, providers: Sequence[LLMProvider]) -> None:
        if not providers:
            raise ValueError("au moins un fournisseur LLM est requis")
        self._providers = list(providers)

    def complete_json(self, system: str, user: str) -> LLMCompletion:
        errors: list[str] = []
        for provider in self._providers:
            try:
                return provider.complete_json(system, user)
            except LLMUnavailableError as error:
                logger.warning("Fournisseur LLM indisponible : %s", error)
                errors.append(str(error))
        raise LLMUnavailableError(" ; ".join(errors))

    def close(self) -> None:
        for provider in self._providers:
            close = getattr(provider, "close", None)
            if close is not None:
                close()
