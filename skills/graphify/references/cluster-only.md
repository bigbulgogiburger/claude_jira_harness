# `--cluster-only` mode — re-run clustering on existing graph

**When to read this file:** The user invoked `/graphify [<path>] --cluster-only`. This skips extraction entirely and just re-clusters the existing graph.

## Skip Steps 1–3

Do NOT run install / detect / extract. The graph already exists.

## Re-cluster

Load the existing graph from `graphify-out/graph.json` and re-run clustering:

```powershell
@'
import sys, json
from graphify.cluster import cluster, score_all
from graphify.analyze import god_nodes, surprising_connections
from graphify.report import generate
from graphify.export import to_json
from networkx.readwrite import json_graph
import networkx as nx
from pathlib import Path

data = json.loads(Path('graphify-out/graph.json').read_text(encoding="utf-8"))
G = json_graph.node_link_graph(data, edges='links')

detection = {'total_files': 0, 'total_words': 99999, 'needs_graph': True, 'warning': None,
             'files': {'code': [], 'document': [], 'paper': []}}
tokens = {'input': 0, 'output': 0}

communities = cluster(G)
cohesion = score_all(G, communities)
gods = god_nodes(G)
surprises = surprising_connections(G, communities)
labels = {cid: 'Community ' + str(cid) for cid in communities}

report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, '.')
Path('graphify-out/GRAPH_REPORT.md').write_text(report, encoding="utf-8")
to_json(G, communities, 'graphify-out/graph.json')

analysis = {
    'communities': {str(k): v for k, v in communities.items()},
    'cohesion': {str(k): v for k, v in cohesion.items()},
    'gods': gods,
    'surprises': surprises,
}
Path('.graphify_analysis.json').write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
print(f'Re-clustered: {len(communities)} communities')
'@ | Out-File -FilePath .graphify_step_for_cluster_only_23.py -Encoding utf8
python .graphify_step_for_cluster_only_23.py
Remove-Item -ErrorAction SilentlyContinue .graphify_step_for_cluster_only_23.py
```

## Continue

Then run **Steps 5–9** from SKILL.md as normal:

- Step 5: Label communities
- Step 6: Generate Obsidian + HTML
- Step 7 (if any export flag was given): see `references/exports.md`
- Step 8: Token benchmark (if `total_words > 5000`)
- Step 9: Save manifest, update cost tracker, clean up, report

When to use this mode: you tweaked the clustering algorithm, want fresh community labels, or want to verify cluster stability without spending tokens on re-extraction.
