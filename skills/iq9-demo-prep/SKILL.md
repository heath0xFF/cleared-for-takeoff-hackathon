---
name: iq9-demo-prep
description: Prepare a LiquidAI × Dragonwing hackathon demo and pitch. Covers the judging rubric, the "why not a cloud API call?" answer, collecting measured latency, decode, memory, and endurance numbers on the IQ-9075, geniex-bench, the two-minute demo structure, and backups. Use when the user is getting ready for judging, wants performance numbers, a pitch, a README for judges, or is going for the Fastest Agent or Best Tiny Agent awards.
compatibility: Metrics script runs on the IQ-9075 with geniex serve running.
metadata:
  version: "0.2"
---

# Demo prep

Rubric and format: `docs/judging.md`. If it ever differs from the organisers' brief, the brief wins.

| Weight | Criterion |
|---|---|
| 25% | Edge-native value: why is this better on-device, or only possible there? |
| 20% | Technical execution: reliable, integrated, and running locally |
| 20% | Originality: not another generic chatbot |
| 15% | Real-world usefulness: a clear user and a clear need |
| 10% | Performance and efficiency |
| 10% | Demo quality: a short, credible offline proof |

## 1. The first question: "Why should this not simply be a cloud API call?"

Help the user write a two-sentence answer that names a **specific constraint**. "It runs on-device" is not an answer. Constraints that work:
- No network where it runs (a field site, a vehicle, a disaster zone, or tonight's network cut).
- The data can't leave the device (camera or mic in a private space, medical, or industrial IP).
- The reaction has to beat a round trip, or has to keep working while the link is down.
- At this volume, a flat marginal cost beats paying per token.

Then tie it to the architecture: what the local rule, optional d1 gate, or other decision design does, how often, and what it costs (measure in step 2). LFM3-1.7B is a reference default, not a required model. External sensors are optional and not provided.

## 2. Numbers (measure them; never quote the docs as your own)

The following collector is for GenieX's local HTTP server. For ZETIC, use its IQ9 CLI or SDK timings plus the app's own end-to-end JSONL, and measure process and device memory on the board.

```bash
# Separate terminal, from the repo root:
skills/iq9-geniex-lfm/scripts/serve.sh run
# Another terminal (choose the app's already-cached model):
skills/iq9-demo-prep/scripts/collect_metrics.sh --model 'cached-name:precision' --log apps/<name>/agent_log.jsonl --out apps/<name>/metrics.json
```

`collect_metrics.sh` invokes the standard-library `collect_metrics.py`. Defaults: five measured streamed requests after one separately recorded warm-up, a 128-token cap, and `enable_think: false`. Change the cap with `--max-tokens`; `--enable-think` includes reasoning. Neither choice guarantees a usable answer.

- `ttft_s` times the first generated reasoning **or** answer delta; `answer_ttft_s` separately times the first answer delta.
- Empty/reasoning-only answers, missing usage, cap violations, and HTTP errors are failures, excluded from successful-run medians. Report n successful **and** failed, plus the warm-up outcome.
- `decode_tok_s` is explicitly an **SSE timing estimate**, using server completion usage and first-to-last generated delta timing. SSE chunks can bundle tokens; do not call it an exact tokenizer benchmark. Missing usage leaves rates null, never substitutes chunk counts. `generation_tok_s` includes the full request time (prefill/transport), not pure decode.
- It records runtime/model metadata, a device-log excerpt, instantaneous server RSS, system memory/disk/thermal state, and optional app gate/loop medians, errors, alerts, and time span. Verify that the device log belongs to this server after a capped request.

Do not reuse legacy or [dated reference results](../../README.md#developer-notes) as this app's fresh measurements. The collector exits 2 if any measured request fails; it never installs or pulls models.

For the Fastest Agent or Best Tiny Agent awards, add:
- **End-to-end loop time** from the app log: `loop_ms` median and p95, not just model speed.
- **Footprint:** model size on disk (GenieX cache or ZETIC package), runtime process RSS, and peak RSS of the app (`/usr/bin/time -v`, "Maximum resident set size"). Measure the chosen d1/model/configuration rather than transferring legacy memory figures. Instantaneous process RSS, peak app RSS, and NPU/device memory are distinct. d1 is optional for tiny-agent designs.
- **Endurance:** run for 30 minutes or more, and report the iteration count, errors, and the temperature trend.
- **Bench, optional:** `geniex-bench` (see `docs/developer-guide.md` §10). Use the v0.10.0 bench to match the runtime, and set `LD_LIBRARY_PATH` as shown there.

Write numbers into the app's README with the board, date, chosen runtime and version, actual model/build and precision, workload, n, and medians. Label estimates as estimates and stored results as prior results. Mark anything not measured as ⚠️. Any new helper behavior must pass local checks and a bounded IQ9 integration check before being called board-verified.

## 3. Two-minute demo

| Time | Show |
|---|---|
| 0:00–0:20 | The user, their problem, and the constraint (from step 1) |
| 0:20–0:35 | **Unplug the network on stage**, then show `curl huggingface.co` failing |
| 0:35–1:30 | The loop running live: an input changes, the local decision runs, the action fires, the one-sentence explanation appears |
| 1:30–1:50 | The local JSONL log scrolling (the proof) plus 2–3 numbers from `metrics.json` |
| 1:50–2:00 | The next step for a real deployment |

Keep a visible timer, a recorded backup video, and a recorded log ready.

## 4. Pre-demo checklist

- [ ] Preflight shows no FAIL for the app's selected profile/model (`reference`, `generator`, or `board`); the app also passes its end-to-end smoke test.
- [ ] The `iq9-offline-rehearsal` network-off run is done, and its evidence is saved.
- [ ] For GenieX, run a visible foreground server with a keepalive covering quiet gaps (`serve.sh run` defaults to 1800 s); verify a usable capped warm-up and HTP0 before showing metrics. For ZETIC, verify its device route and a capped warm-up using the app's local package.
- [ ] Validate answer/tool content. For GenieX raw completions, use unique initial prompts. Know how to safely relaunch the chosen runtime; do not interrupt a shared process.
- [ ] Read the licence for every model shown. LFM3-1.7B and d1-2B use the LFM Open License v1.0.
