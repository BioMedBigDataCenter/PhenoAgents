import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PhenoAssembler on a metadata table.")
    parser.add_argument("--input", required=True, help="Input table path: .xlsx, .csv, or .tsv.")
    parser.add_argument("--output", required=True, help="Output table path: .xlsx, .csv, or .tsv.")
    parser.add_argument(
        "--prompt-style",
        choices=["full", "baseline"],
        default="full",
        help="Agent configuration to use.",
    )
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--max-critics", type=int, default=1)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--sleep", type=float, default=0.0, help="Delay between rows in seconds.")
    parser.add_argument("--limit", type=int, default=None, help="Optional row limit for testing.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    from phenoassembler.main import run

    output = run(
        input_path=args.input,
        output_path=args.output,
        prompt_style=args.prompt_style,
        max_retries=args.max_retries,
        max_critics=args.max_critics,
        temperature=args.temperature,
        sleep_seconds=args.sleep,
        limit=args.limit,
    )
    print(f"Wrote {len(output)} rows to {args.output}")


if __name__ == "__main__":
    main()
