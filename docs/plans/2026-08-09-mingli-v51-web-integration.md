# Mingli-master 5.1 Web Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add the deterministic mingli-master 5.1 `describe → prepare → single-model candidate → guard → complete → Accepted` path to the existing web foundation without importing the core or adding an Agent loop.

**Architecture:** The FastAPI modular monolith owns profiles, immutable reading records and job state. A dedicated Worker runs an explicit `ReadingOrchestrator`, calls the 5.1 one-shot JSON adapter through a small port, calls one standalone model with only the Prepared brief, validates a traceable candidate, and submits the exact assembled copy to complete. The Runtime Release is always the complete, unchanged 5.1 artifact: all 13 Providers, algorithms, 55/55 ancient-book reference packs and 1328 evidence-index records are packaged and admitted together. P0 exposes only bazi, fortune and liuyao through a separate product policy; that allowlist must never slim the runtime artifact or its regression scope. The real runtime stays single-replica on a private persistent volume until its filesystem state model is deliberately replaced.

**Tech Stack:** Python 3.12 FastAPI/SQLAlchemy/asyncio for the business service, dedicated pinned Python 3.14.6 for mingli-master, PostgreSQL 16, JSON Schema, pytest, Next.js/TypeScript, a company-controlled standalone model HTTP endpoint, Docker/Alibaba Cloud ECS.

**Authority:** Read [MINGLI_V51_WEB_INTEGRATION.md](../MINGLI_V51_WEB_INTEGRATION.md), [PRODUCT_BLUEPRINT_WEB_IOS_V2.md](../PRODUCT_BLUEPRINT_WEB_IOS_V2.md), ADR 0002, ADR 0005 and ADR 0010 before implementation. If code and those contracts differ, stop and resolve the contract rather than silently inventing a third path.

---

### Task 1: Freeze the portable JSON and candidate schemas

**Files:**

- Create: `contracts/schemas/mingli-command-v2.schema.json`
- Create: `contracts/schemas/mingli-result-v2.schema.json`
- Create: `contracts/schemas/mingli-narrative-candidate-v1.schema.json`
- Create: `contracts/schemas/mingli-output-contract-v1.schema.json`
- Create: `tests/contract/test_mingli_schemas.py`
- Modify: `backend/pyproject.toml`

**Step 1: Write failing schema tests**

Cover the exact three Command kinds and four Result kinds. Add a regression proving `facts` must be `subject_ref -> object`, and candidate blocks must carry text plus subject/dimension/kind/certainty and closed reference arrays.

```python
def test_prepare_facts_are_grouped_by_subject(validate_schema):
    command = {
        "kind": "prepare",
        "query": "看一下这个八字",
        "intent": {
            "subject_refs": ["profile-version:test"],
            "object_id": "natal",
            "dimension_ids": ["overview"],
            "horizon": {"kind_id": "life", "start": None, "end": None},
            "capability_id": "bazi",
            "comparisons": [],
        },
        "facts": {
            "profile-version:test": {
                "birth_datetime_or_four_pillars": "1994-04-30T05:55:00+08:00"
            }
        },
        "state_token": None,
        "transition": None,
    }
    validate_schema("mingli-command-v2.schema.json", command)
```

Also test that `state_token` exists only in protocol DTOs and never in the narrative candidate schema.

**Step 2: Run the tests and verify RED**

Run:

```bash
uv run --project backend pytest tests/contract/test_mingli_schemas.py -q
```

Expected: FAIL because the four schemas do not exist.

**Step 3: Add JSON Schema validation support**

Add `jsonschema>=4.25,<5` to production dependencies and `referencing>=0.36,<1` only if needed by the validator. Lock with `uv sync --project backend --group dev`.

**Step 4: Implement the minimum closed schemas**

Use `oneOf` with `additionalProperties: false`. Mirror only the public 5.1 interface. Do not include internal provider, reading store, AnswerDraft or legacy command types.

Candidate block enum is initially:

```json
{
  "block_type": "claim",
  "text": "non-empty natural Chinese",
  "subject_ref": "brief-owned ref",
  "dimension_id": "brief-owned id",
  "claim_kind_id": "brief-owned id",
  "certainty_id": "brief-owned id",
  "fact_refs": [],
  "finding_refs": [],
  "evidence_refs": [],
  "limit_kind_ids": []
}
```

The schema validates shape, not whether refs exist in a particular brief; that belongs to Narrative Guard.

**Step 5: Run focused tests and all contract tests**

```bash
uv run --project backend pytest tests/contract/test_mingli_schemas.py tests/contract/test_openapi_contract.py -q
```

Expected: PASS.

**Step 6: Commit**

```bash
git add contracts/schemas backend/pyproject.toml backend/uv.lock tests/contract/test_mingli_schemas.py
git commit -m "feat: freeze mingli v51 web contracts"
```

### Task 2: Replace Phase 1 adapter placeholders with deep ports and lawful Fakes

**Files:**

- Create: `backend/app/readings/__init__.py`
- Create: `backend/app/readings/runtime_contracts.py`
- Create: `backend/app/readings/narrative_contracts.py`
- Modify: `backend/app/adapters/runtime.py`
- Modify: `backend/app/adapters/model.py`
- Modify: `backend/tests/test_fake_adapters.py`
- Create: `backend/tests/test_runtime_contracts.py`

**Step 1: Write failing tests**

Require one runtime method:

```python
class MingliRuntime(Protocol):
    async def execute(self, command: MingliCommand) -> MingliResult: ...
```

Require one model method:

```python
class NarrativeModel(Protocol):
    async def generate(self, request: NarrativeRequest) -> NarrativeCandidate: ...
```

Assert Fake Runtime describes the exact frozen 13-capability set (`bazi`, `fengshui`, `fortune`, `liuren`, `liuyao`, `luming-nayin`, `meihua`, `physiognomy`, `qimen`, `selection`, `taiyi`, `xingming`, `ziwei`), can return Prepared/Stopped/Accepted fixtures, and never sets `production_ready=True`. Assert the separate Product Capability Policy exposes exactly `("bazi", "fortune", "liuyao")` in P0 and rejects direct business requests for the other ten. Assert Fake Model returns traceable blocks and does not own an `accepted` business decision.

**Step 2: Verify RED**

```bash
uv run --project backend pytest backend/tests/test_fake_adapters.py backend/tests/test_runtime_contracts.py -q
```

Expected: FAIL because the current Runtime only has `describe()` and the current Candidate is an arbitrary section dictionary.

**Step 3: Implement immutable DTOs and schema validation**

Build public DTOs in `runtime_contracts.py`, with `from_dict/to_dict` at the JSON boundary. Keep `brief` as validated public DTOs or an immutable mapping; do not import anything from mingli-master.

Build `NarrativeRequest` with only:

- `brief`;
- `narrative_policy_version`;
- `output_contract`;
- `language`;
- `max_output_chars`.

It must not contain User, Order, Entitlement or state token fields.

**Step 4: Implement deterministic Fakes**

Use fixed test-only tokens such as `fake-opaque-state`, never a production-looking token. Fake complete must implement first-write-wins so orchestrator recovery can be tested before the real runtime exists.

The Fake Runtime must preserve the distinction between runtime inventory and product exposure: `describe` returns all 13 capabilities, while `capability_policy.py` filters the three P0 products. Do not hard-code the three-product allowlist into generic runtime DTOs, Narrative Guard or Orchestrator branches.

**Step 5: Run tests**

```bash
uv run --project backend pytest backend/tests/test_fake_adapters.py backend/tests/test_runtime_contracts.py -q
```

Expected: PASS.

**Step 6: Commit**

```bash
git add backend/app/readings backend/app/adapters/runtime.py backend/app/adapters/model.py backend/tests
git commit -m "refactor: define reading runtime and narrative ports"
```

### Task 3: Build the three explicit Request Compilers

**Files:**

- Create: `backend/app/readings/request_compiler.py`
- Create: `backend/app/readings/capability_policy.py`
- Create: `backend/tests/fixtures/mingli/bazi-prepare.json`
- Create: `backend/tests/fixtures/mingli/fortune-day-prepare.json`
- Create: `backend/tests/fixtures/mingli/fortune-week-prepare.json`
- Create: `backend/tests/fixtures/mingli/liuyao-manual-prepare.json`
- Create: `backend/tests/fixtures/mingli/liuyao-digital-prepare.json`
- Create: `backend/tests/test_request_compiler.py`

**Step 1: Write failing mapping tests**

Freeze these routes:

```text
profile_preview / bazi_deep -> bazi + natal
today                    -> fortune + near_time_personal + day
near_seven               -> fortune + near_time_personal + week
liuyao_one_question      -> liuyao + concrete_event + instant
```

Assert no generic `choose_capability(query)` function exists. The input product/action selects the compiler.

**Step 2: Add exact facts tests**

- bazi uses `birth_datetime_or_four_pillars` under the subject ref;
- fortune requires birth_datetime, timezone, location, gender and server-normalized reference_datetime;
- liuyao accepts exactly six bottom-up values in `{6,7,8,9}` or `digital_coin`;
- liuyao `time` is rejected before runtime;
- client timezone cannot overwrite the confirmed Profile Version timezone silently;
- dimension IDs are chosen from the capability-specific UI allowlist.

**Step 3: Verify RED**

```bash
uv run --project backend pytest backend/tests/test_request_compiler.py -q
```

Expected: FAIL because no compiler exists.

**Step 4: Implement small named compilers**

Use `compile_bazi_prepare`, `compile_fortune_prepare` and `compile_liuyao_prepare`. Share only generic subject/horizon serialization. Do not build one parameter-heavy universal compiler.

**Step 5: Verify fixtures byte-for-byte**

Canonicalize JSON with sorted keys only for digest comparison; preserve the real query string. Run:

```bash
uv run --project backend pytest backend/tests/test_request_compiler.py -q
```

Expected: PASS.

**Step 6: Commit**

```bash
git add backend/app/readings backend/tests/fixtures/mingli backend/tests/test_request_compiler.py
git commit -m "feat: compile p0 mingli capability requests"
```

### Task 4: Implement Narrative Guard and exact public-copy assembly

**Files:**

- Create: `backend/app/readings/narrative_guard.py`
- Create: `backend/app/readings/public_copy.py`
- Create: `backend/app/readings/output_contracts.py`
- Create: `backend/tests/fixtures/narrative/valid-bazi-candidate.json`
- Create: `backend/tests/fixtures/narrative/invalid-reference-candidate.json`
- Create: `backend/tests/test_narrative_guard.py`
- Create: `backend/tests/test_public_copy.py`

**Step 1: Write the failing happy-path test**

```python
def test_candidate_refs_close_over_the_current_brief(guard, brief, candidate):
    result = guard.validate(candidate, brief, output_contract="preview-v1")
    assert result.passed is True
    assert result.errors == ()
```

**Step 2: Write table-driven failing counterexamples**

Cover unknown subject, dimension, fact, finding, evidence and limit; disallowed kind; certainty above ceiling; evidence that supports another fact; cross-dimension finding; internal IDs in visible text; `%`/`百分之`; invented specific date/money; excessive length; empty text; extra JSON fields.

**Step 3: Verify RED**

```bash
uv run --project backend pytest backend/tests/test_narrative_guard.py backend/tests/test_public_copy.py -q
```

Expected: FAIL because Guard and assembler do not exist.

**Step 4: Implement pure validation**

Return machine-readable errors such as `unknown_fact_ref`, `scope_mismatch`, `certainty_exceeded`, `limit_missing`, `internal_identifier_visible`. Do not mutate Candidate during validation.

**Step 5: Implement deterministic assembly**

Join candidate block text mechanically in order. Append applicable `PublicLimit.public_text` and the versioned product disclosure before complete. Re-run final non-empty, size and internal-ID checks. The assembler must not call a model or paraphrase.

**Step 6: Add a semantic-limit note to tests**

Tests should prove reference closure, not claim an impossible general proof that prose entails a fact. Semantic quality remains in fixed evaluation fixtures and human release review.

**Step 7: Run tests and commit**

```bash
uv run --project backend pytest backend/tests/test_narrative_guard.py backend/tests/test_public_copy.py -q
git add backend/app/readings backend/tests/fixtures/narrative backend/tests/test_narrative_guard.py backend/tests/test_public_copy.py
git commit -m "feat: guard and assemble mingli narrative candidates"
```

### Task 5: Build the pure Reading Orchestrator state machine with Fakes

**Files:**

- Create: `backend/app/readings/orchestrator.py`
- Create: `backend/app/readings/status.py`
- Create: `backend/app/readings/errors.py`
- Create: `backend/tests/test_reading_orchestrator_prepare.py`
- Create: `backend/tests/test_reading_orchestrator_complete.py`
- Create: `backend/tests/test_reading_orchestrator_recovery.py`

**Step 1: Write failing prepare-state tests**

Test:

- new request sends no token;
- `need_input` stores the token and returns structured requirements;
- resumed input reuses that token;
- unsupported/conflict/error do not change capability or retry;
- no-token transport-unknown becomes `RUNTIME_UNKNOWN`, not another prepare.

**Step 2: Write failing model/complete tests**

Test:

- Prepared is persisted before model call;
- model request has no token or account/payment data;
- normal success calls the model once;
- invalid candidate retries the same model once at most;
- Guard failure never calls complete;
- Accepted bytes equal submitted bytes;
- complete transport-unknown replays the identical token/copy;
- a replay returns the first Accepted and does not regenerate.

**Step 3: Verify RED**

```bash
uv run --project backend pytest backend/tests/test_reading_orchestrator_*.py -q
```

Expected: FAIL because the state machine is missing.

**Step 4: Implement the orchestrator against repository protocols**

Keep it independent of FastAPI routes and SQLAlchemy models. Inject:

```text
ReadingRepository
MingliRuntime
NarrativeModel
NarrativeGuard
PublicCopyAssembler
Clock
```

There must be no `while model_decides_next_action` loop. The only bounded loop is candidate attempt `1..max_attempts`, with P0 default `2`.

**Step 5: Run tests and commit**

```bash
uv run --project backend pytest backend/tests/test_reading_orchestrator_*.py -q
git add backend/app/readings backend/tests/test_reading_orchestrator_*.py
git commit -m "feat: orchestrate mingli readings without agents"
```

### Task 6: Add immutable Profile and Reading persistence

**Files:**

- Create: `backend/alembic/versions/0002_profiles_and_readings.py`
- Create: `backend/app/profiles/__init__.py`
- Create: `backend/app/profiles/models.py`
- Create: `backend/app/profiles/repository.py`
- Create: `backend/app/readings/models.py`
- Create: `backend/app/readings/repository.py`
- Create: `backend/app/security/envelope.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/identity/models.py`
- Create: `backend/tests/test_reading_migrations.py`
- Create: `backend/tests/test_reading_repository.py`
- Create: `backend/tests/test_sensitive_payloads.py`

**Step 1: Write failing migration/constraint tests**

Require tables for `subject_profiles`, `profile_versions`, `runtime_releases`, `reading_roots`, `reading_versions`, `fact_briefs`, `generation_attempts`, `accepted_copies`, and `reading_jobs`.

Require:

- immutable version numbers per root/profile;
- at most one accepted copy per reading version;
- at most one active job per reading version;
- candidate attempt unique by `(reading_version_id, attempt_number)`;
- all content digests non-null after their state is reached.

**Step 2: Write failing sensitive-data tests**

Assert raw birth datetime, location, question, brief, candidate, Accepted Copy and `state_token` do not appear in database rows or logs. Store encrypted payload + key id + nonce/ciphertext, and a separate SHA-256/HMAC fingerprint where lookup or audit needs one.

**Step 3: Verify RED**

```bash
uv run --project backend pytest backend/tests/test_reading_migrations.py backend/tests/test_reading_repository.py backend/tests/test_sensitive_payloads.py -q
```

**Step 4: Add an envelope-encryption port**

Production must require an injected 256-bit key or KMS adapter and record `key_id`. Local/test may use an explicit local-only key. Add a production validator just like Fake OTP protection. Never reuse `identity_hash_key` as an encryption key.

**Step 5: Implement append/insert-only repository methods**

Do not expose generic `save(model)` methods. Use intent-specific methods such as `create_version`, `record_prepared`, `record_generation_attempt`, `record_accepted`, `mark_delayed` and `mark_runtime_unknown`.

**Step 6: Run migrations/tests and commit**

```bash
uv run --project backend alembic -c backend/alembic.ini upgrade head
uv run --project backend pytest backend/tests/test_reading_migrations.py backend/tests/test_reading_repository.py backend/tests/test_sensitive_payloads.py -q
git add backend/alembic backend/app/profiles backend/app/readings backend/app/security backend/app/config.py backend/app/identity/models.py backend/tests
git commit -m "feat: persist immutable encrypted reading versions"
```

### Task 7: Connect Reading Jobs to the existing Worker

**Files:**

- Create: `backend/worker/readings.py`
- Modify: `backend/worker/main.py`
- Create: `backend/tests/test_reading_worker.py`
- Modify: `backend/tests/test_worker.py`

**Step 1: Write failing claim tests**

Use PostgreSQL `FOR UPDATE SKIP LOCKED` or a tested equivalent. Assert two Workers cannot claim the same job, expired leases can recover, and one job preserves its state across process restarts.

**Step 2: Write failing orchestration wiring tests**

Assert the processor loads a job ID, calls `ReadingOrchestrator.run(job_id)`, records status, and never logs decrypted profile/brief/token data.

**Step 3: Verify RED**

```bash
uv run --project backend pytest backend/tests/test_worker.py backend/tests/test_reading_worker.py -q
```

**Step 4: Implement minimal queue-backed WorkSource/Processor**

Keep the current generic Worker loop. Add reading-specific implementations through dependency construction; do not turn `worker/main.py` into the domain module.

Each Worker transaction advances exactly one durable orchestration stage. Prepare commits `Prepared` before requeueing; one model attempt commits its attempt record (and, on success, the exact completion intent) before requeueing; Complete commits `Accepted` separately. Do not cascade prepare, model and complete through one database transaction. Prove the boundaries with the real orchestrator and PostgreSQL, including a failed Accepted commit replay with the same token and byte-identical copy, plus a committed failed model attempt that resumes at the next attempt number.

Do not claim exactly-once for an initial no-token Prepare: if the Runtime succeeds before the response or Prepared checkpoint commits, the Runtime may retain an orphan Root. Never retry that unknown call automatically or add an idempotency meaning that 5.1 does not define; control the residual risk with timeouts, a single Runtime replica, and orphan audit/cleanup.

Fail closed at claim recovery only for no-token Prepare: an expired no-token `INPUT_READY` claim with no committed checkpoint is quarantined as `runtime_unknown` and never returned for automatic processing. This deliberately treats even a pre-call crash as unknown because the database cannot prove that the Runtime did not receive the request. Persist a non-sensitive `prepare_has_state_token` derivation when the Reading Version is created, without decrypting tokens in the WorkSource. A tokened `INPUT_READY` claim is replay-safe under the V5.1 convergence contract and may be reclaimed only after rotating its fencing token; PostgreSQL tests must prove both contrasting paths and that replay passes the original token to Runtime. A direct tokened Prepare transport failure likewise remains `INPUT_READY` with a non-zero retry not-before instead of entering `runtime_unknown`. Separately, a Complete transport failure must schedule a non-zero retry delay/not-before signal; normal successful model-to-COMPLETING transitions remain immediately claimable.

**Step 5: Run tests and commit**

```bash
uv run --project backend pytest backend/tests/test_worker.py backend/tests/test_reading_worker.py -q
git add backend/worker backend/tests/test_worker.py backend/tests/test_reading_worker.py
git commit -m "feat: process reading jobs through the worker"
```

### Task 8: Admit the Mac mini native Runtime Release — hard Gate

Mac mini `native-full` 是唯一强制 Runtime Gate；正常开发、合并、发布和验收不得启动 VZ、Rosetta、QEMU 或 `linux-certify`。

**Files:**

- Modify: `infra/mingli-runtime/local_gate.py`
- Modify: `infra/mingli-runtime/README.md`
- Modify: `tests/contract/test_mingli_local_gate.py`
- Modify: `docs/PHASE_0_GATES.md`

**Step 1: Keep one fail-closed public profile**

`local_gate.py` 只公开 `native-full`。CLI、普通测试、合并检查和发布检查都不能发现或启动 `linux-certify`。已有 Linux/VZ/Rosetta/QEMU 文件仅作为历史实现保留，不得进入后续任务依赖。

**Step 2: Run the complete native release regression**

使用冻结的 PreparedInputs，以路径和 SHA-256 绑定原生 Python（当前验收基线为 CPython 3.14.6），在最多 10 个进程槽、总墙钟不超过 600 秒的条件下运行完整签名回归。唯一可接受的权威摘要是：

`slots` 和 `max_slots` 表示 signed runner 的加权调度额度，不是操作系统 PID 数量上限。运行期间可以只读采样进程树验证活跃计算负载，但不能把 multiprocessing 管理进程和休眠 PID 算成额外调度槽。

```text
targets=126 modules=93 tests=1584 failed_modules=0
```

**Step 3: Verify evidence independently**

发布 `native-full-5.1.json`、`local-native-full-5.1.json`、原始 stdout/stderr 和归档 PreparedInputs。独立 verifier 必须校验输入摘要、命令、完整摘要、原始输出和 600 秒边界；任一缺失即 RED。

**Step 4: Record the accepted baseline**

2026-08-09 的 Mac mini M4 已取得 1584/0，完整门禁约 7 分多钟并满足 `<=600s`；每次正式验收以当次报告的精确计时和独立 verifier 结果为准。该结果通过后 Task 9–13 可以继续，不等待任何 Linux 报告、镜像 digest 或 `release-5.1.json`。

**Step 5: Run focused checks and commit**

```bash
uv run --project backend pytest tests/contract/test_mingli_local_gate.py -k native -q
uv run --project backend ruff check infra/mingli-runtime/local_gate.py tests/contract/test_mingli_local_gate.py
git add infra/mingli-runtime/local_gate.py infra/mingli-runtime/README.md tests/contract/test_mingli_local_gate.py docs/PHASE_0_GATES.md
git commit -m "build: make mac mini native gate authoritative"
```

### Task 9: Implement the real one-shot Runtime Adapter

**Files:**

- Modify: `backend/app/adapters/runtime.py`
- Modify: `backend/app/config.py`
- Create: `backend/tests/test_runtime_process_adapter.py`
- Create: `backend/tests/test_runtime_startup_gate.py`

**Step 1: Write failing subprocess tests**

Use a fake executable fixture to cover:

- one JSON command on stdin;
- exactly one JSON result on stdout;
- timeout and process kill;
- stdout/stderr size caps;
- malformed, empty and multiple JSON outputs;
- stderr redaction;
- no shell interpolation;
- no automatic retry for unknown no-token prepare;
- safe identical replay for complete.

**Step 2: Write the startup describe Gate test**

Production readiness requires protocol v2, exact manifest digest, the exact frozen 13-Provider set with 13/13 readiness, full reference/evidence inventory and the frozen shape of all described capabilities. The separate Product Capability Policy allows only bazi/fortune/liuyao in P0; the other ten are installed and admitted but cannot be selected by a public product request.

**Step 3: Verify RED**

```bash
uv run --project backend pytest backend/tests/test_runtime_process_adapter.py backend/tests/test_runtime_startup_gate.py -q
```

**Step 4: Implement with `asyncio.create_subprocess_exec`**

Execute only the configured fixed path `/opt/mingli-master/scripts/run_reading_transaction.sh`. Pass user content only in JSON stdin. Never use `shell=True`, caller-supplied executable paths or command-line subcommands.

**Step 5: Add production configuration guards**

Production must reject Fake Runtime, relative paths, missing expected manifest digest, missing state root and world/group-writable release/state paths.

**Step 6: Run Fake-executable tests and Mac-native signed Runtime smoke, then commit**

The real smoke lane calls the read-only, signed Mac mini Runtime installation with a
temporary private state root and proves `describe → prepare → complete → identical
Accepted replay`. It must not start or depend on a Linux image, Docker, VZ, Rosetta,
QEMU, `linux-certify`, or `release-5.1.json`.

```bash
uv run --project backend pytest backend/tests/test_runtime_process_adapter.py backend/tests/test_runtime_startup_gate.py backend/tests/test_fake_adapters.py -q
git add backend/app/adapters/runtime.py backend/app/config.py backend/tests
git commit -m "feat: call mingli v51 through the one-shot adapter"
```

### Task 10: Implement the standalone model HTTP adapter without Agent features

**Files:**

- Create: `contracts/openapi/internal-model-v1.yaml`
- Modify: `backend/app/adapters/model.py`
- Modify: `backend/app/config.py`
- Create: `backend/tests/test_standalone_model_adapter.py`
- Create: `backend/tests/test_model_data_boundary.py`

**Step 1: Freeze the company-controlled endpoint**

Define one internal request that accepts model profile, messages, response JSON Schema, temperature/max output and idempotency metadata. It returns output JSON plus usage, latency and model version. It exposes no tools, function calls, memory, retrieval or agent-run IDs.

**Step 2: Write failing boundary tests**

Inspect the outbound request and prove it contains only Narrative Policy, Output Contract and Prepared Brief. Search the serialized request for state tokens, User/Order/Entitlement IDs, raw database rows and service secrets.

**Step 3: Write failing transport tests**

Cover timeout, 429, 5xx, invalid JSON, schema mismatch, response size cap and cost/usage capture. Do not retry inside the HTTP adapter; orchestrator owns the one bounded regeneration decision.

**Step 4: Verify RED**

```bash
uv run --project backend pytest backend/tests/test_standalone_model_adapter.py backend/tests/test_model_data_boundary.py -q
```

**Step 5: Implement the direct adapter**

Use `httpx.AsyncClient` with an allowlisted HTTPS base URL, server-injected credential, connect/read timeout, body cap and request ID. P0 config names exactly one active Model Profile. Production rejects Fake Model.

**Step 6: Run tests and commit**

```bash
uv run --project backend pytest backend/tests/test_standalone_model_adapter.py backend/tests/test_model_data_boundary.py -q
git add contracts/openapi/internal-model-v1.yaml backend/app/adapters/model.py backend/app/config.py backend/tests
git commit -m "feat: generate narratives with one standalone model"
```

### Task 11: Expose Profile and Reading APIs without exposing runtime tokens

**Files:**

- Create: `backend/app/api/profiles.py`
- Create: `backend/app/api/readings.py`
- Create: `backend/app/profiles/schemas.py`
- Create: `backend/app/readings/api_schemas.py`
- Modify: `backend/app/api/router.py`
- Modify: `contracts/openapi/v1.yaml`
- Create: `backend/tests/test_profiles_api.py`
- Create: `backend/tests/test_readings_api.py`
- Modify: `tests/contract/test_openapi_contract.py`

**Step 1: Write failing OpenAPI tests**

Freeze Phase 2 resources for Profile Draft/Version, start Preview/Today/Week/Liuyao, supply missing input, poll status, fetch result, submit Verification and create Follow-up.

No public schema may contain `state_token`, `candidate`, provider prompt or decrypted birth payload.

**Step 2: Write authorization/idempotency tests**

Test User/Guest ownership, guest claim, same Idempotency-Key returning the same Reading Version, cross-user 404, no-store/noindex headers and rate limits.

**Step 3: Verify RED**

```bash
uv run --project backend pytest backend/tests/test_profiles_api.py backend/tests/test_readings_api.py tests/contract/test_openapi_contract.py -q
```

**Step 4: Implement thin routes**

Routes call Profile/Reading application services and enqueue jobs. They do not call runtime/model directly and never wait on a long model request in the HTTP process.

**Step 5: Run tests and commit**

```bash
uv run --project backend pytest backend/tests/test_profiles_api.py backend/tests/test_readings_api.py tests/contract/test_openapi_contract.py -q
git add backend/app/api backend/app/profiles backend/app/readings contracts/openapi/v1.yaml backend/tests tests/contract/test_openapi_contract.py
git commit -m "feat: expose profile and reading phase two APIs"
```

### Task 12: Build the result composition and P0 free website flows

**Files:**

- Create: `web/src/app/app/profile/new/page.tsx` or replace the existing placeholder
- Create: `web/src/app/app/readings/[readingId]/page.tsx`
- Create: `web/src/app/app/fortune/today/page.tsx`
- Create: `web/src/app/app/fortune/week/page.tsx`
- Modify: `web/src/app/app/ask/liuyao/page.tsx`
- Create: `web/src/components/readings/fact-panel.tsx`
- Create: `web/src/components/readings/accepted-copy.tsx`
- Create: `web/src/components/readings/evidence-list.tsx`
- Create: `web/src/components/readings/limit-notice.tsx`
- Create: `web/src/components/readings/verification-form.tsx`
- Create: `web/src/test/reading-flows.test.tsx`
- Create: `web/src/test/reading-result.test.tsx`

**Step 1: Write failing UI tests**

Cover 360px and desktop flows for:

- confirmed profile inputs/time policy;
- today/week target date display;
- six tosses bottom-up or explicit digital coin;
- structured need-input form;
- queued/delayed/runtime-unknown states;
- deterministic fact panel;
- exact Accepted Copy;
- evidence/limits rendered from brief metadata;
- Verification actions;
- no state token/internal refs in DOM or network payloads.

**Step 2: Verify RED**

```bash
npm --prefix web test -- reading-flows.test.tsx reading-result.test.tsx
```

**Step 3: Implement result composition**

Render separate components for deterministic facts, Accepted narrative, evidence, limits and Verification. Never ask the browser to calculate pillars/hexagrams or reformat the Accepted text.

**Step 4: Run frontend and end-to-end contract tests**

```bash
npm --prefix web test -- reading-flows.test.tsx reading-result.test.tsx
npm --prefix web run typecheck
npm --prefix web run build
uv run --project backend pytest backend/tests tests/contract -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add web/src backend/tests tests/contract
git commit -m "feat: deliver p0 free mingli reading flows"
```

### Task 13: Run release verification before enabling real traffic

**Files:**

- Create: `docs/releases/2026-XX-XX-mingli-v51-web-phase2.md`
- Modify: `docs/PHASE_0_GATES.md`
- Modify: `README.md`

**Step 1: Run all static and automated checks**

```bash
make check
make test
```

Expected: all backend, frontend and contract checks PASS.

**Step 2: Run the real staging trajectory suite**

Exercise:

```text
all 13 providers -> frozen describe snapshot -> dependency/evidence smoke fixture
new bazi -> need input -> prepared -> one model call -> guard -> accepted
fortune day and week -> exact target period -> accepted
liuyao manual and digital -> accepted
follow-up -> prior_answer in new brief -> accepted new version
candidate rejected twice -> delayed, never complete
complete committed then DB crash -> identical replay -> one Accepted
```

**Step 3: Inspect sensitive-data boundaries**

Search API bodies, browser storage, structured logs, error tracking and database non-encrypted columns for state token, raw birth data, full Prompt and model credential leakage.

**Step 4: Review operational Gates**

Do not enable production if any of these remain pending:

- Mac mini `native-full` 1584/0 原生报告及独立 verifier；
- complete 13-Provider characterization matrix and native release regression;
- 55/55 reference-pack and 1328-entry evidence-index integrity checks;
- state-volume backup/restore;
- model DPA/data retention and fixed evaluation;
- Narrative Guard red-team set;
- runtime/model production credentials in Secret Manager;
- alerting for runtime_unknown, delayed, Guard rejection and model cost.

**Step 5: Record exact release evidence and commit**

```bash
git add docs/releases docs/PHASE_0_GATES.md README.md
git commit -m "docs: record mingli v51 phase two release evidence"
```

## Execution checkpoints

- After Task 5: the whole algorithm and narrative state machine works with Fakes; review architecture before adding persistence.
- After Task 7: Phase 2 is locally complete with Fake Runtime/Model; website work can continue while external Gates remain closed.
- Task 8 只认 Mac mini `native-full`；不得等待或启动 Linux 模拟认证。
- After Task 10: run fixed model quality evaluation before allowing complete.
- After Task 13: open real traffic only through a small allowlisted rollout.
