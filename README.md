# Type 3 IGM Drilled Shaft Calculator

Desktop application for drilled-shaft design in Type 3 / Category 3 intermediate geomaterials using the Method of Mayne & Harris.

## Architecture

- `app.py`: application entry point
- `gui/`: `tkinter` desktop interface, input parsing, result display, and event wiring
- `core/`: engineering calculations, validation, and three-branch curve generation
- `plotting/`: matplotlib plotting helper
- `tests/`: unit tests for capacities, validation, and curve behavior

## Formula Organization

The Mayne-Harris equations are centralized in `core/calculations.py`. The GUI only collects user inputs and presents outputs. The three-branched load-settlement curve is generated separately in `core/load_settlement.py`.

The beta-method cohesionless-soil app is implemented separately in `core/beta_calculations.py`, `core/beta_models.py`, `core/beta_validation.py`, and `gui/beta_window.py`. Its simple mode supports 1 to 6 soil layers. Each layer has a thickness, unit weight, and `N60`; side resistance is computed for each layer portion intersecting the shaft, while base resistance uses the layer at the shaft tip.

## Running

```bash
./type3/bin/python app.py
```

Beta-method cohesionless-soil version:

```bash
./type3/bin/python app_beta.py
```

## Tests

```bash
./type3/bin/python -m unittest discover -s tests -v
```
