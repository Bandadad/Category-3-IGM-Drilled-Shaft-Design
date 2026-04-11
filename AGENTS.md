# AGENTS.md

## Purpose

This project is a GUI application for preliminary drilled-shaft design in **Type 3 Intermediate Geomaterials** using the **Mayne and Harris** method as summarized by FHWA. The app allows a user to enter material and shaft properties, computes:

- **Total axial capacity**
- **Shaft resistance, Qs**
- **Base resistance, Qb**

and provides a button to generate the **three-branched load–settlement curve**.

This file gives instructions to an AI coding agent working on the app.

---

## Primary Goal

Build a desktop-style GUI application that is clear, engineering-oriented, and easy to validate. The user should be able to:

1. Enter input parameters
2. Click a button to compute results
3. View:
   - `Qs`
   - `Qb`
   - `Qtotal = Qs + Qb`
4. Click a second button to plot the **three-branched load–settlement curve**

The application should prioritize:

- transparency of assumptions
- traceable calculations
- unit consistency
- maintainable code
- engineering clarity over flashy UI

Review the gui style in /home/mpegnam/Projects/Cohesive-IGM-Rock-Socket-Design
This GUI should be visually similar.

---

## Scope

### In scope
- GUI form for user inputs
- Numerical implementation of Mayne–Harris calculations
- Numerical generation of the three-branched load–settlement response
- Plot display inside the app, or in a separate plot window
- Basic validation and error messages
- Ability to inspect intermediate quantities

### Out of scope
- Cloud deployment
- Multi-user storage
- Database integration
- Highly advanced geotechnical calibration workflows
- Automatic parsing of boring logs
- Design-code resistance factors unless specifically requested

---

## Engineering Model Expectations

The app should implement the Mayne–Harris style workflow for **Type 3 / Category 3 IGM** using user-provided inputs such as:

- unit weight
- effective overburden stress inputs or enough data to compute them
- groundwater depth
- corrected SPT blow count, `N60`
- shaft diameter
- shaft length / socket length
- depth to shaft tip
- atmospheric pressure if exposed as an advanced input
- optional stiffness inputs if the user wants to override correlations

The application should calculate, at minimum:

- vertical effective stress, `σ'vo`
- estimated friction angle, `φ'` if required by the chosen implementation
- `K0`
- unit shaft resistance, `fmax`
- `Qs`
- operational undrained strength below base, `su`
- unit base resistance, `qmax`
- `Qb`
- `Qtotal = Qs + Qb`

The app should also compute enough parameters to support plotting of the **three-branched load–settlement curve**.

---

## Input Philosophy

The app should support two modes where practical:

### 1. Simple mode
A streamlined interface for a single-layer or representative-layer calculation.

Typical user inputs:
- Unit weight
- Groundwater depth
- Depth to top of socket
- Socket length
- Shaft diameter
- `N60`
- Optional toggle to enter `σ'vo` directly instead of computing it

### 2. Advanced mode
A more explicit engineering-input mode with optional overrides.

Possible additional inputs:
- direct `σ'vo`
- direct `φ'`
- direct `K0`
- direct side modulus / stiffness
- direct `su`
- atmospheric pressure
- load-settlement model parameters
- discretization controls for plotting

The agent should design the code so that simple mode uses defaults/correlations, while advanced mode allows expert override.

---

## UI Requirements

The UI should be professional and minimal. Do not overdesign it.

### Recommended layout

#### Left panel or top section: Inputs
Group fields under headings such as:
- Material Properties
- Geometry
- Groundwater / Stress Conditions
- Advanced Parameters

#### Right panel or bottom section: Results
Display:
- `Qs`
- `Qb`
- `Qtotal`
- selected intermediate values such as:
  - `σ'vo`
  - `K0`
  - `φ'`
  - `fmax`
  - `qmax`

#### Action buttons
Include at least:
- **Compute Capacity**
- **Plot Load–Settlement Curve**
- **Clear Inputs**

Optional:
- **Export Results**
- **Show Intermediate Calculations**

### Plot area
Either:
- embed the plot in the app, or
- open a dedicated plot window/dialog

The plot must clearly show:
- settlement on x-axis
- load on y-axis
- the three branches
- branch transition points

---

## Calculation Transparency

The agent must write the app so users can understand how results were obtained.

### Requirements
- Keep formulas centralized in a calculation module
- Keep UI logic separate from engineering calculations
- Show assumptions in the interface or a help panel
- Use descriptive variable names
- Preserve comments and docstrings
- Make it easy to inspect intermediate values

### Do not
- bury equations inside UI callbacks
- mix plotting code with the core engineering logic
- hide units
- hardcode unexplained constants without comments

---

## Software Architecture

Use a modular structure.

### Preferred structure
- `app.py` or `main.py`  
  Entry point

- `gui/`
  - UI layout
  - event wiring
  - dialogs

- `core/`
  - engineering calculations
  - validation
  - load-settlement model

- `plotting/`
  - plotting helpers
  - curve generation
  - chart formatting

- `tests/`
  - unit tests for numerical routines

### Strong separation
The agent should separate:

1. **Input parsing / validation**
2. **Engineering calculations**
3. **Presentation of results**
4. **Plot generation**

---

## Preferred Technical Stack

Unless the user specifies otherwise, prefer Python.

### Recommended default stack
- **Python**
- **PySide6** or **PyQt5/PyQt6** for GUI
- **matplotlib** for plotting
- optionally **numpy** for numerical work

Reason:
- strong scientific ecosystem
- familiar for engineering workflows
- easy plotting
- maintainable for desktop calculation tools

If another stack is requested, preserve the same modular structure and engineering clarity.

---

## Numerical Implementation Guidance

### Capacity calculations
The implementation should compute:
- `Qs` from unit side resistance over the embedded length
- `Qb` from unit base resistance times base area
- `Qtotal = Qs + Qb`

The code should be written so that future enhancement to multilayer integration is straightforward.

### Load–settlement curve
Implement the **three-branched load–settlement response** as a dedicated function or class.

The plotting logic should:
- generate settlement values
- generate corresponding load values
- mark the branch transitions
- label the branches if practical

The app should not just plot an arbitrary curve. It should reflect the intended three-stage Mayne–Harris style response:
1. initial branch before full side resistance mobilization
2. second branch as side resistance is capped and base mobilization continues
3. third branch representing post-ultimate response

Keep this model easy to modify because engineering assumptions may later be refined.

---

## Validation Rules

The agent should implement robust input validation.

### Examples
- unit weight must be positive
- diameter must be positive
- socket length must be positive
- `N60` must be positive
- groundwater depth cannot create impossible geometry
- shaft tip depth must be below top of socket
- advanced override inputs must be checked for physical reasonableness

### Error handling
- show user-friendly validation messages
- do not crash on bad input
- identify which field is invalid
- prevent plotting before a successful calculation

---

## Units

The app must make units explicit everywhere.

### Preferred default
Use consistent SI units, for example:
- unit weight: `kN/m³`
- stress: `kPa`
- length: `m`
- capacity: `kN`
- settlement: `mm` or `m` but be consistent and label clearly

If conversions are supported, isolate them in a dedicated utility module.

Never mix units implicitly.

---

## UX Expectations

- Results should update only after the user clicks **Compute Capacity**
- Plot button should remain disabled until valid results exist
- Numeric outputs should be rounded sensibly for display
- Include tooltips or brief notes for technical inputs
- The app should feel like an engineering calculator, not a consumer app

---

## Testing Expectations

The agent should add tests for the core engineering logic.

### Must test
- base area calculations
- `Qs`, `Qb`, and `Qtotal`
- handling of invalid inputs
- generation of the three branches
- branch transition ordering
- monotonicity of settlement values
- reasonable shape of the load–settlement curve

Where possible, use known hand-check values or benchmark examples.

---

## Documentation Expectations

The code should include:
- docstrings for public functions
- comments for formulas and assumptions
- a short README explaining how to run the app
- notes identifying where the engineering equations are implemented

If assumptions are approximate or correlation-based, state that clearly in comments and user-facing help text.

---

## Coding Style Rules

- Favor readable, explicit code
- Use small functions
- Preserve existing comments and unaffected code
- Do not perform large refactors unless needed
- Keep GUI callbacks thin
- Put equations in named functions
- Avoid “magic numbers”; define constants with explanations
- Use type hints where practical

---

## Suggested Feature Enhancements

These are optional unless requested:
- export results to CSV
- export the plot as PNG
- advanced panel showing intermediate calculations
- multi-layer soil profile input
- save/load project inputs
- comparison of multiple shaft geometries

---

## Deliverable Expectations for the Agent

When implementing or modifying the app, the agent should provide:

1. the new or changed files
2. a concise explanation of the architecture
3. a brief description of how the formulas were organized
4. any assumptions made where the engineering model was not fully specified
5. instructions for running the application

If code is incomplete because a formula or assumption is uncertain, the agent should say so explicitly rather than inventing unsupported details.

---

## Final Instruction to the Agent

Treat this as an engineering computation tool. Favor correctness, clarity, traceability, and maintainability. The user should be able to inspect inputs, understand outputs, and trust how `Qs`, `Qb`, `Qtotal`, and the three-branched load–settlement curve were produced.
