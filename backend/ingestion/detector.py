"""
Format + Dataset Type + Schema Detection (Task-agnostic).

No hard-coded case logic; heuristic scores derived from column names.
"""
import mimetypes
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple

SUPPORTED_FORMATS = {".csv": "csv", ".xlsx": "xlsx", ".xls": "xlsx", ".json": "json"}

# Heuristic keywords per normalized dataset type
TYPE_KEYWORDS = {
    "cdrs": ["caller", "callee", "phone", "call", "duration", "tower", "caller_phone", "callee_phone"],
    "transactions": ["sender", "receiver", "amount", "account", "txn", "transfer", "balance"],
    "firs": ["fir", "ipc", "narrative", "station", "complainant", "accused"],
    "social_posts": ["post", "handle", "hashtag", "social", "tweet"],
    "criminal_history": ["criminal", "history", "offence", "gang", "alias", "dob"],
    "intelligence_reports": ["intelligence", "source_reliability", "informant"],
    "surveillance_reports": ["surveillance", "team", "activity_notes", "vehicle"],
    "people_directory": ["person_id", "name", "phone", "account", "directory", "person"],
}

def detect_format(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    if ext in SUPPORTED_FORMATS:
        return SUPPORTED_FORMATS[ext]
    # sniff content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            sample = f.read(2048)
            if sample.strip().startswith(('{', '[')):
                return "json"
            # try csv
            sniffer = csv.Sniffer()
            sniffer.sniff(sample, delimiters=",;\t|")
            return "csv"
    except:
        pass
    return "unknown"

def detect_columns(file_path: Path, fmt: str) -> Tuple[List[str], List[Dict]]:
    """Return (columns, sample_rows[3]) without loading full file."""
    cols, sample = [], []
    try:
        if fmt == "csv":
            with open(file_path, newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                cols = reader.fieldnames or []
                for i, row in enumerate(reader):
                    if i < 3:
                        sample.append(row)
                    else:
                        break
        elif fmt == "xlsx":
            import pandas as pd
            df = pd.read_excel(file_path, nrows=3, dtype=str)
            cols = list(df.columns.astype(str))
            sample = df.fillna("").to_dict(orient="records")
        elif fmt == "json":
            import json as js
            with open(file_path, encoding='utf-8') as f:
                data = js.load(f)
                if isinstance(data, dict) and "data" in data:
                    data = data["data"]
                if isinstance(data, list) and data:
                    cols = list(data[0].keys())
                    sample = data[:3]
                elif isinstance(data, dict):
                    cols = list(data.keys())
                    sample = [data]
    except Exception as e:
        cols = []
    # normalize whitespace
    cols = [c.strip() for c in cols if c and str(c).strip()]
    return cols, sample

def detect_dataset_type(columns: List[str]) -> Tuple[str, float]:
    """Score each type by keyword overlap (0-1). Return best type and confidence."""
    col_low = " ".join(c.lower() for c in columns)
    scores = {}
    for dtype, keywords in TYPE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in col_low)
        scores[dtype] = hits / len(keywords) if keywords else 0
        # bonus for exact canonical columns
        if dtype == "cdrs" and any(x in col_low for x in ["caller_phone", "callee_phone"]):
            scores[dtype] += 0.3
        if dtype == "transactions" and "amount" in col_low:
            scores[dtype] += 0.2
        if dtype == "firs" and "narrative" in col_low:
            scores[dtype] += 0.3
    best = max(scores, key=lambda k: scores[k])
    conf = min(1.0, scores[best])
    # if very low, mark as generic "unknown" but return best guess with low conf
    if conf < 0.15:
        return "unknown", conf
    return best, round(conf, 3)

def detect_schema(file_path: Path) -> Dict:
    fmt = detect_format(file_path)
    cols, sample = detect_columns(file_path, fmt)
    dtype, conf = detect_dataset_type(cols)
    return {
        "file": file_path.name,
        "format": fmt,
        "columns": cols,
        "sample_rows": sample[:2],
        "detected_type": dtype,
        "type_confidence": conf,
        "row_count_estimate": None,
    }
