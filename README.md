# Supply Chain Anomaly Monitoring Agent

A beginner-friendly Python project that reviews fictional supplier shipment data. It uses Pandas, simple business rules, and a basic statistical check. It does not use AI to decide whether a shipment is wrong; it points out records for a person to review.

## What it checks

- Duplicate shipment IDs, blank important fields, and impossible quantities or costs. The script stops before analysis if it finds these issues.
- Late deliveries and late-delivery counts by supplier.
- Short shipments, including how many items are missing.
- Unusually high unit costs compared with the same supplier and material.

## Run it on Mac

Open Terminal in this project folder. Turn on the project's Python workspace, then run the script:

```sh
source .venv/bin/activate
python src/inspect_data.py
```

The default input is the sample CSV. To use the sample Excel workbook instead, run:

```sh
python src/inspect_data.py --input data/raw/supplier_deliveries.xlsx
```

The workbook's first sheet must use the same column headers as the sample file.

If the packages are not installed yet, first run:

```sh
python -m pip install -r requirements.txt
```

## Reports

- `reports/summary_report.txt` is replaced with the latest run.
- `reports/report_YYYY-MM-DD_HH-MM-SS.txt` keeps a dated copy of each run.
- `reports/review_findings.csv` is an Excel-friendly list of late deliveries, short shipments, and unusual unit costs, with suggested follow-ups.
- `reports/email_alert_draft.txt` formats those findings as an email draft for review; the script does not send email.

The report summarizes the data checks, late deliveries, short receipts, and unit-cost review candidates.

## Practice thresholds and limits

The current sample settings are for learning, not universal supply-chain rules:

- A shortage is highlighted when at least 10% of the ordered quantity is missing.
- A supplier delivery pattern is highlighted when at least 30% of its shipments are late.
- A large unit-cost change is highlighted at 50% above the supplier/material's median price.
- The statistical unit-cost review requires a z-score above 2 and a price at least 10% above the median.

The dataset has only 27 fictional shipments. Small samples can make statistical results unstable, so treat every finding as a clue to check against purchase orders, invoices, receiving records, and approved supplier changes. Adjust thresholds with real operational context before using this for business decisions.
