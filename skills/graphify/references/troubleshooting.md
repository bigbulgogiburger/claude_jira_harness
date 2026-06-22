# Troubleshooting

**When to read this file:** A run failed or produced unexpected terminal behavior. Otherwise skip.

## PowerShell 5.1: Vertical scrolling stops working

If vertical scrolling breaks in PowerShell after running graphify, this is caused by ANSI escape sequences from the `graspologic` library. Graphify v0.3.10+ suppresses this output, but if you still see the issue:

1. **Upgrade graphify**: `pip install --upgrade graphifyy`
2. **Use Windows Terminal** instead of the legacy PowerShell console — Windows Terminal handles ANSI codes correctly
3. **Reset your terminal**: close and reopen PowerShell
4. **Skip graspologic**: uninstall it (`pip uninstall graspologic`) and graphify will fall back to NetworkX's built-in Louvain algorithm, which produces no ANSI output

## "ERROR: Graph is empty — extraction produced no nodes"

Step 4 raised this. Possible causes:

- All files were skipped (sensitive file filter)
- Binary-only corpus (no readable text)
- Extraction failed (subagents returned empty / invalid JSON)

Check `.graphify_detect.json` for `skipped_sensitive` counts, then verify chunk JSON files in `graphify-out/.graphify_chunk_*.json` are non-empty.

## "chunk N missing from disk — subagent may have been read-only"

A subagent was dispatched with the wrong agent type (e.g., Explore is read-only and cannot write files). Re-run with `subagent_type="general-purpose"`.

## More than half of chunks failed or missing

Stop and tell the user to re-run, ensuring `subagent_type="general-purpose"` is used for all chunks in Step 3B2.

## `import graphify` fails after Step 1

`pip install graphifyy` failed silently. Try:

1. Check that `python` is on PATH: `python --version`
2. Try `uv tool install --upgrade graphifyy` if `uv` is available (faster, isolated)
3. Manually install: `pip install graphifyy --verbose`
