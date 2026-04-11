"""Tkinter desktop GUI for the Type 3 IGM drilled-shaft calculator."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from core import CalculationInput, calculate_capacity, generate_three_branch_curve
from core.validation import ValidationError
from plotting import show_curve_plot

FIELD_GROUPS: tuple[tuple[str, tuple[tuple[str, str, str], ...]], ...] = (
    (
        "Material Properties",
        (
            ("gamma", "Unit weight, gamma (kN/m^3)", "Representative geomaterial unit weight."),
            ("n60", "Corrected SPT N60 (blows/0.3 m)", "Primary Mayne-Harris correlation input."),
            ("nu", "Poisson's ratio, nu (-)", "Default is 0.30 for the geomaterial."),
            ("ec_simple", "Composite shaft modulus, Ec (kPa)", "Concrete/composite shaft modulus for simple analysis."),
            ("slurry_construction", "Slurry construction (Yes/No)", "If Yes, fmax uses K0 tan(0.75 phi') sigma'vo."),
        ),
    ),
    (
        "Geometry",
        (
            ("z_top_socket", "Depth to top of socket (m)", "Measured from the existing ground surface."),
            ("socket_length", "Socket length, L (m)", "Embedded Type 3 IGM socket length."),
            ("diameter", "Shaft diameter, D (m)", "Diameter used for side and base area."),
        ),
    ),
    (
        "Groundwater / Stress",
        (
            ("z_gwt", "Groundwater depth (m)", "Used to estimate effective stress if no override is entered."),
        ),
    ),
)

ADVANCED_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("sigma_vo_eff_mid_override", "sigma'vo at socket mid-depth (kPa)", "Optional direct override."),
    ("sigma_vo_eff_tip_override", "sigma'vo at socket tip (kPa)", "Optional direct override."),
    ("phi_prime_override_deg", "phi' override (deg)", "Leave blank to use the N60 correlation."),
    ("k0_override", "K0 override (-)", "Leave blank to use the FHWA equation."),
    ("esl_override", "EsL override (kPa)", "Side modulus at base level."),
    ("esm_override", "Esm override (kPa)", "Mid-depth modulus."),
    ("eb_override", "Eb override (kPa)", "Modulus beneath the base."),
    ("ec_override", "Ec override (kPa)", "Composite shaft modulus."),
    ("su_override", "su override (kPa)", "Operational undrained strength below base."),
    ("atmospheric_pressure", "Atmospheric pressure, pa (kPa)", "Default 101 kPa."),
    ("branch3_extension_mm", "Segment 3 extension (mm)", "Plot-only continuation beyond wt2."),
    ("points_per_segment", "Points per segment", "Discretization for the plotted curve."),
    ("slurry_construction_advanced", "Slurry construction (Yes/No)", "If Yes, fmax uses K0 tan(0.75 phi') sigma'vo."),
)

RESULT_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("qs", "Qs (kN)", ".1f"),
    ("qb", "Qb (kN)", ".1f"),
    ("qtotal", "Qtotal (kN)", ".1f"),
    ("q_design", "Design Axial Capacity (kN)", ".1f"),
    ("sigma_vo_eff_mid", "sigma'vo,mid (kPa)", ".2f"),
    ("sigma_vo_eff_tip", "sigma'vo,tip (kPa)", ".2f"),
    ("phi_prime_deg", "phi' (deg)", ".2f"),
    ("k0", "K0 (-)", ".3f"),
    ("fmax", "fmax (kPa)", ".2f"),
    ("qs_max", "Qs,max (kN)", ".1f"),
    ("su", "su (kPa)", ".2f"),
    ("qmax", "qmax (kPa)", ".2f"),
    ("esl", "EsL (kPa)", ".0f"),
    ("influence_factor", "I (-)", ".4f"),
    ("qt1", "Qt1 (kN)", ".1f"),
    ("wt1_m", "wt1 (mm)", "mm"),
    ("wt2_m", "wt2 (mm)", "mm"),
)

class Type3IGMApp:
    """Desktop GUI for preliminary drilled-shaft design in Type 3 IGM."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Category 3 IGM Drilled Shaft Design")
        self.root.geometry("1380x900")
        self.root.minsize(1200, 760)

        self.inputs = CalculationInput()
        self.current_result = None
        self.input_vars: dict[str, tk.StringVar] = {}
        self.result_vars: dict[str, tk.StringVar] = {}
        self.status_var = tk.StringVar(value="Ready.")
        self.slurry_var = tk.StringVar(value="No")

        self._configure_style()
        self._build_ui()
        self.load_defaults()

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        self.root.configure(bg="#e5ebf0")
        style.configure("Shell.TFrame", background="#e5ebf0")
        style.configure("Panel.TFrame", background="#f7fafc")
        style.configure("Section.TLabel", background="#f7fafc", foreground="#183042", font=("TkDefaultFont", 11, "bold"))
        style.configure("Label.TLabel", background="#f7fafc", foreground="#274558")
        style.configure("Hint.TLabel", background="#f7fafc", foreground="#708595")
        style.configure("Value.TLabel", background="#f7fafc", foreground="#0f2740", font=("TkFixedFont", 10))
        style.configure("Action.TButton", padding=(11, 8))
        style.configure("Primary.TButton", padding=(11, 8), foreground="#ffffff", background="#1c608f")
        style.map(
            "Primary.TButton",
            background=[("active", "#174e74"), ("pressed", "#133b57")],
            foreground=[("disabled", "#d9e4ed")],
        )

    def _build_ui(self) -> None:
        shell = ttk.Frame(self.root, padding=14, style="Shell.TFrame")
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=0)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(1, weight=1)

        title = ttk.Frame(shell, style="Shell.TFrame")
        title.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        ttk.Label(
            title,
            text="Category 3 Intermediate Geomaterial Drilled Shaft Design",
            background="#e5ebf0",
            foreground="#163142",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            title,
            text="Axial capacity computed using the Mayne-Harrris Method",
            background="#e5ebf0",
            foreground="#516779",
        ).pack(anchor="w", pady=(4, 0))

        left = ttk.Frame(shell, padding=14, style="Panel.TFrame")
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        left.columnconfigure(0, weight=1)

        right = ttk.Frame(shell, padding=14, style="Panel.TFrame")
        right.grid(row=1, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.columnconfigure(1, weight=1)

        self._build_inputs(left)
        self._build_actions(left)
        self._build_results(right)
        self._build_notes(right)
        self._build_status(shell)

    def _build_inputs(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Inputs", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        container = ttk.Notebook(parent)
        container.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

        simple = ttk.Frame(container, padding=12, style="Panel.TFrame")
        advanced = ttk.Frame(container, padding=12, style="Panel.TFrame")
        container.add(simple, text="Simple Mode")
        container.add(advanced, text="Advanced Mode")

        self._build_simple_fields(simple)
        self._build_advanced_fields(advanced)

    def _build_simple_fields(self, parent: ttk.Frame) -> None:
        current_row = 0
        for group_title, group_fields in FIELD_GROUPS:
            ttk.Label(parent, text=group_title, style="Section.TLabel").grid(row=current_row, column=0, sticky="w", pady=(0, 8))
            current_row += 1
            for field_name, label, hint in group_fields:
                variable = self.slurry_var if field_name == "slurry_construction" else tk.StringVar()
                self.input_vars[field_name] = variable
                ttk.Label(parent, text=label, style="Label.TLabel").grid(row=current_row, column=0, sticky="w")
                self._create_input_widget(parent, field_name, variable, current_row)
                current_row += 1
                ttk.Label(parent, text=hint, style="Hint.TLabel").grid(row=current_row, column=0, columnspan=2, sticky="w", pady=(0, 8))
                current_row += 1
        parent.columnconfigure(1, weight=1)

    def _build_advanced_fields(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)
        for row, (field_name, label, hint) in enumerate(ADVANCED_FIELDS):
            variable = self.slurry_var if field_name == "slurry_construction_advanced" else tk.StringVar()
            self.input_vars[field_name] = variable
            display_row = row * 2
            ttk.Label(parent, text=label, style="Label.TLabel").grid(row=display_row, column=0, sticky="w")
            self._create_input_widget(parent, field_name, variable, display_row)
            ttk.Label(parent, text=hint, style="Hint.TLabel").grid(row=display_row + 1, column=0, columnspan=2, sticky="w", pady=(0, 8))

    def _build_actions(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Actions", style="Section.TLabel").grid(row=2, column=0, sticky="w", pady=(18, 0))
        actions = ttk.Frame(parent, style="Panel.TFrame")
        actions.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)

        ttk.Button(actions, text="Compute Capacity", command=self.compute, style="Primary.TButton").grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))
        self.plot_button = ttk.Button(actions, text="Plot Load-Settlement Curve", command=self.plot_curve, style="Action.TButton")
        self.plot_button.grid(row=0, column=1, sticky="ew", pady=(0, 8))
        ttk.Button(actions, text="Load Draft Defaults", command=self.load_defaults, style="Action.TButton").grid(row=1, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(actions, text="Clear Inputs", command=self.clear_inputs, style="Action.TButton").grid(row=1, column=1, sticky="ew")
        self.plot_button.state(["disabled"])

    def _build_results(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Results", style="Section.TLabel").grid(row=0, column=0, sticky="w", columnspan=2)
        summary = ttk.Frame(parent, style="Panel.TFrame")
        summary.grid(row=1, column=0, sticky="ew", columnspan=2, pady=(10, 0))
        summary.columnconfigure(1, weight=1)
        summary.columnconfigure(3, weight=1)

        for index, (name, label, _) in enumerate(RESULT_FIELDS):
            self.result_vars[name] = tk.StringVar(value="--")
            column = 0 if index < 8 else 2
            row = index if index < 8 else index - 8
            ttk.Label(summary, text=label, style="Label.TLabel").grid(row=row, column=column, sticky="w", pady=4)
            ttk.Label(summary, textvariable=self.result_vars[name], style="Value.TLabel").grid(row=row, column=column + 1, sticky="ew", padx=(12, 20), pady=4)

        ttk.Label(parent, text="Warnings", style="Section.TLabel").grid(row=2, column=0, sticky="w", columnspan=2, pady=(18, 0))

        self.warning_box = tk.Text(parent, height=9, wrap="word", font=("TkFixedFont", 10), background="#fff6e8", foreground="#5d3b00", relief="flat", padx=10, pady=8)
        self.warning_box.grid(row=3, column=0, sticky="nsew", columnspan=2, pady=(10, 0))
        self.warning_box.insert("1.0", "No warnings.")
        self.warning_box.configure(state="disabled")

    def _build_notes(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Intermediate Values", style="Section.TLabel").grid(row=4, column=0, sticky="w", columnspan=2, pady=(18, 0))
        self.intermediate_box = tk.Text(parent, height=12, wrap="word", font=("TkFixedFont", 10), background="#f2f6f9", foreground="#173042", relief="flat", padx=10, pady=8)
        self.intermediate_box.grid(row=5, column=0, sticky="nsew", columnspan=2, pady=(10, 0))
        self.intermediate_box.insert("1.0", "Compute capacity to populate intermediate values.")
        self.intermediate_box.configure(state="disabled")
        parent.rowconfigure(5, weight=1)

    def _build_status(self, parent: ttk.Frame) -> None:
        status = ttk.Frame(parent, style="Shell.TFrame", padding=(0, 10, 0, 0))
        status.grid(row=2, column=0, columnspan=2, sticky="ew")
        ttk.Label(status, textvariable=self.status_var, background="#e5ebf0", foreground="#506676").pack(anchor="w")

    def load_defaults(self) -> None:
        self._set_input_var("gamma", self.inputs.gamma)
        self._set_input_var("n60", self.inputs.n60)
        self._set_input_var("nu", self.inputs.nu)
        self._set_input_var("ec_simple", 25_000_000.0)
        self.input_vars["slurry_construction"].set("No")
        self._set_input_var("z_top_socket", self.inputs.z_top_socket)
        self._set_input_var("socket_length", self.inputs.socket_length)
        self._set_input_var("diameter", self.inputs.diameter)
        self._set_input_var("z_gwt", self.inputs.z_gwt)

        for field_name in (
            "sigma_vo_eff_mid_override",
            "sigma_vo_eff_tip_override",
            "phi_prime_override_deg",
            "k0_override",
            "esl_override",
            "esm_override",
            "eb_override",
            "ec_override",
            "su_override",
        ):
            self.input_vars[field_name].set("")

        self._set_input_var("atmospheric_pressure", self.inputs.atmospheric_pressure)
        self._set_input_var("branch3_extension_mm", self.inputs.branch3_extension_mm)
        self._set_input_var("points_per_segment", self.inputs.points_per_segment)
        self.input_vars["slurry_construction_advanced"].set("No")
        self.status_var.set("Loaded draft default inputs.")

    def clear_inputs(self) -> None:
        for variable in self.input_vars.values():
            variable.set("")
        self.current_result = None
        self.plot_button.state(["disabled"])
        self._clear_result_labels()
        self._set_text(self.warning_box, "No warnings.")
        self._set_text(self.intermediate_box, "Compute capacity to populate intermediate values.")
        self.status_var.set("Cleared inputs.")

    def compute(self) -> None:
        try:
            user_inputs = self._collect_inputs()
            self.current_result = calculate_capacity(user_inputs)
        except ValidationError as exc:
            messagebox.showerror("Input Validation", str(exc), parent=self.root)
            self.status_var.set("Validation failed.")
            return
        except ValueError as exc:
            messagebox.showerror("Input Error", str(exc), parent=self.root)
            self.status_var.set("Unable to parse one or more fields.")
            return

        self._populate_results()
        self.plot_button.state(["!disabled"])
        self.status_var.set("Capacity calculation completed.")

    def plot_curve(self) -> None:
        if self.current_result is None:
            messagebox.showinfo("Plot Load-Settlement Curve", "Run a valid capacity calculation before plotting.", parent=self.root)
            return

        inputs = self._collect_inputs()
        curve = generate_three_branch_curve(inputs, self.current_result)
        show_curve_plot(curve, self.current_result)
        self.status_var.set("Displayed the three-branched load-settlement curve.")

    def _collect_inputs(self) -> CalculationInput:
        return CalculationInput(
            gamma=self._parse_required_float("gamma"),
            slurry_construction=self._parse_slurry_construction(),
            z_gwt=self._parse_required_float("z_gwt"),
            z_top_socket=self._parse_required_float("z_top_socket"),
            socket_length=self._parse_required_float("socket_length"),
            diameter=self._parse_required_float("diameter"),
            n60=self._parse_required_float("n60"),
            nu=self._parse_required_float("nu"),
            sigma_vo_eff_mid_override=self._parse_optional_float("sigma_vo_eff_mid_override"),
            sigma_vo_eff_tip_override=self._parse_optional_float("sigma_vo_eff_tip_override"),
            phi_prime_override_deg=self._parse_optional_float("phi_prime_override_deg"),
            k0_override=self._parse_optional_float("k0_override"),
            esl_override=self._parse_optional_float("esl_override"),
            esm_override=self._parse_optional_float("esm_override"),
            eb_override=self._parse_optional_float("eb_override"),
            ec_override=self._parse_ec_value(),
            su_override=self._parse_optional_float("su_override"),
            atmospheric_pressure=self._parse_required_float("atmospheric_pressure"),
            branch3_extension_mm=self._parse_required_float("branch3_extension_mm"),
            points_per_segment=self._parse_required_int("points_per_segment"),
        )

    def _populate_results(self) -> None:
        assert self.current_result is not None
        for field_name, _, formatter in RESULT_FIELDS:
            value = getattr(self.current_result, field_name)
            if formatter == "mm":
                self.result_vars[field_name].set(f"{value * 1000.0:.2f}")
            else:
                self.result_vars[field_name].set(format(value, formatter))

        warnings = self.current_result.warnings or ["No warnings."]
        self._set_text(self.warning_box, "\n".join(f"- {warning}" for warning in warnings))

        intermediate_text = (
            f"z_mid = {self.current_result.z_mid:.2f} m\n"
            f"z_tip = {self.current_result.z_tip:.2f} m\n"
            f"sigma'p_mid = {self.current_result.sigma_p_eff_mid:.2f} kPa\n"
            f"sigma'p_tip = {self.current_result.sigma_p_eff_tip:.2f} kPa\n"
            f"OCR_mid = {self.current_result.ocr_mid:.3f}\n"
            f"OCR_tip = {self.current_result.ocr_tip:.3f}\n"
            f"Esm = {self.current_result.esm:.0f} kPa\n"
            f"Eb = {self.current_result.eb:.0f} kPa\n"
            f"Ec = {self.current_result.ec:.0f} kPa\n"
            f"xi = {self.current_result.xi:.3f}\n"
            f"lambda = {self.current_result.lambda_value:.3f}\n"
            f"zeta = {self.current_result.zeta:.3f}\n"
            f"muL = {self.current_result.mu_l:.3f}\n"
            f"Qb1 = {self.current_result.qb1:.1f} kN\n"
            f"Delta_wb = {self.current_result.branch2_delta_wb_m * 1000.0:.3f} mm\n\n"
            "Assumptions\n"
            + "\n".join(f"- {assumption}" for assumption in self.current_result.assumptions)
        )
        self._set_text(self.intermediate_box, intermediate_text)

    def _clear_result_labels(self) -> None:
        for variable in self.result_vars.values():
            variable.set("--")

    def _set_input_var(self, name: str, value: float | int) -> None:
        self.input_vars[name].set(str(value))

    def _create_input_widget(self, parent: ttk.Frame, field_name: str, variable: tk.StringVar, row: int) -> None:
        if field_name in {"slurry_construction", "slurry_construction_advanced"}:
            ttk.Combobox(
                parent,
                textvariable=variable,
                values=("No", "Yes"),
                state="readonly",
                width=16,
            ).grid(row=row, column=1, sticky="ew", padx=(12, 0))
            return

        ttk.Entry(parent, textvariable=variable, width=18).grid(row=row, column=1, sticky="ew", padx=(12, 0))

    def _parse_required_float(self, field_name: str) -> float:
        value = self.input_vars[field_name].get().strip()
        if not value:
            raise ValidationError(f"{field_name} is required.")
        return float(value)

    def _parse_optional_float(self, field_name: str) -> float | None:
        value = self.input_vars[field_name].get().strip()
        return None if value == "" else float(value)

    def _parse_required_int(self, field_name: str) -> int:
        value = self.input_vars[field_name].get().strip()
        if not value:
            raise ValidationError(f"{field_name} is required.")
        return int(value)

    def _parse_slurry_construction(self) -> bool:
        raw_value = self.slurry_var.get().strip()
        if not raw_value:
            raise ValidationError("slurry_construction is required.")

        normalized = raw_value.lower()
        if normalized in {"yes", "y", "true", "1"}:
            value = True
        elif normalized in {"no", "n", "false", "0"}:
            value = False
        else:
            raise ValidationError("Slurry construction must be Yes or No.")

        return value

    def _parse_ec_value(self) -> float | None:
        advanced_value = self.input_vars["ec_override"].get().strip()
        simple_value = self.input_vars["ec_simple"].get().strip()
        raw_value = advanced_value or simple_value
        if not raw_value:
            return None
        return float(raw_value)

    def _set_text(self, widget: tk.Text, value: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        widget.configure(state="disabled")


def run() -> None:
    """Launch the desktop application."""

    root = tk.Tk()
    Type3IGMApp(root)
    root.mainloop()
