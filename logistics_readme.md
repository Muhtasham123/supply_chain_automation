# Logistics Master — Database Migration Project

**Goal:** Move the `Qadri-Group-Logistics-Master.xlsx` workbook into a normalized PostgreSQL database, loaded by independent Python scripts (one per sheet).

**Status:** Schema finalized, all scripts written and tested end-to-end against the real workbook. Full pipeline verified on PostgreSQL 16.

---

## 1. What We Did (Summary of the Journey)

### 1.1 Analyzed the workbook
The source file has 4 data sheets: **Export Documentation Database** (163 rows), **Shipment Master Database** (165), **Master Packing Database** (1,375), **Inbound & Outbound Shifting** (464). Analysis of the actual data revealed:

- The natural key (Exp #, Batch #) is **dirty and inconsistent across sheets** — ordinal suffixes (`2360th` vs `2360`), embedded batch numbers (`2224-2 B`), free-text keys, one duplicate. Only 88 of ~164 keys matched exactly between the documentation and shipment sheets.
- The four "status tables" (Customs/Customer/Bank/Other) were ~21 columns that all encode the same fact: *a document, for a party, with a status*.
- Container info was spread across 8 wide columns (Standard/Open Top/Flat Rack/OOG × 20'/40'), mostly empty.
- Many columns were **Excel formulas** (completion %s, delays, variances, savings) — computed values that should never be stored in a database.
- Target Packing Date and Quoted Packing Cost are **100% empty in the source** — the packing performance views are ready but will show data only once these are filled in Excel.

### 1.2 Designed the schema
Key decisions, in order of importance:

| Decision | Reason |
|---|---|
| **`exports` parent table with surrogate `export_id`** | The dirty natural key can't be trusted as a join key; surrogate + cleaned key + raw key preserved solves matching AND traceability |
| **`batch_no NOT NULL DEFAULT ''`** | UNIQUE(exp_no, batch_no) does not block duplicates if batch_no is NULL (Postgres treats NULLs as distinct — verified live) |
| **Documentation fields merged into `exports`** | 1:1 relationship; a separate table bought nothing but a join |
| **`export_documents` in long format** | One row per (export, party, document type) replaces 21 status columns; loading is a single melt; all counts/%s become queries |
| **`shipment_containers` in long format** | One row per container size+type replaces 8 wide columns; extensible without schema changes |
| **Computed Excel columns NOT stored** | Recreated as SQL views — always fresh, can never disagree with the data |
| **Unmatched keys load with `export_id = NULL` + raw key kept** | No data loss; rows can be linked later with a simple UPDATE |

### 1.3 Wrote and tested the ETL pipeline
Five independent scripts (one per sheet) plus one shared module. Tested end-to-end on PostgreSQL 16 against the real workbook — final verified results:

| Table | Rows loaded | Notes |
|---|---|---|
| exports | 717 | union of keys from all 4 sheets |
| exports (doc fields) | 163 updated | 163/163 keys matched after cleaning |
| export_documents | 3,053 | melted from 21 status columns |
| export_shipments | 165 | only 1 unmatched key (was 76 before cleaning) |
| shipment_containers | 80 | melted from 8 wide columns |
| packing_details | 1,375 | 707 Local rows correctly NULL-linked |
| shifting_movements | 464 | source keys were junk; raw preserved |

---

## 2. Folder Structure

```
logistics-db/
│
├── sql/
│   ├── schema.sql              # CREATE TABLE statements (the finalized schema)
│   └── views.sql               # CREATE VIEW statements (computed metrics)
│
├── etl/
│   ├── etl_common.py           # shared module: cleaning, key logic, DB connection
│   ├── load_01_exports.py      # builds the parent table — RUN FIRST
│   ├── load_02_export_documentation.py
│   ├── load_03_shipments.py
│   ├── load_04_packing.py
│   └── load_05_shifting.py
│
├── data/
│   └── Qadri-Group-Logistics-Master.xlsx   # source workbook
│
└── README.md                   # this file
```

(Scripts locate the workbook via the `LOGISTICS_XLSX` environment variable, so the exact folder layout is flexible — this is the recommended arrangement.)

---

## 3. Purpose of Each File

### sql/schema.sql
The six finalized tables:

- **`exports`** — parent table, one row per consignment. Holds the surrogate `export_id`, the cleaned natural key (`exp_no`, `batch_no`), the original raw key text (`exp_batch_raw`), shared identity fields (customer, country, POD), and the merged documentation fields (shipping term/agent, bank, payment term, BL type, gate-out/cut-off/sailing dates, handed_over_to).
- **`export_documents`** — long format, one row per export + party + document type + status. Replaces the four wide status-column groups.
- **`export_shipments`** — one row per shipment; logistics data (agents, line, CRO, ports, dates, stuffing) plus all cost components (sea freight quoted/actual, LHR-KHI, fumigation, lashing, QFL, clearance, DHL, insurance, wharfage) merged in.
- **`shipment_containers`** — long format, one row per shipment + container size + type + qty.
- **`packing_details`** — one row per packing job; RFD dates and packing costs merged in; `export_id` is NULL for Local business.
- **`shifting_movements`** — one row per inbound/outbound movement; vehicle, cost, and the seven status columns merged in; `shipment_ref_idm` is the future bridge to the imports database.

### sql/views.sql
The computed Excel columns, recreated as always-fresh queries:

- **`v_documentation_completion`** — total/completed/pending documents, overall and per-party completion %s, missing-document lists per export.
- **`v_shipment_metrics`** — transit days, QFL stay, freight variance, total logistics cost, cost per kg.
- **`v_packing_metrics`** — packing/RFD/material delays, on-time flag, cost variance and %.
- **`v_shifting_metrics`** — savings (Rs and %), freight variance, rate per kg, transit days.

Views store no data and never need refreshing — they compute from live tables on every query.

### etl/etl_common.py
The shared foundation every loader imports. Contains:

- **`make_export_key(exp, batch)`** — THE critical function: normalizes keys the same way in every script (strips ordinal suffixes like `2360th` → `2360`, trims dashes/spaces, converts placeholders). Because all scripts share it, the same consignment resolves to the same key everywhere.
- **`clean_text / clean_status / clean_number / clean_int / clean_date`** — placeholder-aware converters (`-`, `--`, blank → NULL; DD/MM/YYYY dates; numbers with commas/currency text).
- **`parse_qty_uom()`** — splits values like "1 Nos." into (1.0, "Nos.").
- **`get_connection()`** — reads PGHOST / PGDATABASE / PGUSER / PGPASSWORD environment variables.
- **`load_export_map(conn)`** — fetches `{(exp_no, batch_no): export_id}` so child loaders can resolve Excel keys to surrogate IDs.
- **`read_sheet()`** — opens the workbook (path from `LOGISTICS_XLSX`).

### etl/load_01_exports.py  — RUN FIRST
Reads the key columns from **all four sheets**, cleans every key through `make_export_key()`, deduplicates, and inserts one parent row per distinct consignment (with customer/country/POD where available). Uses `ON CONFLICT DO NOTHING`, so it is safe to re-run.

### etl/load_02_export_documentation.py
Reads **Export Documentation Database**. Two actions:
1. `UPDATE exports SET shipping_term, shipping_agent, bank, ...` — writes the merged 1:1 documentation fields onto the parent rows.
2. Melts the 21 status columns into `export_documents` rows via an explicit `STATUS_MAP` (column name → party + document type).

Idempotent: deletes each export's existing document rows before re-inserting, so re-runs don't duplicate.

Column renames handled here: Excel "Bank Name" → `bank`, "Handed Over To Mr.Umar" → `handed_over_to`.

### etl/load_03_shipments.py
Reads **Shipment Master Database** into `export_shipments` (one INSERT per row, `RETURNING shipment_id`), then melts the 8 container columns into `shipment_containers` rows for that shipment. Unmatched keys load with `export_id = NULL` and the raw key preserved. Renames handled: "Pick-up T." → `pick_up_time`, "Pkgs." parsed as integer.

### etl/load_04_packing.py
Reads **Master Packing Database** into `packing_details`. Splits "Qty" text into `qty` + `qty_uom`. Local-business rows (no Exp #) load with `export_id = NULL` by design — they are domestic jobs with no export parent.

### etl/load_05_shifting.py
Reads **Inbound & Outbound Shifting** into `shifting_movements`. The sheet's own "Primary Key" column is junk (`--` in 433 of 464 rows), so rows get the surrogate `shifting_id`. "Shipment Ref. / IDM #" → `shipment_ref_idm` (the future link to the imports database for inbound moves).

---

## 4. How to Run

```bash
# 1. Install dependencies
pip install pandas openpyxl psycopg2-binary

# 2. Create the database and schema
psql -d your_db -f sql/schema.sql
psql -d your_db -f sql/views.sql

# 3. Point the scripts at your environment
export PGHOST=localhost
export PGDATABASE=logistics
export PGUSER=postgres
export PGPASSWORD=yourpassword
export LOGISTICS_XLSX=data/Qadri-Group-Logistics-Master.xlsx

# 4. Run the loaders — 01 first, the rest in any order
python etl/load_01_exports.py
python etl/load_02_export_documentation.py
python etl/load_03_shipments.py
python etl/load_04_packing.py
python etl/load_05_shifting.py
```

(On Windows, use `set` instead of `export`.)

**Re-running:** load_01 and load_02 are safe to re-run as-is. load_03/04/05 plain-insert — truncate their tables first if reloading:
`TRUNCATE export_shipments CASCADE; TRUNCATE packing_details; TRUNCATE shifting_movements;`

---

## 5. Known Data Issues (carried from the source workbook)

1. **~1 shipment and ~50 legacy keys don't auto-match** — loaded with `export_id = NULL`, original key kept in `exp_batch_raw`. Fix manually with `UPDATE ... SET export_id = ...` as they're identified.
2. **Target Packing Date and Quoted Packing Cost are empty in Excel** — packing delay/cost-variance views return NULL until the team starts filling these columns.
3. **Shifting sheet has no usable key** — movements are not linked to exports; the `shipment_ref_idm` column (LC #, IDM #) is the candidate bridge once the imports database exists.
4. **Data-entry standardization needed going forward:** consistent Exp # format (no ordinal suffixes), batch numbers in the Batch column (not embedded in Exp #), and dropdown-validated status values.
