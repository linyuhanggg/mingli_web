# Conversational reading state

Conversation meaning belongs to the host model. The core receives one
opaque `state_token`, optional structured facts and an optional
transition; it validates state without ever classifying user wording.

## Turn state

| host holds | user intent | prepare call |
|---|---|---|
| no token | an independent new question | `prepare` without `state_token` |
| pending token | supplies the requested facts | `prepare` with the same token and the new facts |
| accepted token | asks a follow-up in the same reading | `prepare` with the token, no transition |
| accepted token | corrects an input used earlier | `prepare` with the token and `transition: "correct"` |
| accepted token | wants a fresh cast with kept lineage | `prepare` with the token and `transition: "restart"` |

Choose among these states from complete conversational meaning; surface
word shape is never a state rule. The core checks the token against its
stored lineage: a stale token or a rival follow-up stops with `conflict`
instead of overwriting anything.

## Continuity

The token is the only continuity handle. Do not reconstruct prior state
from chat text, temporary files or remembered facts, and do not carry a
token across unrelated questions. A follow-up recomputes horizon
extensions and re-retrieves applicable evidence for the new question; a
correction supersedes the old version while keeping it immutable; a
restart creates a child reading whose parent and root lineage stay
recorded inside the core.
