#!/usr/bin/env python3
"""harness-execute.py 자체 테스트 (harness v2 §4.2 — 러너 테스트 필수 조건).

실행: python scripts/test_stanley_execute.py
claude CLI·실 git 상태에 의존하지 않는다 (순수 함수 + tmp 파일 + trivial bash 만).
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
se = __import__("harness-execute")


class TestExtractContext(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        with open(os.path.join(self.d, "adr.md"), "w", encoding="utf-8") as f:
            f.write(
                "# Decision Log\n\nintro — Previous PASS mention\n\n"
                "## ADR-090 — 불량코드 product_line 전환\n\n본문A\n\n### 세부\n\n세부내용\n\n"
                "## ADR-091 — 다음 결정\n\n본문B\n"
            )

    def test_anchor_section(self):
        out = se.extract_context("adr.md#ADR-090", self.d)
        self.assertIn("본문A", out)
        self.assertIn("세부내용", out)          # 하위 헤더(###)는 섹션에 포함
        self.assertNotIn("본문B", out)          # 다음 동레벨 헤더에서 종료
        self.assertNotIn("intro", out)

    def test_whole_file(self):
        out = se.extract_context("adr.md", self.d)
        self.assertIn("본문B", out)

    def test_missing_anchor_warns(self):
        out = se.extract_context("adr.md#ADR-999", self.d)
        self.assertIn("앵커 미발견", out)

    def test_missing_file_warns(self):
        out = se.extract_context("nope.md#X", self.d)
        self.assertIn("파일 없음", out)


class TestBuildPrompt(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        with open(os.path.join(self.d, "always.md"), "w", encoding="utf-8") as f:
            f.write("NEVER 요약블록")
        with open(os.path.join(self.d, "step0.md"), "w", encoding="utf-8") as f:
            f.write("step0 지시")
        self.idx = {
            "issue": "PROJ-999", "always_context": ["always.md"],
            "steps": [
                {"step": 0, "name": "done-one", "status": "completed", "summary": "엔티티 추가함"},
                {"step": 1, "name": "cur", "status": "pending", "prompt_file": "step0.md",
                 "context_refs": [], "touched_files": ["src/**"]},
            ],
        }

    def test_assembly_and_retry_injection(self):
        step = self.idx["steps"][1]
        p = se.build_prompt(self.idx, step, None, self.d)
        self.assertIn("NEVER 요약블록", p)
        self.assertIn("엔티티 추가함", p)       # 완료 step summary 체인
        self.assertIn("step0 지시", p)
        self.assertIn("git commit/push/merge 를 실행하지 마라", p)  # 러너 계약
        self.assertNotIn("직전 시도 실패", p)
        p2 = se.build_prompt(self.idx, step, "AC 실패: gradlew compileJava", self.d)
        self.assertIn("직전 시도 실패", p2)
        self.assertIn("gradlew compileJava", p2)


class TestParseClaudeJson(unittest.TestCase):
    def test_normal(self):
        out = json.dumps({"result": "SUMMARY: ok", "total_cost_usd": 0.42, "is_error": False})
        r = se.parse_claude_json(out)
        self.assertEqual(r["result"], "SUMMARY: ok")
        self.assertEqual(r["cost_usd"], 0.42)
        self.assertFalse(r["is_error"])

    def test_noise_then_json(self):
        out = "some log noise\n" + json.dumps({"result": "done", "total_cost_usd": 0.1})
        r = se.parse_claude_json(out)
        self.assertEqual(r["result"], "done")

    def test_garbage_is_error(self):
        r = se.parse_claude_json("not json at all")
        self.assertTrue(r["is_error"])

    def test_empty_is_error(self):
        self.assertTrue(se.parse_claude_json("")["is_error"])


class TestGateDiffScope(unittest.TestCase):
    STEP = {"touched_files": ["backend/src/main/**", "docs/PROJ-999-dev-guide.md"]}

    def test_in_scope(self):
        paths = ["backend/src/main/java/A.java", "docs/PROJ-999-dev-guide.md",
                 "phases/PROJ-999/index.json"]  # phases/ 는 항상 허용
        self.assertIsNone(se.gate_diff_scope(self.STEP, paths))

    def test_out_of_scope(self):
        err = se.gate_diff_scope(self.STEP, ["frontend/src/App.vue"])
        self.assertIsNotNone(err)
        self.assertIn("frontend/src/App.vue", err)

    def test_baseline_excluded(self):
        # 타 세션의 사전 dirty 파일은 scope 게이트 대상이 아니다 (오발·오커밋 방지)
        baseline = {"frontend/src/App.vue", "backend/src/test/Foo.java"}
        paths = ["frontend/src/App.vue", "backend/src/main/java/A.java"]
        self.assertIsNone(se.gate_diff_scope(self.STEP, paths, baseline=baseline))

    def test_baseline_conflict_refuses(self):
        baseline = {"backend/src/main/java/B.java"}
        err = se.baseline_conflict(self.STEP, baseline)
        self.assertIsNotNone(err)
        self.assertIn("동시 세션 충돌", err)
        self.assertIsNone(se.baseline_conflict(self.STEP, {"unrelated/file.txt"}))


class TestGateForbid(unittest.TestCase):
    IDX = {"forbid": ["git push", "-Pqa", "DROP TABLE", "std_cs_app"]}

    def test_session_hit(self):
        self.assertIn("-Pqa", se.gate_forbid(self.IDX, "gradlew.bat -Pqa flywayMigrate 실행", ""))

    def test_diff_added_line_hit(self):
        diff = "+++ b/build.sh\n+gradlew -Pqa deploy\n context line"
        self.assertIsNotNone(se.gate_forbid(self.IDX, "", diff))

    def test_diff_context_line_no_hit(self):
        # 기존 파일에 이미 있던(컨텍스트/삭제) 라인은 오발하지 않는다
        diff = "--- a/docs/x.md\n+++ b/docs/x.md\n gradlew -Pqa 언급된 기존 산문\n-DROP TABLE old\n+새 내용"
        self.assertIsNone(se.gate_forbid(self.IDX, "", diff))

    def test_clean(self):
        self.assertIsNone(se.gate_forbid(self.IDX, "local flywayMigrate std_dev 완료", "+harmless"))


class TestIndexIO(unittest.TestCase):
    def test_roundtrip_and_first_pending(self):
        d = tempfile.mkdtemp()
        idx = {"issue": "PROJ-1", "steps": [
            {"step": 0, "status": "completed"},
            {"step": 1, "status": "pending"},
            {"step": 2, "status": "pending"},
        ]}
        se.save_index(d, idx)
        loaded = se.load_index(d)
        self.assertEqual(loaded, idx)
        self.assertEqual(se.first_pending(loaded)["step"], 1)
        loaded["steps"][1]["status"] = "error"
        self.assertEqual(se.first_pending(loaded)["step"], 2)
        for s in loaded["steps"]:
            s["status"] = "completed"
        self.assertIsNone(se.first_pending(loaded))


class TestGateAcProbe(unittest.TestCase):
    def test_ac_pass_fail(self):
        self.assertIsNone(se.gate_ac({"ac": ["true", "echo ok"]}))
        err = se.gate_ac({"ac": ["false"]})
        self.assertIn("AC 실패", err)

    def test_probe_expect(self):
        ok = {"probe": [{"kind": "shell", "cmd": "echo value=42", "expect": r"value=\d+"}]}
        self.assertIsNone(se.gate_probe(ok))
        bad = {"probe": [{"kind": "shell", "cmd": "echo value=none", "expect": r"value=\d+"}]}
        self.assertIn("expect 불일치", se.gate_probe(bad))
        crash = {"probe": [{"kind": "shell", "cmd": "exit 3", "expect": "x"}]}
        self.assertIn("실행 실패", se.gate_probe(crash))


class TestExtractSummary(unittest.TestCase):
    def test_marker(self):
        self.assertEqual(se.extract_summary("blah\nSUMMARY: 엔티티 3개 추가\n"), "엔티티 3개 추가")

    def test_fallback_last_line(self):
        self.assertEqual(se.extract_summary("first\nlast line"), "last line")


if __name__ == "__main__":
    unittest.main(verbosity=2)
