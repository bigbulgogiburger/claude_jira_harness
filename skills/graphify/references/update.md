# `--update` mode — incremental re-extraction

**When to read this file:** The user invoked `/graphify [<path>] --update`. This re-extracts only new/changed files since the last run, saving tokens and time.

## Step 1 — Detect changes

```powershell
@'
import sys, json
from graphify.detect import detect_incremental, save_manifest
from pathlib import Path

result = detect_incremental(Path('INPUT_PATH'))
new_total = result.get('new_total', 0)
print(json.dumps(result, indent=2, ensure_ascii=False))
Path('.graphify_incremental.json').write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
if new_total == 0:
    print('No files changed since last run. Nothing to update.')
    raise SystemExit(0)
print(f'{new_total} new/changed file(s) to re-extract.')
'@ | Out-File -FilePath .graphify_step_for_update_incremental_re_extracti_19.py -Encoding utf8
python .graphify_step_for_update_incremental_re_extracti_19.py
Remove-Item -ErrorAction SilentlyContinue .graphify_step_for_update_incremental_re_extracti_19.py
```

## Step 2 — Decide whether semantic extraction is needed

Check whether all changed files are code files:

```powershell
@'
import json
from pathlib import Path

result = json.loads(open('.graphify_incremental.json', encoding='utf-8').read()) if Path('.graphify_incremental.json').exists() else {}
code_exts = {'.py','.ts','.js','.go','.rs','.java','.cpp','.c','.rb','.swift','.kt','.cs','.scala','.php','.cc','.cxx','.hpp','.h','.kts','.lua','.toc'}
new_files = result.get('new_files', {})
all_changed = [f for files in new_files.values() for f in files]
code_only = all(Path(f).suffix.lower() in code_exts for f in all_changed)
print('code_only:', code_only)
'@ | Out-File -FilePath .graphify_step_for_update_incremental_re_extracti_20.py -Encoding utf8
python .graphify_step_for_update_incremental_re_extracti_20.py
Remove-Item -ErrorAction SilentlyContinue .graphify_step_for_update_incremental_re_extracti_20.py
```

- **`code_only` is True**: print `[graphify update] Code-only changes detected — skipping semantic extraction (no LLM needed)`, run only **Step 3A (AST)** from SKILL.md on the changed files, skip Step 3B entirely (no subagents), then go straight to merge and Steps 4–8.
- **`code_only` is False** (any changed file is a doc/paper/image): run the full **Steps 3A–3C pipeline** from SKILL.md.

## Step 3 — Merge new extraction into existing graph

**Before** the merge step, save the old graph for diffing:

```powershell
Copy-Item graphify-out/graph.json .graphify_old.json
```

Then merge:

```powershell
@'
import sys, json
from graphify.build import build_from_json
from graphify.export import to_json
from networkx.readwrite import json_graph
import networkx as nx
from pathlib import Path

# Load existing graph
existing_data = json.loads(Path('graphify-out/graph.json').read_text(encoding="utf-8"))
G_existing = json_graph.node_link_graph(existing_data, edges='links')

# Load new extraction
new_extraction = json.loads(Path('.graphify_extract.json').read_text(encoding="utf-8"))
G_new = build_from_json(new_extraction)

# Prune nodes from deleted files
incremental = json.loads(Path('.graphify_incremental.json').read_text(encoding="utf-8"))
deleted = set(incremental.get('deleted_files', []))
if deleted:
    to_remove = [n for n, d in G_existing.nodes(data=True) if d.get('source_file') in deleted]
    G_existing.remove_nodes_from(to_remove)
    if to_remove:
        print(f'Pruned {len(to_remove)} ghost node(s) from {len(deleted)} deleted file(s) — drift detected and corrected.')
    else:
        print(f'{len(deleted)} file(s) deleted since last run, but no ghost nodes were present in the graph — no drift.')

# Merge: new nodes/edges into existing graph
G_existing.update(G_new)
print(f'Merged: {G_existing.number_of_nodes()} nodes, {G_existing.number_of_edges()} edges')

# Save manifest with the CURRENT full file list so the next --update
# diffs against today's filesystem state, not the prior --update's
# baseline. Without this, deleted files get reported as ghosts again
# on every subsequent --update until a full rebuild runs.
from graphify.detect import save_manifest
save_manifest(incremental['files'])
print('[graphify update] Manifest saved.')
'@ | Out-File -FilePath .graphify_step_for_update_incremental_re_extracti_21.py -Encoding utf8
python .graphify_step_for_update_incremental_re_extracti_21.py
Remove-Item -ErrorAction SilentlyContinue .graphify_step_for_update_incremental_re_extracti_21.py
```

## Step 4 — Continue with Steps 4–8

Run **Steps 4–8** from SKILL.md on the merged graph as normal (build/cluster/analyze, label, viz, optional exports, benchmark).

## Step 5 — Show diff

After Step 4, show the graph diff:

```powershell
@'
import json
from graphify.analyze import graph_diff
from graphify.build import build_from_json
from networkx.readwrite import json_graph
import networkx as nx
from pathlib import Path

# Load old graph (before update) from backup written before merge
old_data = json.loads(Path('.graphify_old.json').read_text(encoding="utf-8")) if Path('.graphify_old.json').exists() else None
new_extract = json.loads(Path('.graphify_extract.json').read_text(encoding="utf-8"))
G_new = build_from_json(new_extract)

if old_data:
    G_old = json_graph.node_link_graph(old_data, edges='links')
    diff = graph_diff(G_old, G_new)
    print(diff['summary'])
    if diff['new_nodes']:
        print('New nodes:', ', '.join(n['label'] for n in diff['new_nodes'][:5]))
    if diff['new_edges']:
        print('New edges:', len(diff['new_edges']))
'@ | Out-File -FilePath .graphify_step_for_update_incremental_re_extracti_22.py -Encoding utf8
python .graphify_step_for_update_incremental_re_extracti_22.py
Remove-Item -ErrorAction SilentlyContinue .graphify_step_for_update_incremental_re_extracti_22.py
```

Clean up after:

```powershell
Remove-Item -ErrorAction SilentlyContinue .graphify_old.json
```

Then finish with SKILL.md Step 9 (manifest, cost tracker, final report).
