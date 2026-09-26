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


def _render_human(formula: str, references, expand_ranges: bool) -> str:
    if not references:
        return f"{formula}\n  (no references found)"
    lines = [formula]
    for ref in references:
        kind = "range" if ref.is_range else "cell"
        lines.append(f"  {ref.text} [{kind}]")
        if expand_ranges and ref.is_range:
            for cell in ref.expand_cells():
                lines.append(f"    {cell}")
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
    parser.add_argument(
        "--expand-ranges",
        action="store_true",
        help="also list every individual cell covered by each range reference",
    )
    args = parser.parse_args(argv)

    formulas = _read_formulas(args)
    if not formulas:
        parser.error("no formulas given (pass them as arguments or pipe them on stdin)")

    parsed = [(formula, extract_references(formula)) for formula in formulas]

    if args.json:
        results = []
        for formula, references in parsed:
            ref_dicts = []
            for ref in references:
                ref_dict = ref.to_dict()
                if args.expand_ranges and ref.is_range:
                    ref_dict["cells"] = ref.expand_cells()
                ref_dicts.append(ref_dict)
            results.append({"formula": formula, "references": ref_dicts})
        print(json.dumps(results, indent=2))
    else:
        print(
            "\n\n".join(
                _render_human(formula, references, args.expand_ranges)
                for formula, references in parsed
            )
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
