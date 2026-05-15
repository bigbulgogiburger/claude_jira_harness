#!/usr/bin/env python3
"""
codebase-ai-readiness audit script.

임의의 git 레포지토리를 7-카테고리 100점 루브릭으로 감사하고
JSON 점수표, 한국어 HTML 대시보드, ROI 우선순위 액션 리스트를 생성한다.

Usage:
    python audit.py                                    # cwd 감사
    python audit.py --path /path/to/repo
    python audit.py --path . --out ./report
    python audit.py --rubric ./custom_rubric.json
    python audit.py --format json                      # JSON만
    python audit.py --no-html                          # HTML 생략

설계 원칙:
- stdlib만 사용 (PyYAML 등 외부 의존성 없음)
- 결정적: 같은 입력 -> 같은 출력
- 프레임워크 무관: 언어 감지는 확장자 + 매니페스트 패턴
- 빠름: git ls-files 사용 (.gitignore 자동 반영)
"""

from __future__ import annotations

import argparse
import datetime
import html
import json
import os
import re
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

# ===========================================================================
# 언어 / 도구 시그니처 — 언어 무관성을 유지하기 위한 단일 데이터 소스
# ===========================================================================

EXT_TO_LANG: dict[str, str] = {
    ".py": "python", ".pyi": "python",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".java": "java", ".kt": "kotlin", ".kts": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp", ".fs": "fsharp",
    ".swift": "swift",
    ".scala": "scala",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".h": "cpp", ".c": "c",
    ".ex": "elixir", ".exs": "elixir",
    ".erl": "erlang",
    ".clj": "clojure",
    ".dart": "dart",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell",
}

# 한 언어를 결정짓는 매니페스트(빌드/패키지 디스크립터)
LANG_MANIFESTS: dict[str, list[str]] = {
    "python": ["pyproject.toml", "setup.py", "setup.cfg", "Pipfile", "requirements.txt"],
    "javascript": ["package.json"],
    "typescript": ["package.json", "tsconfig.json"],
    "java": ["pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"],
    "kotlin": ["build.gradle.kts", "build.gradle"],
    "go": ["go.mod"],
    "rust": ["Cargo.toml"],
    "ruby": ["Gemfile", "*.gemspec"],
    "php": ["composer.json"],
    "csharp": ["*.csproj", "*.sln"],
    "swift": ["Package.swift"],
    "scala": ["build.sbt"],
    "elixir": ["mix.exs"],
    "dart": ["pubspec.yaml"],
}

LOCK_FILES: list[str] = [
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "bun.lock", "bun.lockb",  # 1.2+ 텍스트 포맷 + 구 바이너리
    "poetry.lock", "Pipfile.lock", "uv.lock", "requirements.lock",
    "pdm.lock", "rye.lock",
    "Cargo.lock",
    "go.sum",
    "Gemfile.lock",
    "composer.lock",
    "mix.lock",
    "pubspec.lock",
    "gradle.lockfile",
    "flake.lock",  # Nix
    "deno.lock",
]

LINTER_CONFIGS: dict[str, list[str]] = {
    "python": [".flake8", ".pylintrc", "ruff.toml", ".ruff.toml", "pylintrc"],
    "javascript": [".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yml",
                   ".eslintrc.yaml", "eslint.config.js", "eslint.config.mjs",
                   "eslint.config.cjs", "biome.json", ".biome.json"],
    "typescript": [".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yml",
                   ".eslintrc.yaml", "eslint.config.js", "eslint.config.mjs",
                   "biome.json"],
    "java": ["checkstyle.xml", "config/checkstyle/checkstyle.xml", "pmd.xml",
             "spotbugs-exclude.xml", ".checkstyle"],
    "kotlin": [".editorconfig", "detekt.yml", "detekt-config.yml"],
    "go": [".golangci.yml", ".golangci.yaml", ".golangci.toml"],
    "rust": ["clippy.toml", ".clippy.toml"],
    "ruby": [".rubocop.yml"],
    "php": ["phpstan.neon", "phpcs.xml", ".php-cs-fixer.php"],
    "shell": [".shellcheckrc"],
}

FORMATTER_CONFIGS: dict[str, list[str]] = {
    "python": ["pyproject.toml", ".black", "ruff.toml"],  # black/ruff
    "javascript": [".prettierrc", ".prettierrc.json", ".prettierrc.js",
                   ".prettierrc.yml", ".prettierrc.yaml", "prettier.config.js",
                   "biome.json"],
    "typescript": [".prettierrc", ".prettierrc.json", "biome.json"],
    "java": ["spotless.gradle", ".java-format"],
    "go": [],  # gofmt가 표준이라 설정 불요
    "rust": ["rustfmt.toml", ".rustfmt.toml"],
}

TYPE_CHECKER_CONFIGS: dict[str, list[str]] = {
    "python": ["mypy.ini", ".mypy.ini", "pyrightconfig.json"],  # 또는 pyproject.toml의 [tool.mypy]
    "javascript": ["tsconfig.json", "jsconfig.json"],
    "typescript": ["tsconfig.json"],
    "java": [],  # 컴파일러가 처리
    "go": [],
    "rust": [],
    "ruby": ["sorbet/config", "*.rbi"],
}

# CI 설정 패턴 (글롭/경로)
CI_PATTERNS: list[str] = [
    ".github/workflows/",
    ".gitlab-ci.yml", ".gitlab-ci.yaml",
    ".circleci/config.yml",
    "Jenkinsfile",
    "azure-pipelines.yml", "azure-pipelines.yaml",
    ".travis.yml",
    ".drone.yml",
    "bitbucket-pipelines.yml",
    ".buildkite/",
    ".woodpecker.yml",
    "appveyor.yml",
]

PRECOMMIT_PATTERNS: list[str] = [
    ".pre-commit-config.yaml", ".pre-commit-config.yml",
    ".husky/", ".husky",
    "lefthook.yml", "lefthook.yaml",
    ".lefthook.yml",
    ".git-hooks/", "git-hooks/",
    "hooks/",
]

CONTAINER_PATTERNS: list[str] = [
    "Dockerfile", "dockerfile",
    "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml",
    ".devcontainer/devcontainer.json", ".devcontainer.json",
    "Containerfile",
]

RUNTIME_VERSION_FILES: list[str] = [
    ".nvmrc", ".node-version",
    ".python-version",
    ".ruby-version",
    ".java-version",
    ".tool-versions",
    "rust-toolchain", "rust-toolchain.toml",
    ".terraform-version",
    ".go-version",
]

AGENTS_FILES: list[str] = [
    "AGENTS.md",
    "CLAUDE.md",
    ".cursorrules",
    ".cursor/rules",
    ".github/copilot-instructions.md",
    "AGENT.md",
]

ADR_DIRS: list[str] = [
    "docs/adr",
    "docs/adrs",
    "docs/decisions",
    "doc/adr",
    "adr",
    "adrs",
    "architecture/decisions",
]

LICENSE_FILES: list[str] = [
    "LICENSE", "LICENSE.md", "LICENSE.txt",
    "LICENCE", "LICENCE.md",
    "COPYING", "COPYING.md",
]

ENV_EXAMPLE_FILES: list[str] = [
    ".env.example", ".env.sample", ".env.template",
    "env.example", "example.env", ".env.local.example",
]

DEP_SCAN_PATTERNS: list[str] = [
    ".github/dependabot.yml", ".github/dependabot.yaml",
    "renovate.json", ".renovaterc.json", ".renovaterc",
    ".snyk",
]

# 시크릿 패턴 — 보수적이지만 YAML/properties도 커버
# 핵심 원칙: 따옴표 강제하지 않음 (YAML/env/properties는 따옴표 없이 작성)
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AWS Access Key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("AWS Secret", re.compile(
        r"aws[_\-]?secret[_\-]?access[_\-]?key\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{40}['\"]?",
        re.I)),
    ("Generic API Key (quoted)", re.compile(
        r"(?:api[_\-]?key|apikey|secret[_\-]?key|access[_\-]?token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{24,}['\"]",
        re.I)),
    # YAML/properties 스타일 — 따옴표 없는 시크릿 (단, "your_xxx", "xxx", "<placeholder>" 같은 dummy 제외)
    ("Generic API Key (yaml)", re.compile(
        r"(?:api[_\-]?key|apikey|secret[_\-]?key|access[_\-]?token|password|passwd)"
        r"\s*[:=]\s*(?!['\"]?(?:your[_\-]|xxx|<|\$\{|change[_\-]?me|placeholder|example|sample|fake|dummy|test))"
        r"([A-Za-z0-9_\-./+=]{20,})",
        re.I)),
    ("GitHub Token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,255}\b")),
    ("Slack Token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,48}\b")),
    ("Private Key Header", re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH |)PRIVATE KEY-----")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("Google API Key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("Stripe Secret Key", re.compile(r"\bsk_live_[0-9A-Za-z]{24,}\b")),
]

# 시크릿 스캔에서 무시할 파일 (테스트 픽스처, 문서, 샘플 등)
SECRET_IGNORE_HINTS: list[str] = [
    "test", "tests", "fixture", "fixtures", "sample", "example",
    "mock", "mocks", "doc", "docs", ".md", ".rst", ".txt",
    "node_modules", "vendor", "dist", "build", "target",
    ".lock", "lockfile",
]

# 빈 catch / 에러 무시 패턴
EMPTY_CATCH_PATTERNS: list[re.Pattern[str]] = [
    # JS/Java/C# — 빈 catch (선택적 주석/공백 포함)
    re.compile(r"catch\s*\([^)]*\)\s*\{\s*(?://[^\n]*\s*|/\*[^*]*\*/\s*)*\}", re.M),
    # Python — except: pass / except: ...
    re.compile(r"except\s*[^:]*:\s*pass\b", re.M),
    re.compile(r"except\s*[^:]*:\s*\.\.\.", re.M),
    # Python — except: 그리고 다음 줄에 단일 주석만
    re.compile(r"except\s*[^:]*:\s*\n\s*#[^\n]*\s*\n\s*(?=def|class|except|finally|else|\S)", re.M),
    # Ruby — rescue ... \n end
    re.compile(r"rescue\s+[^=\n]*\s*\n\s*end", re.M),
    # Go — `err != nil { _ = err }` (에러 무시)
    re.compile(r"if\s+err\s*!=\s*nil\s*\{\s*_\s*=\s*err\s*\}", re.M),
]

# 구조화/표준 로거 시그니처
STRUCTURED_LOG_HINTS: list[str] = [
    "structlog", "logback", "log4j", "slf4j", "pino", "winston", "bunyan",
    "zap", "zerolog", "logrus", "tracing-subscriber",
]
PRINT_LOG_PATTERN = re.compile(r"\bprint\(|\bconsole\.log\(|\bSystem\.out\.println\(", re.I)

# 디렉토리에서 무시할 후보 (감사 대상 아님)
SKIP_DIRS: set[str] = {
    "node_modules", "vendor", "target", "build", "dist", "out",
    ".gradle", ".idea", ".vscode", "__pycache__", ".pytest_cache",
    ".tox", ".venv", "venv", ".env", "coverage", ".nyc_output",
    ".next", ".nuxt", "bower_components", "Pods",
}

# ===========================================================================
# 레포 컨텍스트 빌드
# ===========================================================================

class RepoContext:
    """감사 대상 레포의 사전 계산 컨텍스트."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.files: list[Path] = []          # 추적된 파일들 (root 상대 경로)
        self.source_files: list[Path] = []   # 소스 코드만
        self.test_files: list[Path] = []
        self.lang_stats: Counter[str] = Counter()
        self.file_loc: dict[Path, int] = {}
        self.primary_language: str = "unknown"
        self.is_git: bool = False
        self.total_loc: int = 0
        self.depth_per_file: list[int] = []

    def build(self) -> None:
        self._collect_files()
        self._classify_files()
        self._compute_loc()
        self._infer_primary_language()

    def _collect_files(self) -> None:
        # 가능하면 git ls-files (gitignore 자동 반영)
        # -z 플래그 + bytes로 받아서 quotepath로 인한 비ASCII 파일명 손실 방지
        try:
            result = subprocess.run(
                ["git", "-c", "core.quotepath=off", "-C", str(self.root), "ls-files", "-z"],
                capture_output=True, timeout=60, check=False,
            )
            if result.returncode == 0:
                self.is_git = True
                # NUL 분리 + UTF-8 디코드 (실패 시 latin-1 fallback)
                raw = result.stdout
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    text = raw.decode("latin-1", errors="replace")
                lines = [ln for ln in text.split("\0") if ln.strip()]
                self.files = [Path(ln) for ln in lines]
                return
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # Fallback: 파일 시스템 walk (SKIP_DIRS 제외)
        self.is_git = False
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".git")]
            for fn in filenames:
                full = Path(dirpath) / fn
                rel = full.relative_to(self.root)
                self.files.append(rel)

    def _classify_files(self) -> None:
        for rel in self.files:
            ext = rel.suffix.lower()
            lang = EXT_TO_LANG.get(ext)
            self.depth_per_file.append(len(rel.parts))

            if lang:
                self.lang_stats[lang] += 1
                # test 분류
                parts_lower = {p.lower() for p in rel.parts}
                name_lower = rel.name.lower()
                is_test = (
                    any(p in parts_lower for p in ("test", "tests", "spec", "specs", "__tests__"))
                    or name_lower.startswith("test_")
                    or name_lower.endswith("_test" + ext)
                    or ".spec." in name_lower
                    or ".test." in name_lower
                )
                if is_test:
                    self.test_files.append(rel)
                else:
                    self.source_files.append(rel)

    def _compute_loc(self) -> None:
        # 표본 추출: 너무 큰 레포에서는 모든 소스 LOC 계산이 비쌀 수 있음.
        # 5000개 초과시 무작위 샘플링 대신 우선 일정 개수까지만 정확 측정 후 외삽.
        target = self.source_files[:5000]
        for rel in target:
            full = self.root / rel
            try:
                with full.open("rb") as f:
                    # 빠르게 newline 카운트
                    loc = sum(1 for _ in f)
                self.file_loc[rel] = loc
                self.total_loc += loc
            except OSError:
                self.file_loc[rel] = 0

    def _infer_primary_language(self) -> None:
        if not self.lang_stats:
            return
        self.primary_language = self.lang_stats.most_common(1)[0][0]

    # ─── helpers ───────────────────────────────────────────────────
    def has(self, *paths: str) -> bool:
        """주어진 상대경로 중 하나라도 존재하면 True."""
        for p in paths:
            full = self.root / p
            if full.exists():
                return True
        return False

    def has_any_glob(self, patterns: list[str]) -> bool:
        for p in patterns:
            if "/" in p and p.endswith("/"):  # 디렉토리
                if (self.root / p.rstrip("/")).is_dir():
                    return True
            elif "*" in p:
                # glob 처리
                for m in self.root.rglob(p):
                    if m.is_file() or m.is_dir():
                        return True
            else:
                if (self.root / p).exists():
                    return True
        return False

    def find_first(self, names: list[str]) -> Path | None:
        for n in names:
            full = self.root / n
            if full.exists():
                return full
        return None

    def read_text(self, rel: str | Path, max_bytes: int = 200_000) -> str:
        full = self.root / rel
        try:
            with full.open("rb") as f:
                data = f.read(max_bytes)
            return data.decode("utf-8", errors="replace")
        except OSError:
            return ""


# ===========================================================================
# 개별 검사 — 각 함수는 (score, evidence_str, details_dict) 반환
# ===========================================================================

CheckResult = tuple[int, str, dict[str, Any]]
CheckFn = Callable[[RepoContext, dict[str, Any]], CheckResult]


# ─── 카테고리 1: 발견 가능성 & 컨텍스트 ─────────────────────────────────

def check_D1_readme(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    candidates = ["README.md", "README.rst", "README.txt", "README", "readme.md"]
    found = ctx.find_first(candidates)
    if not found:
        return 0, "README 파일을 찾을 수 없음", {}
    rel = str(found.relative_to(ctx.root))
    content = ctx.read_text(rel)
    score = 1
    has_quickstart = bool(re.search(
        r"quick.?start|getting started|시작하기|빠른\s?시작|installation|설치|usage|사용법|how to use|begin",
        content, re.I))
    if has_quickstart:
        score += 1
    # 코드 블록(```) 또는 인라인 명령(`backticks`)이 충분히 있으면 명령 존재로 간주
    code_blocks = len(re.findall(r"```", content)) // 2
    inline_cmds = len(re.findall(r"`[\w./\-]+(?:\s+[\w./\-=:]+){0,8}`", content))
    has_commands = code_blocks >= 2 or inline_cmds >= 6
    has_structure = bool(re.search(
        r"(directory|folder|structure|architecture|구조|디렉토리|아키텍처|모듈)",
        content, re.I))
    if has_commands and has_structure:
        score += 1
    return min(score, crit["max_points"]), f"{rel} ({len(content)} chars)", {
        "file": rel, "size": len(content),
        "has_quickstart": has_quickstart,
        "has_commands": has_commands,
        "has_structure": has_structure,
        "code_blocks": code_blocks,
        "inline_cmds": inline_cmds,
    }


def check_D2_agents_md(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    found = []
    for f in AGENTS_FILES:
        full = ctx.root / f
        if full.exists():
            found.append((f, full.stat().st_size if full.is_file() else -1))
    if not found:
        return 0, "AGENTS.md/CLAUDE.md/.cursorrules 등 에이전트 컨텍스트 파일 없음", {}

    # 가장 큰 파일 선택
    found.sort(key=lambda x: x[1], reverse=True)
    primary, size = found[0]
    if size < 0:  # 디렉토리(.cursor/rules)
        return 2, f"{primary} (디렉토리)", {"file": primary}
    content = ctx.read_text(primary)
    section_count = len(re.findall(r"^##\s+", content, re.M))
    has_commands = bool(re.search(r"(commands?|build|test|lint|run|명령|빌드|테스트)", content, re.I))
    has_structure = bool(re.search(r"(structure|architecture|directory|모듈|구조|디렉토리|아키텍처)", content, re.I))
    has_style = bool(re.search(r"(style|conventions?|규약|컨벤션|스타일)", content, re.I))
    has_workflow = bool(re.search(r"(workflow|git|branch|commit|워크플로|브랜치)", content, re.I))
    # boundaries: never/always/금지/필수 키워드만 — 이모지는 보너스 신호
    has_boundaries = bool(re.search(r"(boundaries|\bnever\b|\balways\b|금지|필수|반드시|절대)", content, re.I))
    quality_signals = sum([has_commands, has_structure, has_style, has_workflow, has_boundaries])
    score = 2  # 존재 자체로 2점
    if section_count >= 4 and quality_signals >= 3:
        score = 3
    if (section_count >= 6 or quality_signals >= 4) and size >= 1000:
        score = 4
    return min(score, crit["max_points"]), f"{primary} ({size} bytes, {section_count} sections)", {
        "file": primary, "size": size, "sections": section_count,
        "quality_signals": quality_signals,
    }


def check_D3_adr(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    for d in ADR_DIRS:
        full = ctx.root / d
        if full.is_dir():
            adr_count = sum(1 for _ in full.rglob("*.md"))
            if adr_count >= 1:
                return 2, f"{d}/ ({adr_count}개 ADR)", {"dir": d, "count": adr_count}
    # 단일 design doc 체크
    for f in ["docs/design.md", "DESIGN.md", "docs/architecture.md", "ARCHITECTURE.md"]:
        if (ctx.root / f).exists():
            return 1, f"{f} 존재 (구조화된 ADR 디렉토리는 아님)", {"file": f}
    return 0, "ADR 또는 설계 문서 없음", {}


def check_D4_architecture(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    # 다이어그램 시그니처: README/docs에 mermaid, plantuml, ASCII tree
    candidates = []
    for cand in ["README.md", "AGENTS.md", "CLAUDE.md",
                 "docs/architecture.md", "ARCHITECTURE.md",
                 "docs/design.md"]:
        full = ctx.root / cand
        if full.exists():
            candidates.append(cand)
    has_diagram = False
    has_text = False
    for c in candidates:
        text = ctx.read_text(c)
        if re.search(r"```mermaid|@startuml|graph TD|graph LR|sequenceDiagram", text, re.I):
            has_diagram = True
        if re.search(r"(architecture|module|component|구조|아키텍처)", text, re.I):
            has_text = True
    if has_diagram:
        return 2, "다이어그램 발견 (Mermaid/PlantUML)", {"diagram": True}
    if has_text:
        return 1, "아키텍처 텍스트 설명 발견 (다이어그램 없음)", {"diagram": False}
    return 0, "아키텍처 문서 흔적 없음", {}


def check_D5_glossary(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    candidates = ["GLOSSARY.md", "docs/glossary.md", "docs/terms.md",
                  "TERMS.md", "docs/dictionary.md"]
    for c in candidates:
        if (ctx.root / c).exists():
            return 1, f"{c} 발견", {"file": c}
    return 0, "용어집 없음", {}


def check_D6_examples(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    sources = []
    for c in ["README.md", "AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md"]:
        if (ctx.root / c).exists():
            sources.append(ctx.read_text(c))
    combined = "\n".join(sources)
    # 펜스 코드블록 (``` 또는 ~~~) — non-greedy + DOTALL로 인라인 백틱 통과
    code_blocks = re.findall(r"```[a-zA-Z0-9_+\-]*\s*\n?(.*?)```", combined, re.DOTALL)
    code_blocks += re.findall(r"~~~[a-zA-Z0-9_+\-]*\s*\n?(.*?)~~~", combined, re.DOTALL)
    # 4-space 들여쓰기 코드블록 (CommonMark) — 라인 단위
    indented_blocks = re.findall(r"(?:^|\n)((?:    [^\n]+\n)+)", combined)
    code_blocks.extend(indented_blocks)
    # 인라인 명령 (단일 백틱 안에 길이 4자 이상) — 일부 README는 인라인만 사용
    inline_cmds = re.findall(r"`([^`\n]{4,80})`", combined)

    # build/test/run 같은 명령처럼 보이는 블록만 카운트
    cmd_keywords = re.compile(
        r"\b(npm|yarn|pnpm|bun|deno|"
        r"pip|poetry|uv|pdm|rye|conda|"
        r"cargo|go|mvn|gradle|sbt|"
        r"make|just|task|"
        r"bash|sh|zsh|fish|powershell|pwsh|"
        r"docker|podman|kubectl|helm|"
        r"python|python3|node|deno|"
        r"rustup|rustc|java|javac|"
        r"test|build|run|install|deploy|start|"
        r"\./gradlew|\./mvnw|\./scripts|"
        r"git|curl|wget)\b",
        re.I)
    cmd_blocks = [blk for blk in code_blocks if cmd_keywords.search(blk)]
    cmd_inlines = [c for c in inline_cmds if cmd_keywords.search(c)]

    # 점수: 코드블록은 2점, 인라인은 1점 가중치 (인라인이 너무 흔해서 weight 낮춤)
    block_n = len(cmd_blocks)
    inline_n = len(cmd_inlines)
    weighted = block_n + inline_n // 3
    if weighted >= 7 or block_n >= 5:
        score = 3
    elif weighted >= 4 or block_n >= 3:
        score = 2
    elif weighted >= 2 or block_n >= 1 or inline_n >= 5:
        score = 1
    else:
        score = 0
    return score, f"코드블록 {block_n}개 + 인라인 명령 {inline_n}개 (가중 {weighted})", {
        "code_blocks": block_n, "inline_cmds": inline_n, "weighted": weighted,
    }


# ─── 카테고리 2: 구조 & 모듈성 ─────────────────────────────────────────

def check_S1_median_file_size(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    locs = [v for v in ctx.file_loc.values() if v > 0]
    if not locs:
        return 0, "소스 파일 없음", {}
    median = int(statistics.median(locs))
    if median <= 200:
        score = 3
    elif median <= 300:
        score = 2
    elif median <= 500:
        score = 1
    else:
        score = 0
    return score, f"중간 파일 크기 {median} LOC", {"median_loc": median, "samples": len(locs)}


def check_S2_huge_files(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    locs = list(ctx.file_loc.values())
    if not locs:
        return 0, "소스 파일 없음", {}
    huge = [v for v in locs if v > 1000]
    ratio = len(huge) / len(locs) if locs else 0.0
    if ratio < 0.005:
        score = 3
    elif ratio < 0.02:
        score = 2
    elif ratio < 0.05:
        score = 1
    else:
        score = 0
    # 가장 큰 5개 파일 정보
    big5 = sorted(ctx.file_loc.items(), key=lambda kv: kv[1], reverse=True)[:5]
    return score, f"1000+ LOC 파일 {len(huge)}개 ({ratio*100:.1f}%)", {
        "huge_count": len(huge), "ratio": ratio,
        "biggest": [{"file": str(p), "loc": l} for p, l in big5],
    }


def check_S3_god_file(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    if not ctx.file_loc or ctx.total_loc == 0:
        return 0, "소스 파일 없음", {}
    biggest = max(ctx.file_loc.items(), key=lambda kv: kv[1])
    ratio = biggest[1] / ctx.total_loc
    if ratio <= 0.05:
        score = 2
    elif ratio <= 0.10:
        score = 1
    else:
        score = 0
    return score, f"최대 파일 {biggest[0]} ({biggest[1]} LOC, {ratio*100:.1f}% of total)", {
        "biggest": str(biggest[0]), "loc": biggest[1], "ratio_of_total": ratio,
    }


def check_S4_dir_structure(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    has_src = any((ctx.root / d).is_dir() for d in [
        "src", "lib", "app", "internal", "pkg",
        "src/main", "src/main/java", "src/main/kotlin",
    ]) or len(ctx.source_files) > 0
    has_tests = (any((ctx.root / d).is_dir() for d in [
        "tests", "test", "src/test", "spec", "__tests__",
    ]) or len(ctx.test_files) > 0)
    has_docs = (ctx.root / "docs").is_dir() or (ctx.root / "doc").is_dir()
    score = sum([has_src, has_tests, has_docs])
    return min(score, crit["max_points"]), f"src={has_src}, tests={has_tests}, docs={has_docs}", {
        "has_src": has_src, "has_tests": has_tests, "has_docs": has_docs,
    }


def check_S5_naming_consistency(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    # 소스 파일이 없으면 vacuous credit 방지 — 네이밍을 검증할 대상 자체가 없음
    if not ctx.source_files:
        return 0, "소스 파일 없음 (검사 불가)", {"empty": True}
    # 같은 확장자 안에서 네이밍 스타일 통일성
    by_ext: dict[str, list[str]] = defaultdict(list)
    for rel in ctx.source_files:
        by_ext[rel.suffix.lower()].append(rel.stem)

    style_violations = 0
    total_checked = 0
    # ratio 분모는 인식된 스타일 합계여야 함 (이전 버전: total_checked로 정규화 → 분모 부풀림)
    classified_total = 0
    for ext, stems in by_ext.items():
        if len(stems) < 5:
            continue
        snake = sum(1 for s in stems if "_" in s and not any(c.isupper() for c in s))
        camel = sum(1 for s in stems if "_" not in s and re.match(r"^[a-z][a-zA-Z0-9]*$", s)
                    and any(c.isupper() for c in s))
        pascal = sum(1 for s in stems if re.match(r"^[A-Z][a-zA-Z0-9]*$", s))
        kebab = sum(1 for s in stems if "-" in s)
        styles = [snake, camel, pascal, kebab]
        total_styles = sum(styles)
        if total_styles == 0:
            continue
        dominant = max(styles)
        non_dominant = total_styles - dominant
        ratio = non_dominant / total_styles
        total_checked += len(stems)
        classified_total += total_styles
        if ratio > 0.2:
            style_violations += int(ratio * total_styles)

    # 분류 가능한 파일이 없으면 (모두 단일 단어 등) 보수적으로 1점
    if classified_total == 0:
        return 1, "스타일 분류 가능한 파일 부족 (보수적 부분 점수)", {
            "classified": 0, "checked": total_checked,
        }
    violation_ratio = style_violations / classified_total
    if violation_ratio < 0.05:
        score = 2
    elif violation_ratio < 0.15:
        score = 1
    else:
        score = 0
    return score, f"네이밍 불일치 비율 {violation_ratio*100:.1f}%", {
        "violation_ratio": violation_ratio, "checked": total_checked,
        "classified": classified_total,
    }


def check_S6_directory_depth(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    # 소스 파일만 대상 (LICENSE/.gitignore 등 루트 dotfile은 깊이 측정에서 제외)
    if not ctx.source_files:
        return 0, "소스 파일 없음", {}
    source_depths = [len(rel.parts) for rel in ctx.source_files]
    avg_depth = statistics.mean(source_depths)
    if 2 <= avg_depth <= 5:
        score = 2
    elif 5 < avg_depth <= 7 or avg_depth == 1:
        score = 1
    else:
        score = 0
    return score, f"소스 평균 깊이 {avg_depth:.1f}", {"avg_depth": avg_depth, "n": len(source_depths)}


# ─── 카테고리 3: 정적 분석 & 스타일 ───────────────────────────────────

def check_A1_linter(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    lang = ctx.primary_language
    configs = LINTER_CONFIGS.get(lang, [])
    found_configs = [c for c in configs if (ctx.root / c).exists()]

    # pyproject.toml의 [tool.ruff] / [tool.flake8] 같은 임베디드 설정
    if lang == "python" and (ctx.root / "pyproject.toml").exists():
        text = ctx.read_text("pyproject.toml")
        if re.search(r"\[tool\.(ruff|flake8|pylint|black)", text):
            found_configs.append("pyproject.toml (linter section)")
    if lang in ("javascript", "typescript") and (ctx.root / "package.json").exists():
        text = ctx.read_text("package.json")
        if "eslint" in text.lower() or "biome" in text.lower():
            found_configs.append("package.json (eslint/biome dep)")

    if not found_configs:
        return 0, f"{lang} 린터 설정 없음", {"language": lang}

    # CI 통합 체크
    ci_uses_lint = False
    for ci in CI_PATTERNS:
        if "/" in ci and ci.endswith("/"):
            d = ctx.root / ci.rstrip("/")
            if d.is_dir():
                for wf in d.rglob("*.yml"):
                    if re.search(r"\b(lint|eslint|ruff|flake8|checkstyle|clippy|golangci)\b",
                                 wf.read_text(errors="ignore"), re.I):
                        ci_uses_lint = True
                        break
        else:
            full = ctx.root / ci
            if full.is_file():
                if re.search(r"\b(lint|eslint|ruff|flake8|checkstyle|clippy|golangci)\b",
                             full.read_text(errors="ignore"), re.I):
                    ci_uses_lint = True
                    break

    if ci_uses_lint:
        score = 3
    elif len(found_configs) >= 1:
        score = 2
    else:
        score = 1
    return score, f"{found_configs[0]} (CI 통합: {ci_uses_lint})", {
        "configs": found_configs[:3], "ci_lint": ci_uses_lint, "language": lang,
    }


def check_A2_formatter(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    lang = ctx.primary_language
    configs = FORMATTER_CONFIGS.get(lang, [])
    found = [c for c in configs if (ctx.root / c).exists()]

    if lang == "python" and (ctx.root / "pyproject.toml").exists():
        text = ctx.read_text("pyproject.toml")
        if re.search(r"\[tool\.(black|ruff|autopep8)", text):
            found.append("pyproject.toml (formatter)")
    if lang in ("javascript", "typescript") and (ctx.root / "package.json").exists():
        text = ctx.read_text("package.json")
        if "prettier" in text.lower():
            found.append("package.json (prettier)")
    # gofmt는 Go 표준이므로 Go라면 항상 만점
    if lang == "go":
        return 3, "Go: gofmt 표준 (설정 불요)", {"language": lang}

    has_precommit = any((ctx.root / p.rstrip("/")).exists() for p in PRECOMMIT_PATTERNS)

    if not found:
        return 0, f"{lang} 포매터 설정 없음", {"language": lang}
    score = 1
    if found:
        score = 2
    if has_precommit:
        score = 3
    return score, f"{found[0]} (pre-commit: {has_precommit})", {
        "configs": found[:3], "precommit": has_precommit,
    }


def check_A3_typechecker(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    lang = ctx.primary_language
    # 정적 타입 언어는 컴파일러가 처리 -> 만점 부여 (관습)
    if lang in ("java", "kotlin", "go", "rust", "csharp", "scala", "swift"):
        return 3, f"{lang}: 컴파일러 타입 검사", {"language": lang, "static": True}

    configs = TYPE_CHECKER_CONFIGS.get(lang, [])
    found = [c for c in configs if (ctx.root / c).exists()]

    if lang == "python":
        # mypy / pyright 설정 또는 pyproject.toml 섹션
        if (ctx.root / "pyproject.toml").exists():
            text = ctx.read_text("pyproject.toml")
            if re.search(r"\[tool\.(mypy|pyright)", text):
                found.append("pyproject.toml (type checker section)")
        # 타입 힌트 사용 정도 sampling (소스 100개)
        sample = ctx.source_files[:100]
        type_hint_files = 0
        for rel in sample:
            text = ctx.read_text(rel, max_bytes=20_000)
            if re.search(r"def\s+\w+\s*\([^)]*:\s*\w", text) or "from typing" in text:
                type_hint_files += 1
        ratio = type_hint_files / max(len(sample), 1)
        if found and ratio >= 0.6:
            return 3, f"mypy/pyright 설정 + 타입힌트 {ratio*100:.0f}%", {"ratio": ratio, "config": True}
        if found:
            return 2, f"타입체커 설정 + 일부 힌트 ({ratio*100:.0f}%)", {"ratio": ratio, "config": True}
        if ratio >= 0.3:
            return 1, f"설정 없음, 부분적 타입힌트 ({ratio*100:.0f}%)", {"ratio": ratio, "config": False}
        return 0, "타입체커 없음, 타입힌트 부족", {"ratio": ratio}

    if lang == "javascript":
        if (ctx.root / "tsconfig.json").exists():
            return 3, "tsconfig.json 발견 (TS 점진 도입)", {"config": "tsconfig.json"}
        # JSDoc 사용 추정
        sample = ctx.source_files[:50]
        jsdoc_files = 0
        for rel in sample:
            text = ctx.read_text(rel, max_bytes=10_000)
            if re.search(r"@param\s*\{", text) or re.search(r"@returns\s*\{", text):
                jsdoc_files += 1
        if jsdoc_files / max(len(sample), 1) >= 0.3:
            return 1, "JSDoc 타입 어노테이션 일부", {"jsdoc": True}
        return 0, "타입체커 없음 (JS, TS로 전환 권장)", {}

    if lang == "typescript":
        if (ctx.root / "tsconfig.json").exists():
            text = ctx.read_text("tsconfig.json")
            strict = '"strict"' in text and "true" in text
            if strict:
                return 3, "tsconfig.json strict=true", {"strict": True}
            return 2, "tsconfig.json 존재 (strict 미설정)", {"strict": False}
        return 0, "tsconfig.json 없음", {}

    if not found:
        return 0, f"{lang} 타입체커 정보 없음", {"language": lang}
    return 2, f"{found[0]}", {"configs": found}


def check_A4_precommit(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    found = []
    for p in PRECOMMIT_PATTERNS:
        if "/" in p and p.endswith("/"):
            if (ctx.root / p.rstrip("/")).is_dir():
                found.append(p)
        elif (ctx.root / p).exists():
            found.append(p)
    if not found:
        return 0, "pre-commit 또는 git hooks 없음", {}

    # 설정 내용 분석으로 점수 결정
    config_text = ""
    for p in [".pre-commit-config.yaml", ".pre-commit-config.yml", "lefthook.yml"]:
        if (ctx.root / p).exists():
            config_text = ctx.read_text(p)
            break
    hook_count = len(re.findall(r"^- (id|hook|script):", config_text, re.M)) if config_text else 0

    if hook_count >= 3:
        score = 3
    elif hook_count >= 1 or found:
        score = 2
    else:
        score = 1
    return min(score, crit["max_points"]), f"{found[0]} ({hook_count} hooks)", {
        "found": found, "hook_count": hook_count,
    }


def check_A5_editorconfig(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    if (ctx.root / ".editorconfig").exists():
        return 1, ".editorconfig 존재", {}
    return 0, ".editorconfig 없음", {}


def check_A6_todo_density(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    # 소스 없으면 vacuous credit 방지
    if not ctx.source_files:
        return 0, "소스 파일 없음 (검사 불가)", {"empty": True}
    todo_count = 0
    sample = ctx.source_files[:1000]
    for rel in sample:
        text = ctx.read_text(rel, max_bytes=200_000)
        todo_count += len(re.findall(r"\b(TODO|FIXME|XXX|HACK)\b", text))
    sample_loc = sum(ctx.file_loc.get(r, 0) for r in sample)
    if sample_loc == 0:
        return 0, "LOC 0 (검사 불가)", {"empty": True}
    density = todo_count / (sample_loc / 1000)
    if density < 1:
        score = 2
    elif density < 3:
        score = 1
    else:
        score = 0
    return score, f"TODO/FIXME 밀도 {density:.2f}/KLOC ({todo_count}개)", {
        "density": density, "count": todo_count,
    }


# ─── 카테고리 4: 테스트 & 검증 ────────────────────────────────────────

def check_T1_tests_exist(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    n = len(ctx.test_files)
    if n >= 30:
        score = 3
    elif n >= 6:
        score = 2
    elif n >= 1:
        score = 1
    else:
        score = 0
    return score, f"테스트 파일 {n}개", {"count": n}


def check_T2_test_ratio(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    src = len(ctx.source_files) or 1
    tests = len(ctx.test_files)
    ratio = tests / src
    if ratio >= 0.6:
        score = 4
    elif ratio >= 0.3:
        score = 3
    elif ratio >= 0.15:
        score = 2
    elif ratio >= 0.05:
        score = 1
    else:
        score = 0
    return score, f"테스트/소스 비율 {ratio:.2f} ({tests}/{src})", {
        "ratio": ratio, "tests": tests, "sources": src,
    }


def check_T3_single_command_test(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    # 우선순위: 빌드 매니페스트의 표준 테스트 명령
    lang = ctx.primary_language
    found_signal = None
    if (ctx.root / "package.json").exists():
        try:
            data = json.loads(ctx.read_text("package.json"))
            if "scripts" in data and "test" in data["scripts"]:
                found_signal = "package.json scripts.test"
        except (json.JSONDecodeError, ValueError):
            pass
    if (ctx.root / "Makefile").exists():
        text = ctx.read_text("Makefile")
        if re.search(r"^(test|tests)\s*:", text, re.M):
            found_signal = "Makefile target 'test'"
    if any((ctx.root / f).exists() for f in ["justfile", "Justfile", ".justfile"]):
        for f in ["justfile", "Justfile", ".justfile"]:
            if (ctx.root / f).exists():
                text = ctx.read_text(f)
                if re.search(r"^(test|tests)\s*:", text, re.M):
                    found_signal = f"{f} recipe 'test'"
                    break
    if (ctx.root / "pyproject.toml").exists():
        text = ctx.read_text("pyproject.toml")
        if re.search(r"\[tool\.pytest", text) or "pytest" in text.lower():
            found_signal = found_signal or "pyproject.toml (pytest)"
    if any((ctx.root / f).exists() for f in ["build.gradle", "build.gradle.kts", "pom.xml"]):
        found_signal = found_signal or "Gradle/Maven 표준"
    if (ctx.root / "go.mod").exists():
        found_signal = found_signal or "go test 표준"
    if (ctx.root / "Cargo.toml").exists():
        found_signal = found_signal or "cargo test 표준"

    if not found_signal:
        return 0, "단일 명령 테스트 실행 미확인", {}

    # CI에서도 같은 명령 사용?
    ci_test = False
    for ci in CI_PATTERNS:
        full = ctx.root / ci
        if "/" in ci and ci.endswith("/") and full.is_dir():
            for wf in full.rglob("*.y*ml"):
                if re.search(r"\b(test|gradle test|npm test|pytest|cargo test|go test)\b",
                             wf.read_text(errors="ignore"), re.I):
                    ci_test = True
                    break
        elif full.is_file():
            if re.search(r"\b(test|gradle test|npm test|pytest|cargo test|go test)\b",
                         full.read_text(errors="ignore"), re.I):
                ci_test = True
                break

    if ci_test:
        score = 3
    elif "표준" in found_signal:
        score = 2
    else:
        score = 2
    return score, f"{found_signal} (CI 사용: {ci_test})", {"signal": found_signal, "ci_test": ci_test}


def check_T4_ci_tests(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    has_ci = False
    has_tests_in_ci = False
    has_coverage_gate = False
    for p in CI_PATTERNS:
        full = ctx.root / p
        if "/" in p and p.endswith("/") and full.is_dir():
            has_ci = True
            for wf in full.rglob("*.y*ml"):
                text = wf.read_text(errors="ignore")
                if re.search(r"\b(test|pytest|jest|gradle test|npm test|cargo test)\b", text, re.I):
                    has_tests_in_ci = True
                if re.search(r"(coverage|jacoco|codecov|coveralls)", text, re.I):
                    has_coverage_gate = True
        elif full.is_file():
            has_ci = True
            text = full.read_text(errors="ignore")
            if re.search(r"\b(test|pytest|jest|gradle test|npm test|cargo test)\b", text, re.I):
                has_tests_in_ci = True
            if re.search(r"(coverage|jacoco|codecov|coveralls)", text, re.I):
                has_coverage_gate = True
    if not has_ci:
        return 0, "CI 설정 없음", {}
    if has_coverage_gate:
        return 3, "CI + 테스트 + 커버리지", {"ci": True, "tests": True, "coverage": True}
    if has_tests_in_ci:
        return 2, "CI + 테스트", {"ci": True, "tests": True}
    return 1, "CI 존재하나 테스트 누락", {"ci": True, "tests": False}


def check_T5_coverage(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    coverage_signals = [
        "jacoco.xml", ".coveragerc", ".nycrc", ".nycrc.json",
        ".jest.config.js", "jest.config.js",
    ]
    found = [c for c in coverage_signals if (ctx.root / c).exists()]
    # build.gradle 안에 jacoco
    for gradle in ["build.gradle", "build.gradle.kts"]:
        full = ctx.root / gradle
        if full.exists() and "jacoco" in full.read_text(errors="ignore").lower():
            found.append(f"{gradle} (jacoco)")
    # pyproject.toml의 coverage 섹션
    if (ctx.root / "pyproject.toml").exists():
        text = ctx.read_text("pyproject.toml")
        if re.search(r"\[tool\.coverage", text):
            found.append("pyproject.toml [tool.coverage]")
    # package.json의 coverage 스크립트
    if (ctx.root / "package.json").exists():
        text = ctx.read_text("package.json")
        if "coverage" in text.lower():
            found.append("package.json (coverage script)")

    if not found:
        return 0, "커버리지 측정 없음", {}
    # 임계값 설정 여부
    has_threshold = False
    for f in found:
        if "pyproject" in f or "gradle" in f or "package.json" in f:
            text = ctx.read_text(f.split(" ")[0]) if " " in f else ctx.read_text(f)
            if re.search(r"(minimum|threshold|fail.under|coverageThreshold|jacocoTestCoverage)", text, re.I):
                has_threshold = True
                break
    if has_threshold:
        return 2, f"{found[0]} + 임계값", {"configs": found, "threshold": True}
    return 1, f"{found[0]}", {"configs": found, "threshold": False}


# ─── 카테고리 5: 빌드 & 재현성 ────────────────────────────────────────

def check_B1_manifest(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    lang = ctx.primary_language
    manifests = LANG_MANIFESTS.get(lang, [])
    found = []
    for m in manifests:
        if "*" in m:
            for match in ctx.root.glob(m):
                if match.is_file():
                    found.append(match.name)
        elif (ctx.root / m).exists():
            found.append(m)
    if not found:
        return 0, f"{lang} 매니페스트 없음", {"language": lang}

    # 메타데이터 충실성
    primary = found[0]
    text = ctx.read_text(primary)
    has_name = bool(re.search(r'(name\s*[:=]|<artifactId>)', text, re.I))
    has_desc = bool(re.search(r'(description\s*[:=]|<description>)', text, re.I))
    has_version = bool(re.search(r'(version\s*[:=]|<version>)', text, re.I))
    has_scripts = bool(re.search(r'("scripts"|<plugin|task |dependencies)', text, re.I))
    quality = sum([has_name, has_desc, has_version, has_scripts])
    if quality >= 3:
        score = 3
    else:
        score = 2
    return score, f"{primary} (품질 {quality}/4)", {"manifests": found, "metadata_quality": quality}


def check_B2_lockfile(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    found = [lf for lf in LOCK_FILES if (ctx.root / lf).exists()]
    if not found:
        return 0, "락 파일 없음 — 의존성 비결정적", {}
    return 3, f"{found[0]}", {"lockfiles": found}


def check_B3_bootstrap(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    # Makefile의 setup/install/bootstrap 타겟
    has_makefile = False
    if (ctx.root / "Makefile").exists():
        text = ctx.read_text("Makefile")
        if re.search(r"^(setup|install|bootstrap|init|dev)\s*:", text, re.M):
            has_makefile = True
    has_just = False
    for f in ["justfile", "Justfile"]:
        if (ctx.root / f).exists():
            text = ctx.read_text(f)
            if re.search(r"^(setup|install|bootstrap|init|dev)\s*:", text, re.M):
                has_just = True
                break
    has_script = False
    for s in ["scripts/setup.sh", "scripts/bootstrap.sh", "bin/setup", "scripts/install.sh",
              "scripts/dev.sh", "scripts/install"]:
        if (ctx.root / s).exists():
            has_script = True
            break
    has_npm_setup = False
    if (ctx.root / "package.json").exists():
        try:
            data = json.loads(ctx.read_text("package.json"))
            scripts = data.get("scripts", {})
            for k in ("setup", "bootstrap", "install:dev", "dev:setup", "prepare"):
                if k in scripts:
                    has_npm_setup = True
                    break
        except (json.JSONDecodeError, ValueError):
            pass

    # Gradle/Maven Wrapper — 의존성 매니저까지 자동 부트스트랩하는 강력한 신호
    has_gradlew = (ctx.root / "gradlew").exists() or (ctx.root / "gradlew.bat").exists()
    has_mvnw = (ctx.root / "mvnw").exists() or (ctx.root / "mvnw.cmd").exists()

    signals = []
    for ok, name in [(has_makefile, "Makefile"), (has_just, "justfile"),
                     (has_script, "setup script"), (has_npm_setup, "npm setup"),
                     (has_gradlew, "Gradle wrapper"), (has_mvnw, "Maven wrapper")]:
        if ok:
            signals.append(name)

    score = 0
    if len(signals) >= 2:
        score = 3
    elif len(signals) >= 1:
        score = 2
    elif (ctx.root / "package.json").exists() or (ctx.root / "pyproject.toml").exists() or \
         (ctx.root / "Cargo.toml").exists() or (ctx.root / "go.mod").exists():
        score = 1
        return score, "표준 도구 install만 (별도 부트스트랩 스크립트 없음)", {"signals": signals}

    return score, ", ".join(signals) if signals else "없음", {"signals": signals}


def check_B4_runtime_version(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    found = [f for f in RUNTIME_VERSION_FILES if (ctx.root / f).exists()]
    # pyproject.toml의 requires-python
    if (ctx.root / "pyproject.toml").exists():
        if re.search(r'requires-python\s*=', ctx.read_text("pyproject.toml")):
            found.append("pyproject.toml requires-python")
    # package.json의 engines
    if (ctx.root / "package.json").exists():
        if '"engines"' in ctx.read_text("package.json"):
            found.append("package.json engines")
    if found:
        return 2, found[0], {"files": found}
    # README에 버전 언급 — 요구사항/필수 컨텍스트로 한정 (산문 false positive 방지)
    section_pat = re.compile(
        r"(?:requirements?|prerequisites?|dependencies|tech\s*stack|runtime|"
        r"요구사항|필수|준비|환경)\s*[:：]?\s*\n",
        re.I)
    version_pat = re.compile(
        r"(?:^|\n|[\-*•]\s+)\s*"
        r"\b(node|python|java|ruby|go(?:lang)?|rust|kotlin|scala|deno|bun|php|dotnet|\.net|elixir|dart|swift)"
        r"(?:\s*(?:version|버전))?\s*[>=]?\s*v?(\d+(?:\.\d+)*)",
        re.I | re.M)
    for r in ["README.md", "AGENTS.md", "CLAUDE.md"]:
        if not (ctx.root / r).exists():
            continue
        text = ctx.read_text(r)
        # 요구사항/Prerequisites 섹션 다음 200줄 내에서 버전 매칭이면 신뢰도 높음
        for m in section_pat.finditer(text):
            section_text = text[m.end():m.end() + 2000]
            vm = version_pat.search(section_text)
            if vm:
                return 1, f"{r} 요구사항 섹션: {vm.group(1)} {vm.group(2)}", {"file": r, "lang": vm.group(1)}
        # 섹션 못 찾으면 전체에서 라인 시작 매칭 (목록 패턴)
        vm = version_pat.search(text)
        if vm:
            return 1, f"{r} 버전 목록: {vm.group(1)} {vm.group(2)}", {"file": r, "lang": vm.group(1), "loose": True}
    return 0, "런타임 버전 명시 없음", {}


def check_B5_ci(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    found = []
    for p in CI_PATTERNS:
        full = ctx.root / p
        if "/" in p and p.endswith("/"):
            if full.is_dir():
                count = sum(1 for _ in full.rglob("*.y*ml"))
                if count > 0:
                    found.append(f"{p} ({count} workflows)")
        elif full.is_file():
            found.append(p)
    if not found:
        return 0, "CI 설정 없음", {}
    score = 1
    # 다중 작업 = 여러 워크플로우 또는 매트릭스
    multi = False
    for f in [".github/workflows", ".github/workflows/"]:
        d = ctx.root / f.rstrip("/")
        if d.is_dir():
            for wf in d.rglob("*.y*ml"):
                if "matrix:" in wf.read_text(errors="ignore"):
                    multi = True
                    break
    if len(found) > 1 or multi:
        score = 2
    return score, found[0], {"ci_signals": found, "multi": multi}


def check_B6_container(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    found = [c for c in CONTAINER_PATTERNS if (ctx.root / c).exists()]
    has_dockerfile = any("Dockerfile" in f or "Containerfile" in f for f in found)
    has_compose = any("compose" in f for f in found)
    has_devcontainer = any("devcontainer" in f for f in found)
    if has_dockerfile and (has_compose or has_devcontainer):
        return 2, ", ".join(found), {"signals": found}
    if has_dockerfile:
        return 1, "Dockerfile만", {"signals": found}
    return 0, "컨테이너화 없음", {}


# ─── 카테고리 6: 보안 & 의존성 ────────────────────────────────────────

def _is_secret_ignored_path(path: Path) -> bool:
    sp = str(path).replace("\\", "/").lower()
    return any(h in sp for h in SECRET_IGNORE_HINTS)


def check_X1_secrets(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    if not ctx.files:
        return 0, "추적된 파일 없음 (검사 불가)", {"empty": True}
    sample = [f for f in ctx.files if not _is_secret_ignored_path(f)][:2000]
    detections: list[tuple[str, str]] = []
    for rel in sample:
        # 너무 큰 파일은 건너뜀
        full = ctx.root / rel
        try:
            if full.stat().st_size > 1_000_000:
                continue
        except OSError:
            continue
        text = ctx.read_text(rel, max_bytes=500_000)
        for label, pat in SECRET_PATTERNS:
            if pat.search(text):
                detections.append((label, str(rel)))
                if len(detections) >= 5:
                    break
        if len(detections) >= 5:
            break
    if detections:
        return 0, f"{len(detections)}개 의심 패턴 발견 (예: {detections[0][0]} in {detections[0][1]})", {
            "detections": detections[:5],
        }
    return 3, "명백한 시크릿 패턴 없음", {}


def check_X2_gitignore(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    full = ctx.root / ".gitignore"
    if not full.exists():
        return 0, ".gitignore 없음", {}
    lines = [ln.strip() for ln in full.read_text(errors="ignore").splitlines()
             if ln.strip() and not ln.strip().startswith("#")]
    if len(lines) < 5:
        return 1, f".gitignore 빈약 ({len(lines)}줄)", {"lines": len(lines)}
    return 2, f".gitignore {len(lines)}줄", {"lines": len(lines)}


def check_X3_license(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    # 1. 루트 LICENSE 파일
    for f in LICENSE_FILES:
        if (ctx.root / f).exists():
            return 1, f, {"file": f}
    # 2. 매니페스트 메타데이터 (modern repos는 별도 파일 없이 메타로만 두기도 함)
    if (ctx.root / "package.json").exists():
        text = ctx.read_text("package.json")
        if re.search(r'"license"\s*:\s*"[^"]+"', text):
            return 1, "package.json license field", {"in_manifest": "package.json"}
    if (ctx.root / "pyproject.toml").exists():
        text = ctx.read_text("pyproject.toml")
        if re.search(r"license\s*=\s*[\"']", text) or re.search(r"\[project\.license\]", text):
            return 1, "pyproject.toml license", {"in_manifest": "pyproject.toml"}
    if (ctx.root / "Cargo.toml").exists():
        text = ctx.read_text("Cargo.toml")
        if re.search(r"^license\s*=", text, re.M):
            return 1, "Cargo.toml license", {"in_manifest": "Cargo.toml"}
    return 0, "LICENSE 파일 또는 메타데이터 없음", {}


def check_X4_env_example(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    for f in ENV_EXAMPLE_FILES:
        if (ctx.root / f).exists():
            text = ctx.read_text(f)
            # 대소문자/숫자/하이픈 모두 허용 — Spring properties는 lowerCase, 일부는 dashed
            keys = len(re.findall(r"^[\s]*(?:export\s+)?[A-Za-z_][A-Za-z0-9_\-.]*\s*=", text, re.M))
            if keys >= 3:
                return 2, f"{f} ({keys} keys)", {"file": f, "keys": keys}
            return 1, f"{f} (적은 키)", {"file": f, "keys": keys}
    # README의 environment 섹션
    for r in ["README.md", "AGENTS.md", "CLAUDE.md"]:
        if (ctx.root / r).exists():
            text = ctx.read_text(r)
            if re.search(r"(environment variables?|환경변수|env vars?)", text, re.I):
                return 1, f"{r}에 env 문서", {"doc_only": True}
    return 0, ".env.example 없음", {}


def check_X5_dep_scan(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    found = []
    for p in DEP_SCAN_PATTERNS:
        if (ctx.root / p).exists():
            found.append(p)
    # CI에서 npm audit / pip-audit / cargo audit
    ci_audit = False
    for p in CI_PATTERNS:
        full = ctx.root / p
        if "/" in p and p.endswith("/") and full.is_dir():
            for wf in full.rglob("*.y*ml"):
                if re.search(r"(audit|snyk|trivy|grype|dependency-check)",
                             wf.read_text(errors="ignore"), re.I):
                    ci_audit = True
                    break
        elif full.is_file():
            if re.search(r"(audit|snyk|trivy|grype)", full.read_text(errors="ignore"), re.I):
                ci_audit = True
                break
    if found and ci_audit:
        return 2, f"{found[0]} + CI 스캔", {"configs": found, "ci_audit": True}
    if found or ci_audit:
        return 1, found[0] if found else "CI 스캔만", {"configs": found, "ci_audit": ci_audit}
    return 0, "의존성 스캔 설정 없음", {}


# ─── 카테고리 7: 운영성 & 관찰성 ──────────────────────────────────────

def check_O1_logging(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    if not ctx.source_files:
        return 0, "소스 없음", {}
    # 매니페스트/소스에서 로거 라이브러리 탐지
    structured = False
    used_loggers = set()
    for r in ["package.json", "pyproject.toml", "build.gradle", "build.gradle.kts",
              "pom.xml", "Cargo.toml", "go.mod", "Gemfile"]:
        if (ctx.root / r).exists():
            text = ctx.read_text(r).lower()
            for hint in STRUCTURED_LOG_HINTS:
                if hint in text:
                    structured = True
                    used_loggers.add(hint)

    # 소스에서 print/console.log 분포
    sample = ctx.source_files[:200]
    print_count = 0
    sample_loc = 0
    for rel in sample:
        text = ctx.read_text(rel, max_bytes=100_000)
        print_count += len(PRINT_LOG_PATTERN.findall(text))
        sample_loc += ctx.file_loc.get(rel, 0)
    print_density = print_count / max(sample_loc / 1000, 1)

    if structured and print_density < 1:
        score = 3
    elif structured:
        score = 2
    elif print_density < 5:
        score = 1
    else:
        score = 0
    return score, f"loggers={list(used_loggers) or 'none'}, print밀도={print_density:.1f}/KLOC", {
        "loggers": list(used_loggers), "print_density": print_density,
    }


def check_O2_error_handling(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    if not ctx.source_files:
        return 0, "소스 없음", {}
    sample = ctx.source_files[:300]
    empty_catches = 0
    catch_blocks = 0
    for rel in sample:
        text = ctx.read_text(rel, max_bytes=100_000)
        for pat in EMPTY_CATCH_PATTERNS:
            empty_catches += len(pat.findall(text))
        catch_blocks += len(re.findall(r"\b(catch|except|rescue)\b", text))
    if catch_blocks == 0:
        # 에러 처리가 거의 없음 — 도메인에 따라 OK일 수도
        return 1, "에러 처리 거의 없음 (도메인에 따라 OK)", {"catches": 0}
    empty_ratio = empty_catches / catch_blocks
    if empty_ratio < 0.05:
        score = 3
    elif empty_ratio < 0.15:
        score = 2
    elif empty_ratio < 0.30:
        score = 1
    else:
        score = 0
    return score, f"빈 catch 비율 {empty_ratio*100:.1f}% ({empty_catches}/{catch_blocks})", {
        "empty_ratio": empty_ratio, "empty_count": empty_catches, "total_catch": catch_blocks,
    }


def check_O3_env_config(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    if not ctx.source_files:
        return 0, "소스 없음", {}
    sample = ctx.source_files[:300]
    env_uses = 0
    hardcoded_urls = 0
    # 사전 컴파일된 패턴 — 핫루프에서 재컴파일 비용 제거
    env_pat = re.compile(
        r"(os\.environ|os\.getenv|process\.env|System\.getenv|env::var|ENV\[|getenv|"
        r"@Value\(|@ConfigurationProperties|dotenv|load_dotenv|config\(\)\.get)")
    # URL 패턴: 따옴표 사이의 진짜 URL 호스트만 — 따옴표/공백/중괄호 제외
    # (?!\.example) 같은 정확한 도메인 화이트리스트로 false positive 방지
    url_pat = re.compile(
        r"['\"]https?://"
        r"(?!"
        r"localhost"
        r"|127\.0\.0\.1"
        r"|0\.0\.0\.0"
        r"|(?:[\w\-]+\.)?example\.(?:com|org|net)"  # 정확히 example.com/.org/.net
        r"|(?:[\w\-]+\.)?(?:github\.com|gitlab\.com|google\.com|w3\.org|developer\.mozilla\.org|stackoverflow\.com|wikipedia\.org)"
        r"|schemas?\."
        r"|api\.openai\.com"
        r"|registry\.npmjs\.org"
        r")"
        r"[A-Za-z0-9\-._~/?#%&=+,:@!*]+"  # URL 문자만 — 따옴표/공백 절대 포함 안 함
        r"['\"]")
    for rel in sample:
        # 미니파이된 번들 스킵 — 라인이 비정상적으로 길면 catastrophic backtracking 위험
        text = ctx.read_text(rel, max_bytes=100_000)
        if any(len(line) > 5000 for line in text.splitlines()[:5]):
            continue
        env_uses += len(env_pat.findall(text))
        hardcoded_urls += len(url_pat.findall(text))
    if env_uses >= 10 and hardcoded_urls < 3:
        score = 3
    elif env_uses >= 3:
        score = 2
    elif env_uses >= 1:
        score = 1
    else:
        score = 0
    return score, f"env 사용 {env_uses}개, 하드코딩 URL {hardcoded_urls}개", {
        "env_uses": env_uses, "hardcoded_urls": hardcoded_urls,
    }


def check_O4_health_endpoint(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    # 1단계: 코드/리소스에서 헬스 엔드포인트 흔적
    sample = ctx.source_files[:500]
    has_health = False
    has_status = False
    for rel in sample:
        text = ctx.read_text(rel, max_bytes=50_000)
        if re.search(r"['\"/](health|healthz|ready|liveness|readiness)['\"/]", text):
            has_health = True
            break
        if re.search(r"['\"/](status|info)['\"/]", text):
            has_status = True

    # 2단계: 매니페스트/락 파일에서 web framework 의존성 (text + lock 모두)
    web_signal = False
    web_keywords = re.compile(
        r"(express|fastify|hapi|koa|nestjs|next|spring-boot-starter-web|spring-webflux|"
        r"actix-web|axum|warp|rocket|gin-gonic|echo|fiber|"
        r"fastapi|flask|django|tornado|sanic|aiohttp|bottle|"
        r"rails|sinatra|hanami|"
        r"phoenix|plug|"
        r"micronaut|quarkus|vertx|ktor|http4k)",
        re.I)
    actuator = False
    manifest_files = [
        "package.json", "pom.xml", "build.gradle", "build.gradle.kts",
        "Cargo.toml", "go.mod", "go.sum",
        "pyproject.toml", "requirements.txt", "Pipfile", "setup.py", "setup.cfg",
        "Gemfile", "composer.json", "mix.exs",
    ]
    for r in manifest_files:
        if not (ctx.root / r).exists():
            continue
        text = ctx.read_text(r).lower()
        if web_keywords.search(text):
            web_signal = True
        if "actuator" in text:
            actuator = True
        if web_signal and actuator:
            break

    # 분기:
    if has_health or actuator:
        return 2, f"health endpoint 발견 (actuator={actuator})", {
            "health": has_health, "actuator": actuator, "web_app": True,
        }
    if web_signal:
        # web framework은 있는데 health endpoint 없음 — 진짜 갭
        if has_status:
            return 1, "web app인데 status 엔드포인트만 (health 누락)", {"web_app": True, "status": True}
        return 0, "web app으로 감지되나 헬스 엔드포인트 없음", {"web_app": True}
    # web framework 시그니처 없음 → 라이브러리/CLI/툴 → N/A
    # 단 매니페스트조차 없으면 (빈 레포) 만점 부여 부적절
    has_manifest = any((ctx.root / m).exists() for m in [
        "package.json", "pom.xml", "build.gradle", "build.gradle.kts",
        "Cargo.toml", "go.mod", "pyproject.toml", "requirements.txt",
        "setup.py", "Gemfile", "composer.json", "mix.exs",
    ])
    if not has_manifest:
        return 0, "매니페스트 없음 (라이브러리/CLI 판정 불가)", {"empty": True}
    return 2, "라이브러리/CLI로 추정 (헬스 엔드포인트 N/A)", {"web_app": False, "na": True}


def check_O5_logging_config(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    candidates = [
        "logback.xml", "logback-spring.xml", "log4j.xml", "log4j2.xml",
        "log4j.properties", "log4j2.properties",
        "logging.yaml", "logging.yml", "logging.json", "logging.conf",
        "src/main/resources/logback.xml", "src/main/resources/logback-spring.xml",
        "src/main/resources/log4j2.xml",
        "src/main/resources/application.yml",  # Spring application.yml의 logging 섹션
        # Python
        "log_config.yaml", "log_config.yml",
    ]
    found = [c for c in candidates if (ctx.root / c).exists()]
    if found:
        # Spring application.yml은 'logging' 섹션이 있을 때만 점수
        if "application" in found[0]:
            text = ctx.read_text(found[0])
            if not re.search(r"^\s*logging\s*:", text, re.M):
                found.pop(0)
        if found:
            return 2, found[0], {"files": found}
    # 코드 안에 표준 로거 설정 — 가벼운 휴리스틱
    code_idioms = re.compile(
        r"(logging\.config\.(?:dictConfig|fileConfig)|"
        r"logging\.basicConfig\s*\(|"
        r"logger\.configure|configureLogger|"
        r"winston\.createLogger\s*\(|"
        r"pino\s*\(|"
        r"zap\.NewProduction\s*\(|zap\.NewDevelopment\s*\(|"
        r"zerolog\.New\s*\(|"
        r"slog\.New\s*\(|slog\.SetDefault\s*\()")
    for rel in ctx.source_files[:80]:
        text = ctx.read_text(rel, max_bytes=20_000)
        if code_idioms.search(text):
            return 1, f"코드 내 로거 설정 발견 ({rel})", {"in_code": str(rel)}
    return 0, "로깅 설정 없음", {}


def check_O6_runbook(ctx: RepoContext, crit: dict[str, Any]) -> CheckResult:
    candidates = [
        "RUNBOOK.md", "docs/runbook.md", "docs/operations.md",
        "TROUBLESHOOTING.md", "docs/troubleshooting.md",
        "docs/ops.md", "docs/playbook.md",
    ]
    for c in candidates:
        if (ctx.root / c).exists():
            text = ctx.read_text(c)
            if len(text) > 500:
                return 2, c, {"file": c, "size": len(text)}
            return 1, c, {"file": c, "size": len(text)}
    return 0, "런북 없음", {}


# ===========================================================================
# 검사 디스패치 테이블
# ===========================================================================

CHECKS: dict[str, CheckFn] = {
    "D1": check_D1_readme, "D2": check_D2_agents_md, "D3": check_D3_adr,
    "D4": check_D4_architecture, "D5": check_D5_glossary, "D6": check_D6_examples,
    "S1": check_S1_median_file_size, "S2": check_S2_huge_files, "S3": check_S3_god_file,
    "S4": check_S4_dir_structure, "S5": check_S5_naming_consistency, "S6": check_S6_directory_depth,
    "A1": check_A1_linter, "A2": check_A2_formatter, "A3": check_A3_typechecker,
    "A4": check_A4_precommit, "A5": check_A5_editorconfig, "A6": check_A6_todo_density,
    "T1": check_T1_tests_exist, "T2": check_T2_test_ratio, "T3": check_T3_single_command_test,
    "T4": check_T4_ci_tests, "T5": check_T5_coverage,
    "B1": check_B1_manifest, "B2": check_B2_lockfile, "B3": check_B3_bootstrap,
    "B4": check_B4_runtime_version, "B5": check_B5_ci, "B6": check_B6_container,
    "X1": check_X1_secrets, "X2": check_X2_gitignore, "X3": check_X3_license,
    "X4": check_X4_env_example, "X5": check_X5_dep_scan,
    "O1": check_O1_logging, "O2": check_O2_error_handling, "O3": check_O3_env_config,
    "O4": check_O4_health_endpoint, "O5": check_O5_logging_config, "O6": check_O6_runbook,
}


# ===========================================================================
# 감사 / 점수 / ROI 산출
# ===========================================================================

def run_audit(ctx: RepoContext, rubric: dict[str, Any]) -> dict[str, Any]:
    cats_out = []
    total_score = 0
    total_max = 0
    for cat in rubric["categories"]:
        cat_score = 0
        cat_max = cat["max_points"]
        crits_out = []
        for crit in cat["criteria"]:
            cid = crit["id"]
            fn = CHECKS.get(cid)
            if not fn:
                # 검사 미구현 -> 만점 부여 (rubric 확장에 안전)
                score = crit["max_points"]
                evidence = "(검사 미구현)"
                details = {"unimplemented": True}
            else:
                try:
                    score, evidence, details = fn(ctx, crit)
                except Exception as e:
                    score = 0
                    evidence = f"검사 오류: {e}"
                    details = {"error": str(e), "type": type(e).__name__}
            score = min(score, crit["max_points"])
            cat_score += score
            crits_out.append({
                "id": cid,
                "name": crit["name"],
                "score": score,
                "max": crit["max_points"],
                "evidence": evidence,
                "details": details,
                "effort_to_fix": crit["effort_to_fix"],
                "why_it_matters": crit["why_it_matters"],
                "how_to_fix": crit["how_to_fix"],
            })
        cats_out.append({
            "id": cat["id"],
            "name": cat["name"],
            "name_en": cat.get("name_en", ""),
            "max_points": cat_max,
            "score": cat_score,
            "rationale": cat.get("rationale", ""),
            "criteria": crits_out,
        })
        total_score += cat_score
        total_max += cat_max

    # 점수 밴드
    band = next((b for b in rubric["score_bands"] if b["min"] <= total_score <= b["max"]),
                rubric["score_bands"][-1])

    # ROI 액션 리스트
    actions = []
    for cat in cats_out:
        for crit in cat["criteria"]:
            lost = crit["max"] - crit["score"]
            if lost <= 0:
                continue
            effort = crit["effort_to_fix"]
            roi = lost / max(effort, 1)
            actions.append({
                "id": crit["id"],
                "category": cat["name"],
                "name": crit["name"],
                "points_lost": lost,
                "points_max": crit["max"],
                "current_score": crit["score"],
                "effort": effort,
                "roi": round(roi, 2),
                "why": crit["why_it_matters"],
                "how": crit["how_to_fix"],
                "evidence": crit["evidence"],
            })
    actions.sort(key=lambda a: (-a["roi"], -a["points_lost"], a["effort"]))

    return {
        "version": rubric["version"],
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "repo": {
            "path": str(ctx.root),
            "is_git": ctx.is_git,
            "primary_language": ctx.primary_language,
            "language_distribution": dict(ctx.lang_stats.most_common()),
            "total_files_tracked": len(ctx.files),
            "source_files": len(ctx.source_files),
            "test_files": len(ctx.test_files),
            "total_loc": ctx.total_loc,
        },
        "score": {
            "total": total_score,
            "max": total_max,
            "percentage": round(total_score / total_max * 100, 1) if total_max else 0,
            "band": band["label"],
            "band_description": band["description"],
        },
        "categories": cats_out,
        "actions": actions,
    }


# ===========================================================================
# 출력 렌더러
# ===========================================================================

def render_html(report: dict[str, Any]) -> str:
    """단일 자체완결 HTML — 외부 CDN 없음."""
    score_pct = report["score"]["percentage"]
    band_color = {
        "AI-Native": "#10b981",      # green
        "AI-Ready": "#3b82f6",       # blue
        "AI-Compatible": "#eab308",  # yellow
        "AI-Cautious": "#f97316",    # orange
        "AI-Hostile": "#ef4444",     # red
    }.get(report["score"]["band"], "#6b7280")

    # ─── 카테고리 카드 ───────────────────────────────
    cat_cards = []
    for cat in report["categories"]:
        pct = round(cat["score"] / cat["max_points"] * 100) if cat["max_points"] else 0
        crit_rows = []
        for crit in cat["criteria"]:
            cpct = round(crit["score"] / crit["max"] * 100) if crit["max"] else 0
            bar_color = "#10b981" if cpct >= 80 else "#eab308" if cpct >= 50 else "#ef4444"
            crit_rows.append(f"""
            <div class="crit-row">
                <div class="crit-head">
                    <span class="crit-id">{html.escape(crit['id'])}</span>
                    <span class="crit-name">{html.escape(crit['name'])}</span>
                    <span class="crit-score">{crit['score']}/{crit['max']}</span>
                </div>
                <div class="crit-bar"><div class="crit-bar-fill" style="width:{cpct}%;background:{bar_color}"></div></div>
                <div class="crit-evidence">{html.escape(crit['evidence'])}</div>
            </div>
            """)
        cat_cards.append(f"""
        <section class="cat-card">
            <header class="cat-head">
                <div class="cat-title">
                    <h3>{html.escape(cat['name'])}</h3>
                    <span class="cat-en">{html.escape(cat['name_en'])}</span>
                </div>
                <div class="cat-score">
                    <span class="cat-num">{cat['score']}</span>
                    <span class="cat-of">/{cat['max_points']}</span>
                </div>
            </header>
            <div class="cat-rationale">{html.escape(cat['rationale'])}</div>
            <div class="cat-bar"><div class="cat-bar-fill" style="width:{pct}%"></div></div>
            <div class="crit-list">
                {''.join(crit_rows)}
            </div>
        </section>
        """)

    # ─── ROI 액션 리스트 ─────────────────────────────
    action_rows = []
    for i, a in enumerate(report["actions"][:20], 1):
        rank_color = "#ef4444" if i <= 3 else "#f97316" if i <= 7 else "#3b82f6"
        action_rows.append(f"""
        <article class="action">
            <div class="action-rank" style="background:{rank_color}">{i}</div>
            <div class="action-body">
                <header>
                    <span class="action-id">{html.escape(a['id'])}</span>
                    <h4>{html.escape(a['name'])}</h4>
                    <span class="action-cat">{html.escape(a['category'])}</span>
                </header>
                <div class="action-stats">
                    <span class="stat"><b>+{a['points_lost']}점</b> 가능</span>
                    <span class="stat">노력 <b>{a['effort']}/5</b></span>
                    <span class="stat">ROI <b>{a['roi']}</b></span>
                    <span class="stat">현재 {a['current_score']}/{a['points_max']}</span>
                </div>
                <details>
                    <summary>왜 중요한가 / 어떻게 고치나</summary>
                    <p class="why"><b>왜:</b> {html.escape(a['why'])}</p>
                    <p class="how"><b>해결:</b> {html.escape(a['how'])}</p>
                    <p class="evidence"><b>근거:</b> {html.escape(a['evidence'])}</p>
                </details>
            </div>
        </article>
        """)

    # ─── 언어 분포 칩 ─────────────────────────────────
    lang_chips = "".join(
        f'<span class="lang-chip">{html.escape(lang)} <b>{cnt}</b></span>'
        for lang, cnt in list(report["repo"]["language_distribution"].items())[:8]
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI-Ready 코드베이스 감사 리포트</title>
<style>
:root {{
  --bg: #0f172a; --surface: #1e293b; --surface-2: #334155;
  --text: #f1f5f9; --text-dim: #94a3b8; --border: #475569;
  --accent: {band_color};
}}
@media (prefers-color-scheme: light) {{
  :root {{
    --bg: #f8fafc; --surface: #ffffff; --surface-2: #f1f5f9;
    --text: #0f172a; --text-dim: #475569; --border: #cbd5e1;
  }}
}}
* {{ box-sizing: border-box; }}
body {{
  margin:0; font-family: -apple-system, BlinkMacSystemFont, 'Pretendard', 'Apple SD Gothic Neo',
    'Noto Sans KR', sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.6;
}}
.container {{ max-width: 1200px; margin: 0 auto; padding: 32px 24px; }}
h1 {{ font-size: 28px; margin: 0 0 8px; }}
h2 {{ font-size: 22px; margin: 40px 0 16px; }}
h3 {{ font-size: 18px; margin: 0; }}
h4 {{ font-size: 15px; margin: 0; }}

/* ─── Header / Score Hero ─────────────────────── */
.hero {{
  background: linear-gradient(135deg, var(--surface) 0%, var(--surface-2) 100%);
  border-radius: 16px; padding: 32px; margin-bottom: 24px;
  border: 1px solid var(--border);
}}
.hero-meta {{ color: var(--text-dim); font-size: 13px; margin-bottom: 16px; }}
.hero-grid {{ display: grid; grid-template-columns: auto 1fr; gap: 32px; align-items: center; }}
.gauge {{ position: relative; width: 200px; height: 200px; }}
.gauge svg {{ width: 100%; height: 100%; transform: rotate(-90deg); }}
.gauge .track {{ fill: none; stroke: var(--surface-2); stroke-width: 16; }}
.gauge .fill {{ fill: none; stroke: var(--accent); stroke-width: 16; stroke-linecap: round; }}
.gauge .label {{
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
}}
.gauge .label .num {{ font-size: 48px; font-weight: 800; color: var(--accent); line-height: 1; }}
.gauge .label .of {{ font-size: 14px; color: var(--text-dim); margin-top: 4px; }}
.hero-info p {{ margin: 4px 0; }}
.band {{
  display: inline-block; background: var(--accent); color: white;
  padding: 4px 12px; border-radius: 999px; font-weight: 700; font-size: 13px;
  margin-bottom: 12px;
}}
.repo-meta {{ display: flex; flex-wrap: wrap; gap: 16px; font-size: 14px; color: var(--text-dim); margin-top: 12px; }}
.repo-meta b {{ color: var(--text); }}
.lang-chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }}
.lang-chip {{
  background: var(--surface-2); border: 1px solid var(--border);
  border-radius: 999px; padding: 4px 12px; font-size: 12px;
}}

/* ─── Categories ────────────────────────────────── */
.cat-grid {{ display: grid; grid-template-columns: 1fr; gap: 16px; }}
.cat-card {{
  background: var(--surface); border-radius: 12px; padding: 20px;
  border: 1px solid var(--border);
}}
.cat-head {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }}
.cat-title h3 {{ display: inline; }}
.cat-en {{ color: var(--text-dim); font-size: 13px; margin-left: 8px; }}
.cat-score {{ font-size: 24px; font-weight: 800; }}
.cat-of {{ color: var(--text-dim); font-size: 16px; font-weight: 400; }}
.cat-rationale {{ font-size: 13px; color: var(--text-dim); margin-bottom: 16px; }}
.cat-bar {{ height: 8px; background: var(--surface-2); border-radius: 4px; overflow: hidden; margin-bottom: 16px; }}
.cat-bar-fill {{ height: 100%; background: var(--accent); transition: width .3s; }}

.crit-list {{ display: flex; flex-direction: column; gap: 12px; }}
.crit-row {{
  background: var(--surface-2); padding: 12px; border-radius: 8px;
  border-left: 3px solid var(--border);
}}
.crit-head {{ display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }}
.crit-id {{ font-family: 'SF Mono', monospace; font-size: 12px; color: var(--text-dim); min-width: 32px; }}
.crit-name {{ flex: 1; font-weight: 600; font-size: 14px; }}
.crit-score {{ font-weight: 700; font-size: 14px; }}
.crit-bar {{ height: 4px; background: var(--bg); border-radius: 2px; overflow: hidden; margin-bottom: 6px; }}
.crit-bar-fill {{ height: 100%; transition: width .3s; }}
.crit-evidence {{ font-size: 12px; color: var(--text-dim); font-family: 'SF Mono', monospace; }}

/* ─── Actions ────────────────────────────────────── */
.actions-list {{ display: flex; flex-direction: column; gap: 12px; }}
.action {{
  display: flex; gap: 16px;
  background: var(--surface); border-radius: 12px; padding: 16px;
  border: 1px solid var(--border);
}}
.action-rank {{
  width: 40px; height: 40px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: white; font-weight: 800; font-size: 18px; flex-shrink: 0;
}}
.action-body {{ flex: 1; }}
.action-body header {{ display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; margin-bottom: 8px; }}
.action-id {{ font-family: 'SF Mono', monospace; font-size: 11px; color: var(--text-dim); }}
.action-cat {{ font-size: 12px; color: var(--text-dim); margin-left: auto; }}
.action-stats {{ display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px; margin-bottom: 8px; }}
.action-stats .stat {{ color: var(--text-dim); }}
.action-stats .stat b {{ color: var(--text); }}
.action details {{ font-size: 13px; }}
.action details summary {{ cursor: pointer; color: var(--text-dim); padding: 4px 0; }}
.action details p {{ margin: 4px 0; }}
.action .evidence {{ font-family: 'SF Mono', monospace; font-size: 12px; color: var(--text-dim); }}

footer {{ text-align: center; color: var(--text-dim); font-size: 12px; margin-top: 48px; padding: 24px 0; }}
</style>
</head>
<body>
<div class="container">

  <header>
    <h1>🤖 AI-Ready 코드베이스 감사 리포트</h1>
    <p class="hero-meta">{html.escape(report['repo']['path'])} · {html.escape(report['generated_at'])}</p>
  </header>

  <section class="hero">
    <div class="hero-grid">
      <div class="gauge">
        <svg viewBox="0 0 200 200">
          <circle class="track" cx="100" cy="100" r="80"></circle>
          <circle class="fill" cx="100" cy="100" r="80"
            stroke-dasharray="{round(score_pct/100*502.65, 2)} 502.65"></circle>
        </svg>
        <div class="label">
          <span class="num">{report['score']['total']}</span>
          <span class="of">/{report['score']['max']}</span>
        </div>
      </div>
      <div class="hero-info">
        <span class="band">{html.escape(report['score']['band'])}</span>
        <p>{html.escape(report['score']['band_description'])}</p>
        <div class="repo-meta">
          <span>주 언어: <b>{html.escape(report['repo']['primary_language'])}</b></span>
          <span>파일 <b>{report['repo']['total_files_tracked']:,}</b>개</span>
          <span>소스 <b>{report['repo']['source_files']:,}</b>개</span>
          <span>테스트 <b>{report['repo']['test_files']:,}</b>개</span>
          <span>LOC <b>{report['repo']['total_loc']:,}</b></span>
          <span>{'Git 추적' if report['repo']['is_git'] else 'Filesystem walk'}</span>
        </div>
        <div class="lang-chips">{lang_chips}</div>
      </div>
    </div>
  </section>

  <h2>📊 카테고리별 점수</h2>
  <div class="cat-grid">
    {''.join(cat_cards)}
  </div>

  <h2>🎯 ROI 우선순위 액션 (상위 20개)</h2>
  <p style="color:var(--text-dim);font-size:13px;">
    ROI = 잃은 점수 / 노력 점수 (1=수분, 5=수일~수주). 상단부터 처리하면 최소 노력으로 최대 점수 향상.
  </p>
  <div class="actions-list">
    {''.join(action_rows) if action_rows else '<p>모든 항목이 만점입니다 🎉</p>'}
  </div>

  <footer>
    Generated by <code>codebase-ai-readiness</code> skill ·
    Rubric v{html.escape(report['version'])}
  </footer>

</div>
</body>
</html>
"""


def render_actions_md(report: dict[str, Any]) -> str:
    lines = ["# ROI 우선순위 액션 리스트", ""]
    lines.append(f"**총점**: {report['score']['total']}/{report['score']['max']} "
                 f"({report['score']['percentage']}%) — **{report['score']['band']}**")
    lines.append("")
    lines.append(f"_{report['score']['band_description']}_")
    lines.append("")
    lines.append("| 순위 | ID | 항목 | 카테고리 | 잃은 점수 | 노력 | ROI |")
    lines.append("|---|---|---|---|---|---|---|")
    for i, a in enumerate(report["actions"][:30], 1):
        lines.append(f"| {i} | `{a['id']}` | {a['name']} | {a['category']} | "
                     f"+{a['points_lost']} | {a['effort']}/5 | {a['roi']} |")
    lines.append("")
    lines.append("## 상위 10개 상세")
    lines.append("")
    for i, a in enumerate(report["actions"][:10], 1):
        lines.append(f"### {i}. [{a['id']}] {a['name']} (+{a['points_lost']}점, ROI {a['roi']})")
        lines.append("")
        lines.append(f"- **카테고리**: {a['category']}")
        lines.append(f"- **현재**: {a['current_score']}/{a['points_max']}점")
        lines.append(f"- **노력**: {a['effort']}/5")
        lines.append(f"- **근거**: `{a['evidence']}`")
        lines.append(f"- **왜 중요한가**: {a['why']}")
        lines.append(f"- **어떻게 고치나**: {a['how']}")
        lines.append("")
    return "\n".join(lines)


# ===========================================================================
# 메인 엔트리
# ===========================================================================

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AI-Ready 코드베이스 감사 (100점 7카테고리 루브릭)"
    )
    parser.add_argument("--path", default=".", help="감사 대상 레포 경로 (기본: cwd)")
    parser.add_argument("--out", default=None,
                        help="출력 디렉토리 (기본: <path>/.ai-readiness)")
    parser.add_argument("--rubric", default=None,
                        help="커스텀 rubric.json (기본: 스크립트 옆 rubric.json)")
    parser.add_argument("--format", default="all",
                        choices=["all", "json", "html", "md"],
                        help="출력 포맷")
    parser.add_argument("--print", action="store_true",
                        help="JSON을 stdout에도 출력")
    parser.add_argument("--quiet", action="store_true", help="진행 메시지 억제")
    args = parser.parse_args(argv)

    repo_path = Path(args.path).resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        print(f"ERROR: {repo_path} is not a directory", file=sys.stderr)
        return 2

    rubric_path = Path(args.rubric) if args.rubric else Path(__file__).parent / "rubric.json"
    if not rubric_path.exists():
        print(f"ERROR: rubric not found at {rubric_path}", file=sys.stderr)
        return 2

    out_dir = Path(args.out) if args.out else repo_path / ".ai-readiness"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.quiet:
        print(f"[1/4] Loading rubric: {rubric_path}", file=sys.stderr)
    rubric = json.loads(rubric_path.read_text(encoding="utf-8"))

    if not args.quiet:
        print(f"[2/4] Scanning repo: {repo_path}", file=sys.stderr)
    ctx = RepoContext(repo_path)
    ctx.build()
    if not args.quiet:
        print(f"      files={len(ctx.files)} sources={len(ctx.source_files)} "
              f"tests={len(ctx.test_files)} primary={ctx.primary_language}", file=sys.stderr)

    if not args.quiet:
        print(f"[3/4] Running 38 checks", file=sys.stderr)
    report = run_audit(ctx, rubric)

    if not args.quiet:
        print(f"[4/4] Writing outputs to {out_dir}", file=sys.stderr)

    # JSON
    if args.format in ("all", "json"):
        json_path = out_dir / "report.json"
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        if not args.quiet:
            print(f"      ✓ {json_path}", file=sys.stderr)

    # HTML
    if args.format in ("all", "html"):
        html_path = out_dir / "dashboard.html"
        html_path.write_text(render_html(report), encoding="utf-8")
        if not args.quiet:
            print(f"      ✓ {html_path}", file=sys.stderr)

    # Markdown actions
    if args.format in ("all", "md"):
        md_path = out_dir / "actions.md"
        md_path.write_text(render_actions_md(report), encoding="utf-8")
        if not args.quiet:
            print(f"      ✓ {md_path}", file=sys.stderr)

    if args.print:
        print(json.dumps(report, ensure_ascii=False, indent=2))

    # 요약 출력
    if not args.quiet:
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"  Score: {report['score']['total']}/{report['score']['max']} "
              f"({report['score']['percentage']}%) — {report['score']['band']}", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)
        for cat in report["categories"]:
            pct = round(cat['score'] / cat['max_points'] * 100) if cat['max_points'] else 0
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            print(f"  {bar} {cat['score']:>3}/{cat['max_points']:<3}  {cat['name']}", file=sys.stderr)
        print(f"\nTop 5 ROI actions:", file=sys.stderr)
        for i, a in enumerate(report["actions"][:5], 1):
            print(f"  {i}. [{a['id']}] +{a['points_lost']}pt (effort {a['effort']}, ROI {a['roi']}) — {a['name']}",
                  file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
