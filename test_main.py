import unittest
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from main import (
    BudgetStore,
    SavedBudget,
    calculate_quote,
    parse_decimal,
    parse_duration,
    parse_optional_decimal,
)


class CalculateQuoteTests(unittest.TestCase):
    def test_calculates_all_costs_and_profit_margin(self) -> None:
        quote = calculate_quote(
            material_grams=Decimal("100"),
            filament_price_per_kg=Decimal("120"),
            print_hours=Decimal("2"),
            print_minutes=Decimal("30"),
            printer_power_watts=Decimal("200"),
            energy_price_per_kwh=Decimal("1"),
            labor_minutes=Decimal("30"),
            labor_rate_per_hour=Decimal("20"),
            profit_margin_percent=Decimal("50"),
        )

        self.assertEqual(quote.print_hours, Decimal("2.5"))
        self.assertEqual(quote.material_cost, Decimal("12.00"))
        self.assertEqual(quote.energy_cost, Decimal("0.50"))
        self.assertEqual(quote.labor_cost, Decimal("10.00"))
        self.assertEqual(quote.total_cost, Decimal("22.50"))
        self.assertEqual(quote.profit, Decimal("11.25"))
        self.assertEqual(quote.final_price, Decimal("33.75"))

    def test_allows_zero_optional_costs(self) -> None:
        quote = calculate_quote(
            material_grams=Decimal("1"),
            filament_price_per_kg=Decimal("10"),
            print_hours=Decimal("1"),
            print_minutes=Decimal("0"),
            printer_power_watts=Decimal("100"),
            energy_price_per_kwh=Decimal("0"),
            labor_minutes=Decimal("0"),
            labor_rate_per_hour=Decimal("0"),
            profit_margin_percent=Decimal("0"),
        )

        self.assertEqual(quote.total_cost, Decimal("0.01"))
        self.assertEqual(quote.final_price, Decimal("0.01"))

    def test_rejects_invalid_print_minutes(self) -> None:
        with self.assertRaisesRegex(ValueError, "entre 0 e 59"):
            calculate_quote(
                material_grams=Decimal("10"),
                filament_price_per_kg=Decimal("100"),
                print_hours=Decimal("1"),
                print_minutes=Decimal("60"),
                printer_power_watts=Decimal("100"),
                energy_price_per_kwh=Decimal("1"),
                labor_minutes=Decimal("0"),
                labor_rate_per_hour=Decimal("0"),
                profit_margin_percent=Decimal("0"),
            )

    def test_rejects_zero_print_duration(self) -> None:
        with self.assertRaisesRegex(ValueError, "tempo de impressão"):
            calculate_quote(
                material_grams=Decimal("10"),
                filament_price_per_kg=Decimal("100"),
                print_hours=Decimal("0"),
                print_minutes=Decimal("0"),
                printer_power_watts=Decimal("100"),
                energy_price_per_kwh=Decimal("1"),
                labor_minutes=Decimal("0"),
                labor_rate_per_hour=Decimal("0"),
                profit_margin_percent=Decimal("0"),
            )

    def test_parses_portuguese_decimal_separator(self) -> None:
        self.assertEqual(parse_decimal(" 12,75 ", "teste"), Decimal("12.75"))

    def test_rejects_invalid_decimal(self) -> None:
        with self.assertRaisesRegex(ValueError, "número válido"):
            parse_decimal("abc", "teste")

    def test_optional_decimal_defaults_blank_to_zero(self) -> None:
        self.assertEqual(parse_optional_decimal("  ", "teste"), Decimal("0"))

    def test_optional_decimal_still_rejects_invalid_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "número válido"):
            parse_optional_decimal("abc", "teste")

    def test_parses_combined_print_duration(self) -> None:
        self.assertEqual(parse_duration("2:30"), (Decimal("2"), Decimal("30")))

    def test_rejects_minutes_outside_combined_duration(self) -> None:
        with self.assertRaisesRegex(ValueError, "entre 0 e 59"):
            parse_duration("2:60")

    def test_rejects_combined_duration_without_separator(self) -> None:
        with self.assertRaisesRegex(ValueError, "horas:minutos"):
            parse_duration("2 horas e 30 minutos")


class BudgetStoreTests(unittest.TestCase):
    def test_saves_and_loads_budgets(self) -> None:
        with TemporaryDirectory() as directory:
            store = BudgetStore(Path(directory) / "budgets.json")
            budget = SavedBudget(
                id="budget-1",
                name="Peça teste",
                inputs={
                    "material_grams": "100",
                    "filament_price_per_kg": "120",
                    "print_duration": "2:30",
                    "printer_power_watts": "200",
                    "energy_price_per_kwh": "1",
                    "labor_minutes": "30",
                    "labor_rate_per_hour": "20",
                    "profit_margin_percent": "50",
                },
                material_cost="12.00",
                energy_cost="0.50",
                labor_cost="10.00",
                total_cost="22.50",
                profit="11.25",
                final_price="33.75",
            )

            store.save([budget])

            self.assertEqual(store.load(), [budget])

    def test_missing_file_starts_with_empty_list(self) -> None:
        with TemporaryDirectory() as directory:
            store = BudgetStore(Path(directory) / "budgets.json")

            self.assertEqual(store.load(), [])

    def test_rejects_invalid_budget_file(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "budgets.json"
            path.write_text('{"not": "a list"}', encoding="utf-8")
            store = BudgetStore(path)

            with self.assertRaisesRegex(ValueError, "formato inválido"):
                store.load()


if __name__ == "__main__":
    unittest.main()
