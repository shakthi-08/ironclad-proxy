"""Three-case attack simulation for the Ironclad Proxy circuit breaker."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.proxy import Decision, IroncladProxy, Transaction, configure_logging, load_rules


def main() -> None:
    configure_logging()
    rules = load_rules(Path(__file__).parents[1] / "config" / "rules.json")
    proxy = IroncladProxy(rules)

    print("\n[1/3] Clean legitimate withdrawal")
    result = proxy.inspect(Transaction("0xa9059cbb" + "00" * 32, "100000"))
    assert result is Decision.ACCEPTED
    print(f"RESULT: {result.value}")

    print("\n[2/3] EIP-7702 sweeper attack")
    result = proxy.inspect(
        Transaction("0xa9059cbb" + "ff" * 32, "5000000", tx_type="0x04")
    )
    assert result is Decision.REJECTED and proxy.is_frozen
    print(f"RESULT: {result.value}; emergency freeze={proxy.is_frozen}")

    print("\n[3/3] Follow-up withdrawal while locked")
    result = proxy.inspect(Transaction("0xa9059cbb" + "00" * 32, "100000"))
    assert result is Decision.DROPPED
    print(f"RESULT: {result.value}; transaction isolated")
    print("\nATTACK SIMULATION PASSED: malicious payload intercepted cleanly.")


if __name__ == "__main__":
    main()
