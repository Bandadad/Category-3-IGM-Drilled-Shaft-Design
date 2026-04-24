# Multi-Layer Beta Method Refactor Plan

## Purpose

Refactor `app_beta.py` and its supporting beta-method modules so the user can model up to 6 soil layers along the drilled shaft. Each layer will have its own thickness, unit weight, and corrected SPT blow count `N60`. The application will compute side resistance layer by layer, sum those layer side resistances into `Qs`, and compute base resistance `Qb` using only the final layer properties at the shaft tip.

This plan keeps the current application style and structure:

- `app_beta.py` remains a thin entry point.
- GUI behavior remains in `gui/beta_window.py`.
- Engineering equations stay in `core/beta_calculations.py`.
- Input and result dataclasses stay in `core/beta_models.py`.
- Validation stays in `core/beta_validation.py`.
- Plot generation remains separated in `core/beta_load_settlement.py` and `plotting/beta_chart.py`.

## Current State

The beta application currently assumes one representative soil layer:

- `BetaCalculationInput.gamma` is a single unit weight.
- `BetaCalculationInput.n60` is a single representative `N60`.
- `calculate_beta_capacity()` computes side resistance using one representative mid-depth effective stress and one `fmax`.
- `Qb` is computed from the same representative `N60`.
- The GUI simple mode exposes one `gamma` field and one `n60` field.

The requested change requires replacing the representative material inputs with a layer table while preserving existing advanced controls where practical.

## Target User Workflow

1. User selects the number of layers, from 1 to 6.
2. The GUI displays a table with one row per active layer.
3. For each layer, the user enters:
   - layer thickness, `H` in m
   - layer unit weight, `gamma` in kN/m^3
   - corrected SPT blow count, `N60`
4. User enters shaft geometry as before:
   - depth to top of shaft
   - shaft length
   - shaft diameter
   - groundwater depth
5. User clicks **Compute Capacity**.
6. The app computes:
   - effective stress through the layered profile
   - side friction for each layer segment intersecting the shaft
   - total side resistance `Qs = sum(Qs_i)`
   - base resistance using the last layer at the shaft tip
   - total capacity `Qtotal = Qs + Qb`
7. Results show total capacity and a layer-by-layer side friction breakdown.
8. The plot button remains disabled until a valid calculation exists.

## Modeling Decisions To Confirm

These assumptions should be explicit in the implementation and user-facing notes:

- Layer thicknesses are measured downward from existing grade.
- The sum of layer thicknesses must reach or exceed the shaft tip depth.
- Side resistance is computed only over the portion of each layer intersecting the shaft length, from `z_top_shaft` to `z_tip`.
- Effective vertical stress at each side-resistance segment is evaluated at that segment's midpoint.
- Base resistance uses the layer containing the shaft tip. If the tip falls exactly on a layer boundary, use the lower layer when available; otherwise use the last layer above the boundary.
- Advanced direct overrides such as `phi_prime_override_deg` and `k0_override` apply globally unless future work adds per-layer overrides.
- Settlement stiffness inputs remain global for now. The retained three-branch settlement model uses total `Qs`, `Qb`, shaft geometry, and global stiffness values.

## Data Model Changes

### Add Layer Input Model

Add a layer dataclass to `core/beta_models.py`:

```python
@dataclass(slots=True)
class BetaSoilLayer:
    thickness: float = 2.0
    gamma: float = 18.0
    n60: float = 25.0
```

### Update Main Input Model

Modify `BetaCalculationInput`:

- Add `layers: list[BetaSoilLayer]`.
- Keep `z_gwt`, `z_top_shaft`, `shaft_length`, `diameter`, `nu`, slurry flag, soil type, advanced overrides, atmospheric pressure, and plot controls.
- Retain `gamma` and `n60` only if backward compatibility is needed for tests or a default single-layer constructor. Prefer migrating callers to `layers`.

Recommended default:

```python
layers: list[BetaSoilLayer] = field(
    default_factory=lambda: [BetaSoilLayer(thickness=12.0, gamma=18.0, n60=25.0)]
)
```

### Add Layer Result Model

Add a per-layer result dataclass:

```python
@dataclass(slots=True)
class BetaLayerResult:
    index: int
    z_top: float
    z_bottom: float
    shaft_overlap_top: float
    shaft_overlap_bottom: float
    shaft_overlap_length: float
    gamma: float
    n60: float
    sigma_vo_eff_mid: float
    sigma_p_eff_mid: float
    ocr_mid: float
    n1_60_mid: float
    phi_prime_deg: float
    k0: float
    kp: float
    fmax: float
    qs: float
```

Extend `BetaCalculationResult` with:

- `layer_results: list[BetaLayerResult]`
- `tip_layer_index: int`
- `tip_layer_n60: float`
- `tip_layer_gamma: float`

Keep existing aggregate fields such as `qs`, `qb`, `qtotal`, `fmax`, `qmax`, and `phi_prime_deg` for display and plotting compatibility. For aggregate display, define:

- `fmax`: representative or maximum layer `fmax`; preferably expose as `max_fmax`.
- `phi_prime_deg`: tip layer friction angle or weighted average; document which is used.
- `sigma_vo_eff_mid`: weighted-average shaft-side effective stress or representative midpoint stress; document the choice.

## Calculation Refactor

### Layer Geometry Helpers

Add small pure functions in `core/beta_calculations.py`:

- `build_layer_depths(layers) -> list[tuple[z_top, z_bottom, layer]]`
- `find_layer_at_depth(layers_with_depths, depth) -> layer_info`
- `compute_layer_overlap(z_layer_top, z_layer_bottom, z_shaft_top, z_tip) -> tuple[overlap_top, overlap_bottom, overlap_length]`

These helpers keep the main capacity function readable and make tests straightforward.

### Layered Effective Stress

Replace the single-layer `compute_effective_stress(depth, groundwater_depth, gamma)` usage with a layered equivalent:

```python
def compute_layered_effective_stress(
    *,
    depth: float,
    groundwater_depth: float,
    layers: list[BetaSoilLayer],
) -> float:
    ...
```

Implementation outline:

- Integrate from grade to target depth.
- For each layer interval above `depth`, use that layer's `gamma`.
- If the interval is below groundwater, use submerged unit weight `gamma_sub = max(gamma - GAMMA_WATER, 1.0)`.
- If the interval crosses groundwater, split it into above-water and below-water subintervals.

Keep the existing `compute_effective_stress()` for single-layer compatibility if useful, but route the main multi-layer workflow through the layered function.

### Per-Layer Side Resistance

For each layer intersecting the shaft:

1. Compute overlap length:
   `L_i = overlap_bottom - overlap_top`
2. Compute midpoint of the overlap:
   `z_mid_i = 0.5 * (overlap_top + overlap_bottom)`
3. Compute effective stress:
   `sigma_vo_eff_mid_i = compute_layered_effective_stress(z_mid_i, z_gwt, layers)`
4. Compute preconsolidation pressure using that layer's `N60`.
5. Compute `OCR_i`.
6. Compute `phi'_i`, unless a global override is provided.
7. Compute `K0_i`, unless a global override is provided, capped by `Kp_i`.
8. Compute unit side resistance:
   `fmax_i = K0_i * tan(delta_i) * sigma_vo_eff_mid_i`
9. Compute side resistance:
   `Qs_i = fmax_i * pi * diameter * L_i`

Then:

```python
qs = sum(layer.qs for layer in layer_results)
```

### End Bearing From Tip Layer Only

Find the layer containing `z_tip`.

Use only that layer's `N60` for:

```python
qmax = min(57.5 * tip_layer.n60, QMAX_CAP_KPA)
qb = qmax * base_area(diameter)
```

This matches the requested behavior: end bearing is computed only from the final/tip layer, not averaged across the shaft.

### Settlement Model

Keep `compute_settlement_parameters()` unchanged initially. Pass:

- total `qs`
- tip-layer `qb`
- existing geometry and global stiffness values

For stiffness correlation `EsL = 22 pa N60^0.82`, use the tip layer `N60` or a weighted shaft average. Recommended initial choice:

- use weighted-average shaft-side `N60` for side-related stiffness `EsL`
- use tip-layer `N60` for base resistance `qmax`

Document this clearly because the settlement correlations may need engineering review later.

## Validation Refactor

Update `core/beta_validation.py` to validate:

- layer count is between 1 and 6
- every active layer has positive thickness
- every active layer has positive unit weight
- every active layer has positive `N60`
- sum of layer thicknesses is greater than or equal to `z_top_shaft + shaft_length`
- groundwater depth is non-negative
- shaft top depth and shaft length are valid
- advanced overrides remain physically reasonable

Add warnings for:

- any layer `N60 > 50`
- any layer `N60 > 100`
- shaft tip very close to a layer boundary
- layer profile extending far beyond the shaft tip, if useful

## GUI Refactor

### Simple Mode

Replace the single `gamma` and `n60` inputs with:

- a `ttk.Combobox` or `ttk.Spinbox` for number of layers, values `1` through `6`
- a layer entry table with columns:
  - `Layer`
  - `Thickness (m)`
  - `Unit weight, gamma (kN/m^3)`
  - `N60 (blows/0.3 m)`

When the selected layer count changes:

- show/enable rows up to the selected count
- hide/disable remaining rows
- preserve existing row values when reducing and then increasing layer count
- clear current results and disable the plot button because inputs changed

### Existing Inputs

Keep these simple mode fields:

- Poisson's ratio
- slurry construction
- depth to top of shaft
- shaft length
- shaft diameter
- groundwater depth

Remove or relocate the old single `gamma` and `n60` fields to avoid conflicting input sources.

### Defaults

For `Load Defaults`, populate one layer or a useful three-layer example. Recommended conservative default:

| Layer | Thickness (m) | gamma (kN/m^3) | N60 |
|---:|---:|---:|---:|
| 1 | 12.0 | 18.0 | 25 |

Set selected layer count to `1`.

### Results Display

Keep existing summary results:

- `Qs`
- `Qb`
- `Qdesign`
- `Qtotal`
- `qmax`
- settlement transition values

Add a layer breakdown area, either in the existing intermediate text box or a new `ttk.Treeview`:

| Layer | z top | z bottom | shaft overlap | sigma'v mid | N60 | phi' | K0 | fmax | Qs |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|

The first implementation can use the existing intermediate text box to reduce UI complexity. A `Treeview` can be added later if the text output becomes too dense.

## Test Plan

Add tests to `tests/test_beta_method.py` or a new `tests/test_beta_multilayer.py`.

Required tests:

- `compute_layered_effective_stress()` integrates multiple layers correctly above groundwater.
- `compute_layered_effective_stress()` splits intervals correctly across groundwater.
- layer overlap calculation handles:
  - shaft starting inside a layer
  - shaft ending inside a layer
  - shaft crossing multiple complete layers
- total `Qs` equals the sum of individual layer `Qs_i`.
- `Qb` uses only the tip layer `N60`.
- validation rejects more than 6 layers.
- validation rejects a layer profile that does not reach the shaft tip.
- validation rejects non-positive thickness, unit weight, and `N60`.
- settlement curve generation still works with the multi-layer aggregate result.

Recommended hand-check case:

- 2 layers, groundwater below tip to avoid submerged-weight complexity.
- Shaft top at 1 m, shaft length 4 m, diameter 1 m.
- Layer 1: thickness 3 m, gamma 18, N60 20.
- Layer 2: thickness 4 m, gamma 20, N60 40.
- Side resistance should have 2 m overlap in layer 1 and 2 m overlap in layer 2.
- Base resistance should use `N60 = 40`.

## Implementation Sequence

1. Add `BetaSoilLayer` and `BetaLayerResult` dataclasses.
2. Update `BetaCalculationInput` and `BetaCalculationResult`.
3. Add layered geometry and effective-stress helper functions.
4. Refactor `calculate_beta_capacity()` to loop over shaft-layer overlaps.
5. Update validation for layer count, layer values, and profile depth.
6. Update GUI input collection to build `layers`.
7. Replace simple mode `gamma` and `n60` fields with the layer-count selector and table.
8. Update default loading, clear behavior, and result rendering.
9. Add or update tests for the layered calculations.
10. Run the test suite and manually launch `app_beta.py` for a GUI smoke test.

## Compatibility Notes

The cleanest implementation is to migrate fully to `layers` and remove direct use of `inputs.gamma` and `inputs.n60` from the beta app. If backward compatibility is needed, provide a helper such as:

```python
def default_single_layer(gamma: float, n60: float, thickness: float) -> list[BetaSoilLayer]:
    return [BetaSoilLayer(thickness=thickness, gamma=gamma, n60=n60)]
```

Avoid keeping two independent input paths active in the GUI, because that can make calculations hard to validate.

## Documentation Updates

Update the following after implementation:

- `README.md`: explain multi-layer input behavior and max layer count.
- `beta_method.md`: add a short note that side resistance is integrated layer by layer and base resistance uses the tip layer.
- GUI assumptions text: state how layer boundaries, groundwater, and tip-layer bearing are handled.

## Open Engineering Questions

These do not block the initial refactor, but should be reviewed:

- Should `phi_prime_override_deg` and `k0_override` be global or per-layer?
- Should settlement stiffness correlations use weighted-average shaft `N60`, tip-layer `N60`, or user-provided overrides only?
- Should end bearing use the layer containing the tip or always the deepest layer entered? The requested behavior says "last layer"; for engineering consistency, this plan interprets that as the layer at the shaft tip, with validation requiring the layer profile to reach the tip.
- Should side resistance be computed using midpoint stress per layer overlap, or should each layer be internally subdivided for better stress integration?

