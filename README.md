# Type 3 IGM Drilled Shaft Calculator

Draft desktop application for preliminary drilled-shaft design in Type 3 / Category 3 intermediate geomaterials using the local `AGENTS.md` and `mayne_harris_method.md` guidance.

## Architecture

- `app.py`: application entry point
- `gui/`: `tkinter` desktop interface, input parsing, result display, and event wiring
- `core/`: engineering calculations, validation, and three-branch curve generation
- `plotting/`: matplotlib plotting helper
- `tests/`: unit tests for capacities, validation, and curve behavior

## Formula Organization

The Mayne-Harris equations are centralized in `core/calculations.py`. The GUI only collects user inputs and presents outputs. The three-branched load-settlement curve is generated separately in `core/load_settlement.py`.

The following items are intentionally labeled as draft assumptions because the project notes flagged them as OCR-sensitive:

- the closed-form settlement parameter transcription used to compute `I`
- the Segment 2 base-settlement increment `Delta_wb`

Both are isolated in `core/calculations.py` so they can be replaced cleanly after verification against the retained FHWA source.

## Running

Use the local virtual environment in `type3/`:

```bash
./type3/bin/python app.py
```

## Tests

```bash
./type3/bin/python -m unittest discover -s tests -v
```

## Current Assumptions

- `tkinter` is used instead of PySide/PyQt because Qt bindings are not installed in the local environment.
- Effective stress below groundwater is approximated from a single unit weight unless direct effective stress overrides are entered.
- Results are intended for draft engineering review and code structure development, not final production design without source verification.
