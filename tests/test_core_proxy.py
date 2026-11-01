from decimal import Decimal

from core.proxy import Decision, IroncladProxy, Transaction, load_rules


def test_telemetry_uses_dashboard_camel_case_event_amount():
    proxy = IroncladProxy(load_rules("config/rules.json"))
    proxy.inspect(Transaction("0xa9059cbb" + "00" * 32, Decimal("100")))

    event = proxy.telemetry_snapshot()["events"][0]
    assert event["amountUsd"] == 100.0
    assert "amount_usd" not in event


def test_core_blocks_padded_and_unpadded_delegation_types():
    for tx_type in ("0x04", "0x4", 4):
        proxy = IroncladProxy(load_rules("config/rules.json"))
        assert proxy.inspect(Transaction("0xa9059cbb", "1", tx_type)) is Decision.REJECTED
