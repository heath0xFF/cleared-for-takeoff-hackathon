# AGENTS.md

Instructions for coding agents (Claude Code, Codex, Cursor, Copilot, Gemini, pi, and others) helping developers build on-device AI apps at the **On-Device AI Hackathon: Cleared for Takeoff ✈️** (LiquidAI × Qualcomm Dragonwing). People read the docs; this file is for agents.

## What this repo is

A knowledge base and set of working examples for one target: the **Dragonwing IQ-9075 EVK** (QCS9075, Hexagon v73 NPU, 36 GB, Ubuntu 24.04 aarch64) running LiquidAI models:

- **Reference generator and tool calls:** `LiquidAI/LFM3-1.7B-GGUF:Q4_0` through **GenieX v0.10.0** (`geniex serve`, OpenAI-compatible, `127.0.0.1:18181`, NPU).
- **Optional decision gate:** `LiquidAI/d1-2B` through **transformers on the CPU** ("Path A"), from a local snapshot at `~/models/d1-2B`.
- **Optional, unverified route:** ZETIC's IQ9 C++ SDK with locally staged LFM3-Omni/d1 packages. Follow [`examples/zetic-iq9/`](examples/zetic-iq9/README.md) and do not treat the reference stack's board results as ZETIC results.

Participants may choose **any LFM3-family model**, and other LFM models are also options. These are reference defaults, not competition restrictions. Verify each chosen model's format, runtime, NPU support, and task behavior on the board; do not transfer the reference model's results to another checkpoint or precision. Do not require d1 when a rule or another design meets the project's needs.

External sensors are **optional, not provided**; participants may bring their own. Do not assume a camera, mic, or other sensor will be supplied. Examples can use simulated inputs, local files/events, or the board's internal readings.

Every project's final demo runs **with the network unplugged**. Assume that from the first line of code.

## Where you are running

Check this before running any command:

- **On the board** (`uname -m` prints `aarch64`; GenieX is on PATH only if that route is installed): run commands directly.
- **On a laptop:** the board is reachable over SSH. Use the host the user gives you (call it `$IQ9_HOST`). Run board commands as `ssh "$IQ9_HOST" '<cmd>'`, and copy files with `rsync`/`scp`. Never assume the laptop has `geniex`, the NPU, or the models.

Start each board-work session with the preflight check: use the default `reference` profile for the GenieX/Transformers stack, or `--profile board` for ZETIC (over SSH: `ssh "$IQ9_HOST" 'bash -s -- --profile board --json' < skills/iq9-preflight/scripts/preflight.sh`). The ZETIC route also needs its separate local artifact and inference checks. For laptop-only documentation work without a supplied host, report that board preflight was not run rather than guessing a host or testing the laptop as if it were the board.

A missing default cache entry is not proof that the weights are absent. Check `geniex list`, disk space, and existing local model directories before proposing a download. An existing GGUF can be imported with `geniex pull <name>:<precision> --local-path <directory>` **with approval**; this copies files into the cache but needs no model download. A d1 GGUF does not satisfy the Transformers snapshot requirement. Back up replaced board files when refreshing examples; do not use destructive sync to remove unrelated files.

Run long-running servers, downloads, benchmarks, and monitoring in a separate terminal or an agreed logged runner, and verify output and exit status. Keep controllable jobs visible rather than hiding them behind `nohup`; never send input into the agent's own or another busy terminal.

## Filesystem safety

- Use absolute paths with filesystem tools; expand the home directory explicitly rather than assuming a tool expands `~`.
- A workspace directory literally named `~` is **not** the home directory. `./~` addresses that literal entry; bare shell `~` expands to the home directory. Never suggest home-root or broad-glob cleanup.
- Before any destructive operation, inspect the exact resolved target and symlinks, show the user what would be affected, and get approval for deleting user files. Keep task-created temporary files inside the task workspace; do not reset user configuration to debug an app.

## Skills

Each folder under `skills/` has a `SKILL.md` and supporting scripts or a linked example. Read the skill before doing that kind of work. Reference behavior has dated IQ9 evidence; revised helpers require local regression and bounded board integration checks before being called board-verified.

| Skill | Use it for |
|---|---|
| [`iq9-preflight`](skills/iq9-preflight/SKILL.md) | "Is the board ready?", the start of a session, "it stopped working" |
| [`iq9-geniex-lfm`](skills/iq9-geniex-lfm/SKILL.md) | LFM calls through GenieX or `geniex serve`. Includes `lfm_client.py` and `serve.sh` |
| [`iq9-d1-decision-gate`](skills/iq9-d1-decision-gate/SKILL.md) | Triage, classification, gating, alerts, d1 questions, threshold calibration |
| [`iq9-always-on-agent`](skills/iq9-always-on-agent/SKILL.md) | Building a monitor or autonomous loop. Includes `scaffold.sh` |
| [`iq9-lfm-tool-calling`](skills/iq9-lfm-tool-calling/SKILL.md) | Function and tool calling, multi-step agents |
| [`iq9-offline-rehearsal`](skills/iq9-offline-rehearsal/SKILL.md) | Offline audit, staging everything before the cut, the network-off test |
| [`iq9-demo-prep`](skills/iq9-demo-prep/SKILL.md) | Judging, metrics, the pitch, the "why not cloud?" answer |

If your agent doesn't load skills automatically, read the `SKILL.md` directly. The same skills are linked from `.claude/skills/` and `.agents/skills/`.

## Runtime and safety rules

1. **Cap every LFM call.** GenieX uses `max_completion_tokens` on chat and `max_tokens` on `/v1/completions`; ZETIC's C++ SDK uses `GenerationConfig::max_tokens`.
2. **The reference LFM3-1.7B reasons by default.** For a direct GenieX answer, try chat with `enable_think: false`, or a raw completion with `<think>\n\n</think>\n\n` already closed (`lfm_client.LFM().sentence()`). Neither the flag nor a token cap guarantees a usable answer. Inspect `content` and `reasoning_content`, and re-test for other models and runtimes.
3. **Validate the expected output, not just token usage or `ok`.** Zero completion tokens are a failure for LFM generation. For text-answer requests, empty content or reasoning alone is also a failure even when tokens are positive; for tool requests, validate calls against the schema and allowlist. Return errors as data and log them. The GenieX helper retries once with a unique tag; use `serve.sh restart` for persistent GenieX server failures only when it is safe to interrupt that server. Do not classify d1's expected zero output tokens as a generation failure.
4. **Use Path A for the reference d1-2B stack.** Run the pinned local snapshot through transformers (`trust_remote_code=True`, `local_files_only=True`, fp32, CPU), loaded once. ZETIC's IQ9 d1 package is a separate, unverified route; do not substitute it for the Transformers snapshot or assume its probabilities share the same calibration. The tested GenieX d1-2B GGUF decision requests failed; do not switch the app to that route or claim all GenieX decision models are unsupported.
5. **Load weights from local paths or caches only at runtime.** Transformers must load a snapshot directory, not a Hugging Face repo ID. GenieX requests use already-registered cached model names. ZETIC apps use complete staged packages through `fromPath()`. No model downloads, `pip install`, CDN assets, or telemetry at runtime. Stage dependencies beforehand; use offline Hugging Face/Transformers settings for local inference.
6. **Keep d1 and the LFM sequential.** Current reference-stack measurements support this policy, not just the legacy stack's results. Re-measure before changing the scheduling policy.
7. **Calibrate d1 on the actual task. Don't trust 0.5.** Use labeled app states and held-out evaluation with `calibrate_threshold.py`, or use a deterministic rule. Do not transfer thresholds between models, tasks, or input formats, or deploy a threshold fitted only to synthetic examples.
8. **The model proposes; code decides.** Validate tool arguments against a schema, run only allowlisted actions, put a policy in code in front of any write or real-world action, and report actions from your own record.
9. **Log every iteration** as flushed JSONL, including errors and actions. Keep the model's proposal separate from the code's action record.
10. **Verify NPU execution for the generator.** Send a capped request and inspect current device evidence for the chosen runtime. The reference GenieX configuration showed `Using 1 device(s): HTP0`; that log line does not apply to ZETIC. A missing device indication is a reason to investigate, not proof of CPU fallback. Do not silently switch the reference generator to `--compute cpu` or quote legacy CPU speeds as current results. d1 Path A deliberately uses the CPU.
11. **For GenieX, make raw-completion prompts unique and plan for idle unloading.** Identical raw requests returned continuing commentary despite nonzero tokens. Include an event timestamp or unique tag before the first call, not only on retry. The default idle keepalive is 300 s; use `--keepalive` or `GENIEX_KEEPALIVE` to cover demo quiet gaps, or send a capped warm-up. Measure reload latency for the chosen model and runtime.

## Ask before you

- Run `sudo`, `apt`, `usermod`, or anything that changes the system.
- Run `geniex pull` (including a local import), `geniex remove`, `geniex clean`, or `fetch_d1.py`. Check `geniex list`, existing local weights, and `df -h /` first; **never re-pull** a model that's already cached or download weights unnecessarily.
- Download ZETIC's model packages or change its SDK installation on a shared board. Check existing local packages and disk space first. Confirm license and access terms before redistribution.
- Install, upgrade, or reinstall GenieX. The active target is v0.10.0; legacy numbers in `docs/` are labeled with the version that produced them.
- Move the d1 revision pin (`10e7671d44e4`). `trust_remote_code` runs the repo's Python code, so review it first.
- Bind `geniex serve` to anything other than loopback, or cut the network. Over SSH, cutting the network also cuts your own session.
- Delete anything under `~/models` or `~/.cache/geniex`, delete other user files, or change shell startup files or user configuration. Inspection is not permission to reset or remove them.

## Facts and evidence

- Start with [`README.md` → Developer Notes](README.md#developer-notes) for the latest dated reference-stack checks; `docs/` supplies detailed setup and version-tagged evidence. Some detailed guides still describe the pre-verification migration. Prefer version-matched board measurements over older or unverified claims, flag conflicts, and do not silently treat vendor snippets or training data as stronger evidence.
- Markers: ✅ confirmed · 🧪 measured on an identified IQ-9075 configuration · ⚠️ unverified. Never upgrade ⚠️ to a fact without measuring it on the board. A reference-stack result does not verify another model, precision, runtime, or device.
- Performance reports must identify the board, runtime version, model/precision, and sample count; report latency/decode medians and distinguish process RSS, peak RSS, and device memory. Label stored measurements as prior results, not fresh results for a user's board. Calibration reports must state label provenance and evaluation split.
- Model-card latencies (Jetson, Apple, GPU) don't apply to this board.

### Verified reference-stack checks — 2026-11-05

🧪 IQ-9075, **GenieX v0.10.0** (QAIRT 2.50, llama.cpp `19cce69`), **LFM3-1.7B QAD-Q4_0** served as `:Q4_0` on **HTP0**, and **d1-2B fp32 CPU, 8 threads**, through Transformers 5.19.0 / torch 2.11.0. These are dated checks, not a guarantee of the board's current state.

- The starter smoke test and d1 typed-answer, image, and batch checks passed. d1 returned zero output tokens as expected.
- d1-2B **Q4_K_M GGUF on CPU** failed all **5** `/v1/decisions` attempts with HTTP 400, `SDKError(Parameter not supported by this plugin)` (`-100016`). `/v1/systemone` returned 404. This is a configuration-specific failure, not a blanket statement about GenieX decision support.
- Caps were honored across **205 recorded LFM requests**; the old zero-token bug was not reproduced, not declared fixed. A tight-cap chat request with thinking disabled still returned reasoning-only output with empty answer content and positive token usage.
- Direct-answer probes improved with `enable_think: false` or a closed reasoning block. Repeated identical raw prompts produced continuing commentary; cache/state handling remains only a hypothesis.
- Idle unloading and both keepalive controls were observed. Do not reuse the old stack's reload penalty; the current default-timeout reload probe had only one post-idle observation.
- The same three-question gate took a median **2.848 s alone** versus **5.572 s during LFM generation**, **n=5 per condition**, paired runs. Keep sequential execution for this configuration.
- In **36 synthetic states**, threshold 0.5 missed **9 of 18 positive cases**. This was not production calibration or held-out evaluation; do not deploy the fitted threshold.
- The network stayed connected during these checks. Offline model-loading settings and a passing starter are **not** a physical network-off rehearsal.

| Question | Read |
|---|---|
| Latest reference-stack validation | [`README.md` → Developer Notes](README.md#developer-notes) |
| Setup, architecture, troubleshooting | [`docs/developer-guide.md`](docs/developer-guide.md) |
| Server endpoints, request fields, known gaps | [`docs/runtimes.md`](docs/runtimes.md) |
| Optional ZETIC IQ9 route | [`examples/zetic-iq9/README.md`](examples/zetic-iq9/README.md) |
| Model families and reference defaults | [`README.md` → Platform and models](README.md#platform-and-models) |
| Model format, precision, runtime compatibility | [`docs/runtimes.md` → Model format and precision](docs/runtimes.md#model-format-and-precision) |
| Measuring latency and memory | [`docs/developer-guide.md` → Measuring performance](docs/developer-guide.md#10-measuring-performance) |
| d1 question types and budget | [`docs/decision-models.md`](docs/decision-models.md) |
| Board facts and drivers | [`docs/hardware.md`](docs/hardware.md) |
| Network-off checklist | [`docs/offline-readiness.md`](docs/offline-readiness.md) |
| Scoring and demo format | [`docs/judging.md`](docs/judging.md) |

## Repo layout

| Path | What | Run |
|---|---|---|
| `starter/run.sh` | Current-stack smoke test, after setup | `./starter/run.sh` (no downloads; measure elapsed time) |
| `examples/system-one-decision/` | d1 install, pinned fetch, env check, example | `~/.venvs/d1/bin/python system_one_example.py` |
| `examples/lfm-server-npu/` | Start the server, one capped request, stop | `python3 serve_lfm_npu.py` |
| `examples/always-on-agent/` | The reference loop | `~/.venvs/d1/bin/python always_on_agent.py --iterations 8` |
| `examples/tool-calling/` | Tool calls with guards | `python3 tool_calling.py --self-test`, then `python3 tool_calling.py` |
| `examples/zetic-iq9/` | Optional ZETIC setup and local smoke check | `python3 smoke.py --help` |
| `skills/` | Agent skills and their scripts | see the table above |
| `apps/` | Put new projects here (`scaffold.sh apps/<name>`) | — |

## Code conventions

- Python 3.12 on the board. Examples use only the standard library, except d1 code, which runs in `~/.venvs/d1` (`--system-site-packages`; it reuses the board's torch 2.11.0).
- Each script gets `--help` and a short smoke-test mode (`--iterations N`, `--self-test`, or `--sensor-mode simulated`) so you can check it without waiting.
- Return errors as data inside loops. Never let the explainer crash the loop. Validate the expected response before acting on it.
- **Helper boundaries:** `lfm_client.py` rejects zero/missing tokens and empty answers, checks tool-call envelopes, tags raw prompts before the first call, and retries unusable output once. It does not fully validate argument schemas, execute tools, enforce action policy, or restart servers. Keep those guards in app code; `ok` is not proof of answer correctness. The raw `sentence()` template targets the reference LFM3 format; re-test it for other models. Revised helper behavior is not board-verified merely because local mocks pass.
- Bash scripts: `set -euo pipefail`, and they must pass shellcheck.
- Each app gets a README with how to run it, what it measured (with markers), and its offline status.

## Out of scope for this repo

Flashing or reimaging the board, camera/GStreamer pipelines, and model conversion or quantisation (QAIRT, AI Hub) are covered by Qualcomm's Dragonwing skills and docs, not here. For those, point the user to the Dragonwing docs (`https://dragonwingdocs.qualcomm.com`), the IM SDK docs (`https://imsdkdocs.qualcomm.com`), and the GenieX docs (`https://geniex.aihub.qualcomm.com`). Keep the reference defaults as a starting point, not an eligibility restriction. When a participant chooses another LFM model, preserve the offline and safety rules and verify its runtime/NPU support and behavior; do not promise reference-stack performance.
