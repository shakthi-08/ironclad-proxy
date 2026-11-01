from decimal import Decimal

from ironclad_proxy.daemon import (
    AdvancedCalldataInspector,
    Decision,
    IroncladProxy,
    SecureTelemetryBridge,
    Transaction,
)
from ironclad_proxy.rules import ProxyConfig, VelocityConfig, load_config


def make_proxy(clock=lambda: 0.0, limit="1000000", window=60):
    return IroncladProxy(
        ProxyConfig(
            allowed_method_signatures=frozenset({"0xa9059cbb"}),
            velocity=VelocityConfig(Decimal(limit), window),
        ),
        clock=clock,
    )


def test_accepts_allowed_method():
    assert make_proxy().inspect(Transaction("0xa9059cbb" + "00" * 32)) is Decision.ACCEPT


def test_rejects_delegation_and_drops_following_transactions():
    proxy = make_proxy()
    assert proxy.inspect(Transaction("0xa9059cbb", tx_type=4)) is Decision.REJECT
    assert proxy.is_frozen
    assert proxy.inspect(Transaction("0xa9059cbb")) is Decision.DROPPED


def test_rejects_padded_and_unpadded_delegation_types():
    for tx_type in ("0x04", "0x4", 4):
        proxy = make_proxy()
        assert proxy.inspect(Transaction("0xa9059cbb", tx_type=tx_type)) is Decision.REJECT
        assert proxy.is_frozen


def test_loads_and_enforces_configured_blocked_types():
    config = load_config("config/rules.json")
    assert config.blocked_transaction_types == frozenset({"0x4"})
    proxy = IroncladProxy(config)
    assert proxy.inspect(Transaction("0xa9059cbb", tx_type="0x04")) is Decision.REJECT


def test_rejects_unknown_method_and_freezes():
    proxy = make_proxy()
    assert proxy.inspect(Transaction("0xdeadbeef")) is Decision.REJECT
    assert proxy.is_frozen


def test_velocity_uses_rolling_window():
    now = [0.0]
    proxy = make_proxy(lambda: now[0], limit="100", window=60)
    assert proxy.inspect(Transaction("0xa9059cbb", "60")) is Decision.ACCEPT
    assert proxy.inspect(Transaction("0xa9059cbb", "40")) is Decision.ACCEPT
    now[0] = 1
    assert proxy.inspect(Transaction("0xa9059cbb", "1")) is Decision.REJECT
    assert proxy.is_frozen


def test_expired_outflow_is_removed():
    now = [0.0]
    proxy = make_proxy(lambda: now[0], limit="100", window=60)
    assert proxy.inspect(Transaction("0xa9059cbb", "100")) is Decision.ACCEPT
    now[0] = 61
    assert proxy.inspect(Transaction("0xa9059cbb", "1")) is Decision.ACCEPT


def test_advanced_inspector_detects_authorization_and_high_risk_selectors():
    inspector = AdvancedCalldataInspector()
    assert inspector.scan("0xa9059cbb" + "00" * 4 + "ef0100" + "00" * 8) == (
        "0xef0100",
    )
    assert inspector.inspect("0xd505accf" + "00" * 32) == ("0xd505accf",)
    assert inspector.scan("0xa22cb465" + "00" * 32) == ("0xa22cb465",)


def test_proxy_rejects_high_risk_calldata_even_when_selector_is_allowed():
    proxy = make_proxy()
    transaction = Transaction("0xa9059cbb" + "00" * 4 + "ef0100" + "00" * 8)
    assert proxy.inspect(transaction) is Decision.REJECT
    assert proxy.is_frozen


def test_secure_telemetry_bridge_signs_canonical_payload():
    bridge = SecureTelemetryBridge("test-secret")
    payload = {"isFrozen": False, "source": "python-daemon"}
    assert bridge.sign(payload) == bridge.sign_payload(payload)
    assert len(bridge.sign(payload)) == 64
