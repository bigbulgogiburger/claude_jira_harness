#!/usr/bin/env python3
"""
fetch_web.py — URL → article main content + meta extractor.

llm-wiki skill 의 source-types.md §1 (Article) ingest 에서 호출.

사용:
    python fetch_web.py --url <URL> --output-dir <raw/articles/> --slug <slug>

산출:
    <output-dir>/<slug>.md          # readability 본문 (markdown 변환)
    <output-dir>/<slug>.html        # 원본 HTML (옵션)
    <output-dir>/<slug>.meta.json   # title, author, publish_date, canonical_url, etc

의존성 (선택, 폴백 체인):
    1. requests + readability-lxml + html2text   (최선)
    2. requests + beautifulsoup4                  (폴백 1)
    3. urllib + 텍스트 추출 단순                  (폴백 2)
    실패 시 stderr 에 메시지 + exit 1 — 사용자 paste 폴백.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

# ----- HTTP fetch -----

def fetch_html(url: str, timeout: int = 30) -> tuple[str, str | None]:
    """(html_text, final_url) — redirect 추적."""
    try:
        import requests  # type: ignore
    except ImportError:
        return _fetch_urllib(url, timeout)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; llm-wiki/1.0; "
            "+https://github.com/anthropics/claude-code)"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
    }
    resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    resp.raise_for_status()
    enc = resp.encoding or "utf-8"
    return resp.content.decode(enc, errors="replace"), str(resp.url)


def _fetch_urllib(url: str, timeout: int) -> tuple[str, str | None]:
    import urllib.request
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; llm-wiki/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
        final = r.geturl()
        try:
            return body.decode("utf-8"), final
        except UnicodeDecodeError:
            return body.decode("utf-8", errors="replace"), final


# ----- Canonical URL / dedup -----

def normalize_url(url: str) -> str:
    """utm_*, fbclid 등 추적 파라미터 제거. 멱등성 보장용."""
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    cleaned = [
        (k, v) for k, v in query
        if not k.startswith("utm_") and k not in {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "_hsenc", "_hsmi"}
    ]
    return urllib.parse.urlunparse(
        parsed._replace(query=urllib.parse.urlencode(cleaned), fragment="")
    )


# ----- Meta extraction -----

META_TAGS = [
    ("meta[property='og:title']", "content"),
    ("meta[name='twitter:title']", "content"),
    ("title", None),
]

AUTHOR_TAGS = [
    ("meta[name='author']", "content"),
    ("meta[property='article:author']", "content"),
    ("meta[name='twitter:creator']", "content"),
]

DATE_TAGS = [
    ("meta[property='article:published_time']", "content"),
    ("meta[name='date']", "content"),
    ("meta[name='publish-date']", "content"),
    ("meta[name='DC.date.issued']", "content"),
    ("time[datetime]", "datetime"),
]

CANONICAL_TAGS = [
    ("link[rel='canonical']", "href"),
    ("meta[property='og:url']", "content"),
]


def _bs_extract(html: str) -> dict | None:
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError:
        return None
    soup = BeautifulSoup(html, "html.parser")
    out: dict = {}

    def first_match(rules):
        for sel, attr in rules:
            el = soup.select_one(sel)
            if not el:
                continue
            if attr is None:
                txt = el.get_text(strip=True)
                if txt:
                    return txt
            else:
                val = el.get(attr)
                if val:
                    return val.strip()
        return None

    out["title"] = first_match(META_TAGS)
    out["author"] = first_match(AUTHOR_TAGS)
    out["publish_date"] = first_match(DATE_TAGS)
    out["canonical_url"] = first_match(CANONICAL_TAGS)

    # JSON-LD
    ld = soup.find("script", type="application/ld+json")
    if ld and ld.string:
        try:
            data = json.loads(ld.string)
            if isinstance(data, list):
                data = data[0] if data else {}
            if isinstance(data, dict):
                if not out.get("author"):
                    a = data.get("author")
                    if isinstance(a, dict):
                        out["author"] = a.get("name")
                    elif isinstance(a, str):
                        out["author"] = a
                if not out.get("publish_date"):
                    out["publish_date"] = data.get("datePublished") or data.get("dateCreated")
                if not out.get("title"):
                    out["title"] = data.get("headline") or data.get("name")
        except (json.JSONDecodeError, AttributeError):
            pass

    # publisher
    site = soup.select_one("meta[property='og:site_name']")
    if site:
        out["publisher"] = site.get("content")

    return {k: v for k, v in out.items() if v}


# ----- Main content extraction -----

def extract_with_readability(html: str, url: str) -> tuple[str | None, str | None]:
    """readability-lxml + html2text. (markdown, title) or (None, None)."""
    try:
        from readability import Document  # type: ignore
        from html2text import HTML2Text  # type: ignore
    except ImportError:
        return None, None

    doc = Document(html)
    article_html = doc.summary(html_partial=True)
    title = doc.short_title()
    h = HTML2Text()
    h.body_width = 0
    h.ignore_images = False
    h.ignore_links = False
    md = h.handle(article_html).strip()
    return md or None, title or None


def extract_with_bs(html: str) -> tuple[str | None, str | None]:
    """BeautifulSoup main/article/body 폴백."""
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError:
        return None, None
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.find("title")
    title = title_el.get_text(strip=True) if title_el else None

    for sel in ["article", "main", "[role=main]", ".post-content", ".entry-content", "#content"]:
        node = soup.select_one(sel)
        if node:
            for junk in node.select("script, style, nav, footer, aside, .ads, .advertisement"):
                junk.decompose()
            text = node.get_text("\n", strip=True)
            if len(text) > 500:
                return text, title

    body = soup.body
    if body:
        for junk in body.select("script, style, nav, footer, aside, header"):
            junk.decompose()
        text = body.get_text("\n", strip=True)
        if len(text) > 300:
            return text, title

    return None, title


# ----- Read time -----

def estimate_read_time(markdown: str, wpm: int = 220) -> str:
    words = len(re.findall(r"\b\w+\b", markdown))
    minutes = max(1, round(words / wpm))
    return f"{minutes} min"


# ----- Main -----

def main():
    p = argparse.ArgumentParser(description="Fetch a URL and extract main article content.")
    p.add_argument("--url", required=True)
    p.add_argument("--output-dir", default=".", help="raw/articles/ 등 출력 디렉토리")
    p.add_argument("--slug", required=True, help="파일명 베이스 (YYYY-MM-DD_kebab-title)")
    p.add_argument("--keep-html", action="store_true", help="원본 HTML 도 보존")
    p.add_argument("--json", action="store_true", help="meta + content 를 stdout JSON 으로")
    p.add_argument("--timeout", type=int, default=30)
    args = p.parse_args()

    canonical = normalize_url(args.url)

    try:
        html, final_url = fetch_html(canonical, timeout=args.timeout)
    except Exception as e:
        print(f"ERROR: fetch failed — {e}", file=sys.stderr)
        sys.exit(1)

    meta = _bs_extract(html) or {}
    meta.setdefault("canonical_url", canonical)
    if final_url and final_url != canonical:
        meta.setdefault("redirected_to", normalize_url(final_url))
    meta["fetched_at"] = datetime.utcnow().isoformat() + "Z"

    md, title2 = extract_with_readability(html, canonical)
    if not md:
        md, title2 = extract_with_bs(html)

    if not md:
        print(
            "ERROR: main content extraction failed. "
            "Try paste mode — copy article text manually.",
            file=sys.stderr,
        )
        sys.exit(2)

    if not meta.get("title") and title2:
        meta["title"] = title2
    meta["estimated_read_time"] = estimate_read_time(md)
    meta["word_count"] = len(re.findall(r"\b\w+\b", md))

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    md_path = out_dir / f"{args.slug}.md"
    meta_path = out_dir / f"{args.slug}.meta.json"

    md_path.write_text(md, encoding="utf-8")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.keep_html:
        html_path = out_dir / f"{args.slug}.html"
        html_path.write_text(html, encoding="utf-8")

    if args.json:
        print(json.dumps({"meta": meta, "content_path": str(md_path)}, ensure_ascii=False, indent=2))
    else:
        print(f"OK: {md_path} ({meta['word_count']} words, {meta['estimated_read_time']})")


if __name__ == "__main__":
    main()
