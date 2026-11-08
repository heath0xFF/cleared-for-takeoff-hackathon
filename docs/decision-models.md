# Decision Layer - LiquidAI d1-2B

`LiquidAI/d1-2B` is a 1.92B-parameter decision model built on LFM3-VL-2B. Give it a state and named questions; it returns probabilities, categories, or ratings in one forward pass with **zero generated output tokens**. It is not a chat model.

Use d1 as an optional gate for triage, routing, severity, or visual questions. For simple thresholds or fast loops, a deterministic rule may be more appropriate. The generator can run only when the app needs an explanation or a tool proposal.

## What it is

| Item | Value |
|---|---|
| Base model | LFM3-VL-2B |
| Parameters | 1.92B |
| Context | 128,000 tokens |
| Input | Text, JSON, images, or a mix |
| Output | Typed answers, zero generated output tokens |
| API | `model.system_one(state, questions, media=None)`, `model.system_one_batch(...)` |
| License | LFM Open License v1.0; read the model's LICENSE |

See the [model card](https://huggingface.co/LiquidAI/d1-2B) for model details and the [developer guide](developer-guide.md#21-two-models-two-jobs) for the reference architecture.

## Question types

| `type` | Asks | `criteria` | Answer fields |
|---|---|---|---|
| `noul` | Yes or no | Optional `{"true": "...", "false": "..."}` | `noul`: probability of yes |
| `choice` | Choose one category | Map from category name to description | `choice`, `confidence`, `probabilities` |
| `score` | Rate on ordered levels | 2-10 descriptions, lowest first | `score`, `confidence`, `probabilities`, `legend` |

A score is the median level index, starting at zero. The response envelope contains `answers` and `usage`; `usage.output_tokens` is zero. Do not treat this as an LFM-generation failure.

## Running it on the IQ-9075

### Path A: transformers on the CPU

The reference d1 integration uses a local Transformers snapshot in fp32 on the CPU. It does not send decision requests to the GenieX server. ZETIC publishes a separate IQ9 d1 package and C++ decision API; see the [optional ZETIC route](../examples/zetic-iq9/README.md). That route is not board-verified here, and its package does not replace this route's snapshot or calibration.

- Create a Python environment with Transformers 5.19+, torch, matching torchvision, and Pillow. Reuse the board's torch installation.
- Stage the safetensors snapshot and its Python code at `~/models/d1-2B`, pinned to revision `10e7671d44e4`.
- A GGUF file is not a substitute for this snapshot.
- Review model code before allowing `trust_remote_code=True`. Ask before downloading a snapshot or changing its revision.
- Load once with `local_files_only=True`, keep offline settings enabled, and reuse the model.
- Keep the gate and the LFM sequential. Size the observation interval for the app's decision and generation work.

Setup details: [System One example](../examples/system-one-decision/README.md).

```python
import json
import os
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

import torch
from transformers import AutoModel

model_dir = Path.home() / "models" / "d1-2B"
model = AutoModel.from_pretrained(
    str(model_dir), trust_remote_code=True, local_files_only=True, dtype=torch.float32
).to("cpu").eval()

questions = {
    "alert": {"type": "noul", "instructions": "Does this state need a human alert now?"},
    "category": {
        "type": "choice",
        "instructions": "Which category fits best?",
        "criteria": {"thermal": "Heat problem", "normal": "No issue"},
    },
}
state = {"soc_temp_c": 74, "change_c_per_min": 13, "trend": "rising"}
with torch.inference_mode():
    result = model.system_one(json.dumps(state), questions)
answers = result["answers"]
```

For an image, pass a Pillow image through `media=[image]` alongside a state or `None`. Image assets can come from local files; a camera is not required. The runnable example also shows batch calls.

## Model files and disk

| Item | Approximate size | Local path |
|---|---:|---|
| d1-2B safetensors weights | 3.84 GB | `~/models/d1-2B` |

Stage the whole snapshot, not only the weights. Runtime memory is separate from disk size and depends on inputs, dtype, and batching.

## Designing state and questions

- Use descriptive keys and consistent schemas between calibration and production.
- Include derived signals such as the change, direction, and time since the last event.
- Ask only questions the app uses; each question adds input work.
- Keep the state, questions, model revision, and probability precision consistent through calibration and policy.

## Calibrating thresholds

Do not deploy a default threshold of 0.5 or copy one from another task.

1. Collect representative app states and probabilities.
2. Label the desired decision with JSON `true` or `false`.
3. Reserve separate held-out states, preferably from different events or time periods.
4. Fit a threshold on the calibration set and evaluate it on the held-out set without refitting.

From the repo root, for rows with stored probabilities:

```bash
python3 skills/iq9-d1-decision-gate/scripts/calibrate_threshold.py calibration.jsonl --eval held-out.jsonl
```

For rows that need scoring, run in the d1 environment with `--score`. For a scaffolded app, add `--questions-from apps/my-agent` to use that app's `questions.py`.

Inspect precision, recall, false positives, and missed alerts against the app's requirements. If the model cannot separate the cases, revise the inputs/questions or use a rule instead. Log the selected threshold, decisions, timings, errors, and actions in the app's JSONL.

## Safety and licensing

`trust_remote_code=True` executes Python from the snapshot. Review that code before loading it and keep the revision pin unchanged unless the board owner approves a new version.

The model's probability does not authorize an action. Validate typed answers, apply policy in code, and execute only allowlisted actions. Read the model's LICENSE before publishing or commercializing an app.
