# beta_method.md

## Purpose

This document is the local engineering reference for implementing the **Beta** drilled-shaft method for **Cohesionless Soils** in the GUI application.
The reference source is Chapter 10 of https://www.fhwa.dot.gov/engineering/geotech/nhi18024.pdf (note however it is written in US customary units and our app is metric)
The intent is to give the implementation agent a clear, local source of truth for:

- required inputs
- governing equations
- calculation sequence
- units
- assumptions
- applicability limits
- outputs
- plotting logic for the **three-branched load–settlement curve**

This file should be read together with `AGENTS.md`.

---

## Design Context

The Beta method is intended for **granular / cohesionless soils**

The method is summarized by FHWA as applicable primarily to materials with:

- **SPT `N60` up to 50 blows per 0.3 m**
- caution advised for **`N60 > 50`**


---

## Engineering Outputs Required by the App

The app shall compute and display, at minimum:

- unit side resistance, `fmax`
- shaft resistance, `Qs`
- unit base resistance, `qmax`
- base resistance, `Qb`
- total axial resistance, `Qtotal = Qs + Qb`

The app shall also generate the **three-branched load–settlement curve**.

---

## Recommended Unit System

Use **consistent SI units** throughout.

### Preferred defaults

- length: `m`
- unit weight: `kN/m^3`
- stress / modulus: `kPa`
- axial resistance: `kN`
- settlement: `mm` for display, `m` internally if preferred
- shaft diameter: `m`
- socket length: `m`

### Pressure reference

- atmospheric pressure: `pa = 101 kPa`

Do not mix SI and US customary units in the same implementation.

---

## Applicability

Use this method only when the material is appropriately classified as a **granular / cohesionless soils**.

---

## Core Assumptions

The implementation should document these assumptions in the UI help text or documentation:

1. **Side resistance** is treated as a **drained friction problem**.
4. **Base resistance** is treated conservatively using an **SPT blow count correlation** beneath the shaft base.
5. The short-term socket response is represented by a **three-branched load–settlement model** based on the Randolph–Wroth style elastic solution as adapted by Mayne and Harris.
6. Overburden elastic shortening above the socket is **not automatically included** in the socket settlement equations and may need to be added separately if desired.

---

## Required Inputs

The app should support a simple mode only.

### Minimum inputs for simple mode

- `gamma` = unit weight of soil
- `z_top_socket` = depth to top of shaft
- `L` = shaft length
- `D` = shaft diameter
- `N60` = energy-corrected SPT blow count
- `z_gwt` = groundwater depth
- optional: `nu` = Poisson’s ratio, default `0.30`

### Derived depths

- `z_tip = z_top_socket + L`
- `z_mid = z_top_socket + L/2`

---

## Effective Stress Calculation

The method requires vertical **effective** stress.

### At mid-depth of socket

Use:

- `sigma_vo_eff_mid`

### At shaft tip

Use:

- `sigma_vo_eff_tip`

If not entered directly, compute from geometry, total unit weight, and groundwater.

### Suggested implementation

Use piecewise effective stress:

- above groundwater:  
  `sigma'_v = gamma * z`

- below groundwater:  
  `sigma'_v = gamma_moist * z_gwt + gamma_sub * (z - z_gwt)`

where:

- `gamma_sub = gamma_sat - gamma_w`

If the user enters only a single representative unit weight and groundwater depth, document the simplification clearly.

---

## Capacity Equations

### 1. Preconsolidation pressure and OCR

The FHWA summary states that the method first estimates the preconsolidation pressure from `N60`, then computes:

`OCR = sigma'_p / sigma'_vo`

where:

- `sigma'_p` = preconsolidation pressure
- `sigma'_vo` = vertical effective stress at the elevation of interest
- `pa = 101 kPa` = atmospheric pressure

`sigma'_p = 0.15 * N60 * pa` for gravelly soils
`sigma'_p = 0.47*(N60)**m*pa` for other soils. Use a default m=0.8, but this should be a user input. m=0.6 for clean quartzitic sand and 0.8 for silty sands to sandy silts.



For the codebase, isolate these as dedicated functions:

- `sigma_p_eff = estimate_preconsolidation_pressure(N60, pa, ...)`
- `OCR = sigma_p_eff / sigma_vo_eff`
- `phi_prime = estimate_friction_angle(N60, sigma_vo_eff, ...)`

Do not hardcode these correlations inside GUI callbacks.

---

### 2. At-rest earth pressure coefficient

Confirmed FHWA summary equation:

`K0 = (1 - sin(phi')) * OCR^(sin(phi')) <= Kp`
`Kp = tan^2(45+phi'/2)`

where:

`phi' = 27.5 + 9.2*log[(N1)60]` (degrees)

- `phi'` is in radians if implemented with standard math functions
`(N1)60 = N60*(pa/sigma'_vo)^0.5` This is the overburdern corrected blow count


---

### 3. Unit side resistance

Confirmed implemented equation:

`fmax = K0 * tan(phi') * sigma'_vo`


Use `sigma'_vo` at the elevation chosen for the side-resistance calculation.

### Recommended implementation choice

For a simple representative-layer app:

- use `sigma'_vo = sigma'_vo_mid`

---

### 4. Shaft resistance

For a single representative value of `fmax`:

`Qs = fmax * pi * D * L`

where:

- `D` = shaft diameter
- `L` = socket length


---

### 5. Unit base resistance

Confirmed FHWA summary equation:

`qmax = 57.5*N60 <=2873 kPa`

---

### 6. Base resistance

`Qb = qmax * (pi * D^2 / 4)`

---

### 7. Total resistance

`Qtotal = Qs + Qb`

---

## Settlement / Load–Settlement Model

The method uses a **three-branched** load–settlement curve.

### Branch meanings

#### Segment 1

Elastic loading before full side resistance is mobilized.

#### Segment 2

Side resistance remains capped while additional load mobilizes base resistance.

#### Segment 3

Continued settlement at essentially constant load equal to the maximum total resistance.

This is a simplified design-level representation.

---

## Settlement Equations

### 1. Settlement along Segment 1

Confirmed FHWA summary equation:

`wt = (Qt * I) / (EsL * D)`

where:

- `wt` = settlement at top of socket
- `Qt` = applied load at top of socket
- `I` = influence factor from the closed-form solution
- `EsL` = Young’s modulus of geomaterial along the sides of the socket at base level
- `D` = shaft diameter

---

### 2. Side modulus correlation

Confirmed FHWA summary equation:

`EsL = 22 * pa * N60^0.82`

with:

- `pa = 101 kPa`
- `N60` in blows per 0.3 m

### Notes

- If pressuremeter, DMT, or seismic stiffness data are available, those may be better than the correlation.
- The app should allow `EsL` override in advanced mode.

---

### 3. Influence factor `I`

Confirmed implemented equation:

`I = 4(1 + nu) * [ 1 + ( 8 * tanh(muL) * L ) / ( pi * lambda * (1 - nu) * xi * muL * D ) ] / [ 4 / ( (1 - nu) * xi ) + ( 4 * pi * (Esm / EsL) * tanh(muL) * L ) / ( zeta * muL * D ) ]`

### Parameter definitions

- `nu` = Poisson’s ratio of geomaterial; default about `0.30`
- `L` = socket length
- `Esm` = Young’s modulus at mid-depth of socket
- `EsL` = Young’s modulus along side at base level
- `D` = shaft diameter
- `xi = EsL / Eb`
- `Eb` = Young’s modulus beneath base

### FHWA guidance for these terms

- where the material stiffens with depth, use `Esm / EsL = 0.5` as a practical default
- for Piedmont residuum modeling, use approximately `Eb = 0.4 * EsL`, hence `xi = EsL / Eb = 2.5`

### Additional definitions from FHWA

`muL = 2 * sqrt(2 / (zeta * lambda)) * (L / D)`

with:

`zeta = ln( [0.25 + (2.5 * (Esm / EsL) * (1 - nu) - 0.25) * xi] * (2L / D) )`

and:

`lambda = 2 * (1 + nu) * Ec / EsL`

where:

- `Ec` = Young’s modulus of composite shaft section

The implemented defaults are:

- `Esm / EsL = 0.5`
- `Eb = 0.4 * EsL`
- `xi = EsL / Eb = 2.5`

---

## Segment Transition Equations

### 1. Maximum side resistance

Confirmed FHWA summary equation:

`Qs_max = fmax * (pi * D * L)`

This is the same as `Qs` in the simple capacity model.

---

### 2. Load at end of Segment 1

Confirmed implemented equation:

`Qt1 = Qs_max / [ 1 - I / ( xi * cosh(muL) * (1 - nu) * (1 + nu) ) ]`

This defines the point where full side resistance has mobilized.

In the current implementation, the raw closed-form value is then bounded to keep Segment 2 physically meaningful:

- `Qt1 >= Qs_max`
- `Qt1 <= Qs_max + 0.75 * Qb_max`
- `Qt1 < Qt_max = Qs_max + Qb_max`

### Settlement at end of Segment 1

Compute:

`wt1 = (Qt1 * I) / (EsL * D)`

---

### 3. Base load at end of Segment 1

Confirmed FHWA summary relation:

`Qb1 = Qt1 - Qs_max`

---

### 4. Load at end of Segment 2

Confirmed FHWA summary relation:

`Qt_max = Qs_max + Qb_max`

where:

- `Qb_max = qmax * (pi * D^2 / 4)`

---

### 5. Settlement increment across Segment 2

The implemented Segment 2 settlement increment is:

`wt2 = wt1 + Delta_wb`

where `Delta_wb` is the base-settlement increment due to the increase in base load from:

`Qb1 --> Qb_max`

with:

`Delta_wb = (Qt_max - Qt1) * (1 - nu) * (1 + nu) / (Eb * D)`

For this project, the code should contain:

- `Delta_wb = compute_base_settlement_increment(...)`
- `wt2 = wt1 + Delta_wb`

---

### 6. Segment 3

Segment 3 is a vertical line in the idealized load–settlement plot:

`Qt = Qt_max`

with settlement continuing beyond `wt2`.

### Recommended plotting rule

Since the branch is conceptual, the implemented plotting rule extends settlement from `wt2` to:

- `wt3_end = wt2 + max(branch3_extension_mm / 1000, 0.01 * D)` in meters

where `branch3_extension_mm` is an advanced plotting-only input.

This extension does **not** change capacity. It only controls the visible plot length.

---

## Recommended App Calculation Sequence

The implementation agent should follow this sequence exactly.

### Step 1

Collect inputs:

- geometry
- unit weight / groundwater
- `N60`
- optional advanced overrides

### Step 2

Compute:

- `z_tip`
- `z_mid`

### Step 3

Compute or accept:

- `sigma'_vo_mid`
- `sigma'_vo_tip`

### Step 4

Estimate or accept:

- `sigma'_p`
- `OCR`
- `phi'`

### Step 5

Compute or accept:

- `K0`

`K0 = (1 - sin(phi')) * OCR^(sin(phi'))`

### Step 6

Compute:

- `fmax`

`fmax = K0 * tan(delta) * sigma'_vo_mid`

with `delta = phi'` for the default case and `delta = 0.75 * phi'` for slurry construction.

### Step 7

Compute shaft resistance:

- `Qs`

`Qs = fmax * pi * D * L`

### Step 8

Compute:

- `qmax`

`qmax = min(57.5 * N60, 2873 kPa)`

### Step 9

Compute:

- `Qb`

`Qb = qmax * pi * D^2 / 4`

### Step 10

Compute:

- `Qtotal = Qs + Qb`

### Step 11

For settlement plotting, compute:

- `EsL`
- `Esm`
- `Eb`
- `Ec`
- `I`
- `Qt1`
- `wt1`
- `Qb1`
- `Qt_max`
- `wt2`

### Step 12

Build the three branches:

- Segment 1: from `(0, 0)` to `(wt1, Qt1)`
- Segment 2: from `(wt1, Qt1)` to `(wt2, Qt_max)`
- Segment 3: from `(wt2, Qt_max)` to `(wt3_end, Qt_max)`

---

## Plotting Requirements

The plot shall show:

- x-axis: settlement
- y-axis: axial load
- point at end of Segment 1
- point at end of Segment 2
- labels:
  - Segment 1
  - Segment 2
  - Segment 3
- optional callouts:
  - `Qt1`
  - `Qt_max`
  - `wt1`
  - `wt2`

### Plotting note

Segment 3 is idealized as a constant-load continuation and is likely conservative for many decomposed geomaterials.

---

## Variables and Definitions

### Geometry

- `D` = shaft diameter
- `L` = socket length
- `z_top_socket` = depth to top of socket
- `z_tip` = depth to base of socket
- `z_mid` = mid-depth of socket

### Stresses

- `sigma'_vo` = vertical effective stress
- `sigma'_p` = preconsolidation pressure
- `OCR` = overconsolidation ratio

### Strength / resistance

- `phi'` = effective friction angle
- `K0` = coefficient of earth pressure at rest
- `fmax` = ultimate unit side resistance
- `qmax` = ultimate unit base resistance

### Capacities

- `Qs` = shaft resistance
- `Qb` = base resistance
- `Qtotal` = total axial resistance

### Stiffness / settlement

- `EsL` = side modulus at base level
- `Esm` = modulus at mid-depth
- `Eb` = modulus beneath base
- `Ec` = composite shaft modulus
- `nu` = Poisson’s ratio
- `I` = influence factor
- `wt` = settlement at top of socket
- `wt1` = settlement at end of Segment 1
- `wt2` = settlement at end of Segment 2
- `Delta_wb` = base settlement increment during Segment 2

---

## Implementation Notes for the Agent

1. Keep all engineering equations in a dedicated calculation module.
2. Do not embed the formulas directly inside UI callbacks.
3. Allow expert overrides for correlated parameters.
4. Preserve unit consistency and label all units in the UI.
5. Prevent plotting before a successful calculation.
6. Show intermediate values so the user can review the computation.
7. Keep the code ready for later extension to layered integration.

---

## Validation Checks

The app should reject or warn on:

- nonpositive diameter
- nonpositive socket length
- nonpositive `N60`
- negative effective stress
- impossible groundwater geometry
- `N60` outside recommended range without warning
- missing advanced parameters when override mode is selected

### Warning logic

- If `N60 > 100`, show a caution message:  
  `"Mayne–Harris should be used with caution for N60 above 100."`

---

## Suggested Defaults

Unless the user overrides them:

- `nu = 0.30`
- `pa = 101 kPa`
- `Esm / EsL = 0.5`
- `Eb = 0.4 * EsL`
- `xi = 2.5`

These defaults should be visible in an advanced panel, not hidden.

---

## Verification Expectations

Before the app is treated as reliable, verify it against at least one worked example.

### Required checks

- hand-check `Qs`
- hand-check `Qb`
- hand-check `Qtotal`
- confirm branch breakpoints are ordered properly
- confirm segment 1 and 2 slopes are positive
- confirm segment 3 is horizontal in load
- confirm the plot reproduces the intended three-branched shape

---

## Important Caution About Source Transcription

The current local source of truth is the implemented version in `core/calculations.py`. If the retained FHWA scan is revisited later, compare it against the code carefully before changing any of the following:

1. the `phi'` correlation from `N60` and `sigma'_vo`
2. the closed-form settlement terms `zeta`, `muL`, and `I`
3. the Segment 1 transition equation for `Qt1`
4. the Segment 2 increment `Delta_wb`

Therefore:

- keep those formulas in one place in code
- preserve source comments
- verify them against the retained project reference before final release
- include unit tests and a worked example

Do not silently invent missing constants.

---

## References

Primary implementation basis:

1. O’Neill, Townsend, Hassan, Buller, and Chan.  
   **Load Transfer for Drilled Shafts in Intermediate Geomaterials**.  
   FHWA-RD-95-172, 1996.

2. FHWA.  
   **Drilled Shafts: Construction Procedures and Design Methods**.  
   FHWA-NHI-18-024, 2018.

3. Mayne and Harris.  
   **Axial Load-Displacement Behavior of Drilled Shaft Foundations in Piedmont Residuum**.  
   Referenced by FHWA as the source method.

---

## Final Instruction to the Implementation Agent

Implement this as an engineering calculator with transparent assumptions. Favor correctness, traceability, and modularity. If any source equation is uncertain due to scan quality, isolate it, label it clearly, and do not obscure the uncertainty.
