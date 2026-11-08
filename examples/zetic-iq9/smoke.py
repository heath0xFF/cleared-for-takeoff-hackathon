#!/usr/bin/env python3
"""Check staged ZETIC IQ9 artifacts and run bounded local example calls."""

import argparse
import platform
import subprocess
import sys
from pathlib import Path


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def require_file(path: Path, executable: bool = False) -> None:
    if not path.is_file():
        raise ValueError(f"missing file: {path}")
    if executable and not path.stat().st_mode & 0o111:
        raise ValueError(f"not executable: {path}")


def run(command: list[str], cwd: Path, timeout: int) -> str:
    print(f"Running {Path(command[0]).name} with local files", flush=True)
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"{Path(command[0]).name} timed out after {timeout} s") from exc
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")
    if result.returncode:
        raise RuntimeError(f"{Path(command[0]).name} exited with status {result.returncode}")
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apps-dir", type=Path, required=True, help="local LFM3-zetic-apps checkout")
    parser.add_argument("--with-d1", action="store_true", help="also run the d1-2B text example")
    parser.add_argument("--check-only", action="store_true", help="check local files without running inference")
    parser.add_argument("--max-tokens", type=positive_int, default=48, help="generation cap (default: 48)")
    parser.add_argument("--timeout", type=positive_int, default=300, help="seconds per call (default: 300)")
    args = parser.parse_args()

    root = args.apps_dir.expanduser().resolve()
    generator = root / "iq9/out/lfm3_cli"
    generator_model = root / "models/qualcomm/lfm3-omni-2b/v73"
    checks = [
        (generator, True),
        (root / "iq9/sdk/lib/libzetic_mlange_hexagon.so", False),
        (root / "iq9/sdk/lib/libhexrt_v73_skel.so", False),
        (generator_model / "manifest.json", False),
    ]
    if args.with_d1:
        checks += [
            (root / "iq9/out/d1_example", True),
            (root / "models/qualcomm/d1-2b/v73/manifest.json", False),
            (root / "samples/d1_text/ticket.txt", False),
        ]
    try:
        for path, executable in checks:
            require_file(path, executable)
        if args.check_only:
            print("Local binaries, SDK libraries, and requested manifests are present. Inference was not run.")
            return 0
        if platform.machine() != "aarch64":
            raise ValueError("inference must run on the IQ-9075 (aarch64); use --check-only elsewhere")

        output = run(
            [str(generator), "--model", str(generator_model), "--max-tokens", str(args.max_tokens),
             "What is the capital of France?"],
            root,
            args.timeout,
        )
        answer = output.split("[TTFT ", 1)[0].strip()
        if "[TTFT " not in output or "paris" not in answer.casefold():
            raise RuntimeError("generation did not return the expected Paris answer and timing line")
        if args.with_d1:
            output = run(
                [str(root / "iq9/out/d1_example"), "--model", str(root / "models/qualcomm/d1-2b"),
                 "--mode", "ticket", "--text-file", str(root / "samples/d1_text/ticket.txt")],
                root,
                args.timeout,
            )
            if "Selected:" not in output or "decision " not in output:
                raise RuntimeError("d1 returned no selected answer or timing line")
    except (ValueError, RuntimeError) as exc:
        print(f"smoke check failed: {exc}", file=sys.stderr)
        return 1

    print("ZETIC IQ9 example smoke check passed. NPU offload and network-off operation still need separate verification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
