from decimal import Decimal

from ironclad_proxy.daemon import Decision, IroncladProxy, Transaction
from ironclad_proxy.rules import ProxyConfig, VelocityConfig


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
