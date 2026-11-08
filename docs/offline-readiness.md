# Offline Readiness

The final demo runs with the network removed. Stage everything the app needs on the board and rehearse its normal startup and core workflow offline.

## Disk first

Before downloading or importing assets:

```bash
df -h /
geniex list  # if using GenieX
```

Inspect existing local model directories as well as the cache. A missing cache entry does not mean the weights are absent. Reuse local weights with an approved import where possible.

For approximate reference-stack staging, the LFM3-1.7B QAD-Q4_0 weights use about **1.05 GB**; the optional d1-2B Transformers snapshot uses about **3.84 GB**. For another model or precision, use its exact artifact's file list and inspect the local files rather than carrying over these estimates.

Budget for the full set of matching weights, model code, tokenizer, prompt template, and any modality assets (such as vision projectors or audio tokenizer/vocoder files). Also allow for environments, recovery wheels, runtime archives, UI assets, sample data, and extra copies made during local imports. Stage only what the app needs.

Weight-file size is not runtime RAM usage: host RAM and device buffers are separate budgets. See [Measuring performance](developer-guide.md#10-measuring-performance) for app-level timing and memory checks.

Ask before deleting files or running `geniex remove` or `geniex clean` on a shared board. Do not remove unrelated models or edit cache metadata to free space.

## Before the network goes down

### Software

- [ ] The chosen runtime is staged; the reference GenieX version is v0.10.0. For ZETIC, keep its built IQ9 binaries and matching SDK libraries locally.
- [ ] NPU driver packages and device permissions are set up for the generator.
- [ ] The app's language environment and other dependencies are installed or staged.
- [ ] Runtime installers, matching archives, and any recovery wheels are available locally if needed.
- [ ] UI JavaScript, CSS, fonts, and other assets are served locally rather than from a CDN.
- [ ] No installation or model download happens when the app starts.

For an offline Python reinstall, stage wheels for the app's requirements and try `pip install --no-index --find-links <wheel-directory>` in a scratch environment before relying on it. Some packages need additional runtime assets; stage those too. Do not replace a working environment unnecessarily.

### Models

- [ ] Every generator model used by the app is available locally: registered in the GenieX cache or present as a complete ZETIC package for the chosen route.
- [ ] Its matching tokenizer, prompt template, projector, and any other required modality assets are present.
- [ ] If using the reference Transformers d1 route, the full pinned snapshot is at `~/models/d1-2B`; its `REVISION` matches `10e7671d44e4`. If using ZETIC, stage its complete matching d1 package instead.
- [ ] Model code has been reviewed before `trust_remote_code=True` is used.
- [ ] Model licenses have been read.

Stage only what this app needs. LFM3-1.7B and d1-2B are reference defaults, not mandatory models.

### Data and docs

- [ ] The repo's docs, examples, and skills are available on the board.
- [ ] Local sample inputs cover the demo workflow.
- [ ] If using a decision threshold, calibration and held-out data are available locally.
- [ ] Any brought sensors have local drivers and a sample-data fallback. External sensors are optional and not provided.

Back up board files being replaced when copying updates. Avoid destructive sync that removes unrelated files.

## Code rules

- **Local model loads:** Transformers loads a snapshot directory with `local_files_only=True`; GenieX requests use already-registered cached IDs; ZETIC apps use staged packages through `fromPath()`.
- **Offline settings:** if using Transformers, set `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, and `HF_HUB_DISABLE_TELEMETRY=1` before imports.
- **No external runtime dependencies:** no downloads, package installs, telemetry, cloud services, or remote UI assets in the core workflow. Loopback calls to the local inference server are allowed.
- **Bounded calls:** cap LFM requests, validate output, and log errors without crashing the monitor loop.

The [static audit](../skills/iq9-offline-rehearsal/scripts/offline_audit.py) helps locate likely network dependencies:

```bash
python3 skills/iq9-offline-rehearsal/scripts/offline_audit.py apps/my-agent
```

Review each finding and the dependencies it cannot inspect. A static scan is not a substitute for running the app with its uplinks disconnected.

## Rehearsal: network-off test

Get explicit approval before a network cut or reboot. Use the board's local console: disconnecting networking over SSH can also disconnect your control session.

1. Disconnect Ethernet, disable Wi-Fi, and check for other uplinks, including USB networking. An external `curl` failure alone does not establish that all links are down.
2. Start the chosen runtime from a stopped state, then launch the app using its normal command. A reboot is optional, not required.
3. Send a capped request and inspect current board evidence for the chosen runtime's NPU route. For GenieX, inspect the server's device/offload log for `HTP0`. For ZETIC, confirm its actual device route rather than inferring offload from the model name or CLI timing.
4. Run the core workflow for at least 10 minutes, including an event that triggers an explanation or allowlisted action. Exercise local UI assets and input handling too.
5. Inspect the app's flushed JSONL for decisions, executed actions, usable explanations, and errors. Check responsiveness and memory for the intended workload.
6. Restore networking from the local console when the rehearsal is complete.

Do not use a generic one-interface network-cut script. A scripted cut needs an approved interface list and a restoration plan.

## Recovery drill

- Keep local sample data, a recorded demo, and a copy of the decision log.
- Know the normal launch command and where errors are logged.
- Know how to stop and relaunch the chosen runtime without interrupting another team's work.
- An already-cached alternative model can be an optional fallback; do not download a second stack just for this checklist.

## Common failures

| Failure | What to inspect | Next step |
|---|---|---|
| Online startup works but offline startup fails | Model paths, install steps, remote assets, dependency network calls | Stage missing assets and remove runtime fetches |
| Offline reinstall fails | Missing wheels or package-specific runtime files | Stage and exercise recovery before the cut |
| Generator is slow or device output is missing | Current log, compute configuration, drivers, permissions | Diagnose NPU access; do not silently switch to CPU |
| No space left on device | Cache, local snapshots, archives, duplicate copies | Ask the owner before removing unused files |
| Server request fails | Listener, model ID, response body, current server log | Correct configuration or safely relaunch the owned server |
| Empty LFM answer or zero completion tokens | Answer/reasoning fields, cap, prompt uniqueness | Retry once with a fresh tag; log persistent failure |
