"""
Synthetic crime-network dataset generator.

Reads ground_truth_network.json (the "answer key" network) and produces
realistic-looking CDRs, financial transactions, FIR narratives, and social
media posts that are CONSISTENT with that hidden structure, plus noise.

IMPORTANT: all names, phone numbers, and account numbers are fictional.
Phone/account numbers use an obviously fake, sequential placeholder block
so nothing can be mistaken for a real subscriber/account.

Design decisions for this run (per team discussion):
  - Cell B (arms smuggling) is the "noisiest" cell: more decoy/background
    calls and more variable call durations around its burst window, so its
    signal is harder to isolate than Cells A and C.
  - Cell C (extortion) carries the "structuring" (smurfing) financial red
    flag: many small cash collections just under a fictional reporting
    threshold, consolidated upward. Cells A and B instead get simple large
    lump-sum transfers before their events - a different anomaly signature.

A `ground_truth_flag` column is included on transactions purely for your
own evaluation/scoring of the pipeline later. Strip it before feeding data
into the actual extraction/anomaly-detection system - it should have to
rediscover these patterns, not be told about them.

D8 alias variance (added 2026-09-03): structured sources (CDR/txn IDs and
name columns) stay canonical - they are the resolution anchors. Unstructured
text (FIR narratives, social posts) gets modest variance (nicknames,
transliteration variants, typos) via a SEPARATE rng stream, so counts and
structured rows stay byte-identical to the base run. An eval-only
`alias_map.json` (alias -> canonical name) is written alongside the CSVs;
strip it before the pipeline like `ground_truth_flag`.
"""

import argparse
import json
import random
import datetime
import os
import csv
from pathlib import Path

random.seed(42)

# D8: dedicated stream for ALL alias decisions. The main `random` stream is
# never touched by alias code, so CDR/txn counts and structured rows stay
# byte-identical to the pre-D8 run.
alias_rng = random.Random(20260715)

parser = argparse.ArgumentParser(description="Synthetic crime-network dataset generator (D8: alias variance).")
parser.add_argument("--gt", default=str(Path(__file__).resolve().parent / "ground_truth_network.json"),
                    help="Path to ground_truth_network.json")
parser.add_argument("--out", default=str(Path(__file__).resolve().parent),
                    help="Output directory for CSVs + people_directory.json + alias_map.json")
args = parser.parse_args()

OUT_DIR = args.out
os.makedirs(OUT_DIR, exist_ok=True)

START_DATE = datetime.date(2026, 1, 1)  # Day 1 of the synthetic timeline
THRESHOLD = 50000  # fictional reporting threshold used for the structuring pattern

# ---------------------------------------------------------------------------
# 1. Load ground truth
# ---------------------------------------------------------------------------
with open(args.gt) as f:
    gt = json.load(f)

nodes = gt["nodes"]
edges = gt["edges"]
events = gt["events"]
node_by_id = {n["id"]: n for n in nodes}


def make_phone(idx):
    # Obviously fictional, sequential placeholder block - not a real allocated series
    return f"70000{idx:05d}"


def make_account(idx):
    return f"AC0009{idx:06d}"


for i, n in enumerate(nodes, start=1):
    n["phone"] = make_phone(i)
    n["account"] = make_account(i)

# ---------------------------------------------------------------------------
# 2. Noise / background people - NOT part of the ground-truth network
# ---------------------------------------------------------------------------
NOISE_FIRST = ["Rakesh", "Priya", "Manoj", "Sunita", "Ajay", "Pooja", "Deepa",
               "Vinay", "Anita", "Kiran", "Sneha", "Arjun", "Divya", "Naveen",
               "Shalini", "Rohan", "Kavya", "Amit", "Poonam", "Alok"]
NOISE_LAST = ["Mishra", "Reddy", "Naidu", "Kulkarni", "Bhatia", "Iyer", "Menon",
              "Chatterjee", "Dutta", "Rao", "Nair", "Sinha", "Malhotra", "Bansal"]

noise_people = []
used_names = set()
for i in range(20):
    while True:
        name = f"{random.choice(NOISE_FIRST)} {random.choice(NOISE_LAST)}"
        if name not in used_names:
            used_names.add(name)
            break
    pid = f"N{i + 1}"
    noise_people.append({
        "id": pid, "name": name, "role": "Unrelated/background", "cell": "Noise",
        "phone": make_phone(100 + i), "account": make_account(100 + i)
    })

all_people = nodes + noise_people
id_to_person = {p["id"]: p for p in all_people}
noise_ids = [p["id"] for p in noise_people]

LOCATIONS = ["Dockside Ward", "Old Market Circle", "Riverside Colony",
             "Industrial Estate Road", "Central Junction", "Eastgate",
             "Hilltop Society", "Station Road", "New Colony",
             "Warehouse District", "North Bypass", "Lakeview Chowk"]

# ---------------------------------------------------------------------------
# 3. CDR generation
# ---------------------------------------------------------------------------
call_counter = 0
cdr_rows = []


def add_call(a_id, b_id, day, duration_range=(20, 600)):
    global call_counter
    if a_id == b_id:
        return
    day = max(1, min(90, day))
    call_counter += 1
    t = START_DATE + datetime.timedelta(days=day - 1)
    ts = datetime.datetime.combine(t, datetime.time(random.randint(7, 23), random.randint(0, 59)))
    call_type = random.choices(["voice", "sms"], weights=[0.75, 0.25])[0]
    a, b = id_to_person[a_id], id_to_person[b_id]
    cdr_rows.append({
        "call_id": f"CDR{call_counter:05d}",
        "caller_id": a_id, "caller_name": a["name"], "caller_phone": a["phone"],
        "callee_id": b_id, "callee_name": b["name"], "callee_phone": b["phone"],
        "timestamp": ts.isoformat(sep=" "),
        "day": day,
        "call_type": call_type,
        "duration_sec": random.randint(*duration_range) if call_type == "voice" else 0,
        "cell_tower_location": random.choice(LOCATIONS),
    })


# 3a. Baseline recurring calls along every ground-truth edge
for e in edges:
    n_calls = random.randint(6, 14)
    for d in sorted(random.sample(range(1, 91), n_calls)):
        add_call(e["source"], e["target"], d)

# 3b. Event-driven bursts (asymmetric noise: Cell B is noisiest)
CELL_NOISE_MULT = {"A": 1.0, "B": 1.8, "C": 1.0}

for ev in events:
    day_ev = ev["day"]
    core = ev["core_participants"]
    mult = CELL_NOISE_MULT[ev["cell"]]
    window = list(range(day_ev - 6, day_ev))

    # Burst calls among core participants
    n_burst = int(random.randint(12, 20) * mult)
    for _ in range(n_burst):
        a, b = random.sample(core, 2)
        dur = (30, 900) if mult <= 1.2 else (10, 900)  # more variable duration in noisy cell
        add_call(a, b, random.choice(window), duration_range=dur)

    # Decoy calls to unrelated/noise contacts, localized to this cell's window
    n_decoy = int(random.randint(5, 10) * mult)
    cell_members = [n["id"] for n in nodes if n["cell"] == ev["cell"]]
    for _ in range(n_decoy):
        add_call(random.choice(cell_members), random.choice(noise_ids),
                  random.choice(window + [day_ev, day_ev + 1]), duration_range=(5, 60))

# 3c. Bridge activity bump right before the events each bridge is relevant to
bridge_relevance = {"X1": ["A", "B", "C"], "X2": ["B", "C"], "X3": ["A", "B"], "X4": ["A", "B", "C"]}
for ev in events:
    for bridge_id, cells in bridge_relevance.items():
        if ev["cell"] not in cells:
            continue
        targets = [e["target"] for e in edges if e["source"] == bridge_id
                   and node_by_id.get(e["target"], {}).get("cell") == ev["cell"]]
        for tgt in targets:
            for _ in range(random.randint(2, 4)):
                add_call(bridge_id, tgt, random.randint(ev["day"] - 5, ev["day"] - 1),
                         duration_range=(20, 300))

# 3d. Pure background noise, unrelated to the network entirely
for _ in range(160):
    a, b = random.sample(noise_ids, 2)
    add_call(a, b, random.randint(1, 90), duration_range=(10, 400))

# ---------------------------------------------------------------------------
# 4. Financial transactions
# ---------------------------------------------------------------------------
txn_counter = 0
txn_rows = []


def add_txn(sender_id, receiver_id, amount, day, txn_type="Bank Transfer", flag="none"):
    global txn_counter
    day = max(1, min(90, day))
    txn_counter += 1
    t = START_DATE + datetime.timedelta(days=day - 1)
    ts = datetime.datetime.combine(t, datetime.time(random.randint(8, 22), random.randint(0, 59)))
    s, r = id_to_person[sender_id], id_to_person[receiver_id]
    txn_rows.append({
        "txn_id": f"TXN{txn_counter:05d}",
        "sender_id": sender_id, "sender_name": s["name"], "sender_account": s["account"],
        "receiver_id": receiver_id, "receiver_name": r["name"], "receiver_account": r["account"],
        "amount_inr": amount,
        "timestamp": ts.isoformat(sep=" "),
        "day": day,
        "txn_type": txn_type,
        "ground_truth_flag": flag,  # evaluation-only - do not feed to the detection pipeline
    })


# 4a. Baseline legit-looking transfers within each cell's finance-adjacent roles
finance_roles = {"Accountant", "Financier", "Cache keeper", "Safehouse keeper",
                  "Collection agent", "Kingpin"}
finance_people = [n for n in nodes if n["role"] in finance_roles]
for _ in range(140):
    s, r = random.sample(finance_people, 2)
    if s["cell"] != r["cell"]:
        continue
    add_txn(s["id"], r["id"], random.randint(2000, 20000), random.randint(1, 90),
            txn_type=random.choice(["UPI", "Bank Transfer"]))

# 4b. Background noise transactions among unrelated noise people
for _ in range(90):
    s, r = random.sample(noise_people, 2)
    add_txn(s["id"], r["id"], random.randint(500, 15000), random.randint(1, 90),
            txn_type=random.choice(["UPI", "Bank Transfer", "Cash"]))

# 4c. Suspicious lump-sum transfers before Cell A and Cell B events
lump_sum_chains = {
    "A": {"chain": [("A1", "A11"), ("A11", "X3")], "amount_range": (150000, 450000)},
    "B": {"chain": [("B1", "B11"), ("B11", "X2"), ("B11", "X3")], "amount_range": (200000, 600000)},
}
for ev in events:
    cfg = lump_sum_chains.get(ev["cell"])
    if not cfg:
        continue
    for s, r in cfg["chain"]:
        add_txn(s, r, random.randint(*cfg["amount_range"]),
                random.randint(ev["day"] - 4, ev["day"] - 1),
                txn_type=random.choice(["Bank Transfer", "Hawala"]),
                flag=f"suspicious_lump_{ev['cell']}")

# 4d. Structuring / smurfing pattern for Cell C (extortion)
ev_c = next(e for e in events if e["cell"] == "C")
struct_days = list(range(ev_c["day"] - 12, ev_c["day"] - 1))

# many small "collections" from unrelated payers, each just under THRESHOLD
for _ in range(random.randint(18, 25)):
    payer = random.choice(noise_people)["id"]
    add_txn(payer, "C12", random.randint(35000, 49500), random.choice(struct_days),
            txn_type="Cash", flag="structuring_component")

# consolidation: collection agent -> accountant
for _ in range(3):
    add_txn("C12", "C11", random.randint(250000, 400000),
            random.randint(ev_c["day"] - 6, ev_c["day"] - 1),
            txn_type="Cash", flag="structuring_consolidation")

# accountant forwards upward / to the hawala bridge
for s, r in [("C11", "X1"), ("C11", "C1")]:
    add_txn(s, r, random.randint(200000, 500000),
            random.randint(ev_c["day"] - 3, ev_c["day"] - 1),
            txn_type="Hawala", flag=f"suspicious_lump_C")

# ---------------------------------------------------------------------------
# 4.5 Alias variance (D8) — eval-only map; strip before the pipeline
# ---------------------------------------------------------------------------
# Structured columns (caller_name, sender_name, ...) stay canonical.
# Only free text gets variance, with P_ALIAS per mention. Modest by design:
# resolution should need fuzzy matching, not a miracle.
P_ALIAS_FIR = 0.35
P_ALIAS_SOCIAL = 0.25

NICKNAMES = {
    "Anwar Sheikh": ["Annu Bhai"],
    "Suresh Rane": ["Suresh Anna"],
    "Farhan Qureshi": ["Farhan"],
    "Rajan Naik": ["Rajan Bhau"],
    "Salim Pathan": ["Salim"],
    "Prakash Shetty": ["Prakash Anna"],
    "Nasir Malik": ["Nasir Bhai"],
    "Meena Joshi": ["Meena Madam"],
    "Kavita Desai": ["Kavita Madam"],
    "Neha Kulkarni": ["Neha Madam"],
    "Sunil Pillai": ["Sunil"],
    "Dinesh Mehta": ["Dinesh Seth"],
    "Javed Ansari": ["Javed Bhai"],
    "Arvind Kapoor": ["AK"],
    "R.K. Verma": ["Verma Sir"],
}

SURNAME_ALT = {
    "Sheikh": ["Shaikh"],
    "Qureshi": ["Quraishi"],
}

VOWELS = set("aeiouAEIOU")

# alias string -> canonical full name (eval-only ground truth for resolution)
alias_map = {}


def typo_variant(name):
    """Single small corruption: drop one internal vowel or swap one adjacent pair."""
    if len(name) < 4:
        return name
    if alias_rng.random() < 0.5:
        cand = [i for i in range(1, len(name)) if name[i] in VOWELS and name[i - 1] != " "]
        if cand:
            i = alias_rng.choice(cand)
            return name[:i] + name[i + 1:]
        return name
    i = alias_rng.randrange(1, len(name) - 1)
    if name[i] == " " or name[i - 1] == " ":
        return name
    return name[:i - 1] + name[i] + name[i - 1] + name[i + 1:]


def alias_form(name):
    """Pick one alias surface form for a canonical name (always aliases)."""
    r = alias_rng.random()
    if name in NICKNAMES and r < 0.60:
        return alias_rng.choice(NICKNAMES[name])
    parts = name.split()
    if len(parts) > 1 and parts[-1] in SURNAME_ALT and r < 0.75:
        return " ".join(parts[:-1] + [alias_rng.choice(SURNAME_ALT[parts[-1]])])
    return typo_variant(name)


def maybe_alias(person):
    """Return canonical name usually, an alias sometimes; record the map."""
    if alias_rng.random() < P_ALIAS_FIR:
        txt = alias_form(person["name"])
        if txt != person["name"]:
            alias_map[txt] = person["name"]
        return txt
    return person["name"]


# ---------------------------------------------------------------------------
# 5. FIR narratives (structured + unstructured mix)
# ---------------------------------------------------------------------------
fir_rows = []
fir_counter = 0

IPC_BY_CELL = {
    "A": ["NDPS Act Section 8/20 (possession & trafficking)", "IPC 120B (criminal conspiracy)"],
    "B": ["Arms Act Section 25", "IPC 120B (criminal conspiracy)"],
    "C": ["IPC 384 (extortion)", "IPC 506 (criminal intimidation)"],
}

REL_TEMPLATES = [
    "Acting on a tip-off, a patrol team intercepted {a} near {loc} on suspicion of involvement "
    "with a network linked to {kp}. {a} was found in possession of a mobile phone with frequent "
    "contact to {b}. Case registered under {ipc}.",
    "Complainant reported suspicious movement of unknown persons believed to include {a} and {b} "
    "around {loc} in the days preceding {evtype}. Surveillance recommended.",
    "Informant states that {a}, associated with {kp}'s network, was seen meeting {b} at {loc}. "
    "Nature of meeting unclear; flagged for financial-record cross-check.",
    "FIR registered after a scuffle involving {a} at {loc}. Preliminary questioning suggests a "
    "possible link to {b} through a prior known association. Case under {ipc}.",
    "Source intelligence indicates {kp}'s group may be preparing for an upcoming operation. "
    "{a} and {b} were observed conferring near {loc} multiple times this week.",
]

NOISE_FIR_TEMPLATES = [
    "Complaint of two-wheeler theft reported outside {loc}. No suspects identified. Case under IPC 379.",
    "Minor road-rage altercation reported near {loc}; both parties counselled and released.",
    "Shopkeeper at {loc} reported a break-in overnight; petty cash and goods stolen. Case under IPC 380.",
    "Noise complaint received regarding a private function at {loc}; resolved on-site.",
    "Missing-person report filed for a local resident last seen near {loc}; family contacted, resolved.",
]

for ev in events:
    kp = node_by_id[ev["core_participants"][0]]["name"]
    cell_members = [n for n in nodes if n["cell"] == ev["cell"] and n["id"] != ev["core_participants"][0]]
    for _ in range(random.randint(7, 9)):
        fir_counter += 1
        a, b = random.sample(cell_members, 2) if len(cell_members) >= 2 else (cell_members[0], cell_members[0])
        template = random.choice(REL_TEMPLATES)
        loc = random.choice(LOCATIONS)
        ipc = random.choice(IPC_BY_CELL[ev["cell"]])
        evtype = ev["type"].replace("_", " ")
        narrative = template.format(a=maybe_alias(a), b=maybe_alias(b), kp=kp, loc=loc, ipc=ipc, evtype=evtype)
        fir_day = random.randint(max(1, ev["day"] - 20), ev["day"] - 1)
        fir_rows.append({
            "fir_id": f"FIR{fir_counter:04d}",
            "date": (START_DATE + datetime.timedelta(days=fir_day - 1)).isoformat(),
            "day": fir_day,
            "station": f"{loc} Police Station",
            "location": loc,
            "ipc_sections": ipc,
            "narrative": narrative,
            "ground_truth_flag": f"relevant_cell_{ev['cell']}",
        })

# noise FIRs unrelated to the network
for _ in range(12):
    fir_counter += 1
    loc = random.choice(LOCATIONS)
    fir_day = random.randint(1, 90)
    fir_rows.append({
        "fir_id": f"FIR{fir_counter:04d}",
        "date": (START_DATE + datetime.timedelta(days=fir_day - 1)).isoformat(),
        "day": fir_day,
        "station": f"{loc} Police Station",
        "location": loc,
        "ipc_sections": "IPC 379/380 (petty offence)",
        "narrative": random.choice(NOISE_FIR_TEMPLATES).format(loc=loc),
        "ground_truth_flag": "noise",
    })

random.shuffle(fir_rows)

# ---------------------------------------------------------------------------
# 6. Social media posts
# ---------------------------------------------------------------------------
social_rows = []
social_counter = 0

CODED_TEMPLATES = [
    "Big delivery coming through {loc} soon, everyone ready? #hustle",
    "Meeting the usual crew near {loc} tonight, don't be late.",
    "Package count almost done, moving it by this weekend near {loc}.",
    "Collections running slow this week around {loc}, need to speed up.",
    "New shipment landing soon, {loc} side clear for now.",
]

# D8: coded posts that name-drop an associate by alias. person_id stays the
# AUTHOR (canonical); the mentioned alias must be resolved to a second person.
CODED_ALIAS_TEMPLATES = [
    "Met {alias} near {loc} last night, keep it quiet. #hustle",
    "Told {alias} the drop moves to {loc}, pass it on.",
    "{alias} collecting around {loc}, wrap up fast. #grind",
]

NOISE_SOCIAL_TEMPLATES = [
    "Great biryani at the new place near {loc} today! 10/10 #foodie",
    "Traffic near {loc} is unbearable this morning, avoid if you can.",
    "Watching the match tonight, who's up for it? #cricket",
    "Beautiful sunset from {loc} today, needed this.",
    "Anyone recommend a good electrician near {loc}?",
]

HASHTAGS = ["#hustle", "#grind", "#weekend", "#business", "#family", "#blessed"]


def handle_for(person):
    base = person["name"].split()[0].lower()
    return f"@{base}{random.randint(10, 99)}"


for ev in events:
    core_ids = ev["core_participants"]
    for _ in range(random.randint(12, 16)):
        social_counter += 1
        pid = random.choice(core_ids)
        p = id_to_person[pid]
        loc = random.choice(LOCATIONS)
        post_day = random.randint(ev["day"] - 8, ev["day"] - 1)
        if alias_rng.random() < P_ALIAS_SOCIAL:
            others = [c for c in core_ids if c != pid]
            mentioned = id_to_person[alias_rng.choice(others)] if others else p
            alias_txt = alias_form(mentioned["name"])
            if alias_txt != mentioned["name"]:
                alias_map[alias_txt] = mentioned["name"]
            post_text = alias_rng.choice(CODED_ALIAS_TEMPLATES).format(alias=alias_txt, loc=loc)
        else:
            post_text = random.choice(CODED_TEMPLATES).format(loc=loc)
        social_rows.append({
            "post_id": f"SOC{social_counter:04d}",
            "handle": handle_for(p),
            "person_id": pid,
            "timestamp": (START_DATE + datetime.timedelta(days=post_day - 1)).isoformat(),
            "day": post_day,
            "location_tag": loc,
            "post_text": post_text,
            "hashtags": random.choice(HASHTAGS),
            "ground_truth_flag": f"relevant_cell_{ev['cell']}",
        })

for _ in range(25):
    social_counter += 1
    p = random.choice(noise_people)
    loc = random.choice(LOCATIONS)
    post_day = random.randint(1, 90)
    social_rows.append({
        "post_id": f"SOC{social_counter:04d}",
        "handle": handle_for(p),
        "person_id": p["id"],
        "timestamp": (START_DATE + datetime.timedelta(days=post_day - 1)).isoformat(),
        "day": post_day,
        "location_tag": loc,
        "post_text": random.choice(NOISE_SOCIAL_TEMPLATES).format(loc=loc),
        "hashtags": random.choice(HASHTAGS),
        "ground_truth_flag": "noise",
    })

random.shuffle(social_rows)

# ---------------------------------------------------------------------------
# 7. Write outputs
# ---------------------------------------------------------------------------
def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


write_csv(os.path.join(OUT_DIR, "cdrs.csv"), cdr_rows)
write_csv(os.path.join(OUT_DIR, "transactions.csv"), txn_rows)
write_csv(os.path.join(OUT_DIR, "firs.csv"), fir_rows)
write_csv(os.path.join(OUT_DIR, "social_posts.csv"), social_rows)

with open(os.path.join(OUT_DIR, "people_directory.json"), "w") as f:
    json.dump({"network_people": nodes, "noise_people": noise_people}, f, indent=2)

# D8 eval-only: alias surface form -> canonical name. Strip before the pipeline.
with open(os.path.join(OUT_DIR, "alias_map.json"), "w") as f:
    json.dump(alias_map, f, indent=2, sort_keys=True)

print(f"People (network): {len(nodes)}   Noise people: {len(noise_people)}")
print(f"CDRs: {len(cdr_rows)}")
print(f"Transactions: {len(txn_rows)}  (suspicious/structuring: "
      f"{sum(1 for t in txn_rows if t['ground_truth_flag'] != 'none')})")
print(f"FIRs: {len(fir_rows)}  (noise: {sum(1 for f in fir_rows if f['ground_truth_flag']=='noise')})")
print(f"Social posts: {len(social_rows)}  (noise: "
      f"{sum(1 for s in social_rows if s['ground_truth_flag']=='noise')})")
print(f"Aliases (eval-only): {len(alias_map)}")
