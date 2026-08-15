from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QC_RUNNER = ROOT / "agent" / "run_qc.py"
PROFILE_RUNNER = ROOT / "agent" / "run_profile.py"
DATASET_FILES = {
    "explicit": ROOT / "data" / "simulation_dataset" / "dataset_1_explicit.csv",
    "format_coding": ROOT / "data" / "simulation_dataset" / "dataset_2_format_coding.csv",
    "semantic_context": ROOT / "data" / "simulation_dataset" / "dataset_3_semantic_context.csv",
}
STEP_ORDER = {"qc": 0, "profile": 1, "plots": 2}


def run(command: list[str]) -> None:
    print("RUN:", " ".join(command))
    process = subprocess.run(command)
    if process.returncode != 0:
        raise SystemExit(process.returncode)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the PhenoCurator agent and statistical analysis"
    )
    parser.add_argument("--start-step", choices=STEP_ORDER, default="qc")
    parser.add_argument("--end-step", choices=STEP_ORDER, default="plots")
    parser.add_argument("--dataset", choices=[*DATASET_FILES, "nhanes", "custom"], required=True)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument(
        "--input-level",
        choices=["name_only", "basic_metadata", "enhanced_metadata"],
        required=True,
    )
    parser.add_argument("--prompt", choices=["prompt1", "prompt2"], required=True)
    parser.add_argument("--qc-result", type=Path)
    parser.add_argument("--profile-mode", choices=["raw", "candidate_filtered"], default="raw")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--api-url", default=os.getenv("PHENOCURATOR_API_URL", ""))
    parser.add_argument("--model", default=os.getenv("PHENOCURATOR_MODEL", ""))
    parser.add_argument("--rscript", default="Rscript")
    parser.add_argument("--resume", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if STEP_ORDER[args.start_step] > STEP_ORDER[args.end_step]:
        raise ValueError("start-step must not be later than end-step")
    input_path = args.input or DATASET_FILES.get(args.dataset)
    if input_path is None:
        raise ValueError("--input is required for nhanes or custom datasets")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    qc_result = args.qc_result or args.output_dir / "qc_result.csv"

    if args.start_step == "qc":
        command = [
            sys.executable,
            str(QC_RUNNER),
            "--dataset",
            args.dataset,
            "--input",
            str(input_path),
            "--input-level",
            args.input_level,
            "--prompt",
            args.prompt,
            "--output",
            str(qc_result),
            "--api-url",
            args.api_url,
            "--model",
            args.model,
        ]
        if args.metadata:
            command.extend(["--metadata", str(args.metadata)])
        if args.resume:
            command.append("--resume")
        run(command)

    if args.end_step == "qc":
        return
    if not qc_result.exists():
        raise FileNotFoundError(f"QC result not found: {qc_result}")

    profile_command = [
        sys.executable,
        str(PROFILE_RUNNER),
        "--input",
        str(input_path),
        "--qc-result",
        str(qc_result),
        "--profile-mode",
        args.profile_mode,
        "--output-dir",
        str(args.output_dir / "statistical_profile"),
        "--rscript",
        args.rscript,
    ]
    if STEP_ORDER[args.start_step] <= STEP_ORDER["profile"]:
        profile_command.append("--run-distribution")
    if args.end_step == "plots":
        profile_command.append("--run-plots")
    run(profile_command)


if __name__ == "__main__":
    main()
