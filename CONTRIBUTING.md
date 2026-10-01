# Contributing

Thanks for helping improve a Thai commerce integration.

Set up Python 3.11 or newer, install the development extras, and run the same checks as CI:

```sh
python -m pip install -e ".[dev]"
ruff check .
pytest -q
```

Keep pricing deterministic and inside the application code. New LLM behavior must be validated against the configured menu and must never choose a price. Add a regression test for webhook, cart, payment-payload, or parser changes. Do not include `.env` files, channel credentials, customer identifiers, or real order payloads in issues or pull requests.

For security issues, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.
