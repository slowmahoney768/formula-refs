"""Parse spreadsheet formulas and extract the cell/range references they depend on."""

import re
from dataclasses import dataclass
from typing import List, Optional

# A single cell token, e.g. A1, $A1, A$1, $A$1.
_CELL = r"\$?[A-Za-z]{1,3}\$?[0-9]+"

# A sheet prefix is either a quoted name (allows spaces) or a bare
# identifier, always followed by '!'. e.g. Sheet1!A1 or 'My Sheet'!A1
_SHEET = r"(?:'[^']+'|[A-Za-z_][A-Za-z0-9_.]*)!"

# The lookbehind/lookahead pair keeps this from matching inside a longer
# identifier (so "MyVar1" isn't mistaken for cell "Var1"), and the final
# negative lookahead for "(" excludes function names that happen to look
# like a cell reference, such as LOG10( or ATAN2(.
_REFERENCE_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    rf"(?:(?P<sheet>{_SHEET}))?"
    rf"(?P<start>{_CELL})"
    rf"(?::(?P<end>{_CELL}))?"
    r"(?![A-Za-z0-9])(?!\s*\()"
)


@dataclass
class Reference:
    text: str
    sheet: Optional[str]
    start: str
    end: Optional[str]

    @property
    def is_range(self) -> bool:
        return self.end is not None

    def _absolute(self, cell: str):
        # A cell like "$A$1" has two possible '$' markers: one for the
        # column, one for the row. Report each independently.
        col_absolute = cell.startswith("$")
        row_absolute = "$" in cell[1:]
        return col_absolute, row_absolute

    def to_dict(self) -> dict:
        start_col_abs, start_row_abs = self._absolute(self.start)
        result = {
            "text": self.text,
            "sheet": self.sheet,
            "start": self.start,
            "end": self.end,
            "is_range": self.is_range,
            "absolute": {
                "start_col": start_col_abs,
                "start_row": start_row_abs,
            },
        }
        if self.end is not None:
            end_col_abs, end_row_abs = self._absolute(self.end)
            result["absolute"]["end_col"] = end_col_abs
            result["absolute"]["end_row"] = end_row_abs
        return result


def _strip_sheet_quotes(sheet: Optional[str]) -> Optional[str]:
    if sheet is None:
        return None
    name = sheet[:-1]  # drop trailing '!'
    if name.startswith("'") and name.endswith("'"):
        name = name[1:-1]
    return name


def extract_references(formula: str) -> List[Reference]:
    """Return every cell/range reference found in a formula, in order.

    This is a text-level scan, not a full formula parser: it does not
    evaluate the formula or understand operator precedence, it just finds
    tokens that look like cell references while skipping function names.
    """
    references = []
    for match in _REFERENCE_RE.finditer(formula):
        references.append(
            Reference(
                text=match.group(0),
                sheet=_strip_sheet_quotes(match.group("sheet")),
                start=match.group("start"),
                end=match.group("end"),
            )
        )
    return references
