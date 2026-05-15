#!/usr/bin/env python3
"""
build_graph.py — wiki/ → static D3.js graph view (+ optional Obsidian Canvas).

llm-wiki skill 의 §3 query 모드 / §4 lint 모드 보조.
의존성 zero (Python stdlib only). D3 는 CDN.

사용:
    python build_graph.py --wiki-root <WIKI_ROOT> --output-dir <out>

산출:
    <output-dir>/graph.json    # {nodes: [...], links: [...]}
    <output-dir>/graph.html    # standalone D3 force-directed (브라우저 더블클릭)
    <output-dir>/graph.canvas  # (옵션 --canvas) Obsidian Canvas JSON
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

WIKI_SUBDIRS = ["entities", "concepts", "sources", "questions", "syntheses"]

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\[\]|#]+)(?:\|([^\]]+))?(?:#[^\]]*)?\]\]")
MDLINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+\.md)(?:#[^)]*)?\)")


# ----- Parsing -----

def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    yaml_block = m.group(1)
    body = text[m.end():]
    fm: dict = {}
    for line in yaml_block.split("\n"):
        line = line.rstrip()
        if not line or ":" not in line:
            continue
        if line.startswith(("  ", "\t", "- ")):
            continue
        k, _, v = line.partition(":")
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            v = [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
        else:
            v = v.strip("'\"")
        fm[k.strip()] = v
    return fm, body


def discover_notes(wiki_root: Path) -> list[dict]:
    notes = []
    for sub in WIKI_SUBDIRS:
        d = wiki_root / "wiki" / sub
        if not d.exists():
            continue
        for md in d.rglob("*.md"):
            try:
                text = md.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            fm, body = parse_frontmatter(text)
            slug = md.stem
            title = fm.get("title") or slug.replace("-", " ").replace("_", " ")
            ntype = fm.get("type") or sub.rstrip("s")
            notes.append({
                "id": fm.get("id") or slug,
                "title": title,
                "type": ntype,
                "tags": fm.get("tags") if isinstance(fm.get("tags"), list) else [],
                "status": fm.get("status") or "draft",
                "path": str(md.relative_to(wiki_root)).replace("\\", "/"),
                "abs_path": str(md.resolve()),
                "_body": body,
                "_slug": slug,
            })
    return notes


# ----- Link extraction & resolution -----

def build_title_index(notes: list[dict]) -> dict[str, str]:
    """title (lowercased) / slug → note id."""
    idx = {}
    for n in notes:
        idx[n["title"].lower()] = n["id"]
        idx[n["_slug"].lower()] = n["id"]
        idx[n["id"].lower()] = n["id"]
    return idx


def extract_links(note: dict, title_index: dict, notes_by_path: dict) -> list[dict]:
    """wikilink + md link 추출 + resolve."""
    out = []
    body = note["_body"]

    for m in WIKILINK_RE.finditer(body):
        target_raw = m.group(1).strip()
        target_id = title_index.get(target_raw.lower())
        out.append({
            "source": note["id"],
            "target": target_id or target_raw,
            "label": m.group(2) or target_raw,
            "kind": "wikilink",
            "resolved": target_id is not None,
        })

    note_dir = Path(note["path"]).parent
    for m in MDLINK_RE.finditer(body):
        label = m.group(1)
        rel = m.group(2)
        if rel.startswith(("http://", "https://")):
            continue
        try:
            target_path = str((note_dir / rel).as_posix())
        except ValueError:
            continue
        # try resolve to a note by path
        target_id = None
        target_path_norm = target_path.replace("\\", "/")
        for path_key, nid in notes_by_path.items():
            if path_key.endswith(target_path_norm) or target_path_norm.endswith(path_key):
                target_id = nid
                break
        if not target_id:
            target_id = title_index.get(Path(rel).stem.lower())
        out.append({
            "source": note["id"],
            "target": target_id or rel,
            "label": label,
            "kind": "mdlink",
            "resolved": target_id is not None,
        })
    return out


# ----- Graph building -----

def build_graph(wiki_root: Path, include_orphans: bool, type_filter: list[str] | None) -> dict:
    notes = discover_notes(wiki_root)
    if type_filter:
        notes = [n for n in notes if n["type"] in type_filter]
    title_index = build_title_index(notes)
    notes_by_path = {n["path"]: n["id"] for n in notes}

    all_links = []
    for n in notes:
        all_links.extend(extract_links(n, title_index, notes_by_path))

    referenced = set()
    for link in all_links:
        if link["resolved"]:
            referenced.add(link["source"])
            referenced.add(link["target"])

    nodes = []
    for n in notes:
        is_orphan = n["id"] not in referenced
        if is_orphan and not include_orphans:
            continue
        nodes.append({
            "id": n["id"],
            "title": n["title"],
            "type": n["type"],
            "tags": n["tags"],
            "status": n["status"],
            "path": n["path"],
            "abs_path": n["abs_path"],
            "orphan": is_orphan,
        })

    valid_ids = {n["id"] for n in nodes}
    links = [
        {"source": l["source"], "target": l["target"], "kind": l["kind"]}
        for l in all_links
        if l["resolved"] and l["source"] in valid_ids and l["target"] in valid_ids
    ]

    inbound = defaultdict(int)
    outbound = defaultdict(int)
    for l in links:
        outbound[l["source"]] += 1
        inbound[l["target"]] += 1
    for n in nodes:
        n["inbound"] = inbound[n["id"]]
        n["outbound"] = outbound[n["id"]]
        n["degree"] = n["inbound"] + n["outbound"]

    return {"nodes": nodes, "links": links, "stats": {
        "note_count": len(notes),
        "rendered_nodes": len(nodes),
        "links": len(links),
        "orphans": sum(1 for n in nodes if n["orphan"]),
    }}


# ----- HTML emission -----

TYPE_COLORS = {
    "entity": "#4A90E2",
    "concept": "#7ED321",
    "source": "#F5A623",
    "question": "#D0021B",
    "synthesis": "#9013FE",
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>LLM Wiki Graph</title>
<style>
  body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #1a1a1a; color: #eee; }
  #toolbar { position: fixed; top: 0; left: 0; right: 0; background: #2a2a2a; padding: 8px 16px; z-index: 10; display: flex; gap: 12px; align-items: center; }
  #search { padding: 4px 8px; width: 240px; background: #1a1a1a; color: #eee; border: 1px solid #555; }
  .stats { font-size: 12px; color: #aaa; }
  .legend { display: flex; gap: 8px; font-size: 12px; }
  .legend-item { display: flex; align-items: center; gap: 4px; }
  .legend-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
  svg { display: block; }
  .node circle { stroke: #fff; stroke-width: 1.5; cursor: pointer; }
  .node text { font-size: 10px; fill: #ddd; pointer-events: none; }
  .node.dim { opacity: 0.15; }
  .link { stroke: #555; stroke-opacity: 0.4; }
  .link.dim { opacity: 0.05; }
  .link.highlight { stroke: #fff; stroke-opacity: 0.9; }
</style>
</head>
<body>
<div id="toolbar">
  <strong>LLM Wiki Graph</strong>
  <input id="search" placeholder="search notes…">
  <span class="stats">__STATS__</span>
  <div class="legend">__LEGEND__</div>
</div>
<svg id="graph"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const data = __DATA__;
const typeColors = __COLORS__;

const width = window.innerWidth, height = window.innerHeight;
const svg = d3.select("#graph").attr("width", width).attr("height", height);
const g = svg.append("g");

svg.call(d3.zoom().scaleExtent([0.1, 5]).on("zoom", e => g.attr("transform", e.transform)));

const sim = d3.forceSimulation(data.nodes)
  .force("link", d3.forceLink(data.links).id(d => d.id).distance(60))
  .force("charge", d3.forceManyBody().strength(-200))
  .force("center", d3.forceCenter(width / 2, height / 2))
  .force("collide", d3.forceCollide().radius(d => Math.max(8, Math.sqrt(d.degree + 1) * 4) + 2));

const link = g.append("g").selectAll("line").data(data.links).join("line")
  .attr("class", "link").attr("stroke-width", 1);

const node = g.append("g").selectAll("g.node").data(data.nodes).join("g")
  .attr("class", "node")
  .call(d3.drag()
    .on("start", (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
    .on("drag", (e, d) => { d.fx = e.x; d.fy = e.y; })
    .on("end", (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }));

node.append("circle")
  .attr("r", d => Math.max(4, Math.sqrt(d.degree + 1) * 3))
  .attr("fill", d => typeColors[d.type] || "#888")
  .attr("opacity", d => d.orphan ? 0.4 : 1);

node.append("title").text(d => `${d.title}\\n${d.type} | inbound ${d.inbound} | outbound ${d.outbound}\\n${d.path}`);

node.append("text").attr("dx", 8).attr("dy", 3).text(d => d.title);

node.on("click", (e, d) => {
  if (d.abs_path) {
    const url = "file:///" + d.abs_path.replace(/\\\\/g, "/").replace(/^\\//, "");
    window.open(url, "_blank");
  }
});

sim.on("tick", () => {
  link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
  node.attr("transform", d => `translate(${d.x},${d.y})`);
});

const search = document.getElementById("search");
search.addEventListener("input", () => {
  const q = search.value.toLowerCase().trim();
  node.classed("dim", d => q && !(d.title.toLowerCase().includes(q) || (d.tags || []).some(t => t.toLowerCase().includes(q))));
  link.classed("dim", d => {
    if (!q) return false;
    const s = data.nodes.find(n => n.id === (d.source.id || d.source));
    const t = data.nodes.find(n => n.id === (d.target.id || d.target));
    return !((s && (s.title.toLowerCase().includes(q) || (s.tags||[]).some(x=>x.toLowerCase().includes(q)))) ||
             (t && (t.title.toLowerCase().includes(q) || (t.tags||[]).some(x=>x.toLowerCase().includes(q)))));
  });
});
</script>
</body>
</html>"""


def render_html(graph: dict, out_path: Path) -> None:
    stats = graph["stats"]
    stats_str = (
        f"{stats['rendered_nodes']} nodes / {stats['links']} links "
        f"({stats['orphans']} orphans)"
    )
    legend = "".join(
        f'<span class="legend-item"><span class="legend-dot" style="background:{c}"></span>{t}</span>'
        for t, c in TYPE_COLORS.items()
    )
    html = (
        HTML_TEMPLATE
        .replace("__DATA__", json.dumps(graph, ensure_ascii=False))
        .replace("__COLORS__", json.dumps(TYPE_COLORS))
        .replace("__STATS__", stats_str)
        .replace("__LEGEND__", legend)
    )
    out_path.write_text(html, encoding="utf-8")


# ----- Obsidian Canvas -----

def render_canvas(graph: dict, out_path: Path, wiki_root: Path) -> None:
    """JsonCanvas 1.0 format. node `type: file` references wiki notes."""
    nodes = []
    cols = max(4, int(len(graph["nodes"]) ** 0.5))
    cell_w, cell_h = 420, 280
    pad_x, pad_y = 40, 40
    for i, n in enumerate(graph["nodes"]):
        r, c = divmod(i, cols)
        nodes.append({
            "id": n["id"],
            "type": "file",
            "file": n["path"],
            "x": c * (cell_w + pad_x),
            "y": r * (cell_h + pad_y),
            "width": cell_w,
            "height": cell_h,
            "color": TYPE_COLORS.get(n["type"], "#888"),
        })
    edges = [
        {
            "id": f"e-{i}",
            "fromNode": l["source"],
            "fromSide": "right",
            "toNode": l["target"],
            "toSide": "left",
        }
        for i, l in enumerate(graph["links"])
    ]
    canvas = {"nodes": nodes, "edges": edges}
    out_path.write_text(json.dumps(canvas, ensure_ascii=False, indent=2), encoding="utf-8")


# ----- Main -----

def main():
    p = argparse.ArgumentParser(description="Build a D3.js graph from a wiki/ directory.")
    p.add_argument("--wiki-root", required=True, help="WIKI_ROOT (containing wiki/ subdir)")
    p.add_argument("--output-dir", default=".", help="결과물 출력 디렉토리")
    p.add_argument("--include-orphans", action="store_true", help="고립 노트도 포함 (default include)")
    p.add_argument("--exclude-orphans", action="store_true", help="고립 노트 제외")
    p.add_argument("--type", default=None, help="콤마 구분 type 필터 (entity,concept,...)")
    p.add_argument("--canvas", action="store_true", help="Obsidian Canvas (.canvas) 도 함께 출력")
    args = p.parse_args()

    wiki_root = Path(args.wiki_root).resolve()
    if not (wiki_root / "wiki").exists():
        print(f"ERROR: {wiki_root}/wiki/ not found.", file=sys.stderr)
        sys.exit(1)

    include_orphans = not args.exclude_orphans
    type_filter = [t.strip() for t in args.type.split(",")] if args.type else None

    graph = build_graph(wiki_root, include_orphans, type_filter)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    public = {
        "nodes": [{k: v for k, v in n.items() if not k.startswith("_")} for n in graph["nodes"]],
        "links": graph["links"],
        "stats": graph["stats"],
    }
    (out_dir / "graph.json").write_text(
        json.dumps(public, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    render_html(public, out_dir / "graph.html")

    if args.canvas:
        render_canvas(public, out_dir / "graph.canvas", wiki_root)

    stats = public["stats"]
    print(
        f"OK: {out_dir}/graph.html — {stats['rendered_nodes']} nodes / "
        f"{stats['links']} links ({stats['orphans']} orphans)"
    )


if __name__ == "__main__":
    main()
