# Email OTP Delivery Runbook

Status: **staging-capable, production fail-closed.** The backend can send real
email verification codes over TLS, but production stays blocked until a durable
challenge store (Redis or Postgres-backed) replaces the in-memory OTP stores.

## 1. Prerequisites outside this repository

Email delivery is only as trustworthy as the sending domain. Before enabling
`otp_adapter=smtp` anywhere reachable by real users:

- A dedicated sender domain (e.g. `mail.example.com`) with an `MX` record.
- SPF record authorizing the SMTP provider for that domain.
- DKIM signing configured at the provider for the sender domain.
- A DMARC policy (`p=none` first, then tighten).
- Sender address that users can reply to or ignore safely
  (e.g. `no-reply@mail.example.com`).

No credentials belong in Git. Inject `MINGLI_SMTP_USERNAME` and
`MINGLI_SMTP_PASSWORD` as environment secrets at deploy time.

## 2. Configuration

```bash
MINGLI_ENVIRONMENT=staging
MINGLI_OTP_ADAPTER=smtp
MINGLI_SMTP_HOST=smtp.example.com
MINGLI_SMTP_PORT=587            # 465 with ssl, 587 with starttls
MINGLI_SMTP_SECURITY=starttls   # starttls | ssl; plaintext is never a mode
MINGLI_SMTP_SENDER=no-reply@mail.example.com
MINGLI_SMTP_USERNAME=<injected secret>
MINGLI_SMTP_PASSWORD=<injected secret>
```

The app refuses to start with `otp_adapter=smtp` unless host, username,
password and sender are all present. If the SMTP server does not advertise
STARTTLS, delivery fails closed; the adapter never downgrades to plaintext.

## 3. Behavior matrix

| Adapter | Local/test | Staging | Production |
| --- | --- | --- | --- |
| `fake` | Records deliveries; code is `MINGLI_FAKE_OTP_CODE`, echoed only in local/test | Echo suppressed | Rejected at startup |
| `disabled` | Fails closed | Fails closed | Fails closed |
| `smtp` | Real SMTP attempted (unit tests inject a fake client) | Real TLS SMTP | Rejected at startup until a durable challenge store exists |

Every adapter in production fails closed because OTP challenge and rate-limit
state is still in memory; a second instance or a restart cannot be trusted with
it. `MINGLI_OTP_ADAPTER=smtp` in `production` is rejected with the
"durable challenge store" error until Redis/DB-backed stores land.

## 4. Verification

Unit tests use an injected in-memory SMTP client factory, so no test touches
the network:

```bash
uv run --project backend pytest backend/tests/test_smtp_otp_adapter.py -q
```

For a staging smoke test, send to an address you control with a real sender
domain configured. Check the email header for `Received` TLS cipher and DKIM
signature, then verify the six-digit code round-trips through
`POST /api/v1/auth/otp/request` + `POST /api/v1/auth/otp/verify`.

## 5. Rollback

- Switch `MINGLI_OTP_ADAPTER` back to `fake` (local/test) or `disabled`, restart
  the API, and confirm `POST /api/v1/auth/otp/request` returns 503 with
  `OTP delivery unavailable`.
- Rotate SMTP credentials if they were ever printed in logs (they should never
  be: configuration is `SecretStr` and SMTP errors surface only a generic
  message).

## 6. Still required before production email

- Durable challenge store (Redis or Postgres) for challenges and rate limits.
- Sender domain, SPF/DKIM/DMARC verified.
- SMTP credentials injected through a secret manager.
