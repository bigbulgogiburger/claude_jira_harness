# Optional export formats — Step 7, 7b, 7c, 7d

**When to read this file:** The user passed one of `--neo4j`, `--neo4j-push`, `--svg`, `--graphml`, or `--mcp`. Otherwise skip.

These all run AFTER Step 6 (Obsidian + HTML) completes. They are additive — pick the one(s) the user asked for.

---

## Step 7 — Neo4j export

### If `--neo4j` (file only)

Generate a Cypher file for manual import:

```powershell
@'
import sys, json
from graphify.build import build_from_json
from graphify.export import to_cypher
from pathlib import Path

G = build_from_json(json.loads(Path('.graphify_extract.json').read_text(encoding="utf-8")))
to_cypher(G, 'graphify-out/cypher.txt')
print('cypher.txt written — import with: cypher-shell < graphify-out/cypher.txt')
'@ | Out-File -FilePath .graphify_step_7_neo4j_export_only_if_neo4j_or__13.py -Encoding utf8
python .graphify_step_7_neo4j_export_only_if_neo4j_or__13.py
Remove-Item -ErrorAction SilentlyContinue .graphify_step_7_neo4j_export_only_if_neo4j_or__13.py
```

### If `--neo4j-push <uri>` (push directly)

Push directly to a running Neo4j instance. Ask the user for credentials if not provided:

```powershell
@'
import sys, json
from graphify.build import build_from_json
from graphify.cluster import cluster
from graphify.export import push_to_neo4j
from pathlib import Path

extraction = json.loads(Path('.graphify_extract.json').read_text(encoding="utf-8"))
analysis   = json.loads(Path('.graphify_analysis.json').read_text(encoding="utf-8"))
G = build_from_json(extraction)
communities = {int(k): v for k, v in analysis['communities'].items()}

result = push_to_neo4j(G, uri='NEO4J_URI', user='NEO4J_USER', password='NEO4J_PASSWORD', communities=communities)
print(f'Pushed to Neo4j: {result["nodes"]} nodes, {result["edges"]} edges')
'@ | Out-File -FilePath .graphify_step_7_neo4j_export_only_if_neo4j_or__14.py -Encoding utf8
python .graphify_step_7_neo4j_export_only_if_neo4j_or__14.py
Remove-Item -ErrorAction SilentlyContinue .graphify_step_7_neo4j_export_only_if_neo4j_or__14.py
```

Replace `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` with actual values. Default URI is `bolt://localhost:7687`, default user is `neo4j`. Uses MERGE — safe to re-run without creating duplicates.

---

## Step 7b — SVG export (only if `--svg`)

```powershell
@'
import sys, json
from graphify.build import build_from_json
from graphify.export import to_svg
from pathlib import Path

extraction = json.loads(Path('.graphify_extract.json').read_text(encoding="utf-8"))
analysis   = json.loads(Path('.graphify_analysis.json').read_text(encoding="utf-8"))
labels_raw = json.loads(Path('.graphify_labels.json').read_text(encoding="utf-8")) if Path('.graphify_labels.json').exists() else {}

G = build_from_json(extraction)
communities = {int(k): v for k, v in analysis['communities'].items()}
labels = {int(k): v for k, v in labels_raw.items()}

to_svg(G, communities, 'graphify-out/graph.svg', community_labels=labels or None)
print('graph.svg written — embeds in Obsidian, Notion, GitHub READMEs')
'@ | Out-File -FilePath .graphify_step_7b_svg_export_only_if_svg_flag_15.py -Encoding utf8
python .graphify_step_7b_svg_export_only_if_svg_flag_15.py
Remove-Item -ErrorAction SilentlyContinue .graphify_step_7b_svg_export_only_if_svg_flag_15.py
```

---

## Step 7c — GraphML export (only if `--graphml`)

```powershell
@'
import json
from graphify.build import build_from_json
from graphify.export import to_graphml
from pathlib import Path

extraction = json.loads(Path('.graphify_extract.json').read_text(encoding="utf-8"))
analysis   = json.loads(Path('.graphify_analysis.json').read_text(encoding="utf-8"))

G = build_from_json(extraction)
communities = {int(k): v for k, v in analysis['communities'].items()}

to_graphml(G, communities, 'graphify-out/graph.graphml')
print('graph.graphml written — open in Gephi, yEd, or any GraphML tool')
'@ | Out-File -FilePath .graphify_step_7c_graphml_export_only_if_graphml_16.py -Encoding utf8
python .graphify_step_7c_graphml_export_only_if_graphml_16.py
Remove-Item -ErrorAction SilentlyContinue .graphify_step_7c_graphml_export_only_if_graphml_16.py
```

---

## Step 7d — MCP server (only if `--mcp`)

```powershell
python -m graphify.serve graphify-out/graph.json
```

This starts a stdio MCP server that exposes tools: `query_graph`, `get_node`, `get_neighbors`, `get_community`, `god_nodes`, `graph_stats`, `shortest_path`. Add to Claude Desktop or any MCP-compatible agent orchestrator so other agents can query the graph live.

To configure in Claude Desktop, add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "graphify": {
      "command": "python",
      "args": ["-m", "graphify.serve", "/absolute/path/to/graphify-out/graph.json"]
    }
  }
}
```

After running any of these, return to SKILL.md Step 8 (benchmark) and Step 9 (manifest).
