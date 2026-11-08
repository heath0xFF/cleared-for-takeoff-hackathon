# Judging and Demos

Use this rubric to plan the project and its demo. If the organizers' brief differs, follow the brief.

Runtime, SDK, programming language, and model-package choice do not earn points by themselves. Apply the same offline and evidence requirements to every route; score the resulting app against the criteria below.

## Scoring

| Weight | Criterion | What judges look for |
|---|---|---|
| 25% | **Edge-native value** | Why is this better, or only possible, on-device? |
| 20% | **Technical execution** | Reliability, integration quality, local operation |
| 20% | **Originality** | A distinct insight, not another generic chatbot |
| 15% | **Real-world usefulness** | A clear user, a real need, a plausible next step |
| 10% | **Performance / efficiency** | Latency, memory, endurance, resource awareness |
| 10% | **Demo quality** | A concise, clear offline demonstration |

## The first question

Every finalist gets this question: **"Why should this not simply be a cloud API call?"**

Prepare an answer that names a specific constraint. Examples: the network is unavailable, the data is sensitive, the reaction must happen in under a second, or the marginal cost has to stay flat at scale. Being on-device is not an answer by itself.

## Bonus awards

- **Fastest Agent** — speed of the end-to-end loop
- **Best Tiny Agent** — the best result for the smallest footprint

Include the app's timing and footprint in the demo. See [`runtimes.md`](runtimes.md) for `geniex-bench` and [`developer-guide.md` §10](developer-guide.md#10-measuring-performance).

## Demo format

- Two minutes per team, plus one judge question.
- The network is removed for the final demo. The core workflow must keep running offline.
- Show local inputs, decisions, executed actions, and errors from the app's log.
- Prepare a visible timer, local sample data, and a backup recording.

## What to measure and show

| Metric | How | Why it matters |
|---|---|---|
| Time-to-first-token | Benchmark or timed stream; distinguish generated reasoning from answer content | Responsiveness |
| Decode tokens/s | Benchmark or usage-based streamed estimate; do not count chunks as tokens | Generation efficiency |
| Peak process memory | `/usr/bin/time -v`; track system/device memory separately | Footprint |
| Decision-gate latency | Time the app's actual rule or optional d1 questions on the board | Fits the observation interval |
| End-to-end loop time | Timing in the app's flushed JSONL | Includes decision, action, and explanation work |
| Network-off run | Disconnect all uplinks and demonstrate the core workflow | Offline operation |
| Decision log | Local timestamps, decisions, executed actions, and errors | Explains what the app did |

Use the app's own workload and selected model/precision when collecting numbers. Keep the shared documentation as a reference; put project-specific results in the app's README.
