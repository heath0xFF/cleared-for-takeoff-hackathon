# Runtimes and Tooling on the IQ-9075

The reference generator uses **GenieX CLI v0.10.0** with a cached LFM GGUF. The optional reference d1-2B gate uses **Transformers on the CPU (Path A)** and does not call the GenieX server. [ZETIC's IQ9 SDK](../examples/zetic-iq9/README.md) is a separate, currently unverified route for locally staged LFM3 and d1 packages.

If using GenieX, use `geniex version` and `geniex --help` to inspect the installed runtime. Do not reinstall or change versions unnecessarily, especially between rehearsal and the demo.

## Runtimes

| Runtime | Model format | Compute routes | Use in this repository |
|---|---|---|---|
| `llama_cpp` through GenieX | GGUF and associated model assets | NPU, GPU, CPU, hybrid, depending on model support | Reference LFM generator |
| `qairt` | Qualcomm AI Hub bundles | NPU | Alternative deployment format; conversion is outside this guide |
| Transformers | Local safetensors snapshot and model code | CPU for d1 Path A | Optional decision gate |
| ZETIC IQ9 SDK | ZETIC v73 model packages and bundled C++ library | Hexagon v73 per upstream IQ9 guide; verify on the board | Optional LFM3-Omni/d1 route; not board-verified here |

The [ZETIC guide](../examples/zetic-iq9/README.md) covers its artifact staging and smoke check. Its C++ API is not the GenieX OpenAI-compatible HTTP endpoint. Do not apply GenieX model IDs, request fields, or performance results to ZETIC. Keep the two runtimes' packages and version records separate.

## Model format and precision

Choose the model, input modality, file format, precision, and compute route together. A familiar model name or smaller weight file does not establish runtime or NPU compatibility. Check the chosen artifact against the installed runtime's documentation and test it on the IQ-9075; the reference configuration's results do not verify other checkpoints or precisions.

- The reference LFM3-1.7B **QAD-Q4_0** build is registered as `LiquidAI/LFM3-1.7B-GGUF:Q4_0` in GenieX. Other Q4 formats are not interchangeable with this build.
- Match weights, tokenizer, prompt template, and any projector or other modality assets to the selected model. Vision and audio need their own supported request handling, not just a different model ID.
- The helper's raw `sentence()` template targets the reference LFM3 format. Re-test templates, reasoning controls, usable answers, and tool-call behavior when changing models.
- Record the exact artifact, revision, precision, and runtime in the app's configuration so it can be reproduced offline.

The optional d1 Path A uses a pinned local Transformers snapshot, not a GGUF. See [Decision layer](decision-models.md) for loading and calibration, and [Offline readiness](offline-readiness.md#disk-first) for asset staging and disk budgeting.

## CLI

| Command | Purpose | Notes |
|---|---|---|
| `geniex --help`, `geniex version` | Inspect CLI options and version | Use the installed version's help for flags |
| `geniex config get chipset` | Inspect board configuration | Reference target: IQ-9075 |
| `geniex list` | List registered cached models | Check before proposing a download |
| `geniex pull <name>:<precision>` | Download and register model assets | Setup only; obtain approval first |
| `geniex pull <name>:<precision> --local-path <directory>` | Import existing local assets into the cache | Copies files; obtain approval and check disk space |
| `geniex model set-type <model> llm\|vlm` | Set model modality | Use the matching assets and client for vision models |
| `geniex infer <model> --compute npu` | Interactive exploration | Use capped HTTP requests for scripted calls |
| `geniex serve --compute npu --keepalive 1800 --log info` | Run an OpenAI-compatible server | Reference address: `127.0.0.1:18181`; no model downloads |
| `geniex remove <model>[:<precision>]` | Delete cached assets | Destructive; ask the board owner first |
| `geniex clean` | Delete all cached models | Destructive; not a routine troubleshooting step |

## Local server

Run a foreground server in a separate terminal. From the repo root:

```bash
bash skills/iq9-geniex-lfm/scripts/serve.sh run
```

Keep the server visible and use another terminal for requests and diagnostics. Do not bind to a non-loopback address without approval.

The helper defaults to NPU compute, a 1800-second keepalive, and `./geniex-serve.log`. In another terminal, `serve.sh status` reports the listener, model IDs, and device-log excerpt. Stop only a server you can safely interrupt.

## Server endpoints

| Endpoint | Purpose |
|---|---|
| `GET /v1/models` | List registered model IDs with precision suffixes |
| `POST /v1/chat/completions` | Chat messages and native `tools` requests |
| `POST /v1/completions` | Raw text prompts using the selected model's template |

The reference d1 integration uses `model.system_one()` locally, not `/v1/systemone` or `/v1/decisions`. See [Decision layer](decision-models.md).

### Request fields

| Field | Use |
|---|---|
| `model` | Already-registered cache ID, such as `LiquidAI/LFM3-1.7B-GGUF:Q4_0` |
| `messages` | Chat message list for `/v1/chat/completions` |
| `prompt` | Model-specific raw prompt for `/v1/completions` |
| `max_completion_tokens` | Required output budget for chat calls |
| `max_tokens` | Required output budget for raw completions |
| `compute` | `npu` for the reference generator |
| `stream` | `false` for a single JSON response, `true` for SSE |
| `stream_options.include_usage` | Request token usage in the streamed response |
| `enable_think` | Try `false` for direct LFM3-1.7B chat answers |
| `tools` | OpenAI-style function schemas for tool requests |

Set the endpoint's token-budget field explicitly. Stop sequences or a prompt asking for brevity are not substitutes for a cap.

LFM3-1.7B reasons by default. For a direct answer, try chat with `enable_think: false` or the helper's raw `sentence()` template with its reasoning block already closed. Always inspect the returned answer; neither method guarantees useful content. Other models may require different templates or reasoning controls.

<a id="known-gap-zero-token-responses-on-v080"></a>

## Handling unusable output

- Reject zero or missing completion tokens for LFM generation.
- For text requests, reject empty `content`, including reasoning-only output with positive usage.
- For tools, require valid call envelopes, parse argument JSON, and validate schemas, allowlists, and policy before execution. A valid tool call need not include accompanying text.
- Return errors as data and log them. Retry unusable output once with a fresh request tag.
- Make raw prompts unique before the first request, not only on retry. Include an event ID or use `lfm_client.py`.
- For persistent server failures, inspect the error and current log before safely relaunching the owned server. Do not automatically interrupt shared jobs.

The standard-library [LFM client](../skills/iq9-geniex-lfm/scripts/lfm_client.py) implements caps, output checks, prompt tags, and one retry. Argument schemas and action policy remain the app's responsibility.

## Server lifecycle: model loading and idle unloading

The first request loads weights. After an idle period, the model may unload and the next request must reload it. The default keepalive is 300 seconds; choose a timeout that covers the demo's quiet gaps:

```bash
geniex serve --compute npu --keepalive 1800 --log info
# Alternative configuration:
GENIEX_KEEPALIVE=1800 geniex serve --compute npu --log info
```

Send a capped warm-up before the demo and check its answer. Plan the observation interval and user experience around the chosen model's cold and warm request times rather than assuming a fixed reload penalty.

<a id="known-gap-server-cpu-decode"></a>
<a id="known-gap-npu-decode-speed"></a>

## Compute and memory

Use NPU compute for the reference generator. After a capped request, inspect the current server's device/offload log for `Using 1 device(s): HTP0`. If device output is missing, inspect logs, drivers, permissions, and configuration before concluding which compute route is active.

The optional d1 gate deliberately runs on the CPU. Keep it sequential with LFM generation. Compare alternative scheduling or compute routes on the app's workload before changing this policy.

Process RSS, peak process RSS, system memory, and device memory describe different resources. Do not use one as a substitute for the others.

## Benchmarking

Use `geniex-bench` for GGUF prefill and decode timing; match the benchmark version to the runtime. Keep its archive and libraries on the board before the network cut. The [developer guide](developer-guide.md#10-measuring-performance) includes a local-file command.

The [metrics collector](../skills/iq9-demo-prep/scripts/collect_metrics.sh) collects capped server requests and app-log timing. It separates first generated output from first answer content. Its streamed decode rate is an estimate: SSE chunks can bundle tokens. Missing server usage must not be replaced with chunk counts.

## Pitfalls

- **Downloading unnecessarily:** inspect `geniex list`, local weight directories, and disk space first. Import existing assets with approval; never pull models during app runtime.
- **Deleting to troubleshoot:** do not use `geniex clean` or edit cache metadata as a first response to an error. Ask before removing assets and back up any files being replaced.
- **Mistaking verbosity for slow inference:** examine token usage, reasoning, and answer content alongside request time.
- **Installing at runtime:** stage dependencies and archives beforehand. No `pip install`, `geniex pull`, telemetry, or remote UI assets in the running app.

## Python SDK

The examples use the OpenAI-compatible HTTP server and Python's standard library. If you choose GenieX's Python SDK, follow its version-specific setup instructions and stage all of its dependencies before the network cut. SDK installation and HTTP inference are separate integration paths.
