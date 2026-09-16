import argparse
import json
import sys
from typing import List

from . import extract_references


def _read_formulas(args: argparse.Namespace) -> List[str]:
    if args.formulas:
        return args.formulas
    # No formulas given on the command line: read one per line from stdin,
    # skipping blank lines so `cat sheet.txt | formularefs` works.
    return [line.strip() for line in sys.stdin if line.strip()]


def _render_human(formula: str, references) -> str:
    if not references:
        return f"{formula}\n  (no references found)"
    lines = [formula]
    for ref in references:
        kind = "range" if ref.is_range else "cell"
        lines.append(f"  {ref.text} [{kind}]")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="formularefs",
        description="List the cell and range references a spreadsheet formula depends on.",
    )
    parser.add_argument(
        "formulas",
        nargs="*",
        help="one or more formulas, e.g. '=SUM(A1:A10)+Sheet2!B1'. "
        "If omitted, formulas are read one per line from stdin.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON instead of the human-readable listing",
    )
    args = parser.parse_args(argv)

    formulas = _read_formulas(args)
    if not formulas:
        parser.error("no formulas given (pass them as arguments or pipe them on stdin)")

    parsed = [(formula, extract_references(formula)) for formula in formulas]

    if args.json:
        results = [
            {"formula": formula, "references": [r.to_dict() for r in references]}
            for formula, references in parsed
        ]
        print(json.dumps(results, indent=2))
    else:
        print("\n\n".join(_render_human(formula, references) for formula, references in parsed))

    return 0


if __name__ == "__main__":
    sys.exit(main())
