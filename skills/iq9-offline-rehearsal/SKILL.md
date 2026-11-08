---
name: iq9-offline-rehearsal
description: Get a Dragonwing IQ-9075 app ready for the network-off demo and rehearse it. Covers a static audit for repo-ID loads, URLs, CDN assets, telemetry, and install-time fetches; staging models, wheels, and archives while the network is up; the network-off run; and evidence for the judges. Use before the network is cut, at T-1, when the user says "offline", "network cut", "airplane mode", "rehearsal", or "will this work without internet".
compatibility: Audit script runs anywhere with Python 3. The rehearsal runs on the IQ-9075.
metadata:
  version: "0.2"
---

# Offline rehearsal

The event ends with the network removed. A project that only works online scores zero on the main constraint. The checklist and the common failures are in `docs/offline-readiness.md`. This skill is the procedure. [Prior reference checks](../../README.md#developer-notes) used local/offline model loading while the network stayed connected; they are **not a physical network-off rehearsal**.

## 1. Static audit (run on the app's code)

```bash
python3 skills/iq9-offline-rehearsal/scripts/offline_audit.py apps/<name>
```

| Finding | Fix |
|---|---|
| `hub-id` (error) | Load from a local path: the Transformers snapshot or ZETIC package, or a model name already in the GenieX cache |
| `pull` (error) | Move `geniex pull`, `pip install`, `npm install`, and `apt install` into a setup step that runs before the cut. Never at runtime |
| `cdn` (error) | Vendor the JS and CSS into the app, and serve them locally |
| `url` (warn) | Every non-localhost URL has to be optional, or gone. Check each one |
| `telemetry` (warn) | Disable it or remove it |
| `env` (info) | Add `export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` to the launch script |

This is a heuristic static check, not proof of offline operation. Inspect runtime imports/dependencies and each warning. Finding an offline environment variable in text does not prove it is active; enforce `local_files_only=True` for Transformers and offline/telemetry settings before imports. Step 3 tests the whole app.

## 2. Stage everything while the network is up

Inspect the selected runtime's cache or local model directories and `df -h /` first. **Ask before every `geniex pull` (including local imports), `fetch_d1.py`, ZETIC package download, installation/system change, or deletion**, regardless of size. Reuse local weights with an approved import rather than downloading again; never re-pull cached models. Run long staging jobs in a separate terminal and verify exit status.

- [ ] For GenieX, run `geniex list` and confirm every model is cached; run `geniex version` and confirm the reference v0.10.0. For ZETIC, check its complete local v73 packages, binaries, and SDK libraries with the [local smoke check](../../examples/zetic-iq9/README.md#smoke-check-from-this-repository).
- [ ] **If the app uses reference Transformers d1**, confirm `~/models/d1-2B/REVISION` reads `10e7671d44e4…`. For ZETIC d1, confirm its matching staged package instead. Use `preflight.sh --profile generator --model <cached-name:precision>` for GenieX without d1, or `--profile board` for ZETIC. Reference defaults are not mandatory models.
- [ ] If needed, with approval, download wheels for an offline reinstall: `~/.venvs/d1/bin/python -m pip download -r <app>/requirements.txt -d ~/wheels`, then test `pip install --no-index --find-links ~/wheels -r <app>/requirements.txt` in a scratch venv.
- [ ] Keep the selected runtime's matching recovery assets locally (for the reference route, the GenieX v0.10.0 archive and `install.sh`; for ZETIC, its SDK libraries and build sources).
- [ ] Put sample and recorded data for the demo on the board (in case a sensor fails).
- [ ] Stage this repo's docs and skills on the board. Back up files being replaced; do not use destructive sync to remove unrelated files.
- [ ] Stage only the app's needed models/assets. External sensors are optional and not supplied; keep local sample/recorded inputs for any hardware-dependent demo.

## 3. Network-off run (the real test)

**Get explicit permission before any network cut or reboot.** Over SSH this can cut your session. Prefer the user physically unplugging Ethernet and disabling Wi-Fi from the board's local console; inspect all active uplinks, including USB networking.

1. The user unplugs Ethernet and turns off Wi-Fi. Check: `curl -sS -m 5 https://huggingface.co` must fail.
2. Cold start: with approval, stop the owned generator and start the selected runtime and app normally. For GenieX, run `skills/iq9-geniex-lfm/scripts/serve.sh run` in a separate terminal. For ZETIC, launch the app with staged local packages. A reboot is optional and needs approval. Do not silently switch a foreground server to a detached restart.
3. Run the core loop end to end for at least 10 minutes, including at least one alert or action.
4. Collect evidence: the app's JSONL log and a screen or phone recording. The `collect_metrics.sh` helper measures GenieX; for ZETIC, record the app's own timings and footprint using its selected package and runtime.
5. Plug the network back in. Record anything that failed in the app's README, along with its fix.

Do not use a generic one-interface `ip link ... down` one-liner: it can leave another uplink active or fail to restore connectivity. A scripted cut requires an approved, board-specific interface list, a local console, and a tested restoration plan. A failed external `curl` is supporting evidence, not proof that every uplink is disconnected.

## 4. Recovery drill (T-1)

- If an already-cached, previously tested stack is useful, keep it as an optional rollback. Do not require participants to download a legacy model or delete their chosen models.
- A recorded decision log and a recorded video, in case the live demo fails.
- Know where the log lives, and have a one-line command ready to show its last entries.
- Know how to safely stop and relaunch the owned foreground server. The old zero-token failure was not reproduced in current reference checks; retain recovery for persistent failures, not as a guaranteed diagnosis.
