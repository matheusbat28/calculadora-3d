from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from uuid import uuid4


CENT = Decimal("0.01")
BUDGET_INPUT_KEYS = (
    "material_grams",
    "filament_price_per_kg",
    "print_duration",
    "printer_power_watts",
    "energy_price_per_kwh",
    "labor_minutes",
    "labor_rate_per_hour",
    "profit_margin_percent",
)


@dataclass(frozen=True)
class ProjectQuote:
    print_hours: Decimal
    material_cost: Decimal
    energy_cost: Decimal
    labor_cost: Decimal
    total_cost: Decimal
    profit: Decimal
    final_price: Decimal


@dataclass(frozen=True)
class SavedBudget:
    id: str
    name: str
    inputs: dict[str, str]
    material_cost: str
    energy_cost: str
    labor_cost: str
    total_cost: str
    profit: str
    final_price: str


class BudgetStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[SavedBudget]:
        if not self.path.exists():
            return []
        try:
            raw_budgets = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ValueError(f"Não foi possível ler os orçamentos: {error}") from error
        if not isinstance(raw_budgets, list):
            raise ValueError("O arquivo de orçamentos está em um formato inválido.")

        budgets = []
        for raw_budget in raw_budgets:
            if not isinstance(raw_budget, dict):
                raise ValueError("O arquivo de orçamentos está em um formato inválido.")
            try:
                budget = SavedBudget(**raw_budget)
            except TypeError as error:
                raise ValueError(
                    "O arquivo de orçamentos está em um formato inválido."
                ) from error
            if (
                not isinstance(budget.id, str)
                or not budget.id
                or not isinstance(budget.name, str)
                or not budget.name
                or not isinstance(budget.inputs, dict)
                or set(budget.inputs) != set(BUDGET_INPUT_KEYS)
                or any(not isinstance(value, str) for value in budget.inputs.values())
                or any(
                    not isinstance(value, str)
                    for value in (
                        budget.material_cost,
                        budget.energy_cost,
                        budget.labor_cost,
                        budget.total_cost,
                        budget.profit,
                        budget.final_price,
                    )
                )
            ):
                raise ValueError("O arquivo de orçamentos está em um formato inválido.")
            try:
                stored_values = (
                    Decimal(budget.material_cost),
                    Decimal(budget.energy_cost),
                    Decimal(budget.labor_cost),
                    Decimal(budget.total_cost),
                    Decimal(budget.profit),
                    Decimal(budget.final_price),
                )
            except InvalidOperation as error:
                raise ValueError(
                    "O arquivo de orçamentos está em um formato inválido."
                ) from error
            if any(not value.is_finite() for value in stored_values):
                raise ValueError("O arquivo de orçamentos está em um formato inválido.")
            budgets.append(budget)
        return budgets

    def save(self, budgets: list[SavedBudget]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = self.path.with_suffix(".tmp")
            temporary_path.write_text(
                json.dumps(
                    [budget.__dict__ for budget in budgets],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            temporary_path.replace(self.path)
        except OSError as error:
            raise ValueError(f"Não foi possível salvar os orçamentos: {error}") from error


def parse_decimal(value: str, field_name: str) -> Decimal:
    normalized = value.strip().replace(",", ".")
    try:
        number = Decimal(normalized)
    except InvalidOperation as error:
        raise ValueError(f"Informe um número válido para {field_name}.") from error
    if not number.is_finite():
        raise ValueError(f"Informe um número válido para {field_name}.")
    return number


def parse_optional_decimal(value: str, field_name: str) -> Decimal:
    if not value.strip():
        return Decimal("0")
    return parse_decimal(value, field_name)


def parse_duration(value: str) -> tuple[Decimal, Decimal]:
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError("Informe o tempo de impressão no formato horas:minutos (ex.: 2:30).")
    hours = parse_decimal(parts[0], "horas de impressão")
    minutes = parse_decimal(parts[1], "minutos de impressão")
    if hours < 0:
        raise ValueError("As horas de impressão devem ser iguais ou maiores que zero.")
    if minutes < 0 or minutes >= 60:
        raise ValueError("Os minutos de impressão devem estar entre 0 e 59.")
    return hours, minutes


def calculate_quote(
    material_grams: Decimal,
    filament_price_per_kg: Decimal,
    print_hours: Decimal,
    print_minutes: Decimal,
    printer_power_watts: Decimal,
    energy_price_per_kwh: Decimal,
    labor_minutes: Decimal,
    labor_rate_per_hour: Decimal,
    profit_margin_percent: Decimal,
) -> ProjectQuote:
    values = {
        "peso do material": material_grams,
        "preço do filamento por kg": filament_price_per_kg,
        "horas de impressão": print_hours,
        "minutos de impressão": print_minutes,
        "potência da impressora": printer_power_watts,
        "preço da energia por kWh": energy_price_per_kwh,
        "tempo de mão de obra": labor_minutes,
        "valor da mão de obra por hora": labor_rate_per_hour,
        "margem de lucro": profit_margin_percent,
    }
    for field_name, value in values.items():
        if not value.is_finite() or value < 0:
            raise ValueError(f"{field_name.capitalize()} deve ser um valor igual ou maior que zero.")

    if material_grams == 0:
        raise ValueError("O peso do material deve ser maior que zero.")
    if filament_price_per_kg == 0:
        raise ValueError("O preço do filamento por kg deve ser maior que zero.")
    if printer_power_watts == 0:
        raise ValueError("A potência da impressora deve ser maior que zero.")
    if print_minutes >= 60:
        raise ValueError("Os minutos de impressão devem estar entre 0 e 59.")

    duration_hours = print_hours + print_minutes / Decimal("60")
    if duration_hours == 0:
        raise ValueError("O tempo de impressão deve ser maior que zero.")

    material_cost = (material_grams * filament_price_per_kg / Decimal("1000")).quantize(
        CENT, rounding=ROUND_HALF_UP
    )
    energy_cost = (
        printer_power_watts
        / Decimal("1000")
        * duration_hours
        * energy_price_per_kwh
    ).quantize(CENT, rounding=ROUND_HALF_UP)
    labor_cost = (
        labor_minutes / Decimal("60") * labor_rate_per_hour
    ).quantize(CENT, rounding=ROUND_HALF_UP)
    total_cost = material_cost + energy_cost + labor_cost
    final_price = (
        total_cost * (Decimal("1") + profit_margin_percent / Decimal("100"))
    ).quantize(CENT, rounding=ROUND_HALF_UP)

    return ProjectQuote(
        print_hours=duration_hours,
        material_cost=material_cost,
        energy_cost=energy_cost,
        labor_cost=labor_cost,
        total_cost=total_cost,
        profit=final_price - total_cost,
        final_price=final_price,
    )


def format_currency(value: Decimal) -> str:
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def main() -> None:
    root = tk.Tk()
    root.title("Calculadora de Preço 3D")
    root.geometry("1000x900")
    root.minsize(360, 600)
    data_directory = Path(
        os.environ.get("LOCALAPPDATA", str(Path.home()))
    ) / "PrintCost"
    budget_store = BudgetStore(data_directory / "budgets.json")
    try:
        budgets = budget_store.load()
    except ValueError as error:
        messagebox.showerror("Erro ao carregar orçamentos", str(error), parent=root)
        root.destroy()
        return

    style = ttk.Style(root)
    style.theme_use("clam")
    dark_mode = tk.BooleanVar(value=True)
    palette: dict[str, str] = {}

    def apply_theme() -> None:
        palette.update(
            {
                "background": "#10141D" if dark_mode.get() else "#F3F5F9",
                "surface": "#191F2B" if dark_mode.get() else "#FFFFFF",
                "surface_alt": "#202838" if dark_mode.get() else "#F7F8FC",
                "text": "#F1F5F9" if dark_mode.get() else "#172033",
                "muted": "#9AA7BA" if dark_mode.get() else "#69758A",
                "border": "#303A4D" if dark_mode.get() else "#E1E6EF",
                "accent": "#8B7CFF" if dark_mode.get() else "#635BDB",
                "accent_hover": "#7868F0" if dark_mode.get() else "#5148C7",
                "success": "#56D6A0" if dark_mode.get() else "#14845A",
            }
        )
        root.configure(background=palette["background"])
        canvas.configure(background=palette["background"])
        style.configure("App.TFrame", background=palette["background"])
        style.configure("Vertical.TScrollbar", background=palette["surface"])
        style.configure(
            "Status.TLabel",
            background=palette["surface"],
            foreground=palette["muted"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "StatusError.TLabel",
            background=palette["surface"],
            foreground="#FF8A8A" if dark_mode.get() else "#B42318",
            font=("Segoe UI", 9),
        )
        style.configure("Card.TFrame", background=palette["surface"])
        style.configure("PriceCard.TFrame", background=palette["surface_alt"])
        style.configure(
            "Budget.Treeview",
            background=palette["surface_alt"],
            fieldbackground=palette["surface_alt"],
            foreground=palette["text"],
            bordercolor=palette["border"],
            rowheight=30,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Budget.Treeview.Heading",
            background=palette["surface"],
            foreground=palette["text"],
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "Budget.Treeview",
            background=[("selected", palette["accent"])],
            foreground=[("selected", "#FFFFFF")],
        )
        style.map(
            "Budget.Treeview.Heading",
            background=[("active", palette["surface_alt"])],
        )
        budget_table.tag_configure("odd", background=palette["surface"])
        style.configure(
            "Title.TLabel",
            background=palette["background"],
            foreground=palette["text"],
            font=("Segoe UI", 23, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=palette["background"],
            foreground=palette["muted"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "CardTitle.TLabel",
            background=palette["surface"],
            foreground=palette["text"],
            font=("Segoe UI", 11, "bold"),
        )
        style.configure(
            "CardHint.TLabel",
            background=palette["surface"],
            foreground=palette["muted"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "Formula.TLabel",
            background=palette["surface"],
            foreground=palette["muted"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "FormulaValue.TLabel",
            background=palette["surface"],
            foreground=palette["text"],
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Field.TLabel",
            background=palette["surface"],
            foreground=palette["text"],
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Unit.TLabel",
            background=palette["surface"],
            foreground=palette["muted"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "Result.TLabel",
            background=palette["surface"],
            foreground=palette["muted"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "ResultValue.TLabel",
            background=palette["surface"],
            foreground=palette["text"],
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "PriceHint.TLabel",
            background=palette["surface_alt"],
            foreground=palette["muted"],
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Price.TLabel",
            background=palette["surface_alt"],
            foreground=palette["success"],
            font=("Segoe UI", 25, "bold"),
        )
        style.configure(
            "TEntry",
            fieldbackground=palette["surface_alt"],
            foreground=palette["text"],
            insertcolor=palette["text"],
            bordercolor=palette["border"],
            lightcolor=palette["border"],
            darkcolor=palette["border"],
            padding=(10, 9),
            font=("Segoe UI", 10),
        )
        style.map(
            "TEntry",
            bordercolor=[("focus", palette["accent"])],
            lightcolor=[("focus", palette["accent"])],
            darkcolor=[("focus", palette["accent"])],
        )
        style.configure(
            "Accent.TButton",
            background=palette["accent"],
            foreground="#FFFFFF",
            borderwidth=0,
            padding=(14, 11),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Accent.TButton",
            background=[
                ("pressed", palette["accent_hover"]),
                ("active", palette["accent_hover"]),
            ],
        )
        style.configure(
            "Theme.TButton",
            background=palette["surface"],
            foreground=palette["text"],
            bordercolor=palette["border"],
            padding=(10, 7),
            font=("Segoe UI", 9, "bold"),
        )
        style.map("Theme.TButton", background=[("active", palette["surface_alt"])])
        theme_button.configure(
            text="☀  Modo claro" if dark_mode.get() else "☾  Modo escuro"
        )

    scroll_area = ttk.Frame(root, style="App.TFrame")
    scroll_area.pack(fill="both", expand=True)
    scroll_area.rowconfigure(0, weight=1)
    scroll_area.columnconfigure(0, weight=1)

    canvas = tk.Canvas(
        scroll_area,
        background="#10141D",
        borderwidth=0,
        highlightthickness=0,
    )
    scrollbar = ttk.Scrollbar(
        scroll_area, orient="vertical", command=canvas.yview, style="Vertical.TScrollbar"
    )
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    container = ttk.Frame(canvas, padding=(24, 20), style="App.TFrame")
    container_window = canvas.create_window((0, 0), window=container, anchor="nw")
    container.columnconfigure((0, 1), weight=1, uniform="columns")

    def update_scroll_region(_event: tk.Event[tk.Misc]) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))

    def resize_content(event: tk.Event[tk.Misc]) -> None:
        canvas.itemconfigure(container_window, width=event.width)
        narrow_layout = event.width < 800
        container.configure(padding=(14, 16) if narrow_layout else (24, 20))
        status_label.configure(wraplength=max(240, event.width - 48))
        if narrow_layout:
            print_section.grid_configure(row=1, column=0, columnspan=2, padx=0)
            costs_section.grid_configure(row=2, column=0, columnspan=2, padx=0, pady=(12, 0))
            result_section.grid_configure(row=3)
            calculate_button.grid_configure(row=4)
            budget_section.grid_configure(row=5)
            formula_section.grid_configure(row=6)
        else:
            print_section.grid_configure(row=1, column=0, columnspan=1, padx=(0, 8))
            costs_section.grid_configure(row=1, column=1, columnspan=1, padx=(8, 0), pady=0)
            result_section.grid_configure(row=2)
            calculate_button.grid_configure(row=3)
            budget_section.grid_configure(row=4)
            formula_section.grid_configure(row=5)

    container.bind("<Configure>", update_scroll_region)
    canvas.bind("<Configure>", resize_content)
    canvas.bind_all(
        "<MouseWheel>",
        lambda event: canvas.yview_scroll(int(-event.delta / 120), "units"),
    )

    header = ttk.Frame(container, style="App.TFrame")
    header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 22))
    header.columnconfigure(0, weight=1)
    ttk.Label(header, text="Calculadora de Preço 3D", style="Title.TLabel").grid(
        row=0, column=0, sticky="w"
    )
    theme_button = ttk.Button(
        header,
        style="Theme.TButton",
        command=lambda: (dark_mode.set(not dark_mode.get()), apply_theme()),
    )
    theme_button.grid(row=0, column=1, rowspan=2, sticky="e")
    ttk.Label(
        header,
        text="O orçamento atualiza automaticamente enquanto você preenche.",
        style="Subtitle.TLabel",
    ).grid(row=1, column=0, sticky="w", pady=(3, 0))

    fields = {
        "material_grams": ("Material usado (g)", "g"),
        "filament_price_per_kg": ("Preço do filamento", "R$/kg"),
        "print_duration": ("Tempo de impressão", "horas:minutos"),
        "printer_power_watts": ("Potência da impressora", "W"),
        "energy_price_per_kwh": ("Tarifa de energia", "R$/kWh"),
        "labor_minutes": ("Tempo de mão de obra (opcional)", "min"),
        "labor_rate_per_hour": ("Valor da mão de obra (opcional)", "R$/hora"),
        "profit_margin_percent": ("Margem de lucro (opcional)", "%"),
    }
    entries: dict[str, ttk.Entry] = {}

    def add_form(section: ttk.Frame, keys: tuple[str, ...]) -> None:
        section.columnconfigure(0, weight=1)
        for row, key in enumerate(keys):
            label, unit = fields[key]
            field_label = ttk.Frame(section, style="Card.TFrame")
            field_label.grid(row=row * 2, column=0, sticky="ew", pady=(10, 3))
            ttk.Label(field_label, text=label, style="Field.TLabel").pack(
                side="left"
            )
            ttk.Label(field_label, text=unit, style="Unit.TLabel").pack(
                side="right"
            )
            entry = ttk.Entry(section)
            entry.grid(row=row * 2 + 1, column=0, sticky="ew")
            entries[key] = entry

    print_section = ttk.Frame(container, style="Card.TFrame", padding=(18, 16))
    print_section.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
    ttk.Label(
        print_section, text="Impressão e material", style="CardTitle.TLabel"
    ).grid(row=0, column=0, sticky="w")
    ttk.Label(
        print_section, text="Dados da peça e da máquina", style="CardHint.TLabel"
    ).grid(row=1, column=0, sticky="w", pady=(3, 2))
    form = ttk.Frame(print_section, style="Card.TFrame")
    form.grid(row=2, column=0, sticky="ew")
    add_form(
        form,
        (
            "material_grams",
            "filament_price_per_kg",
            "print_duration",
            "printer_power_watts",
        ),
    )

    costs_section = ttk.Frame(container, style="Card.TFrame", padding=(18, 16))
    costs_section.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
    ttk.Label(
        costs_section, text="Custos e margem", style="CardTitle.TLabel"
    ).grid(row=0, column=0, sticky="w")
    ttk.Label(
        costs_section,
        text="Complete os custos adicionais do projeto",
        style="CardHint.TLabel",
    ).grid(row=1, column=0, sticky="w", pady=(3, 2))
    form = ttk.Frame(costs_section, style="Card.TFrame")
    form.grid(row=2, column=0, sticky="ew")
    add_form(
        form,
        (
            "energy_price_per_kwh",
            "labor_minutes",
            "labor_rate_per_hour",
            "profit_margin_percent",
        ),
    )

    result_section = ttk.Frame(container, style="Card.TFrame", padding=(20, 18))
    result_section.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(18, 10))
    result_section.columnconfigure(1, weight=1)
    ttk.Label(
        result_section, text="Resumo do orçamento", style="CardTitle.TLabel"
    ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
    result_status = tk.StringVar(
        value="Preencha os campos obrigatórios para ver o orçamento."
    )
    status_label = ttk.Label(
        result_section, textvariable=result_status, style="Status.TLabel",
        wraplength=780, justify="left",
    )
    status_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 6))
    result_vars: dict[str, tk.StringVar] = {}
    result_labels = (
        ("tempo", "Tempo total de impressão"),
        ("material", "Custo do material"),
        ("energia", "Custo de energia"),
        ("labor", "Custo de mão de obra"),
        ("cost", "Custo total"),
        ("profit", "Lucro estimado"),
        ("price", "Preço final"),
    )
    for row, (key, label) in enumerate(result_labels, start=2):
        value = tk.StringVar(value="—")
        result_vars[key] = value
        if key == "price":
            price_card = ttk.Frame(
                result_section, style="PriceCard.TFrame", padding=(14, 12)
            )
            price_card.grid(
                row=row, column=0, columnspan=2, sticky="ew", pady=(9, 0)
            )
            price_card.columnconfigure(0, weight=1)
            ttk.Label(
                price_card, text="PREÇO FINAL SUGERIDO", style="PriceHint.TLabel"
            ).grid(row=0, column=0, sticky="w")
            ttk.Label(price_card, textvariable=value, style="Price.TLabel").grid(
                row=1, column=0, sticky="w", pady=(2, 0)
            )
        else:
            ttk.Label(result_section, text=label, style="Result.TLabel").grid(
                row=row, column=0, sticky="w", pady=4
            )
            ttk.Label(
                result_section, textvariable=value, style="ResultValue.TLabel"
            ).grid(row=row, column=1, sticky="e", pady=4)

    def calculate(show_errors: bool = False) -> ProjectQuote | None:
        try:
            values = {
                key: (
                    parse_optional_decimal(entry.get(), fields[key][0])
                    if key in {"labor_minutes", "labor_rate_per_hour", "profit_margin_percent"}
                    else parse_decimal(entry.get(), fields[key][0])
                )
                for key, entry in entries.items()
                if key != "print_duration"
            }
            print_hours, print_minutes = parse_duration(
                entries["print_duration"].get()
            )
            values["print_hours"] = print_hours
            values["print_minutes"] = print_minutes
            quote = calculate_quote(**values)
        except ValueError as error:
            result_status.set(str(error))
            status_label.configure(style="StatusError.TLabel")
            for value in result_vars.values():
                value.set("—")
            if show_errors:
                messagebox.showerror("Confira os dados", str(error), parent=root)
            return None

        status_label.configure(style="Status.TLabel")
        result_status.set("Orçamento atualizado automaticamente.")
        total_minutes = int(quote.print_hours * Decimal("60"))
        hours, minutes = divmod(total_minutes, 60)
        result_vars["tempo"].set(f"{hours}h {minutes:02d}min")
        result_vars["material"].set(format_currency(quote.material_cost))
        result_vars["energia"].set(format_currency(quote.energy_cost))
        result_vars["labor"].set(format_currency(quote.labor_cost))
        result_vars["cost"].set(format_currency(quote.total_cost))
        result_vars["profit"].set(format_currency(quote.profit))
        result_vars["price"].set(format_currency(quote.final_price))
        return quote

    pending_calculation: str | None = None

    def run_scheduled_calculation() -> None:
        nonlocal pending_calculation
        pending_calculation = None
        calculate()

    def schedule_calculation(_event: tk.Event[tk.Misc] | None = None) -> None:
        nonlocal pending_calculation
        if pending_calculation is not None:
            root.after_cancel(pending_calculation)
        pending_calculation = root.after(250, run_scheduled_calculation)

    for entry in entries.values():
        entry.bind("<KeyRelease>", schedule_calculation)
        entry.bind("<<Paste>>", schedule_calculation)
        entry.bind("<FocusOut>", schedule_calculation)

    calculate_button = ttk.Button(
        container,
        text="Calcular orçamento   →",
        style="Accent.TButton",
        command=lambda: calculate(show_errors=True),
    )
    calculate_button.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 0))

    budget_section = ttk.Frame(container, style="Card.TFrame", padding=(20, 16))
    budget_section.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(14, 0))
    budget_section.columnconfigure(0, weight=1)
    ttk.Label(
        budget_section, text="Meus orçamentos", style="CardTitle.TLabel"
    ).grid(row=0, column=0, sticky="w")
    ttk.Label(
        budget_section,
        text="Salve os cálculos para consultar, editar ou excluir depois.",
        style="CardHint.TLabel",
    ).grid(row=1, column=0, sticky="w", pady=(3, 10))
    budget_name = ttk.Entry(budget_section)
    budget_name.grid(row=2, column=0, sticky="ew", pady=(0, 8))
    budget_name.insert(0, "Nome do projeto ou peça")
    budget_name.configure(foreground="#9AA7BA")

    def clear_name_placeholder(_event: tk.Event[tk.Misc]) -> None:
        if budget_name.get() == "Nome do projeto ou peça":
            budget_name.delete(0, "end")
            budget_name.configure(foreground=palette["text"])

    def restore_name_placeholder(_event: tk.Event[tk.Misc]) -> None:
        if not budget_name.get().strip():
            budget_name.insert(0, "Nome do projeto ou peça")
            budget_name.configure(foreground="#9AA7BA")

    budget_name.bind("<FocusIn>", clear_name_placeholder)
    budget_name.bind("<FocusOut>", restore_name_placeholder)

    budget_columns = (
        "name",
        "material",
        "energy",
        "labor",
        "cost",
        "profit",
        "price",
    )
    budget_table = ttk.Treeview(
        budget_section,
        columns=budget_columns,
        show="headings",
        height=6,
        style="Budget.Treeview",
        selectmode="browse",
    )
    for column, heading, width in (
        ("name", "Projeto", 160),
        ("material", "Material", 105),
        ("energy", "Energia", 105),
        ("labor", "Mão de obra", 110),
        ("cost", "Custo total", 110),
        ("profit", "Lucro", 100),
        ("price", "Preço final", 115),
    ):
        budget_table.heading(column, text=heading)
        budget_table.column(column, width=width, minwidth=75, stretch=False)
    budget_scrollbar = ttk.Scrollbar(
        budget_section, orient="horizontal", command=budget_table.xview
    )
    budget_table.configure(xscrollcommand=budget_scrollbar.set)
    budget_table.grid(row=3, column=0, sticky="ew")
    budget_scrollbar.grid(row=4, column=0, sticky="ew")
    budget_actions = ttk.Frame(budget_section, style="Card.TFrame")
    budget_actions.grid(row=5, column=0, sticky="ew", pady=(10, 0))
    budget_actions.columnconfigure((0, 1), weight=1, uniform="actions")
    editing_budget_id: str | None = None

    def refresh_budget_table() -> None:
        budget_table.delete(*budget_table.get_children())
        for index, budget in enumerate(budgets):
            budget_table.insert(
                "",
                "end",
                iid=budget.id,
                tags=("odd",) if index % 2 else (),
                values=(
                    budget.name,
                    format_currency(Decimal(budget.material_cost)),
                    format_currency(Decimal(budget.energy_cost)),
                    format_currency(Decimal(budget.labor_cost)),
                    format_currency(Decimal(budget.total_cost)),
                    format_currency(Decimal(budget.profit)),
                    format_currency(Decimal(budget.final_price)),
                ),
            )

    def cancel_budget_edit() -> None:
        nonlocal editing_budget_id
        editing_budget_id = None
        budget_name.delete(0, "end")
        budget_name.insert(0, "Nome do projeto ou peça")
        budget_name.configure(foreground="#9AA7BA")
        save_budget_button.configure(text="Salvar orçamento")
        cancel_edit_button.grid_remove()

    def save_current_budget() -> None:
        nonlocal budgets, editing_budget_id
        name = budget_name.get().strip()
        if not name or name == "Nome do projeto ou peça":
            messagebox.showerror(
                "Nome do orçamento", "Informe um nome para o orçamento.", parent=root
            )
            budget_name.focus_set()
            return
        quote = calculate(show_errors=True)
        if quote is None:
            return

        saved = SavedBudget(
            id=editing_budget_id or str(uuid4()),
            name=name,
            inputs={key: entry.get() for key, entry in entries.items()},
            material_cost=str(quote.material_cost),
            energy_cost=str(quote.energy_cost),
            labor_cost=str(quote.labor_cost),
            total_cost=str(quote.total_cost),
            profit=str(quote.profit),
            final_price=str(quote.final_price),
        )
        if editing_budget_id:
            updated_budgets = [
                saved if item.id == editing_budget_id else item for item in budgets
            ]
        else:
            updated_budgets = [*budgets, saved]
        try:
            budget_store.save(updated_budgets)
        except ValueError as error:
            messagebox.showerror("Erro ao salvar orçamento", str(error), parent=root)
            return
        budgets = updated_budgets
        refresh_budget_table()
        cancel_budget_edit()

    def edit_selected_budget() -> None:
        nonlocal editing_budget_id
        selected = budget_table.selection()
        if not selected:
            messagebox.showinfo(
                "Selecione um orçamento",
                "Selecione um orçamento na tabela para editar.",
                parent=root,
            )
            return
        budget = next(item for item in budgets if item.id == selected[0])
        for key, entry in entries.items():
            entry.delete(0, "end")
            entry.insert(0, budget.inputs[key])
        budget_name.delete(0, "end")
        budget_name.insert(0, budget.name)
        budget_name.configure(foreground=palette["text"])
        editing_budget_id = budget.id
        save_budget_button.configure(text="Atualizar orçamento")
        cancel_edit_button.grid()
        calculate(show_errors=True)
        canvas.yview_moveto(0)
        budget_name.focus_set()

    def delete_selected_budget() -> None:
        nonlocal budgets
        selected = budget_table.selection()
        if not selected:
            messagebox.showinfo(
                "Selecione um orçamento",
                "Selecione um orçamento na tabela para excluir.",
                parent=root,
            )
            return
        budget = next(item for item in budgets if item.id == selected[0])
        if not messagebox.askyesno(
            "Excluir orçamento",
            f'Deseja excluir o orçamento "{budget.name}"?',
            parent=root,
        ):
            return
        updated_budgets = [item for item in budgets if item.id != budget.id]
        try:
            budget_store.save(updated_budgets)
        except ValueError as error:
            messagebox.showerror("Erro ao excluir orçamento", str(error), parent=root)
            return
        budgets = updated_budgets
        refresh_budget_table()
        if editing_budget_id == budget.id:
            cancel_budget_edit()

    save_budget_button = ttk.Button(
        budget_actions,
        text="Salvar orçamento",
        style="Accent.TButton",
        command=save_current_budget,
    )
    save_budget_button.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=2)
    edit_budget_button = ttk.Button(
        budget_actions, text="Editar selecionado", command=edit_selected_budget
    )
    edit_budget_button.grid(row=0, column=1, sticky="ew", padx=(4, 0), pady=2)
    delete_budget_button = ttk.Button(
        budget_actions, text="Excluir selecionado", command=delete_selected_budget
    )
    delete_budget_button.grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=2)
    cancel_edit_button = ttk.Button(
        budget_actions, text="Cancelar edição", command=cancel_budget_edit
    )
    cancel_edit_button.grid(row=1, column=1, sticky="ew", padx=(4, 0), pady=2)
    cancel_edit_button.grid_remove()
    refresh_budget_table()

    formula_section = ttk.Frame(container, style="Card.TFrame", padding=(20, 16))
    formula_section.grid(
        row=5, column=0, columnspan=2, sticky="ew", pady=(14, 0)
    )
    formula_section.columnconfigure(1, weight=1)
    ttk.Label(
        formula_section, text="Como funciona o cálculo", style="CardTitle.TLabel"
    ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 7))
    formulas = (
        ("Material", "peso (g) × preço do filamento (R$/kg) ÷ 1.000"),
        ("Energia", "potência (W) ÷ 1.000 × tempo (h) × tarifa (R$/kWh)"),
        ("Mão de obra", "tempo (min) ÷ 60 × valor por hora (R$/h)"),
        ("Custo total", "material + energia + mão de obra"),
        ("Preço final", "custo total × (1 + margem de lucro (%) ÷ 100)"),
    )
    for row, (label, formula) in enumerate(formulas, start=1):
        ttk.Label(formula_section, text=label, style="Formula.TLabel").grid(
            row=row, column=0, sticky="w", padx=(0, 18), pady=3
        )
        ttk.Label(
            formula_section, text=formula, style="FormulaValue.TLabel",
            wraplength=520,
        ).grid(row=row, column=1, sticky="w", pady=3)
    ttk.Label(
        formula_section,
        text="Os valores monetários são arredondados para centavos. Campos opcionais em branco são considerados zero.",
        style="CardHint.TLabel",
        wraplength=780,
        justify="left",
    ).grid(row=len(formulas) + 1, column=0, columnspan=2, sticky="w", pady=(7, 0))

    apply_theme()
    root.mainloop()


if __name__ == "__main__":
    main()
