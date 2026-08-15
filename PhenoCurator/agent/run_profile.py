from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
R_DIR = ROOT / "statistical_analysis"
TYPE_GROUPS = {
    "Continuous variable": "continuous",
    "Discrete variable": "discrete",
    "Ordinal variable": "qualitative",
    "Nominal variable": "qualitative",
}


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs)
        except UnicodeDecodeError:
            continue
    raise UnicodeError(f"Cannot decode CSV: {path}")


def parse_json_list(value: Any) -> set[str]:
    if value is None or pd.isna(value):
        return set()
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return {str(value)}
    if not isinstance(parsed, list):
        return {str(parsed)}
    return {str(item) for item in parsed}


def prepare_inputs(
    matrix_path: Path,
    qc_path: Path,
    output_dir: Path,
    profile_mode: str,
) -> dict[str, Path]:
    matrix = read_csv(matrix_path, dtype=object, keep_default_na=False)
    qc = read_csv(qc_path, dtype=object, keep_default_na=False)
    id_column = matrix.columns[0]
    matrix[id_column] = matrix[id_column].astype(str)
    qc_key = "variable_key" if "variable_key" in qc.columns else "Term"
    qc[qc_key] = qc[qc_key].astype(str)
    if "status" in qc.columns:
        qc = qc.loc[qc["status"] == "success"]
    qc = qc.drop_duplicates(qc_key, keep="last")
    qc_index = qc.set_index(qc_key)

    grouped: dict[str, list[pd.Series]] = {name: [] for name in set(TYPE_GROUPS.values())}
    for _, row in matrix.iterrows():
        key = str(row[id_column])
        if key not in qc_index.index:
            continue
        qc_row = qc_index.loc[key]
        if isinstance(qc_row, pd.DataFrame):
            qc_row = qc_row.iloc[-1]
        group = TYPE_GROUPS.get(str(qc_row.get("variable_type", "")))
        if group is None:
            continue
        prepared = row.copy()
        if profile_mode == "candidate_filtered":
            remove = parse_json_list(qc_row.get("na_values_json"))
            remove.update(parse_json_list(qc_row.get("anomalous_values_json")))
            for column in matrix.columns[1:]:
                if str(prepared[column]) in remove:
                    prepared[column] = ""
        grouped[group].append(prepared)

    inputs_dir = output_dir / "profile_inputs" / profile_mode
    inputs_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for group, rows in grouped.items():
        if not rows:
            continue
        frame = pd.DataFrame(rows, columns=matrix.columns)
        path = inputs_dir / f"{group}_bigtable.csv"
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        paths[group] = path
    return paths


def run_rscript(
    executable: str,
    script: Path,
    arguments: list[Path | str],
    log_path: Path,
) -> None:
    command = [executable, str(script), *map(str, arguments)]
    process = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "COMMAND:\n"
        + " ".join(command)
        + "\n\nSTDOUT:\n"
        + (process.stdout or "")
        + "\n\nSTDERR:\n"
        + (process.stderr or ""),
        encoding="utf-8",
    )
    if process.returncode != 0:
        raise RuntimeError(f"R script failed: {script}. See {log_path}")


def run_profile(args: argparse.Namespace) -> None:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    fit_dir = output_dir / "distribution_fit" / args.profile_mode
    plot_dir = output_dir / "plots" / args.profile_mode
    log_dir = output_dir / "logs"
    for directory in (fit_dir, plot_dir, log_dir):
        directory.mkdir(parents=True, exist_ok=True)

    inputs = prepare_inputs(args.input, args.qc_result, output_dir, args.profile_mode)
    run_record = {
        "input": str(args.input.resolve()),
        "qc_result": str(args.qc_result.resolve()),
        "profile_mode": args.profile_mode,
        "prepared_inputs": {key: str(value) for key, value in inputs.items()},
        "run_distribution": args.run_distribution,
        "run_plots": args.run_plots,
    }
    (output_dir / "run_config.json").write_text(
        json.dumps(run_record, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    if args.run_distribution and "continuous" in inputs:
        run_rscript(
            args.rscript,
            R_DIR / "fit_continuous.R",
            [
                "--input",
                inputs["continuous"],
                "--output-dir",
                fit_dir,
                "--output-csv",
                fit_dir / "continuous_distribution_fit_summary.csv",
            ],
            log_dir / "fit_continuous.log",
        )
    if args.run_distribution and "discrete" in inputs:
        run_rscript(
            args.rscript,
            R_DIR / "fit_discrete.R",
            [
                "--input",
                inputs["discrete"],
                "--output-dir",
                fit_dir,
                "--output-csv",
                fit_dir / "discrete_distribution_fit_summary.csv",
            ],
            log_dir / "fit_discrete.log",
        )

    if args.run_plots:
        for group in ("continuous", "discrete", "qualitative"):
            if group not in inputs:
                continue
            run_rscript(
                args.rscript,
                R_DIR / f"plot_{group}.R",
                ["--input", inputs[group], "--output-dir", plot_dir / group],
                log_dir / f"plot_{group}.log",
            )

    print(f"Statistical profile written to: {output_dir}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PhenoCurator statistical profiling")
    parser.add_argument("--input", type=Path, required=True, help="Phenotype matrix CSV")
    parser.add_argument("--qc-result", type=Path, required=True, help="QC result CSV from run_qc.py")
    parser.add_argument("--profile-mode", choices=["raw", "candidate_filtered"], default="raw")
    parser.add_argument("--run-distribution", action="store_true")
    parser.add_argument("--run-plots", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--rscript", default="Rscript")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not args.run_distribution and not args.run_plots:
        parser.error("Specify --run-distribution, --run-plots, or both")
    run_profile(args)


if __name__ == "__main__":
    main()
