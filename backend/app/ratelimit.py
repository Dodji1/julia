"""Limitation de débit en mémoire (un seul processus API en V0).

Au congrès, des centaines de personnes partagent l'IP publique du Wi-Fi de la salle : la limite
fine porte donc sur l'identifiant anonyme du navigateur (en-tête `X-Client-Id`), et la limite par
IP reste large, pour contenir un abus sans bloquer toute la salle. Un budget global par jour borne
le coût LLM.
"""

from __future__ import annotations

import math
import re
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

_CLIENT_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")
_SWEEP_EVERY = 1000


class RateLimited(Exception):
    def __init__(self, code: str, message: str, retry_after_s: float) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retry_after_s = max(1, math.ceil(retry_after_s))


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_s: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._limit = limit
        self._window = window_s
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._calls = 0

    def hit(self, key: str) -> float | None:
        """Enregistre une requête. Renvoie le délai d'attente (s) si la limite est atteinte."""
        with self._lock:
            now = self._clock()
            self._calls += 1
            if self._calls % _SWEEP_EVERY == 0:
                self._sweep(now)
            hits = self._hits[key]
            while hits and hits[0] <= now - self._window:
                hits.popleft()
            if len(hits) >= self._limit:
                return hits[0] + self._window - now
            hits.append(now)
            return None

    def _sweep(self, now: float) -> None:
        stale = [key for key, hits in self._hits.items() if not hits or hits[-1] <= now - self._window]
        for key in stale:
            del self._hits[key]


class DailyBudget:
    def __init__(self, limit: int, now: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self._limit = limit
        self._now = now
        self._day = now().date()
        self._used = 0
        self._lock = threading.Lock()

    def consume(self) -> float | None:
        """Consomme une unité. Renvoie le délai jusqu'à minuit UTC si le budget est épuisé."""
        with self._lock:
            now = self._now()
            if now.date() != self._day:
                self._day, self._used = now.date(), 0
            if self._used >= self._limit:
                midnight = datetime.combine(self._day + timedelta(days=1), datetime.min.time(), UTC)
                return (midnight - now).total_seconds()
            self._used += 1
            return None


class AnswerRateLimits:
    def __init__(self, client_per_minute: int, client_per_day: int, ip_per_minute: int, daily_budget: int):
        self._client_minute = SlidingWindowLimiter(client_per_minute, 60)
        self._client_day = SlidingWindowLimiter(client_per_day, 86_400)
        self._ip_minute = SlidingWindowLimiter(ip_per_minute, 60)
        self._budget = DailyBudget(daily_budget)

    def check_ip(self, ip: str) -> None:
        if (wait := self._ip_minute.hit(ip)) is not None:
            raise RateLimited("RATE_LIMITED", "Trop de requêtes depuis ce réseau. Réessayez dans un instant.", wait)

    def check_answer(self, client_id: str | None, ip: str) -> None:
        self.check_ip(ip)
        key = f"client:{client_id}" if client_id and _CLIENT_ID.match(client_id) else f"ip:{ip}"
        for limiter in (self._client_minute, self._client_day):
            if (wait := limiter.hit(key)) is not None:
                raise RateLimited(
                    "RATE_LIMITED",
                    f"Vous avez posé beaucoup de questions. Réessayez dans {math.ceil(wait)} s.",
                    wait,
                )
        if (wait := self._budget.consume()) is not None:
            raise RateLimited(
                "DAILY_QUOTA_EXCEEDED",
                "Julia a atteint son nombre maximal de questions pour aujourd'hui. Revenez demain.",
                wait,
            )
