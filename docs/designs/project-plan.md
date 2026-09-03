# AI-Powered Criminal Network Analysis — Project Plan

**Goal:** Analyze fragmented crime data (FIRs, CDRs, financial records, social media, criminal history) to automatically uncover hidden relationships, identify key influencers, and flag suspicious patterns for investigators.

## Architecture (pipeline)

1. **Data sources** — FIRs, CDRs, financial records, social media, criminal history DB
2. **Ingestion & preprocessing** — clean and normalize raw records
3. **Entity & relation extraction (NLP)** — pull out people, locations, phones, vehicles, orgs
4. **Entity resolution** — merge aliases/duplicates into single nodes
5. **Knowledge graph (Neo4j)** — entities as nodes, relationships as edges with source/timestamp/confidence
6. **Graph analytics** — centrality (key players), community detection (cells), anomaly detection (bursts)
7. **Investigator dashboard** — visual network explorer, natural-language search, alerts

## Tech stack

| Layer | Tool |
|---|---|
| Backend | Python + FastAPI |
| NER (structured) | Regex + `phonenumbers` |
| NER (unstructured) | spaCy / fine-tuned transformer |
| Entity resolution | RapidFuzz + embedding clustering |
| Graph database | Neo4j Community Edition |
| Graph analytics | Neo4j GDS (PageRank, betweenness, Louvain) |
| Frontend | React + Cytoscape.js / react-force-graph |
| Deployment | Docker Compose |

## Team roles (2–4 people)

- **Data + backend** — synthetic dataset, ingestion pipeline, API
- **NLP/ML** — entity + relation extraction, entity resolution
- **Graph + analytics** — Neo4j schema, centrality/community/anomaly algorithms
- **Frontend + demo** — dashboard, visualization, pitch deck

*(with 2–3 people, combine roles — one person should own graph analytics end-to-end)*

## Demo dataset: ground-truth network

- 43 fictional entities across **3 cells** (drug distribution, arms smuggling, extortion), each with a kingpin → lieutenants → street-level structure
- **4 bridge figures** connecting cells: hawala operator, weapons supplier, logistics broker, corrupt police contact
- **3 scripted events** (one per cell, clustered in the same week) to drive communication/transaction bursts — the payoff: three "unrelated" cells show correlated activity spikes only visible once data is fused across sources
- Files: `ground_truth_network.json` (schema) + `ground_truth_network.png` (visual)

## Step-by-step build plan

1. **Lock scope & schema** — entity types, relationship types, Neo4j schema, UI wireframe
2. **Generate synthetic dataset** — from the ground-truth network, produce CDRs, financial transactions (with structuring/burst anomalies), FIR narratives, social posts, criminal history records, plus ~30–40% unrelated noise
3. **Build NLP extraction pipeline** — regex for phones/plates, NER for people/places/orgs, simple relation extraction
4. **Entity resolution** — fuzzy-match aliases/duplicate mentions into single nodes
5. **Load into Neo4j** — push resolved entities/relationships with source, timestamp, confidence
6. **Run graph analytics** — centrality (key influencers), community detection (cells), anomaly detection (bursts, structuring)
7. **Build investigator dashboard** — network explorer, search/filter, timeline, natural-language query bar
8. **Polish & rehearse** — seed one clear storyline, prepare pitch deck, record a backup demo video

## Differentiators to emphasize

- **Explainability** — show *why* someone is flagged (centrality score, specific edges), not a black box
- **Provenance** — every edge traceable to its source record + confidence score
- **Natural-language query** — "who's connected to X within 2 hops and transacted over ₹1 lakh"
- **Ethics/privacy** — role-based access, audit logging (judges reward this)

## Key risks

- Entity resolution is hard — keep demo naming variance modest, explain the general approach when asked
- Scope creep — skip audio/video surveillance analysis entirely
- Live demo failure — always have a pre-recorded backup video ready
