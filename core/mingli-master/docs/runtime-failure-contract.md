# Runtime Stopped Failure Contract

`Stopped(reason="error")` carries a bounded `failure` object.  It is intended
for host routing and audit logs; `public_copy` remains the only user-facing
text.

```json
{
  "kind": "stopped",
  "reason": "error",
  "public_copy": "本次处理未完成，请稍后重试。",
  "state_token": null,
  "input_request": null,
  "failure": {
    "schema_version": "mingli-runtime-failure/v1",
    "code": "runtime.internal_error",
    "category": "runtime_internal",
    "retryable": false
  },
  "continuation_allowed": false,
  "terminal": true,
  "completion_committed": false
}
```

The object is closed over static values.  It never carries exception text,
paths, command values, state tokens, subject identifiers or caller metadata.
Diagnostics may still be written to the Runtime process's private stderr, but
they are not part of the portable Result.

## Categories and codes

| Category | Code | Retryable | Meaning |
|---|---|---:|---|
| `bootstrap` | `bootstrap.unexpected_arguments` | no | The fixed launcher surface was invoked with arguments. |
| `bootstrap` | `bootstrap.guard_load_failed` | no | The signed Runtime guard could not be loaded. |
| `bootstrap` | `bootstrap.runtime_lock_failed` | no | The release lock could not be acquired for a non-transient reason. |
| `bootstrap` | `bootstrap.runtime_identity_invalid` | no | Runtime identity or dependency admission failed. |
| `bootstrap` | `bootstrap.state_root_invalid` | no | The configured private state root is invalid. |
| `input_contract` | `input_contract.malformed_json` | no | stdin is not a JSON document. |
| `input_contract` | `input_contract.invalid_command` | no | JSON does not satisfy the Command union. |
| `input_contract` | `input_contract.invalid_payload` | no | A typed command contains invalid values or state transition data. |
| `input_contract` | `input_contract.invalid_state_token` | no | The supplied opaque token is not valid in this Runtime instance. |
| `runtime_internal` | `runtime.internal_error` | no | A deterministic Runtime/provider/store invariant failed. |
| `transient` | `transient.timeout` | yes | A bounded Runtime operation timed out. |
| `transient` | `transient.resource_unavailable` | yes | A temporary process/file/resource limit prevented execution. |

`retryable=true` is telemetry, not permission for blind replay.  The existing
no-token Prepare rule still applies: when transport or completion is uncertain,
the host must not replay automatically.

## Compatibility

The portable interface remains `mingli-portable-interface-v2`; this field is a
versioned additive diagnostic on `Stopped`.  Strict host validators must add
the `failure` object to their Result schema and decoder before admitting a
release that emits it.  `failure` is `null` for non-error `Stopped` variants.
Legacy error Results without `failure` deserialize as
`runtime.internal_error`, but every Result emitted by this Runtime includes the
field.
