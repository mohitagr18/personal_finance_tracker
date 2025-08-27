#!/usr/bin/env python3
"""
extract_transactions.py

Robust PDF -> table extraction pipeline using Camelot, Tabula (optional), and pdfplumber.
- Safe imports with helpful messages for missing packages.
- Suppresses noisy PDFBox logs.
- Defensive cleaning/normalization of extracted tables.
- Ensures consistent columns/indexes before concatenation.
- Saves per-table CSVs, a combined CSV, and a JSON grouped by cardholder (if present).

Configure:
  INPUT_FOLDER  = "./statements"   (put your PDFs here)
  OUTPUT_FOLDER = "./output_tables" (CSV/JSON will be written here)
"""

import os
import re
import json
import warnings
import logging
from typing import List, Dict

# === Quiet noisy Java/PDFBox logging (set early) ===
# This helps suppress Apache PDFBox stdout/stderr noise coming from tabula/camelot.
os.environ.setdefault("JAVA_TOOL_OPTIONS", "-Dorg.apache.commons.logging.Log=org.apache.commons.logging.impl.NoOpLog")
warnings.filterwarnings("ignore", category=UserWarning)

# Basic logging for the script
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("extract_transactions")

# I/O folders
INPUT_FOLDER = "./statements"
OUTPUT_FOLDER = "./output_tables"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# ---------------------------
# Safe imports / diagnostics
# ---------------------------
def _import_camelot_read_pdf():
    """
    Robust import for Camelot's read_pdf.
    Raises a helpful RuntimeError if camelot-py isn't installed correctly.
    """
    try:
        # common import
        from camelot import read_pdf as camelot_read_pdf  # type: ignore
        return camelot_read_pdf
    except Exception:
        try:
            from camelot.io import read_pdf as camelot_read_pdf  # type: ignore
            return camelot_read_pdf
        except Exception as e:
            raise RuntimeError(
                "Failed to import Camelot's read_pdf. "
                "Install the correct package with: pip uninstall camelot && pip install 'camelot-py[cv]'"
            ) from e


def _import_tabula():
    """
    Try to import tabula-py. If missing, return None (tabula is optional).
    Requires Java to be installed on the system.
    """
    try:
        import tabula  # type: ignore
        return tabula
    except Exception:
        warnings.warn("tabula-py not found. You can pip install tabula-py and install Java to enable this fallback.")
        return None


def _import_pdfplumber():
    try:
        import pdfplumber  # type: ignore
        return pdfplumber
    except Exception as e:
        raise RuntimeError("pdfplumber not installed. Run: pip install pdfplumber") from e


# ---------------------------
# Extraction functions
# ---------------------------
def extract_with_camelot(pdf_path: str) -> List["pd.DataFrame"]:
    """
    Use Camelot in both lattice and stream flavors; return list of raw DataFrames.
    """
    read_pdf = _import_camelot_read_pdf()
    dfs = []
    for flavor in ("lattice", "stream"):
        try:
            tables = read_pdf(pdf_path, pages="all", flavor=flavor)
            for t in tables:
                try:
                    df = t.df
                    if df is not None and not df.empty:
                        dfs.append(df)
                except Exception:
                    continue
        except Exception:
            continue
    return dfs


def extract_with_tabula(pdf_path: str) -> List["pd.DataFrame"]:
    """
    Use tabula-py fallback (requires Java). Returns list of DataFrames.
    """
    tabula = _import_tabula()
    if tabula is None:
        return []
    dfs = []
    try:
        tdfs = tabula.read_pdf(pdf_path, pages="all", lattice=True, multiple_tables=True, pandas_options={"dtype": str})
        if tdfs:
            dfs.extend([d for d in tdfs if getattr(d, "empty", True) is False])
    except Exception:
        pass
    try:
        tdfs = tabula.read_pdf(pdf_path, pages="all", lattice=False, multiple_tables=True, pandas_options={"dtype": str})
        if tdfs:
            dfs.extend([d for d in tdfs if getattr(d, "empty", True) is False])
    except Exception:
        pass
    return dfs


def extract_with_pdfplumber(pdf_path: str) -> List["pd.DataFrame"]:
    """
    Use pdfplumber page-wise extraction of tables.
    """
    pdfplumber = _import_pdfplumber()
    dfs = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            try:
                tables = page.extract_tables()
                for table in tables or []:
                    if not table or len(table) < 2:
                        continue
                    header = table[0]
                    rows = table[1:]
                    # ensure header values are strings
                    header = [str(h).strip() if h is not None else "" for h in header]
                    import pandas as _pd  # local import to keep top-level lighter
                    df = _pd.DataFrame(rows, columns=header)
                    if not df.empty:
                        dfs.append(df)
            except Exception:
                # some pages may fail; continue
                continue
    return dfs


def extract_all_tables(pdf_path: str) -> List["pd.DataFrame"]:
    """
    Run extractors in order and return list of raw DataFrames (may have messy columns).
    """
    raw_candidates = []
    try:
        raw_candidates.extend(extract_with_camelot(pdf_path))
    except RuntimeError as e:
        log.warning(str(e))
    # Tabula fallback
    raw_candidates.extend(extract_with_tabula(pdf_path))
    # pdfplumber fallback
    try:
        raw_candidates.extend(extract_with_pdfplumber(pdf_path))
    except RuntimeError as e:
        log.warning(str(e))

    return raw_candidates


# ---------------------------
# Cleaning / normalization
# ---------------------------
import pandas as pd


def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names to a small set of canonical names where possible.
    """
    df = df.copy()
    # unify header types to str
    df.columns = [re.sub(r"\s+", " ", str(c)).strip().lower() for c in df.columns]

    col_map: Dict[str, str] = {}
    for c in df.columns:
        if any(k in c for k in ["post date", "transaction date", "date"]):
            col_map[c] = "date"
        elif any(k in c for k in ["description", "merchant", "details", "transaction"]):
            col_map[c] = "description"
        elif any(k in c for k in ["amount", "amt", "value"]):
            col_map[c] = "amount"
        elif any(k in c for k in ["debit", "withdrawal", "charge", "dr"]):
            col_map[c] = "debit"
        elif any(k in c for k in ["credit", "payment", "deposit", "cr"]):
            col_map[c] = "credit"
        elif any(k in c for k in ["cardholder", "card holder", "member", "employee", "user"]):
            col_map[c] = "cardholder"
        elif any(k in c for k in ["last4", "last 4", "card no", "card #", "card ending"]):
            col_map[c] = "card_last4"

    df = df.rename(columns=col_map)
    return df


def _series_to_numeric_aligned(df: pd.DataFrame, col: str) -> pd.Series:
    """
    Return a numeric Series aligned to df.index for column `col`.
    If column missing -> returns zero Series.
    Cleans common formatting ($, commas, parentheses).
    """
    if col not in df.columns:
        return pd.Series(0.0, index=df.index, dtype=float)

    ser = df[col]
    # If a DataFrame (happens when duplicate column names), pick the first column
    if isinstance(ser, pd.DataFrame):
        ser = ser.iloc[:, 0]

    # Ensure Series with same index
    ser = pd.Series(ser.values, index=df.index).astype(object)

    # Normalize text
    ser = ser.fillna("").astype(str).str.strip()

    # Convert "(1,234.56)" to "-1234.56"
    ser = ser.str.replace(r"^\((.*)\)$", r"-\1", regex=True)

    # Remove currency commas and dollar signs and NBSPs and unicode minus variants
    ser = ser.str.replace(",", "", regex=False)
    ser = ser.str.replace("$", "", regex=False)
    ser = ser.str.replace("\u00A0", " ", regex=False)
    ser = ser.str.replace("−", "-", regex=False)
    ser = ser.str.replace(r"\s+", " ", regex=True).str.strip()

    # Convert empty strings to NA, then to numeric
    num = pd.to_numeric(ser.replace("", pd.NA), errors="coerce").fillna(0.0).astype(float)

    # Reindex to ensure proper alignment
    num = num.reindex(df.index).fillna(0.0).astype(float)
    return num


def _clean_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply robust cleaning to a single extracted table DataFrame.
    Returns a cleaned DataFrame with canonical columns where possible.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    # If header rows are embedded as first row (common), try to detect and fix:
    # If first row is all non-numeric and looks like header and columns are generic (0,1,2...), use it as header.
    try:
        first_row = df.iloc[0].astype(str).str.strip()
        numeric_count = sum(1 for v in first_row if re.search(r"\d", str(v)))
        if numeric_count < max(1, len(first_row) // 3) and any(re.search(r"[a-zA-Z]", str(v)) for v in first_row):
            # promote first row to header
            df.columns = [re.sub(r"\s+", " ", str(x)).strip().lower() for x in df.iloc[0].tolist()]
            df = df.iloc[1:].reset_index(drop=True)
    except Exception:
        pass

    # Normalize column names
    df = _normalize_cols(df)

    # Remove fully empty columns
    df = df.loc[:, ~(df.isna().all())]

    # Drop rows that are completely empty
    df = df.dropna(how="all")

    # Remove rows that look like separators or dashes
    df = df[~df.apply(lambda r: all(str(x).strip() in {"", "-", "—", "–"} for x in r), axis=1)]

    # Minimal description normalization
    if "description" in df.columns:
        df["description"] = df["description"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()

    # Amount handling
    try:
        if "amount" in df.columns:
            df["amount"] = _series_to_numeric_aligned(df, "amount")
        else:
            debit_ser = _series_to_numeric_aligned(df, "debit")
            credit_ser = _series_to_numeric_aligned(df, "credit")

            # Defensive reindex
            debit_ser = debit_ser.reindex(df.index).fillna(0.0).astype(float)
            credit_ser = credit_ser.reindex(df.index).fillna(0.0).astype(float)

            df["amount"] = (credit_ser - debit_ser).astype(float)
    except Exception as e:
        warnings.warn(f"Failed to compute amount column robustly: {e}")
        df["amount"] = pd.Series([pd.NA] * len(df.index), index=df.index)

    # Date parsing: try to coerce to ISO YYYY-MM-DD
    if "date" in df.columns:
        parsed = pd.to_datetime(df["date"].astype(str), errors="coerce", infer_datetime_format=True)
        try:
            df["date"] = parsed.dt.strftime("%Y-%m-%d")
        except Exception:
            df["date"] = parsed

    # Remove rows without meaningful description or amount
    if "description" in df.columns:
        df = df[df["description"].astype(str).str.len() > 0]
    if "amount" in df.columns:
        df = df[~df["amount"].isna()]

    # Deduplicate and remove duplicate columns
    df = df.loc[:, ~df.columns.duplicated()].copy()
    df = df.drop_duplicates().reset_index(drop=True)

    # Reorder columns to make output tidy
    preferred = [c for c in ["date", "description", "amount", "cardholder", "card_last4"] if c in df.columns]
    other = [c for c in df.columns if c not in preferred]
    df = df[preferred + other]

    return df


def clean_transaction_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    High-level wrapper: normalize + clean rows, ensure unique columns + reset index.
    """
    cleaned = _clean_rows(df)
    if cleaned is None:
        return pd.DataFrame()
    # Ensure no duplicate columns and reset index
    cleaned = cleaned.loc[:, ~cleaned.columns.duplicated()].reset_index(drop=True)
    return cleaned


# ---------------------------
# Orchestration
# ---------------------------
def process_folder(input_folder: str = INPUT_FOLDER, output_folder: str = OUTPUT_FOLDER) -> Dict:
    """
    Process all PDFs in input folder and write:
      - per-PDF per-table CSVs for inspection
      - combined CSV: all_transactions.csv
      - combined JSON grouped by cardholder (if available): all_transactions.json
    Returns the grouped JSON-like dict.
    """
    pdf_files = sorted([os.path.join(input_folder, f) for f in os.listdir(input_folder) if f.lower().endswith(".pdf")])
    if not pdf_files:
        log.warning(f"No PDF files found in {input_folder}")
        return {}

    all_cleaned = []
    for pdf_path in pdf_files:
        log.info(f"Processing: {pdf_path}")
        raw_tables = extract_all_tables(pdf_path)
        if not raw_tables:
            log.warning(f"  No tables found in: {os.path.basename(pdf_path)}")
            continue

        base = os.path.splitext(os.path.basename(pdf_path))[0]
        for i, tbl in enumerate(raw_tables):
            try:
                cleaned = clean_transaction_table(tbl)
                if cleaned.empty:
                    log.debug(f"  Table {i} cleaned to empty, skipping.")
                    continue
                # save per-table CSV for debugging/inspection
                per_csv = os.path.join(output_folder, f"{base}_table_{i}.csv")
                cleaned.to_csv(per_csv, index=False)
                log.info(f"  Saved table CSV: {per_csv}")

                all_cleaned.append(cleaned)
            except Exception as e:
                log.warning(f"  Failed cleaning table {i} from {base}: {e}")
                continue

    if not all_cleaned:
        log.warning("No cleaned tables to combine.")
        return {}

    # Ensure a consistent set of columns across frames: take union and reindex each df
    all_columns = []
    for df in all_cleaned:
        for c in df.columns:
            if c not in all_columns:
                all_columns.append(c)

    reindexed = []
    for df in all_cleaned:
        # reindex to union columns, preserving existing values
        df2 = df.reindex(columns=all_columns)
        reindexed.append(df2.reset_index(drop=True))

    # Now safe concat
    combined = pd.concat(reindexed, ignore_index=True, sort=False)

    # Final sanitization: ensure amount numeric and drop invalid rows
    if "amount" in combined.columns:
        combined["amount"] = pd.to_numeric(combined["amount"], errors="coerce")
        combined = combined[~combined["amount"].isna()]

    if "description" in combined.columns:
        combined = combined[combined["description"].astype(str).str.len() > 0]

    # Save combined CSV
    combined_csv = os.path.join(output_folder, "all_transactions.csv")
    combined.to_csv(combined_csv, index=False)
    log.info(f"Saved combined CSV: {combined_csv}")

    # Group into JSON by cardholder if available
    if "cardholder" in combined.columns:
        grouped = (
            combined.groupby("cardholder")
            .apply(lambda g: g.drop(columns=[c for c in ["cardholder"] if c in g.columns]).to_dict(orient="records"))
            .to_dict()
        )
    else:
        grouped = {"transactions": combined.to_dict(orient="records")}

    # Save JSON
    combined_json = os.path.join(output_folder, "all_transactions.json")
    with open(combined_json, "w") as f:
        json.dump(grouped, f, indent=2, default=str)
    log.info(f"Saved combined JSON: {combined_json}")

    return grouped


# ---------------------------
# CLI
# ---------------------------
if __name__ == "__main__":
    try:
        result = process_folder()
        # Print a short sample
        if result:
            sample_keys = list(result.keys())[:5]
            log.info(f"Sample groups/keys: {sample_keys}")
    except Exception as exc:
        log.exception(f"Script failed: {exc}")
        
