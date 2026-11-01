"""Pre-execution transaction security enforcement."""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from threading import RLock
from typing import Callable

from .rules import ProxyConfig

LOGGER = logging.getLogger("ironclad_proxy")


def configure_logging(level: int = logging.INFO) -> None:
    """Configure concise terminal output for simulations and local operation."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )


class Decision(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    DROPPED = "dropped"


@dataclass(frozen=True)
class Transaction:
    """The security-relevant fields of an incoming transaction."""

    data: str
    value_usd: Decimal | int | float | str = Decimal("0")
    tx_type: int | str = 0


class IroncladProxy:
    """Thread-safe pre-execution gate with emergency freeze semantics."""

    def __init__(
        self,
        config: ProxyConfig,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config
        self._clock = clock
        self._outflows: deque[tuple[float, Decimal]] = deque()
        self._lock = RLock()
        self.is_frozen = False

    def inspect(self, transaction: Transaction) -> Decision:
        """Inspect one transaction and return the enforcement decision."""
        with self._lock:
            if self.is_frozen:
                LOGGER.warning("transaction dropped: emergency freeze is active")
                return Decision.DROPPED

            if self._is_delegation(transaction.tx_type):
                return self._freeze("EIP-7702 set-code delegation (type 0x04)")

            signature = self._method_signature(transaction.data)
            if signature is None:
                return self._freeze("malformed transaction data")
            if signature not in self.config.allowed_method_signatures:
                return self._freeze(f"method signature {signature} is not allowed")

            try:
                value = Decimal(str(transaction.value_usd))
            except (InvalidOperation, ValueError) as exc:
                return self._freeze("transaction value is invalid", exc)
            if not value.is_finite() or value < 0:
                return self._freeze("transaction value is invalid")

            now = self._clock()
            self._prune(now)
            if sum(amount for _, amount in self._outflows) + value > self.config.velocity.limit_usd:
                return self._freeze("rolling USD outflow limit breached")

            self._outflows.append((now, value))
            LOGGER.info("transaction accepted: signature=%s value_usd=%s", signature, value)
            return Decision.ACCEPT

    def _freeze(self, reason: str, error: Exception | None = None) -> Decision:
        self.is_frozen = True
        if error is None:
            LOGGER.error("EMERGENCY FREEZE: %s", reason)
        else:
            LOGGER.error("EMERGENCY FREEZE: %s: %s", reason, error)
        return Decision.REJECT

    def _prune(self, now: float) -> None:
        cutoff = now - self.config.velocity.window_seconds
        while self._outflows and self._outflows[0][0] <= cutoff:
            self._outflows.popleft()

    @staticmethod
    def _is_delegation(tx_type: int | str) -> bool:
        if isinstance(tx_type, int):
            return tx_type == 4
        return isinstance(tx_type, str) and tx_type.lower().removeprefix("0x") == "04"

    @staticmethod
    def _method_signature(data: str) -> str | None:
        if not isinstance(data, str):
            return None
        normalized = data.lower()
        if not normalized.startswith("0x") or len(normalized) < 10:
            return None
        signature = normalized[:10]
        try:
            int(signature[2:], 16)
        except ValueError:
            return None
        return signature
