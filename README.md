# formularefs

A command line tool that reads a spreadsheet formula and tells you exactly
which cells and ranges it depends on.

## Why

If you've ever needed to rename a sheet, move a block of cells, or just
figure out what a 200-character formula actually touches before you change
it, you end up eyeballing the formula bar and hoping you didn't miss a
reference buried inside a nested `IF`. `formularefs` does that scan for you:
point it at a formula and it lists every cell and range reference it finds,
including ones qualified with a sheet name, and tells you whether each one
uses absolute (`$A$1`) or relative addressing.

It's a text scanner, not a formula engine — it does not evaluate anything
or understand what the formula computes. It only answers "what does this
formula read from?"

## Usage

```
$ formularefs "=SUM(Sheet1!A1:A10)+B1"
=SUM(Sheet1!A1:A10)+B1
  Sheet1!A1:A10 [range]
  B1 [cell]
```

Multiple formulas can be passed at once:

```
$ formularefs "=A1+B1" "=VLOOKUP(C1,'Lookup Table'!A:B,2,FALSE)"
```

Or piped in, one formula per line:

```
$ cat formulas.txt | formularefs
```

Pass `--json` for machine-readable output, e.g. to feed into another script
that builds a dependency graph across a workbook:

```
$ formularefs --json "=A1+\$B\$2"
[
  {
    "formula": "=A1+$B$2",
    "references": [
      {
        "text": "A1",
        "sheet": null,
        "start": "A1",
        "end": null,
        "is_range": false,
        "absolute": {
          "start_col": false,
          "start_row": false
        }
      },
      {
        "text": "$B$2",
        "sheet": null,
        "start": "$B$2",
        "end": null,
        "is_range": false,
        "absolute": {
          "start_col": true,
          "start_row": true
        }
      }
    ]
  }
]
```

## Installing

No third-party dependencies. Clone the repo and run it directly:

```
$ python -m formularefs "=A1+B1"
```

or install it locally so `formularefs` is on your `PATH`:

```
$ pip install .
```

## Limitations (for now)

- Doesn't validate that a column is within the real spreadsheet limit
  (`XFD`), so a formula containing something like `ZZZ1` will be reported
  as a reference even though no such column exists.
- Doesn't support R1C1-style references.
- Treats each formula independently; it won't tell you if two formulas in
  different cells reference each other in a cycle.

## License

MIT, see [LICENSE](LICENSE).
