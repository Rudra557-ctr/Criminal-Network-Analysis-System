"""
Centrality / Betweenness — uses Neo4j GDS if available else networkx.
Per design: betweenness ranks X1-X4 top-6; we compute normalized 0-1.
"""
from typing import Dict, List
import pickle
from pathlib import Path

try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False

from backend.config import PROJECT_ROOT, BRIDGE_TOP_K
from backend.graph.neo4j_client import get_driver, is_available
from backend.config import NEO4J_DATABASE

def compute_centrality_networkx() -> List[Dict]:
    pkl = PROJECT_ROOT / "output" / "graph.pkl"
    if not pkl.exists() or not HAS_NX:
        return []
    with open(pkl, "rb") as f:
        G = pickle.load(f)
    # Convert MultiDiGraph to undirected simple for betweenness
    H = nx.Graph()
    for u, v, data in G.edges(data=True):
        # limit to Person-Person edges for bridge relevance (CALLED/TRANSACTED)
        if data.get("kind") in ("CALLED","TRANSACTED") and G.nodes[u].get("kind")=="Person" and G.nodes[v].get("kind")=="Person":
            H.add_edge(u, v)
    if len(H.nodes) == 0:
        return []
    bet = nx.betweenness_centrality(H, normalized=True)
    deg = dict(H.degree())
    # also degree centrality
    deg_cent = nx.degree_centrality(H)
    try:
        pagerank = nx.pagerank(H, alpha=0.85)
    except:
        pagerank = {n:0 for n in H.nodes}
    res = []
    for nid in H.nodes:
        res.append({
            "id": nid,
            "name": G.nodes[nid].get("label"),
            "cell": G.nodes[nid].get("cell"),
            "betweenness": round(bet.get(nid,0),4),
            "degree": deg.get(nid,0),
            "degree_centrality": round(deg_cent.get(nid,0),4),
            "pagerank": round(pagerank.get(nid,0),4)
        })
    res.sort(key=lambda x: x["betweenness"], reverse=True)
    return res

def compute_centrality_neo4j() -> List[Dict]:
    drv = get_driver()
    if not drv:
        return []
    # Try GDS — fallback to cypher degree if GDS unavailable
    try:
        # Use GDS in-memory projection if exists — simplified: run brandes via cypher
        # Attempt GDS betweenness if installed
        with drv.session(database=NEO4J_DATABASE) as session:
            # Check GDS available
            try:
                session.run("CALL gds.version()").consume()
                gds_available = True
            except:
                gds_available = False
            if gds_available:
                # Create projection
                try:
                    session.run("CALL gds.graph.drop('fusion', false)").consume()
                except:
                    pass
                session.run("""
                CALL gds.graph.project('fusion', 'Person', {CALLED:{orientation:'UNDIRECTED'}, TRANSACTED:{orientation:'UNDIRECTED'}})
                """).consume()
                result = session.run("CALL gds.betweenness.stream('fusion') YIELD nodeId, score RETURN gds.util.asNode(nodeId).id AS id, gds.util.asNode(nodeId).name AS name, gds.util.asNode(nodeId).cell AS cell, score ORDER BY score DESC")
                rows = [dict(r) for r in result]
                session.run("CALL gds.graph.drop('fusion')").consume()
                return [{"id": r["id"], "name": r["name"], "cell": r["cell"], "betweenness": round(r["score"],4)} for r in rows]
            else:
                # Fallback degree
                result = session.run("MATCH (p:Person) RETURN p.id AS id, p.name AS name, p.cell AS cell, size((p)--()) AS degree ORDER BY degree DESC")
                return [dict(r) for r in result]
    except Exception as e:
        print(f"[centrality] neo4j error {e}")
        return []

def compute_centrality() -> List[Dict]:
    if is_available():
        rows = compute_centrality_neo4j()
        if rows:
            return rows
    return compute_centrality_networkx()
