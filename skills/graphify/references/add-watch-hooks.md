# Ingestion and integration — `add` / `--watch` / `hook` / `claude install`

**When to read this file:** The user invoked one of:
- `/graphify add <url>` — fetch a URL and append to the corpus
- `/graphify --watch` — background folder watcher
- `graphify hook install|uninstall|status` — git post-commit hook
- `graphify claude install|uninstall` — native CLAUDE.md integration

These are all integration / ingestion modes that bypass the full pipeline.

---

## `/graphify add <url>` — Fetch URL and add to corpus

Fetch a URL and add it to the corpus, then update the graph.

```powershell
@'
import sys
from graphify.ingest import ingest
from pathlib import Path

try:
    out = ingest('URL', Path('./raw'), author='AUTHOR', contributor='CONTRIBUTOR')
    print(f'Saved to {out}')
except ValueError as e:
    print(f'error: {e}', file=sys.stderr)
    sys.exit(1)
except RuntimeError as e:
    print(f'error: {e}', file=sys.stderr)
    sys.exit(1)
'@ | Out-File -FilePath .graphify_step_for_graphify_add_30.py -Encoding utf8
python .graphify_step_for_graphify_add_30.py
Remove-Item -ErrorAction SilentlyContinue .graphify_step_for_graphify_add_30.py
```

Replace `URL` with the actual URL, `AUTHOR` with the user's name if provided, `CONTRIBUTOR` likewise. If the command exits with an error, tell the user what went wrong — do not silently continue. After a successful save, automatically run the `--update` pipeline on `./raw` to merge the new file into the existing graph (see `references/update.md`).

### Supported URL types (auto-detected)

- **Twitter / X** → fetched via oEmbed, saved as `.md` with tweet text and author
- **arXiv** → abstract + metadata saved as `.md`
- **PDF** → downloaded as `.pdf`
- **Images** (`.png` / `.jpg` / `.webp`) → downloaded, vision extraction runs on next build
- **Any webpage** → converted to markdown via `html2text`

---

## `--watch` — Background folder watcher

Start a background watcher that monitors a folder and auto-updates the graph when files change.

```powershell
python -m graphify.watch INPUT_PATH --debounce 3
```

Replace `INPUT_PATH` with the folder to watch. Behavior depends on what changed:

- **Code files only** (`.py`, `.ts`, `.go`, etc.): re-runs AST extraction + rebuild + cluster immediately, no LLM needed. `graph.json` and `GRAPH_REPORT.md` are updated automatically.
- **Docs, papers, or images**: writes a `graphify-out/needs_update` flag and prints a notification to run `/graphify --update` (LLM semantic re-extraction required).

**Debounce** (default `3s`): waits until file activity stops before triggering, so a wave of parallel agent writes doesn't trigger a rebuild per file.

Press `Ctrl+C` to stop.

### Agentic workflow tip

For agentic workflows: run `--watch` in a background terminal. Code changes from agent waves are picked up automatically between waves. If agents are also writing docs or notes, you'll need a manual `/graphify --update` after those waves.

---

## Git commit hook — `graphify hook`

Install a post-commit hook that auto-rebuilds the graph after every commit. No background process needed — triggers once per commit, works with any editor.

```bash
graphify hook install    # install
graphify hook uninstall  # remove
graphify hook status     # check
```

After every `git commit`, the hook detects which code files changed (via `git diff HEAD~1`), re-runs AST extraction on those files, and rebuilds `graph.json` and `GRAPH_REPORT.md`. Doc/image changes are ignored by the hook — run `/graphify --update` manually for those.

If a post-commit hook already exists, graphify appends to it rather than replacing it.

---

## Native CLAUDE.md integration — `graphify claude`

Run once per project to make graphify always-on in Claude Code sessions:

```bash
graphify claude install
```

This writes a `## graphify` section to the local `CLAUDE.md` that instructs Claude to check the graph before answering codebase questions and rebuild it after code changes. No manual `/graphify` needed in future sessions.

```bash
graphify claude uninstall  # remove the section
```
