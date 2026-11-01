"""Enterprise pre-execution transaction security daemon."""

from __future__ import annotations

import json
import logging
import time
from collections import deque
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from threading import RLock
from typing import Any, Callable

LOGGER = logging.getLogger("ironclad_proxy")


class Decision(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DROPPED = "dropped"


@dataclass(frozen=True)
class Transaction:
    """Fields required before a transaction may be executed."""

    data: str
    value_usd: Decimal | int | float | str = Decimal("0")
    tx_type: int | str = 0


@dataclass(frozen=True)
class ProxyEvent:
    id: str
    timestamp: str
    status: str
    detail: str
    amountUsd: float


@dataclass(frozen=True)
class ProxyRules:
    allowed_method_signatures: frozenset[str]
    blocked_transaction_types: frozenset[str]
    max_outflow_usd: Decimal
    window_seconds: float


def load_rules(path: str | Path) -> ProxyRules:
    """Load and validate security rules from JSON."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        velocity = raw["velocity"]
        allowed = frozenset(_method_signature(item) for item in raw["allowed_method_signatures"])
        blocked = frozenset(_transaction_type(item) for item in raw["blocked_transaction_types"])
        limit = Decimal(str(velocity["limit_usd"]))
        window = float(velocity["window_seconds"])
    except (OSError, KeyError, TypeError, ValueError, InvalidOperation, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid Ironclad rules file: {path}") from exc
    if not allowed or not blocked or not limit.is_finite() or limit < 0 or window <= 0:
        raise ValueError("rules must define valid allowed methods, blocked types, limit, and window")
    return ProxyRules(allowed, blocked, limit, window)


class IroncladProxy:
    """Thread-safe gate with permanent emergency-freeze behavior."""

    def __init__(
        self,
        rules: ProxyRules,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.rules = rules
        self._clock = clock
        self._outflows: deque[tuple[float, Decimal]] = deque()
        self._events: deque[ProxyEvent] = deque(maxlen=100)
        self._lock = RLock()
        self.is_frozen = False

    def inspect(self, transaction: Transaction | dict[str, Any]) -> Decision:
        """Parse and inspect a transaction before execution."""
        tx = _coerce_transaction(transaction)
        with self._lock:
            if self.is_frozen:
                self._record("tripped", "Circuit breaker locked; transaction dropped", 0)
                LOGGER.warning("DROP | circuit breaker locked; transaction rejected")
                return Decision.DROPPED

            tx_type = _transaction_type(tx.tx_type)
            if tx_type in self.rules.blocked_transaction_types:
                return self._freeze(
                    f"BLOCK | unauthorized transaction type {tx_type} "
                    "(EIP-7702 set-code delegation)"
                )

            signature = _method_signature(tx.data)
            if signature not in self.rules.allowed_method_signatures:
                return self._freeze(f"BLOCK | unauthorized method signature {signature!r}")

            try:
                amount = Decimal(str(tx.value_usd))
            except (InvalidOperation, ValueError) as exc:
                return self._freeze("BLOCK | invalid USD outflow", exc)
            if not amount.is_finite() or amount < 0:
                return self._freeze("BLOCK | invalid USD outflow")

            now = self._clock()
            self._prune(now)
            current = sum(value for _, value in self._outflows)
            if current + amount > self.rules.max_outflow_usd:
                return self._freeze(
                    f"FREEZE | rolling outflow {current + amount} exceeds "
                    f"${self.rules.max_outflow_usd} limit"
                )
            self._outflows.append((now, amount))
            self._record("accepted", f"ERC-20 transfer · {signature}", amount)
            LOGGER.info("ALLOW | method=%s amount_usd=%s", signature, amount)
            return Decision.ACCEPTED

    def lockdown(self) -> None:
        """Trip the global freeze from an operator control or API adapter."""
        with self._lock:
            if not self.is_frozen:
                self._freeze("MANUAL | operator emergency lockdown")

    def telemetry_snapshot(self) -> dict[str, object]:
        """Return the JSON-shaped state expected by the SOC dashboard adapter."""
        with self._lock:
            now = self._clock()
            self._prune(now)
            return {
                "isFrozen": self.is_frozen,
                "rollingOutflowUsd": float(sum(value for _, value in self._outflows)),
                "velocityLimitUsd": float(self.rules.max_outflow_usd),
                "windowSeconds": self.rules.window_seconds,
                "events": [event.__dict__ for event in self._events],
                "source": "python-daemon",
            }

    def _freeze(self, message: str, error: Exception | None = None) -> Decision:
        self.is_frozen = True
        self._record("blocked" if "BLOCK" in message else "tripped", message, 0)
        LOGGER.error("EMERGENCY FREEZE | %s%s", message, f": {error}" if error else "")
        return Decision.REJECTED

    def _record(self, status: str, detail: str, amount: Decimal | int | float) -> None:
        self._events.append(
            ProxyEvent(
                id=f"evt-{time.time_ns()}",
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                status=status,
                detail=detail,
                amountUsd=float(amount),
            )
        )

    def _prune(self, now: float) -> None:
        cutoff = now - self.rules.window_seconds
        while self._outflows and self._outflows[0][0] <= cutoff:
            self._outflows.popleft()


def configure_logging() -> None:
    """Configure readable simulation and daemon logs."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _coerce_transaction(transaction: Transaction | dict[str, Any]) -> Transaction:
    if isinstance(transaction, Transaction):
        return transaction
    try:
        return Transaction(
            data=str(transaction["data"]),
            value_usd=transaction.get("value_usd", Decimal("0")),
            tx_type=transaction.get("tx_type", 0),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError("transaction must provide data and value_usd") from exc


def _method_signature(data: object) -> str | None:
    if not isinstance(data, str) or not data.startswith("0x") or len(data) < 10:
        return None
    signature = data[:10].lower()
    try:
        int(signature[2:], 16)
    except ValueError:
        return None
    return signature


def _transaction_type(value: object) -> str:
    if isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return f"0x{value:x}" if value >= 0 else ""
    if isinstance(value, str):
        normalized = value.lower()
        try:
            number = int(normalized, 16 if normalized.startswith("0x") else 10)
        except ValueError:
            return ""
        return f"0x{number:x}" if number >= 0 else ""
    return ""
