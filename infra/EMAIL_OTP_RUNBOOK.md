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

## 7. Abuse protection and single-process limits

All OTP and guest-session abuse limits are enforced with in-process memory
state; there is no persistent fake and no distributed counter:

- Destination rolling window: `MINGLI_OTP_DESTINATION_WINDOW_LIMIT` (default 5)
  requests per `MINGLI_OTP_RATE_WINDOW_SECONDS` (default 600s) per normalized
  destination, shared across guest sessions. The key is the HMAC of
  `channel + normalized destination` (`identity_hash_key`), so raw email
  addresses and phone numbers are never stored by the limiter.
- Per-guest and per-network OTP windows: `MINGLI_OTP_GUEST_WINDOW_LIMIT`
  (default 5) and `MINGLI_OTP_NETWORK_WINDOW_LIMIT` (default 30).
- Guest-session creation window: `MINGLI_GUEST_SESSION_CREATE_RATE_LIMIT`
  (default 10) per client IP per
  `MINGLI_GUEST_SESSION_CREATE_RATE_WINDOW_SECONDS` (default 600s). The client
  IP resolves through the trusted proxy chain configured by
  `MINGLI_TRUSTED_PROXY_CIDRS`; the 429 response carries `Retry-After`.

Delivery-failure semantics: when SMTP delivery raises
`OtpDeliveryUnavailable`, the just-issued challenge is deleted, its own
cooldown claim is released, and the guest and destination windows that attempt
consumed are rolled back so a retry succeeds immediately; the network window is
kept so a provider outage cannot be used to hammer retries past the per-IP
limit.

Single-process constraint: challenge, cooldown, and all rolling-window state
live in the API process (`max_keys` caps each window table at 20,000 entries).
Run a single API instance for these endpoints; a second instance, a restart, or
a blue/green deploy resets or splits the state. Production keeps
`otp_adapter` fail-closed until a durable Redis/Postgres-backed store replaces
the in-memory ports, and the same durable store is required before any
multi-instance deployment can enforce these limits safely.
