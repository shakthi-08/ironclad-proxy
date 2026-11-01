"""Configuration loading and validation for Ironclad Proxy."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VelocityConfig:
    limit_usd: Decimal = Decimal("1000000")
    window_seconds: float = 60.0


@dataclass(frozen=True)
class ProxyConfig:
    allowed_method_signatures: frozenset[str]
    velocity: VelocityConfig = VelocityConfig()
    blocked_transaction_types: frozenset[str] = frozenset({"0x4"})


def _signature(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("method signatures must be strings")
    normalized = value.lower()
    if not (normalized.startswith("0x") and len(normalized) == 10):
        raise ValueError(f"invalid method signature: {value!r}")
    try:
        int(normalized[2:], 16)
    except ValueError as exc:
        raise ValueError(f"invalid method signature: {value!r}") from exc
    return normalized


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be a number") from exc
    if not result.is_finite() or result < 0:
        raise ValueError(f"{field} must be finite and non-negative")
    return result


def normalize_transaction_type(value: Any) -> str:
    """Normalize numeric and hexadecimal transaction types to canonical hex."""
    if isinstance(value, bool):
        raise ValueError("transaction types must be integers or strings")
    try:
        if isinstance(value, int):
            number = value
        elif isinstance(value, str):
            text = value.strip().lower()
            if not text:
                raise ValueError("transaction type cannot be empty")
            number = int(text, 16 if text.startswith("0x") else 10)
        else:
            raise ValueError("transaction types must be integers or strings")
    except ValueError as exc:
        raise ValueError(f"invalid transaction type: {value!r}") from exc
    if number < 0:
        raise ValueError("transaction type cannot be negative")
    return f"0x{number:x}"


def load_config(path: str | Path) -> ProxyConfig:
    """Load and validate the JSON security rules file."""
    config_path = Path(path)
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"unable to load rules from {config_path}") from exc

    signatures = raw.get("allowed_method_signatures")
    if not isinstance(signatures, list) or not signatures:
        raise ValueError("allowed_method_signatures must be a non-empty list")
    velocity = raw.get("velocity", {})
    if not isinstance(velocity, dict):
        raise ValueError("velocity must be an object")
    blocked_types = raw.get("blocked_transaction_types")
    if not isinstance(blocked_types, list) or not blocked_types:
        raise ValueError("blocked_transaction_types must be a non-empty list")
    limit = _decimal(velocity.get("limit_usd", "1000000"), "limit_usd")
    window = float(velocity.get("window_seconds", 60))
    if window <= 0:
        raise ValueError("window_seconds must be greater than zero")

    return ProxyConfig(
        allowed_method_signatures=frozenset(_signature(item) for item in signatures),
        velocity=VelocityConfig(limit_usd=limit, window_seconds=window),
        blocked_transaction_types=frozenset(
            normalize_transaction_type(item) for item in blocked_types
        ),
    )
