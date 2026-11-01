"""Pre-execution transaction security enforcement."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from threading import RLock
from typing import Any, Callable, Mapping

from .rules import ProxyConfig, normalize_transaction_type

LOGGER = logging.getLogger("ironclad_proxy")


class AdvancedCalldataInspector:
    """Detect EIP-7702 authorization injection and high-risk selectors."""

    AUTHORIZATION_PREFIX = "0xef0100"
    HIGH_RISK_SELECTORS = frozenset({"0xd505accf", "0xa22cb465"})

    def scan(self, data: str) -> tuple[str, ...]:
        """Return the matching risk indicators in transaction calldata."""
        normalized = self._normalize(data)
        findings: list[str] = []
        if self.AUTHORIZATION_PREFIX in normalized:
            findings.append(self.AUTHORIZATION_PREFIX)
        selector = normalized[:10]
        if selector in self.HIGH_RISK_SELECTORS:
            findings.append(selector)
        return tuple(findings)

    def inspect(self, data: str) -> tuple[str, ...]:
        """Alias for callers that use inspection terminology."""
        return self.scan(data)

    def is_high_risk(self, data: str) -> bool:
        """Return whether calldata contains a configured risk indicator."""
        return bool(self.scan(data))

    @staticmethod
    def _normalize(data: str) -> str:
        if not isinstance(data, str) or not data.startswith("0x"):
            raise ValueError("transaction data must be a hexadecimal 0x-prefixed string")
        normalized = data.lower()
        if len(normalized) % 2 != 0:
            raise ValueError("transaction data must contain complete bytes")
        try:
            int(normalized[2:] or "0", 16)
        except ValueError as exc:
            raise ValueError("transaction data must be hexadecimal") from exc
        return normalized


class SecureTelemetryBridge:
    """Serialize telemetry and authenticate it with an HMAC-SHA256 signature."""

    def __init__(self, secret: str | bytes | None = None) -> None:
        configured_secret = secret if secret is not None else os.environ.get("IRONCLAD_HMAC_SECRET")
        if configured_secret is None or configured_secret == "":
            raise ValueError("IRONCLAD_HMAC_SECRET must be configured")
        self._secret = (
            configured_secret.encode("utf-8")
            if isinstance(configured_secret, str)
            else configured_secret
        )
        if not self._secret:
            raise ValueError("IRONCLAD_HMAC_SECRET must not be empty")

    def serialize(self, payload: Mapping[str, Any] | str | bytes) -> bytes:
        """Return the canonical wire representation used for signing."""
        if isinstance(payload, bytes):
            return payload
        if isinstance(payload, str):
            return payload.encode("utf-8")
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def sign(self, payload: Mapping[str, Any] | str | bytes) -> str:
        """Return the lowercase hexadecimal HMAC-SHA256 signature."""
        return hmac.new(self._secret, self.serialize(payload), hashlib.sha256).hexdigest()

    def sign_payload(self, payload: Mapping[str, Any] | str | bytes) -> str:
        """Return the signature for an outbound telemetry payload."""
        return self.sign(payload)


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
        calldata_inspector: AdvancedCalldataInspector | None = None,
    ) -> None:
        self.config = config
        self._clock = clock
        self._calldata_inspector = calldata_inspector or AdvancedCalldataInspector()
        self._outflows: deque[tuple[float, Decimal]] = deque()
        self._lock = RLock()
        self.is_frozen = False

    def inspect(self, transaction: Transaction) -> Decision:
        """Inspect one transaction and return the enforcement decision."""
        with self._lock:
            if self.is_frozen:
                LOGGER.warning("transaction dropped: emergency freeze is active")
                return Decision.DROPPED

            try:
                tx_type = normalize_transaction_type(transaction.tx_type)
            except ValueError as exc:
                return self._freeze("malformed transaction type", exc)
            if tx_type in self.config.blocked_transaction_types:
                return self._freeze(f"blocked transaction type {tx_type}")

            try:
                findings = self._calldata_inspector.scan(transaction.data)
            except ValueError as exc:
                return self._freeze("malformed transaction data", exc)
            if findings:
                return self._freeze(f"high-risk calldata detected: {', '.join(findings)}")

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
