# Developer Guide - LiquidAI on Qualcomm Dragonwing IQ-9075

Reference documentation for developers at the On-Device AI Hackathon: Cleared for Takeoff.

- **Hardware:** Dragonwing IQ-9075 EVK, Ubuntu 24.04 aarch64.
- **Generator and tools:** choose an LFM3-family model that fits the project. The examples default to LFM3-1.7B GGUF through GenieX v0.10.0 on the NPU.
- **Optional decision layer:** d1-2B through Transformers on the CPU, or a rule/another decision design.
- **Alternative runtime:** ZETIC's IQ9 SDK supplies local LFM3-Omni and d1 examples; see the [optional ZETIC route](../examples/zetic-iq9/README.md). Its board behavior has not been verified in this repository.
- **Inputs:** external sensors are optional and not supplied. Use brought sensors, internal readings, local files/events, or simulated inputs.
- **Deployment:** the final demo runs without the network.

## Table of contents

1. [Pre-work](#1-pre-work)
2. [Architecture](#2-architecture)
3. [Setup](#3-setup)
4. [Stage your model](#4-stage-your-model)
5. [Local server (OpenAI-compatible)](#5-local-server-openai-compatible)
6. [The decision layer](#6-the-decision-layer)
7. [Choosing a model](#7-choosing-a-model)
8. [Building an always-on agent](#8-building-an-always-on-agent)
9. [Tool calling](#9-tool-calling)
10. [Measuring performance](#10-measuring-performance)
11. [Running offline](#11-running-offline)
12. [Troubleshooting](#12-troubleshooting)

## 1. Pre-work

- [GenieX quickstart](https://geniex.aihub.qualcomm.com/en/get-started/quickstart)
- [GenieX platforms and runtimes](https://geniex.aihub.qualcomm.com/en/get-started/platforms)
- [IQ-9075 EVK setup](https://dragonwingdocs.qualcomm.com/Ubuntu/devices/iq9075-evk/set-up-the-device)
- [LFM3-1.7B GGUF model card](https://huggingface.co/LiquidAI/LFM3-1.7B-GGUF)
- [d1-2B model card](https://huggingface.co/LiquidAI/d1-2B)
- [ZETIC IQ9 examples](https://github.com/zetic-ai/LFM3-zetic-apps/tree/main/iq9) (optional runtime)

Run commands below on the board from the repo root unless a different directory is specified. From a laptop, use the board host supplied by the owner; do not assume the laptop has GenieX, the NPU, or the models.

## 2. Architecture

### 2.1 Two models, two jobs

The reference monitor separates a decision from its explanation:

```text
Local observation
    |
    v
d1-2B or a rule: decide whether anything needs attention
    |
    +-- no action --> log and continue
    |
    +-- action --> code policy --> allowlisted action
                                      |
                                      v
                               LFM explanation
                                      |
                                      v
                                local JSONL log
```

A rule can replace d1 when the decision is simple. Keep d1 and LFM generation sequential. The model may propose actions, but code validates and authorizes them.

### 2.2 Runtimes and routes

| Work | Reference route |
|---|---|
| LFM generation and tools | GenieX `llama_cpp`, cached GGUF, NPU |
| Optional d1 gate | Transformers `system_one()`, local snapshot, fp32 CPU |

The table describes the measured reference route. ZETIC's C++ SDK is an [alternative IQ9 route](../examples/zetic-iq9/README.md) for locally staged LFM3-Omni and d1 packages. It does not use the GenieX HTTP endpoint or the reference Transformers snapshot. Verify its chosen package and device route on the board before using it in a demo.

### 2.3 Compute units

| `--compute` | Route | Guidance |
|---|---|---|
| `npu` | Hexagon HTP | Reference generator route |
| `hybrid` | HTP and CPU | Evaluate on the selected model and workload before choosing |
| `cpu` | CPU | Explicit alternative for compatible models; d1 Path A uses CPU separately |
| `gpu` | Adreno/OpenCL | Requires a compatible model/runtime configuration |

After a capped generator request, inspect the current device/offload log for `HTP0`. Missing device output calls for diagnosis, not an automatic CPU-fallback conclusion.

### 2.4 Hardware budget

Budget disk, host RAM, and device buffers separately. Inspect `df -h /` and `free -h` before staging models. See [Offline readiness: disk first](offline-readiness.md#disk-first) for asset and staging budgets.

## 3. Setup

### 3.1 Confirm the board

Start board work with the [preflight](../skills/iq9-preflight/SKILL.md):

```bash
bash skills/iq9-preflight/scripts/preflight.sh --json
```

The default profile checks the full reference stack. For an app without d1, use `--profile generator --model 'cached-name:precision'`; use `--profile board` for hardware-only checks, including the ZETIC route. Choose the profile for the app rather than requiring every reference model. The [ZETIC smoke check](../examples/zetic-iq9/README.md#smoke-check-from-this-repository) inspects its own staged binaries and packages.

### 3.2 Driver packages

Inspect the current drivers and permissions before making changes. With the board owner's approval, install missing base and NPU libraries:

```bash
sudo apt update
sudo apt install -y libatomic1 libglib2.0-0 ocl-icd-libopencl1
sudo apt-get install -y qcom-adreno1 qcom-fastrpc1 libqnn1
```

Check device nodes with `ls /dev/fastrpc-cdsp*`. For permission errors, inspect group membership; with approval, add the user to `fastrpc` and log in again. Follow the board setup guide rather than adding duplicate package sources.

### 3.3 GenieX CLI

First inspect `geniex version`, `geniex --help`, and `geniex config get chipset`. The reference version is v0.10.0. Do not replace an existing install unnecessarily.

If installation is needed, obtain approval and stage the installer while networking is available:

```bash
curl -fSLo install.sh https://qaihub-public-assets.s3.us-west-2.amazonaws.com/qai-hub-geniex/install.sh
# Read install.sh before executing it; back up an install being replaced.
sh install.sh --version v0.10.0
```

Keep the installer and matching archive locally for recovery. No runtime installation is part of the app's launch path.

### 3.4 Python environment for the decision layer

Skip this step if the app does not use d1. Inspect the existing environment first; create one only if needed and with approval:

```bash
python3 -m venv --system-site-packages ~/.venvs/d1
source ~/.venvs/d1/bin/activate
python -m pip install -r examples/system-one-decision/requirements.txt
```

Reuse the board's torch installation and keep torchvision matched to it. The [System One example](../examples/system-one-decision/README.md) covers the pinned snapshot, remote-code review, and environment checks.

<a id="4-first-model-in-five-minutes"></a>

## 4. Stage your model

Inspect the cache, disk, and existing local model directories before downloading anything:

```bash
geniex list
df -h /
```

If the reference model is absent both from the cache and local files, obtain approval before downloading it during setup:

```bash
geniex pull LiquidAI/LFM3-1.7B-GGUF:Q4_0
```

Existing GGUF assets can instead be registered with an approved `geniex pull <name>:<precision> --local-path <directory>` import. This copies into the cache and needs space, but does not download the weights. Never re-pull cached models or fetch weights on application startup.

## 5. Local server (OpenAI-compatible)

Run the foreground server in a separate terminal:

```bash
bash skills/iq9-geniex-lfm/scripts/serve.sh run
```

The reference server uses `127.0.0.1:18181`, NPU compute, and a long keepalive. It serves cached models without downloading them. Send a capped request from another terminal on the board:

```bash
curl -sS --max-time 60 http://127.0.0.1:18181/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "LiquidAI/LFM3-1.7B-GGUF:Q4_0",
    "messages": [{"role": "user", "content": "Say hello in five words."}],
    "max_completion_tokens": 64,
    "compute": "npu",
    "enable_think": false,
    "stream": false
  }'
```

- Cap every chat call with `max_completion_tokens`; use `max_tokens` on raw completions.
- Inspect answer content and reasoning separately. Positive token usage does not make an empty answer usable.
- For direct LFM3-1.7B answers, try `enable_think: false` or the helper's closed-reasoning raw template. Keep output validation either way.
- Tag raw prompts before the first call and retry unusable output once. Return persistent errors as data.
- Plan for idle unloading and warm up with a capped request before the demo. See [Server lifecycle](runtimes.md#server-lifecycle-model-loading-and-idle-unloading).
- Do not bind to non-loopback addresses or interrupt shared servers without approval.

The standard-library [LFM client](../skills/iq9-geniex-lfm/scripts/lfm_client.py) provides these request guards. [Runtime reference](runtimes.md) describes endpoints and fields.

## 6. The decision layer

If using d1-2B, use Path A: a pinned local snapshot through Transformers, fp32 on the CPU. Load once and reuse it. Set offline/telemetry settings before imports and pass `local_files_only=True` to the loader.

The [decision-layer reference](decision-models.md) includes loading, typed questions, and calibration. The runnable [System One example](../examples/system-one-decision/README.md) shows state, image, and batch calls.

Do not route this reference d1 integration through GenieX decision endpoints. A d1 GGUF does not replace the Transformers snapshot. Zero generated output tokens are expected for d1, unlike an empty LFM-generation response.

## 7. Choosing a model

Choose based on task, format, precision, runtime/NPU support, and available memory. Any LFM3-family model is welcome; other LFM models are options too. LFM3-1.7B is the examples' default, not an eligibility rule.

Use a rule instead of d1 when a local threshold is enough. For vision or audio, stage the matching assets and use the modality's API. External sensors are optional; local images, recordings, or simulated events can serve as inputs.

Browse [LiquidAI's published models](../README.md#platform-and-models), then check [format, precision, and runtime compatibility](runtimes.md#model-format-and-precision). The example READMEs explain their reference choices; re-test your selected model on the board rather than transferring their results.

## 8. Building an always-on agent

The reference loop is **observe -> decide -> act -> explain -> log**.

1. **Generate only when needed.** Use a decision gate or rule before invoking the LFM for an explanation.
2. **Calibrate on the app's task.** Fit thresholds on labeled states and evaluate separately on held-out data.
3. **Constrain actions.** Schemas, allowlists, and write-action policy belong in code.
4. **Log each iteration.** Flush JSONL with the observation, decision, executed action, explanation, timing, and errors.
5. **Cap and validate output.** Empty answers, reasoning alone, and zero LFM tokens are failures even when the HTTP request succeeds.
6. **Keep the loop alive.** Input and explanation failures become logged data; avoid unhandled exceptions inside a monitor.
7. **Keep inference sequential.** Do not overlap d1 and the generator without evaluating a changed scheduling design on the app's workload.

Start from [Always-on agent](../examples/always-on-agent/README.md), or create an app using the [scaffold](../skills/iq9-always-on-agent/SKILL.md). Use bounded iterations and simulated inputs while adapting it.

## 9. Tool calling

Send OpenAI-style function schemas in `tools` to `/v1/chat/completions`. Validate returned call envelopes, IDs, names, and arguments before executing anything.

The model proposes; code decides. Apply a policy before every write or real-world action, and report executed actions from the app's own records rather than the model's prose. Keep the tool list short and the number of turns bounded. A token budget is not a guarantee that the model chooses a valid tool.

The [tool-calling example](../examples/tool-calling/README.md) includes schema, allowlist, policy, execution, and local guard checks.

## 10. Measuring performance

Choose an observation interval and token budget based on the app's workload. Include cold startup, warm requests, decision latency, loop time, memory, and error rate.

For server requests, use the [metrics collector](../skills/iq9-demo-prep/scripts/collect_metrics.sh). It separates generated-output TTFT from answer TTFT and labels streamed decode timing as an estimate. Do not count SSE chunks as tokens.

For a local GGUF benchmark, stage `geniex-bench` matching the runtime, then point it at the actual file:

```bash
D="$HOME/geniex-bench-linux-arm64-v0.10.0"
export LD_LIBRARY_PATH="$D/lib:$D/lib/llama_cpp:$D/lib/qairt"
"$D/bin/geniex-bench" --plugin llama_cpp --device npu \
  -m /absolute/path/to/model.gguf -r 5 -p 512 -n 128
```

This command selects five runs, a 512-token prefill, and 128 generated tokens. It does not time d1; time `system_one()` separately for the app's exact questions. Process RSS, peak process RSS, and device memory are different resources.

Put app results in the app's README with the board, runtime, model/precision, workload, sample count, and medians. Keep this shared reference focused on setup and APIs.

## 11. Running offline

Stage the chosen models, packages, UI assets, docs, and sample data before the cut. At runtime, load local snapshots/cache entries only; do not install packages, pull models, send telemetry, or fetch remote assets.

Rehearse cold startup and the core workflow with all uplinks disconnected. Get approval before cutting the network and use the board's local console; a cut over SSH may disconnect your session.

Full checklist: [Offline readiness](offline-readiness.md).

## 12. Troubleshooting

| Symptom | What to inspect | Next step |
|---|---|---|
| `geniex: command not found` | Installed CLI path and shell `PATH` | Use the existing install or follow approved setup; do not reinstall blindly |
| Missing NPU libraries | Driver packages and loader error | Install missing packages with approval; see section 3.2 |
| CDSP permission denied | Device permissions and `fastrpc` group | Correct group membership with approval, then log in again |
| Slow generator or no HTP0 output | Current server log, compute route, drivers, permissions | Diagnose NPU access without silently changing compute |
| Long or reasoning-only answer | Token cap, prompt template, answer/reasoning fields | Keep the cap, try direct-answer controls, and validate usable content |
| Empty answer or zero LFM tokens | Response body, prompt uniqueness, cap | Retry once with a fresh tag; log persistent failure before safely relaunching the owned server |
| d1 request sent to a server endpoint | Integration route | Use the local Path A API |
| Slower first or post-idle request | Weight loading and keepalive | Plan cold/warm startup and adjust keepalive for quiet gaps |
| Benchmark cannot find libraries | Archive layout and `LD_LIBRARY_PATH` | Set paths to the matching local benchmark libraries |
| No space left on device | Cache, snapshots, archives, duplicate copies | Ask the owner before removing unused files |
| Python import fails | Selected interpreter, venv, package versions | Inspect the environment before changing or recreating it |
| d1 loader requests code approval | Snapshot revision and loader options | Review local model code before enabling `trust_remote_code=True` |
