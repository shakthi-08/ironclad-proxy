# Ironclad Proxy

Ironclad Proxy is a pre-execution transaction gate for a zero-trust hot-wallet
security boundary. It rejects EIP-7702 set-code delegation transactions,
validates method signatures against [`config/rules.json`](config/rules.json),
tracks rolling USD outflow, and permanently isolates the process after an
emergency freeze.

## Usage

```python
from ironclad_proxy import IroncladProxy, Transaction, configure_logging, load_config

configure_logging()
proxy = IroncladProxy(load_config("config/rules.json"))

decision = proxy.inspect(
    Transaction(data="0xa9059cbb" + "00" * 32, value_usd="2500")
)
print(decision.value)  # accept
```

`Decision.REJECT` freezes the proxy when malformed or malicious bytes,
unknown method signatures, invalid values, or a velocity limit breach are
detected. Every later transaction returns `Decision.DROPPED` until the process
is restarted or an external operator replaces the proxy instance.

Run the tests with:

```text
python -m pytest
```
