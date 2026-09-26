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

    def expand_cells(self) -> List[str]:
        """Return every individual cell covered by this reference.

        For a single-cell reference this is just that cell. For a range,
        it walks the rectangle from top-left to bottom-right regardless of
        which corner the formula listed first (e.g. "B2:A1" still expands
        starting at A1).
        """
        prefix = _format_sheet_prefix(self.sheet)
        if not self.is_range:
            start_match = _CELL_PARTS_RE.match(self.start)
            col, row = start_match.group(1), start_match.group(2)
            return [f"{prefix}{col.upper()}{row}"]

        start_match = _CELL_PARTS_RE.match(self.start)
        end_match = _CELL_PARTS_RE.match(self.end)
        start_col = _col_to_num(start_match.group(1))
        start_row = int(start_match.group(2))
        end_col = _col_to_num(end_match.group(1))
        end_row = int(end_match.group(2))

        lo_col, hi_col = sorted((start_col, end_col))
        lo_row, hi_row = sorted((start_row, end_row))

        cells = []
        for row in range(lo_row, hi_row + 1):
            for col_num in range(lo_col, hi_col + 1):
                cells.append(f"{prefix}{_num_to_col(col_num)}{row}")
        return cells


def _strip_sheet_quotes(sheet: Optional[str]) -> Optional[str]:
    if sheet is None:
        return None
    name = sheet[:-1]  # drop trailing '!'
    if name.startswith("'") and name.endswith("'"):
        name = name[1:-1].replace("''", "'")
    return name


_BARE_SHEET_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")

# Splits a single cell token into its column letters and row number,
# ignoring any '$' absolute markers.
_CELL_PARTS_RE = re.compile(r"^\$?([A-Za-z]{1,3})\$?([0-9]+)$")


def _format_sheet_prefix(sheet: Optional[str]) -> str:
    if sheet is None:
        return ""
    if _BARE_SHEET_NAME_RE.match(sheet):
        return f"{sheet}!"
    return f"'{sheet.replace(chr(39), chr(39) * 2)}'!"


def _col_to_num(col: str) -> int:
    num = 0
    for ch in col.upper():
        num = num * 26 + (ord(ch) - ord("A") + 1)
    return num


def _num_to_col(num: int) -> str:
    letters = ""
    while num > 0:
        num, rem = divmod(num - 1, 26)
        letters = chr(rem + ord("A")) + letters
    return letters


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
