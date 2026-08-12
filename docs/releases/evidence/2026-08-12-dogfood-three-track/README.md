# Dogfood three-track acceptance (2026-08-12)

- Release current: `0586730` (`0586730052fc2c178b5e6725f37340274c830f8f`)
- Account: operator email (masked in summary as `1***@qq.com`)
- Grants: `today,week,liuyao` via `scripts/dogfood_grant.py`
- Env: `smtp` + `one-shot` + `deepseek` + dogfood entitlement gates on
- Result: **today / week / liuyao all `accepted`** (API+Worker path)
- Negative: ungranted user `POST /readings/today` → `403 Paid reading not granted`
- Artifacts: sanitized only (`*-safe.json`, `summary.json`, `console.log`); no tokens/secrets

This is internal dogfood evidence, not Production Ready.
