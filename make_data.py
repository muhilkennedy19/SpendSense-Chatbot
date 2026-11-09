"""
make_data.py  —  Generates a realistic SYNTHETIC procurement spend dataset.
Reproducible (fixed random seed). Output: data/procurement_spend.csv
Run:  python3 make_data.py
"""
import csv, random, datetime, os

random.seed(42)
os.makedirs("data", exist_ok=True)
OUT = "data/procurement_spend.csv"

# category -> (unit_price_low, unit_price_high, [suppliers])
categories = {
    "IT Hardware":           (300, 2500,   ["Dell Technologies", "HP Inc.", "Lenovo Group", "Cisco Systems", "Apple Inc."]),
    "Software & SaaS":       (1000, 60000, ["Microsoft", "SAP SE", "Oracle", "Salesforce", "Adobe"]),
    "Logistics & Freight":   (500, 40000,  ["DHL Supply Chain", "Kuehne+Nagel", "DB Schenker", "Maersk", "FedEx"]),
    "Raw Materials":         (2000, 120000,["BASF", "Dow Chemical", "ArcelorMittal", "LyondellBasell", "Alcoa"]),
    "Office Supplies":       (50, 1500,    ["Staples", "Office Depot", "Lyreco", "Amazon Business"]),
    "Professional Services": (2000, 90000, ["Deloitte", "Accenture", "PwC", "KPMG", "McKinsey"]),
    "MRO":                   (200, 15000,  ["Grainger", "Fastenal", "RS Components", "Bosch"]),
    "Marketing":             (500, 50000,  ["Ogilvy", "WPP", "Publicis", "Nielsen"]),
}
regions     = ["North America", "EMEA", "APAC", "LATAM"]
departments = ["IT", "Operations", "Finance", "Marketing", "R&D", "Facilities", "Sales", "HR"]
terms       = ["Net 15", "Net 30", "Net 45", "Net 60"]
buyers      = ["A. Sharma", "L. Chen", "M. Okafor", "S. Muller", "J. Rossi", "P. Nguyen", "R. Gupta", "K. Silva"]

start = datetime.date(2023, 7, 1)
end   = datetime.date(2025, 6, 30)
span  = (end - start).days

rows = []
N = 2600
for i in range(1, N + 1):
    cat = random.choice(list(categories))
    lo, hi, suppliers = categories[cat]
    supplier = random.choice(suppliers)
    d = start + datetime.timedelta(days=random.randint(0, span))
    qty = random.randint(1, 50) if cat in ("IT Hardware", "Office Supplies", "MRO") else random.randint(1, 10)
    unit = round(random.uniform(lo, hi), 2)
    amount = round(qty * unit, 2)
    on_contract = random.random() > 0.30            # ~30% off-contract = "maverick" spend
    contract_id = f"C-{random.randint(1000, 9999)}" if on_contract else ""
    promised = random.randint(3, 30)
    delay = max(0, int(random.gauss(0 if on_contract else 3, 4)))  # off-contract tends to run later
    actual = promised + delay
    q = (d.month - 1) // 3 + 1
    rows.append([
        f"PO-{d.year}-{i:05d}", d.isoformat(), f"FY{d.year} Q{q}", supplier, cat,
        random.choice(departments), random.choice(regions), qty, unit, amount, "USD",
        random.choice(terms), contract_id, random.choice(buyers), promised, actual,
        "Yes" if actual <= promised else "No",
    ])

header = ["po_id","po_date","fiscal_quarter","supplier","category","department","region",
          "quantity","unit_price","amount","currency","payment_terms","contract_id","buyer",
          "delivery_days_promised","delivery_days_actual","on_time"]
with open(OUT, "w", newline="") as f:
    w = csv.writer(f); w.writerow(header); w.writerows(rows)

total = sum(r[9] for r in rows)
maverick = sum(r[9] for r in rows if r[12] == "")
print(f"Wrote {len(rows)} rows -> {OUT}")
print(f"Date range: {start} .. {end}")
print(f"Total spend: ${total:,.0f}")
print(f"Off-contract (maverick) spend: ${maverick:,.0f}  ({maverick/total*100:.1f}%)")
print(f"Categories: {len(categories)} | Suppliers: {sum(len(v[2]) for v in categories.values())}")
