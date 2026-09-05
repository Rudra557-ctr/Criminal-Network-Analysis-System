"""
Normalization — mapped rows → pipeline's datasets dict.

Keeps same keys as load_all: cdrs, transactions, firs etc., but values are normalized.
"""
from typing import Dict, List
from datetime import datetime

def _to_day(timestamp_str):
    if not timestamp_str:
        return None
    # try parse day from string or date
    try:
        # try ISO
        dt = datetime.fromisoformat(str(timestamp_str).replace(" ", "T").split(".")[0])
        # synthetic start date 2026-01-01 day 1
        start = datetime(2026,1,1)
        delta = (dt - start).days + 1
        if 1 <= delta <= 90:
            return delta
    except:
        pass
    return None

def normalize_cdrs(rows: List[Dict]) -> List[Dict]:
    out=[]
    for i, r in enumerate(rows):
        # fill missing ids
        call_id = r.get("call_id") or f"GEN-CDR{i+1:05d}"
        # timestamp fallback
        ts = r.get("timestamp") or r.get("date") or ""
        day = r.get("day")
        if not day or str(day).strip() in ("", "None"):
            day = _to_day(ts)
        out.append({
            "call_id": str(call_id),
            "caller_id": str(r.get("caller_id") or r.get("caller_name") or f"UNK{i}"),
            "caller_name": str(r.get("caller_name") or r.get("caller_id") or ""),
            "caller_phone": str(r.get("caller_phone") or ""),
            "callee_id": str(r.get("callee_id") or r.get("callee_name") or f"UNK{i}"),
            "callee_name": str(r.get("callee_name") or r.get("callee_id") or ""),
            "callee_phone": str(r.get("callee_phone") or ""),
            "timestamp": str(ts),
            "day": int(day) if str(day).isdigit() else day,
            "call_type": str(r.get("call_type") or "voice"),
            "duration_sec": int(str(r.get("duration_sec") or "0").split(".")[0]) if str(r.get("duration_sec") or "").strip().isdigit() or str(r.get("duration_sec") or "").replace('.','',1).isdigit() else 0,
            "cell_tower_location": str(r.get("cell_tower_location") or r.get("location") or "Unknown"),
        })
    return out

def normalize_transactions(rows: List[Dict]) -> List[Dict]:
    out=[]
    for i, r in enumerate(rows):
        txn_id = r.get("txn_id") or f"GEN-TXN{i+1:05d}"
        ts = r.get("timestamp") or r.get("date") or ""
        day = r.get("day") or _to_day(ts)
        amt = r.get("amount_inr") or r.get("amount") or 0
        try:
            amt = int(str(amt).replace(",","").replace("₹","").strip().split(".")[0])
        except:
            amt = 0
        out.append({
            "txn_id": str(txn_id),
            "sender_id": str(r.get("sender_id") or r.get("sender_name") or f"UNK{i}"),
            "sender_name": str(r.get("sender_name") or r.get("sender_id") or ""),
            "sender_account": str(r.get("sender_account") or ""),
            "receiver_id": str(r.get("receiver_id") or r.get("receiver_name") or f"UNK{i}"),
            "receiver_name": str(r.get("receiver_name") or r.get("receiver_id") or ""),
            "receiver_account": str(r.get("receiver_account") or ""),
            "amount_inr": amt,
            "timestamp": str(ts),
            "day": int(day) if str(day).isdigit() else day,
            "txn_type": str(r.get("txn_type") or r.get("type") or "Bank Transfer"),
        })
    return out

def normalize_firs(rows: List[Dict]) -> List[Dict]:
    out=[]
    for i, r in enumerate(rows):
        fid = r.get("fir_id") or f"GEN-FIR{i+1:04d}"
        out.append({
            "fir_id": str(fid),
            "date": str(r.get("date") or r.get("timestamp") or ""),
            "day": r.get("day") or _to_day(r.get("date")),
            "station": str(r.get("station") or ""),
            "location": str(r.get("location") or ""),
            "ipc_sections": str(r.get("ipc_sections") or ""),
            "narrative": str(r.get("narrative") or r.get("description") or r.get("text") or ""),
        })
    return out

def normalize_people_directory(rows: List[Dict]) -> Dict:
    people = []
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            continue
        pid = r.get("person_id") or r.get("id") or f"P{i+1:02d}"
        people.append({
            "id": str(pid),
            "name": str(r.get("name") or r.get("caller_name") or f"Person {pid}"),
            "phone": str(r.get("phone") or r.get("caller_phone") or ""),
            "account": str(r.get("account") or r.get("receiver_account") or ""),
            "location": str(r.get("location") or r.get("cell_tower_location") or "")
        })
    return {"network_people": people, "noise_people": []}

def normalize_generic(rows: List[Dict], dtype: str):
    if dtype == "cdrs":
        return normalize_cdrs(rows)
    if dtype == "transactions":
        return normalize_transactions(rows)
    if dtype == "firs":
        return normalize_firs(rows)
    if dtype == "people_directory":
        return normalize_people_directory(rows)
    # fallback: return as-is
    return rows
