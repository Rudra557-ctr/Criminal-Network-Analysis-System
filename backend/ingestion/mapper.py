"""
Schema Mapping — alias dictionary + fuzzy matching.

Maps any reasonable column names (caller/source_phone etc.) to normalized internal schema.
Fast path: if headers exactly equal known synthetic, auto-map without user.

Normalized schemas (internal keys used by pipeline):
- cdrs: call_id, caller_id, caller_name, caller_phone, callee_id, callee_name, callee_phone, timestamp, day, call_type, duration_sec, cell_tower_location
- transactions: txn_id, sender_id, sender_name, sender_account, receiver_id, receiver_name, receiver_account, amount_inr, timestamp, day, txn_type
- firs: fir_id, date, day, station, location, ipc_sections, narrative
"""
from typing import Dict, List, Tuple
import re
try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except:
    HAS_RAPIDFUZZ = False
    import difflib

# Normalized target -> list of aliases (lowercase, underscores)
ALIASES = {
    # cdrs
    "call_id": ["call_id", "id", "cdr_id", "record_id"],
    "caller_id": ["caller_id", "caller", "source_id", "from_id", "callerid"],
    "caller_name": ["caller_name", "caller", "source_name", "from_name"],
    "caller_phone": ["caller_phone", "source_phone", "caller phone", "source phone", "from_phone", "caller_number", "source_number", "phone1"],
    "callee_id": ["callee_id", "callee", "destination_id", "receiver_id", "to_id", "calleeid"],
    "callee_name": ["callee_name", "callee", "destination_name", "receiver_name", "to_name"],
    "callee_phone": ["callee_phone", "destination_phone", "receiver_phone", "to_phone", "callee_number", "dest_phone", "phone2"],
    "timestamp": ["timestamp", "event_time", "call_time", "date_time", "datetime", "time", "event time"],
    "day": ["day", "day_number", "daynum"],
    "call_type": ["call_type", "type", "category"],
    "duration_sec": ["duration_sec", "duration", "call_duration", "duration_seconds", "length"],
    "cell_tower_location": ["cell_tower_location", "tower", "location", "tower_location", "cell_tower"],
    # transactions
    "txn_id": ["txn_id", "transaction_id", "id", "trans_id"],
    "sender_id": ["sender_id", "sender", "from_id", "source_id", "payer_id"],
    "sender_name": ["sender_name", "sender", "from_name", "payer_name"],
    "sender_account": ["sender_account", "sender_acc", "from_account", "payer_account"],
    "receiver_id": ["receiver_id", "receiver", "to_id", "destination_id", "payee_id"],
    "receiver_name": ["receiver_name", "receiver", "to_name", "payee_name"],
    "receiver_account": ["receiver_account", "receiver_acc", "to_account", "payee_account"],
    "amount_inr": ["amount_inr", "amount", "value", "sum", "inr", "price"],
    "txn_type": ["txn_type", "type", "transaction_type", "payment_type"],
    # firs
    "fir_id": ["fir_id", "case_id", "id", "report_id", "fir id"],
    "date": ["date", "timestamp", "event_time", "incident_date"],
    "station": ["station", "police_station", "station_name", "ps"],
    "location": ["location", "place", "area", "ward", "site"],
    "ipc_sections": ["ipc_sections", "ipc", "sections", "act", "law"],
    "narrative": ["narrative", "description", "details", "text", "story", "incident", "report"],
    # social_posts
    "post_id": ["post_id", "post id", "id", "social_id"],
    "handle": ["handle", "username", "user", "author_handle"],
    "person_id": ["person_id", "person id", "author_id", "user_id"],
    "location_tag": ["location_tag", "location tag", "location", "tagged_location", "place"],
    "post_text": ["post_text", "post text", "post", "content", "message", "caption", "tweet", "text"],
    "hashtags": ["hashtags", "hashtag", "tags", "tag"],
    # criminal_history
    "record_id": ["record_id", "record id", "id", "history_id"],
    "alias": ["alias", "nickname", "aka", "alias_name"],
    "dob": ["dob", "date_of_birth", "birth_date", "birthdate"],
    "prior_offences": ["prior_offences", "prior offences", "offences", "offenses", "criminal_record", "history"],
    "gang_affiliation": ["gang_affiliation", "gang affiliation", "gang", "affiliation", "group", "syndicate"],
    "known_address": ["known_address", "known address", "address", "residence", "location"],
    # intelligence_reports
    "source_reliability": ["source_reliability", "source reliability", "reliability", "source_rating", "credibility"],
    "mentioned_entity_ids": ["mentioned_entity_ids", "mentioned entities", "entities", "mentioned_ids", "entity_ids"],
    # surveillance_reports
    "team": ["team", "unit", "surveillance_team", "officer", "squad"],
    "confidence": ["confidence", "certainty", "reliability_score"],
    "activity_notes": ["activity_notes", "activity notes", "notes", "observations", "activity", "remarks", "details"],
    # generic
    "name": ["name", "person_name", "full_name"],
    "phone": ["phone", "phone_number", "mobile", "contact"],
}

# Required fields per detected type (for validation)
REQUIRED = {
    "cdrs": ["caller_phone", "callee_phone"],
    "transactions": ["sender_id", "receiver_id", "amount_inr"],
    "firs": ["narrative"],
    "social_posts": ["post_text"],
    "criminal_history": ["name"],
    "intelligence_reports": ["narrative"],
    "surveillance_reports": ["activity_notes"],
    "unknown": [],
}

def _norm(s: str) -> str:
    return re.sub(r'[^a-z0-9]', '', s.lower())

def suggest_mapping(columns: List[str], detected_type: str) -> Dict[str, str]:
    """
    Return {normalized_field: original_column or None if not found}
    Uses alias exact + fuzzy (≥80).
    """
    # Build target set for this type (must cover every REQUIRED field)
    targets_by_type = {
        "cdrs": ["call_id","caller_id","caller_name","caller_phone","callee_id","callee_name","callee_phone","timestamp","day","call_type","duration_sec","cell_tower_location"],
        "transactions": ["txn_id","sender_id","sender_name","sender_account","receiver_id","receiver_name","receiver_account","amount_inr","timestamp","day","txn_type"],
        "firs": ["fir_id","date","day","station","location","ipc_sections","narrative"],
        "social_posts": ["post_id","handle","person_id","timestamp","day","location_tag","post_text","hashtags"],
        "criminal_history": ["record_id","person_id","name","alias","dob","prior_offences","gang_affiliation","known_address"],
        "intelligence_reports": ["report_id","date","day","source_reliability","narrative","mentioned_entity_ids"],
        "surveillance_reports": ["report_id","date","day","team","location","confidence","activity_notes"],
    }
    targets = targets_by_type.get(detected_type)
    if targets is None:
        # unknown type: fall back to every known target
        targets = list(ALIASES.keys())

    col_norm = {_norm(c): c for c in columns}
    col_low = {c.lower(): c for c in columns}
    mapping = {}
    used = set()
    # Priority order: phone/account/id fields first to avoid name fields stealing phone columns
    priority = {
        "caller_phone": 0, "callee_phone": 0, "sender_account": 0, "receiver_account": 0,
        "caller_id": 1, "callee_id": 1, "sender_id": 1, "receiver_id": 1,
        "amount_inr": 1, "duration_sec": 2, "timestamp": 2, "day": 3,
    }
    # sort targets by priority (lower = earlier)
    sorted_targets = sorted(targets, key=lambda t: priority.get(t, 5))
    for tgt in sorted_targets:
        aliases = ALIASES.get(tgt, [tgt])
        found = None
        # exact alias match (normalized) — only if column not used
        for alias in aliases:
            an = _norm(alias)
            if an in col_norm and col_norm[an] not in used:
                found = col_norm[an]
                break
            if alias.lower() in col_low and col_low[alias.lower()] not in used:
                found = col_low[alias.lower()]
                break
        if found:
            mapping[tgt] = found
            used.add(found)
            continue
        # fuzzy — only consider unused columns, threshold 85
        best, best_score = None, 0
        for c in columns:
            if c in used:
                continue
            for alias in aliases:
                if HAS_RAPIDFUZZ:
                    score = fuzz.ratio(_norm(c), _norm(alias))
                else:
                    import difflib
                    score = difflib.SequenceMatcher(None, _norm(c), _norm(alias)).ratio()*100
                if score > best_score:
                    best_score, best = score, c
        if best_score >= 85:
            mapping[tgt] = best
            used.add(best)
        else:
            mapping[tgt] = None
    # Ensure all targets present (for those not in priority order, fill None if not mapped)
    for tgt in targets:
        if tgt not in mapping:
            mapping[tgt] = None
    return mapping

def validate_mapping(mapping: Dict[str, str], detected_type: str) -> Tuple[bool, List[str]]:
    req = REQUIRED.get(detected_type, [])
    missing = [f for f in req if not mapping.get(f)]
    return (len(missing)==0, missing)

def apply_mapping(rows: List[Dict], mapping: Dict[str, str]) -> List[Dict]:
    """Remap each row's keys from original to normalized."""
    out = []
    for row in rows:
        new = {}
        for norm_field, orig_col in mapping.items():
            if orig_col and orig_col in row:
                new[norm_field] = row[orig_col]
            elif orig_col is None:
                # keep as None/Missing to be quarantined later
                new[norm_field] = None
        # preserve extra fields that were not mapped but exist
        for k, v in row.items():
            if k not in mapping.values() and k not in new:
                new[k] = v
        out.append(new)
    return out
