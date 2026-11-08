# ZETIC on the IQ-9075 (optional route)

ZETIC's [LFM3 IQ9 examples](https://github.com/zetic-ai/LFM3-zetic-apps/tree/main/iq9) provide a C++ SDK and CLI for Hexagon v73. Their published IQ9 examples use local packages for LFM3-Omni-2B generation, d1-2B text decisions, and d1-Omni-2B image/audio decisions. This is an alternative inference runtime; it does not use the GenieX HTTP server or the Transformers d1 environment.

⚠️ **Status:** this repository has not run the ZETIC packages on an IQ-9075. The upstream instructions and SDK headers were reviewed on 2026-11-08 at commit `35acef15824f4df435c36faf6439b2204a89c029`. The [model repository](https://huggingface.co/ZETIC-ai/LFM3) was gated at that time. Confirm access and SDK/model terms before distributing artifacts. No ZETIC latency, memory, NPU-offload, or network-off result is claimed here.

## Choose the smallest path that fits

| Need | Package in the upstream IQ9 examples |
|---|---|
| Text, image, or audio generation | `lfm3-omni-2b` |
| Typed decisions from text | `d1-2b` |
| Typed decisions from image or audio | `d1-omni-2b` |

The packages are not interchangeable with the GGUF in GenieX or the safetensors snapshot used by the reference Transformers example. Stage only the packages your project uses. Other LFM3-family models may be possible through the SDK, but verify their exact IQ9 package and modality support with ZETIC.

## Prepare while the network is available

Run these commands **on the IQ-9075**, not a laptop. First check the board and available disk:

```bash
uname -m                  # aarch64
bash skills/iq9-preflight/scripts/preflight.sh --profile board --json
df -h /
command -v g++
command -v make
```

If build tools or board drivers are missing, ask the board owner before installing or changing system packages. Then follow [ZETIC's IQ9 setup](https://github.com/zetic-ai/LFM3-zetic-apps/blob/main/iq9/README.md) to obtain its repository and the model packages you need. The upstream guide shows the Hugging Face access and download steps; do those **before** the network cut. Record the exact upstream commit and package revisions in your app's README. Do not put credentials in your app or log.

For the upstream repository cloned as `LFM3-zetic-apps` and its models placed under its `models/` directory:

```bash
cd LFM3-zetic-apps
make -C iq9 CXX=g++
ls iq9/out/lfm3_cli iq9/out/d1_example
ls models/qualcomm/*/v73/manifest.json
```

The wildcard may list only the packages you staged. Keep `iq9/sdk/lib/` alongside the built binaries. If another process is using the NPU, coordinate before stopping it; do not interrupt a shared GenieX server.

## Smoke check from this repository

The local smoke check does not download, install, or modify ZETIC assets. It requires the upstream directory and the LFM3-Omni-2B package. Use `--with-d1` only if you also staged d1-2B.

```bash
python3 examples/zetic-iq9/smoke.py --apps-dir /absolute/path/to/LFM3-zetic-apps --check-only
python3 examples/zetic-iq9/smoke.py --apps-dir /absolute/path/to/LFM3-zetic-apps
python3 examples/zetic-iq9/smoke.py --apps-dir /absolute/path/to/LFM3-zetic-apps --with-d1
```

The generation request is capped at 48 text tokens. The script checks for nonempty answer text and a timing line; the optional d1 call checks for selected answers. A passing smoke check confirms only those calls. To try other modalities, use the [upstream samples](https://github.com/zetic-ai/LFM3-zetic-apps/blob/main/iq9/README.md#more-generation-samples) and their local input files. The CLI expects 512 × 512 binary PPM images and WAV audio, with audio input limited to 30 seconds.

## Turn the example into an agent

The upstream CLI is a useful first check. For a persistent app, use the [ZETIC C++ SDK](https://github.com/zetic-ai/LFM3-zetic-apps/tree/main/iq9/sdk/include) so the model loads once and can be reused. `LLM::fromPath()` and `Decision::fromPath()` use local packages; set `GenerationConfig::max_tokens` for each generation request and check response status and text. Apply the app's own threshold, allowlist, and action policy to d1 results. Keep flushed JSONL records of observations, model outputs, actions, timings, and errors. Do not transfer thresholds or performance numbers from the reference GenieX/Transformers stack.

Before a demo, run the [network-off rehearsal](../../docs/offline-readiness.md#rehearsal-network-off-test) from a local console. Start the app from a stopped state, exercise its real core workflow, confirm the ZETIC SDK's device route using current board evidence, and record the exact runtime/package versions and measured results in the app's README. A model loading from a local path is necessary for offline operation but does not by itself prove the full app works offline.
