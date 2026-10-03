import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

project_folder = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description="Review supplier shipment data from CSV or Excel.")
parser.add_argument(
    "--input",
    type=Path,
    default=project_folder / "data" / "raw" / "supplier_deliveries.csv",
    help="Input .csv or .xlsx file (default: sample CSV)",
)
input_file = parser.parse_args().input
if not input_file.exists():
    raise SystemExit(f"Input file not found: {input_file}")
if input_file.suffix.lower() == ".csv":
    shipments = pd.read_csv(input_file)
elif input_file.suffix.lower() == ".xlsx":
    shipments = pd.read_excel(input_file)
else:
    raise SystemExit("Please choose a .csv or .xlsx input file.")

duplicate_ids = shipments["shipment_id"].duplicated()
important_columns = [
    "shipment_id", "supplier", "material", "planned_delivery_date",
    "actual_delivery_date", "quantity_ordered", "quantity_received", "cost_per_unit",
]
missing_values = shipments[important_columns].isna().sum()
planned = pd.to_datetime(shipments["planned_delivery_date"], format="mixed", dayfirst=True, errors="coerce")
actual = pd.to_datetime(shipments["actual_delivery_date"], format="mixed", dayfirst=True, errors="coerce")
invalid_date_rows = planned.isna() | actual.isna()
invalid_numeric_rows = (
    (shipments["quantity_ordered"] <= 0)
    | (shipments["quantity_received"] < 0)
    | (shipments["cost_per_unit"] <= 0)
)
print("Duplicate shipment IDs:", int(duplicate_ids.sum()))
print("Blank values in important fields:")
print(missing_values)
print("Rows with impossible quantities or costs:", int(invalid_numeric_rows.sum()))
print("Rows with unreadable delivery dates:", int(invalid_date_rows.sum()))
if duplicate_ids.any() or missing_values.any() or invalid_numeric_rows.any() or invalid_date_rows.any():
    raise SystemExit("Please fix data-quality issues before reviewing shipments.")

print(shipments.head())
print("Number of shipments:", len(shipments))
late_shipments = actual > planned
print("Late shipments:", late_shipments.sum())
late_by_supplier = shipments.assign(is_late=late_shipments).groupby("supplier")["is_late"].sum()
print("\nLate shipments by supplier:")
print(late_by_supplier)
total_by_supplier = shipments.groupby("supplier").size()
late_percent = (late_by_supplier / total_by_supplier * 100).round(1)
print("\nPercent late by supplier:")
print(late_percent)
short_shipments = shipments["quantity_received"] < shipments["quantity_ordered"]
print("\nShort shipments:", short_shipments.sum())
print("Short shipment details:")
print(shipments.loc[short_shipments, ["shipment_id", "supplier", "quantity_ordered", "quantity_received"]])
short_details = shipments.loc[short_shipments, ["shipment_id", "supplier", "material", "unit", "quantity_ordered", "quantity_received"]].copy()
short_details["quantity_missing"] = short_details["quantity_ordered"] - short_details["quantity_received"]
print("\nMissing quantity by short shipment:")
print(short_details[["shipment_id", "quantity_missing"]])
short_details["percent_missing"] = (short_details["quantity_missing"] / short_details["quantity_ordered"] * 100).round(1)
print("\nPercent missing by short shipment:")
print(short_details[["shipment_id", "percent_missing"]])
large_shortages = short_details[short_details["percent_missing"] >= 10]
print("\nShortage review messages:")
if large_shortages.empty:
    print("No shipment crossed the practice threshold.")
else:
    for shipment in large_shortages.itertuples():
        print(
            f"{shipment.shipment_id}: {shipment.percent_missing}% of the order is missing. "
            "Check the receiving record and follow up with the supplier."
        )
late_details = shipments.loc[late_shipments, ["shipment_id", "supplier"]].copy()
late_details["days_late"] = (actual[late_shipments] - planned[late_shipments]).dt.days
print("\nLate shipment details:")
print(late_details)
delay_days = (actual - planned).dt.days.clip(lower=0)
average_delay = shipments.assign(days_late=delay_days).groupby("supplier")["days_late"].mean().round(1)
print("\nAverage days late per shipment (on-time = 0):")
print(average_delay)
typical_cost = shipments.groupby(["supplier", "material"])["cost_per_unit"].median().round(2)
print("\nTypical unit cost by supplier and material (middle value):")
print(typical_cost)
shipments["typical_cost"] = shipments.groupby(["supplier", "material"])["cost_per_unit"].transform("median")
shipments["cost_change_percent"] = ((shipments["cost_per_unit"] - shipments["typical_cost"]) / shipments["typical_cost"] * 100).round(1)
aluminium_costs = shipments[shipments["material"] == "Aluminium sheet"]
print("\nMeridian aluminium unit costs compared with its usual cost:")
print(aluminium_costs[["shipment_id", "cost_per_unit", "typical_cost", "cost_change_percent"]])
high_costs = shipments[shipments["cost_change_percent"] >= 50]
print("\nUnit cost review messages:")
if high_costs.empty:
    print("No shipment crossed the practice threshold.")
else:
    for shipment in high_costs.itertuples():
        print(
            f"{shipment.shipment_id}: {shipment.material} costs {shipment.currency} "
            f"{shipment.cost_per_unit:.2f} per {shipment.unit}, "
            f"{shipment.cost_change_percent:.1f}% above the usual "
            f"{shipment.typical_cost:.2f}. Check the purchase order, invoice, "
            "and any approved price changes."
        )
report_lines = [
    "Supply Chain Monitoring Report",
    "Fictional practice data; findings need human review.",
    "Data quality checks:",
    f"  Duplicate shipment IDs: {int(duplicate_ids.sum())}",
    f"  Blank important fields: {int(missing_values.sum())}",
    f"  Rows with impossible quantities or costs: {int(invalid_numeric_rows.sum())}",
    f"  Rows with unreadable delivery dates: {int(invalid_date_rows.sum())}",
    f"Shipments reviewed: {len(shipments)}",
    f"Late shipments: {int(late_shipments.sum())}",
    "Late shipments by supplier:",
]
for supplier, count in late_by_supplier.items():
    report_lines.append(f"  {supplier}: {int(count)}")
report_lines.append(f"Short shipments: {int(short_shipments.sum())}")
for shipment in short_details.itertuples():
    report_lines.append(f"  {shipment.shipment_id}: {int(shipment.quantity_missing)} items missing")
report_lines.append("Unit cost items to review:")
for shipment in high_costs.itertuples():
    report_lines.append(
        f"  {shipment.shipment_id}: {shipment.material} at {shipment.currency} "
        f"{shipment.cost_per_unit:.2f} per {shipment.unit}, "
        f"{shipment.cost_change_percent:.1f}% above the usual cost."
    )
report_path = project_folder / "reports" / "summary_report.txt"
report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
print(f"\nReport saved to: {report_path}")
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
history_path = project_folder / "reports" / f"report_{timestamp}.txt"
history_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
print(f"Dated copy saved to: {history_path}")
cost_baseline = shipments.groupby(["supplier", "material"])["cost_per_unit"].agg(["mean", "std"]).round(2)
print("\nStatistical cost baseline (average and usual variation):")
print(cost_baseline)
cost_groups = shipments.groupby(["supplier", "material"])["cost_per_unit"]
shipments["cost_average"] = cost_groups.transform("mean")
shipments["cost_spread"] = cost_groups.transform("std")
shipments["cost_z_score"] = ((shipments["cost_per_unit"] - shipments["cost_average"]) / shipments["cost_spread"]).round(2)
print("\nMeridian aluminium costs measured in usual price wiggles (z-score):")
print(shipments.loc[shipments["material"] == "Aluminium sheet", ["shipment_id", "cost_per_unit", "cost_z_score"]])
statistical_cost_flags = shipments[
    (shipments["cost_z_score"] > 2) & (shipments["cost_change_percent"] >= 10)
]
print("\nStatistical cost review messages (z-score above 2 and at least 10% higher):")
if statistical_cost_flags.empty:
    print("No shipment crossed the practice threshold.")
else:
    for shipment in statistical_cost_flags.itertuples():
        print(
            f"{shipment.shipment_id}: unit cost {shipment.currency} {shipment.cost_per_unit:.2f} "
            f"is {shipment.cost_z_score:.2f} usual price wiggles above its supplier/material average "
            f"and {shipment.cost_change_percent:.1f}% above the usual cost. "
            "Review the purchase order and invoice; this is a flag, not proof of an error."
        )
report_lines.append("Statistical cost review candidates (z-score above 2 and at least 10% higher):")
if statistical_cost_flags.empty:
    report_lines.append("  None")
else:
    for shipment in statistical_cost_flags.itertuples():
        report_lines.append(
            f"  {shipment.shipment_id}: {shipment.material} at {shipment.currency} "
            f"{shipment.cost_per_unit:.2f} per {shipment.unit}; "
            f"z-score {shipment.cost_z_score:.2f}, "
            f"{shipment.cost_change_percent:.1f}% above usual cost. Human review needed."
        )
report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
history_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
print("Statistical finding added to the latest and dated reports.")
review_rows = []
late_review_rows = shipments.loc[late_shipments, ["shipment_id", "supplier", "material"]].copy()
late_review_rows["days_late"] = delay_days.loc[late_shipments]
for shipment in late_review_rows.itertuples():
    review_rows.append({
        "shipment_id": shipment.shipment_id,
        "supplier": shipment.supplier,
        "material": shipment.material,
        "finding": "Late delivery",
        "details": f"{int(shipment.days_late)} days after planned arrival",
        "recommended_follow_up": "Check carrier status and update the receiving or production plan.",
    })
high_late_rates = late_percent[late_percent >= 30]
for supplier, percentage in high_late_rates.items():
    review_rows.append({
        "shipment_id": "",
        "supplier": supplier,
        "material": "All materials",
        "finding": "Repeated late-delivery pattern",
        "details": f"{int(late_by_supplier[supplier])} of {int(total_by_supplier[supplier])} shipments late ({percentage:.1f}%)",
        "recommended_follow_up": "Review the supplier's recent lead-time commitments and recurring delivery delays.",
    })
for shipment in short_details.itertuples():
    review_rows.append({
        "shipment_id": shipment.shipment_id,
        "supplier": shipment.supplier,
        "material": shipment.material,
        "finding": "Short shipment",
        "details": f"{int(shipment.quantity_missing)} {shipment.unit} missing ({shipment.percent_missing:.1f}% of the order)",
        "recommended_follow_up": "Check the receiving record and follow up with the supplier.",
    })
for shipment in statistical_cost_flags.itertuples():
    review_rows.append({
        "shipment_id": shipment.shipment_id,
        "supplier": shipment.supplier,
        "material": shipment.material,
        "finding": "Unusual unit cost",
        "details": f"{shipment.currency} {shipment.cost_per_unit:.2f} per {shipment.unit}; {shipment.cost_change_percent:.1f}% above usual cost",
        "recommended_follow_up": "Review the purchase order, invoice, and approved price changes.",
    })
review_export = pd.DataFrame(review_rows)
review_export_path = project_folder / "reports" / "review_findings.csv"
review_export.to_csv(review_export_path, index=False)
print(f"Review findings CSV saved to: {review_export_path}")
email_lines = [
    "Subject: Supply chain shipment review needed",
    "",
    f"Monitoring run: {timestamp}",
    f"Review items found: {len(review_rows)}",
    "Please review these shipment and supplier findings:",
    "",
]
for item in review_rows:
    label = item["shipment_id"] or "Supplier summary"
    email_lines.append(f"- {label} | {item['supplier']} | {item['finding']}: {item['details']}")
    email_lines.append(f"  Suggested follow-up: {item['recommended_follow_up']}")
email_draft_path = project_folder / "reports" / "email_alert_draft.txt"
email_draft_path.write_text("\n".join(email_lines) + "\n", encoding="utf-8")
print(f"Email alert draft saved to: {email_draft_path}")
