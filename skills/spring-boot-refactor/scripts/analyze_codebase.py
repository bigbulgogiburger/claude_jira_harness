#!/usr/bin/env python3
"""
CS-Back 프로젝트 코드베이스 분석 스크립트

이 스크립트는 다음을 분석합니다:
1. CQRS 미적용 Service 클래스 식별
2. N+1 위험이 있는 Repository 메서드
3. 테스트 커버리지 누락
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class ServiceAnalysis:
    """Service 클래스 분석 결과"""
    file_path: str
    class_name: str
    read_methods: List[str]
    write_methods: List[str]
    is_cqrs_applied: bool
    has_transaction: bool


@dataclass
class RepositoryAnalysis:
    """Repository 분석 결과"""
    file_path: str
    class_name: str
    methods_without_fetch_join: List[str]
    n_plus_one_risk: bool


@dataclass
class TestCoverage:
    """테스트 커버리지 분석"""
    service_name: str
    has_test_file: bool
    test_file_path: str = ""
    test_count: int = 0


class CodebaseAnalyzer:
    """코드베이스 분석기"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.src_main = self.base_path / "src" / "main" / "java" / "com" / "suri" / "cs"
        self.src_test = self.base_path / "src" / "test" / "java" / "com" / "suri" / "cs"

    def analyze_services(self) -> List[ServiceAnalysis]:
        """Service 클래스 분석"""
        results = []

        # Service 파일 찾기
        service_files = list(self.src_main.rglob("*Service.java"))

        for service_file in service_files:
            # Read/Write Service는 이미 분리되어 있으므로 제외
            if "ReadService" in service_file.name or "WriteService" in service_file.name:
                continue

            analysis = self._analyze_service_file(service_file)
            if analysis:
                results.append(analysis)

        return results

    def _analyze_service_file(self, file_path: Path) -> ServiceAnalysis:
        """개별 Service 파일 분석"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        class_name = file_path.stem

        # 메서드 추출
        read_methods = []
        write_methods = []

        # public 메서드 찾기
        method_pattern = r'public\s+(?:[\w<>]+)\s+(\w+)\s*\([^)]*\)'
        methods = re.findall(method_pattern, content)

        for method in methods:
            # Read 메서드 패턴
            if any(method.startswith(prefix) for prefix in
                   ['get', 'find', 'search', 'list', 'count', 'exists']):
                read_methods.append(method)
            # Write 메서드 패턴
            elif any(method.startswith(prefix) for prefix in
                     ['create', 'update', 'delete', 'save', 'modify', 'register']):
                write_methods.append(method)

        # CQRS 적용 여부 (Read/Write 메서드가 모두 있으면 미적용)
        is_cqrs_applied = not (read_methods and write_methods)

        # @Transactional 존재 여부
        has_transaction = '@Transactional' in content

        return ServiceAnalysis(
            file_path=str(file_path),
            class_name=class_name,
            read_methods=read_methods,
            write_methods=write_methods,
            is_cqrs_applied=is_cqrs_applied,
            has_transaction=has_transaction
        )

    def analyze_repositories(self) -> List[RepositoryAnalysis]:
        """Repository Custom 구현체 분석 (N+1 위험 감지)"""
        results = []

        # RepositoryCustomImpl 파일 찾기
        impl_files = list(self.src_main.rglob("*RepositoryCustomImpl.java"))

        for impl_file in impl_files:
            analysis = self._analyze_repository_file(impl_file)
            if analysis and analysis.n_plus_one_risk:
                results.append(analysis)

        return results

    def _analyze_repository_file(self, file_path: Path) -> RepositoryAnalysis:
        """개별 Repository 파일 분석"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        class_name = file_path.stem

        # leftJoin 있으나 fetchJoin 없는 메서드 찾기
        methods_at_risk = []

        # 메서드별로 분석
        method_pattern = r'public\s+(?:[\w<>]+)\s+(\w+)\s*\([^)]*\)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
        methods = re.finditer(method_pattern, content, re.DOTALL)

        for match in methods:
            method_name = match.group(1)
            method_body = match.group(2)

            # leftJoin 또는 innerJoin이 있는지 확인
            has_join = 'leftJoin(' in method_body or 'innerJoin(' in method_body

            # fetchJoin()이 있는지 확인
            has_fetch_join = 'fetchJoin()' in method_body

            # join은 있으나 fetchJoin이 없으면 위험
            if has_join and not has_fetch_join:
                methods_at_risk.append(method_name)

        n_plus_one_risk = len(methods_at_risk) > 0

        return RepositoryAnalysis(
            file_path=str(file_path),
            class_name=class_name,
            methods_without_fetch_join=methods_at_risk,
            n_plus_one_risk=n_plus_one_risk
        )

    def analyze_test_coverage(self) -> List[TestCoverage]:
        """테스트 커버리지 분석"""
        results = []

        # 모든 Service 파일 찾기
        service_files = list(self.src_main.rglob("*Service.java"))

        for service_file in service_files:
            service_name = service_file.stem

            # 대응되는 테스트 파일 찾기
            test_file_name = f"{service_name}Test.java"
            test_file_path = self.src_test / service_file.parent.relative_to(self.src_main) / test_file_name

            has_test = test_file_path.exists()
            test_count = 0

            if has_test:
                with open(test_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # @Test 개수 세기
                    test_count = len(re.findall(r'@Test', content))

            results.append(TestCoverage(
                service_name=service_name,
                has_test_file=has_test,
                test_file_path=str(test_file_path) if has_test else "",
                test_count=test_count
            ))

        return results

    def generate_report(self) -> str:
        """분석 리포트 생성"""
        report = []
        report.append("=" * 80)
        report.append("CS-Back 코드베이스 리팩토링 분석 리포트")
        report.append("=" * 80)
        report.append("")

        # 1. CQRS 미적용 Service
        report.append("## 1. CQRS 미적용 Service 클래스")
        report.append("-" * 80)

        services = self.analyze_services()
        non_cqrs_services = [s for s in services if not s.is_cqrs_applied]

        if non_cqrs_services:
            report.append(f"총 {len(non_cqrs_services)}개 Service가 CQRS 패턴 미적용")
            report.append("")

            for service in non_cqrs_services:
                report.append(f"📦 {service.class_name}")
                report.append(f"   파일: {service.file_path}")
                report.append(f"   Read 메서드 ({len(service.read_methods)}개): {', '.join(service.read_methods[:3])}")
                if len(service.read_methods) > 3:
                    report.append(f"               ... 외 {len(service.read_methods) - 3}개")
                report.append(f"   Write 메서드 ({len(service.write_methods)}개): {', '.join(service.write_methods[:3])}")
                if len(service.write_methods) > 3:
                    report.append(f"                ... 외 {len(service.write_methods) - 3}개")
                report.append(f"   @Transactional: {'✓' if service.has_transaction else '✗'}")
                report.append("")
        else:
            report.append("✅ 모든 Service가 CQRS 패턴 적용됨")
            report.append("")

        # 2. N+1 위험 Repository
        report.append("## 2. N+1 위험이 있는 Repository 메서드")
        report.append("-" * 80)

        repositories = self.analyze_repositories()

        if repositories:
            report.append(f"총 {len(repositories)}개 Repository에서 N+1 위험 감지")
            report.append("")

            for repo in repositories:
                report.append(f"📦 {repo.class_name}")
                report.append(f"   파일: {repo.file_path}")
                report.append(f"   위험 메서드:")
                for method in repo.methods_without_fetch_join:
                    report.append(f"      - {method}() → leftJoin() 있으나 fetchJoin() 누락")
                report.append("")
        else:
            report.append("✅ N+1 위험이 감지된 메서드 없음")
            report.append("")

        # 3. 테스트 커버리지
        report.append("## 3. 테스트 커버리지")
        report.append("-" * 80)

        test_coverage = self.analyze_test_coverage()
        untested_services = [t for t in test_coverage if not t.has_test_file]

        total_services = len(test_coverage)
        tested_services = total_services - len(untested_services)
        coverage_percentage = (tested_services / total_services * 100) if total_services > 0 else 0

        report.append(f"전체 Service: {total_services}개")
        report.append(f"테스트 있음: {tested_services}개 ({coverage_percentage:.1f}%)")
        report.append(f"테스트 없음: {len(untested_services)}개")
        report.append("")

        if untested_services:
            report.append("테스트 파일이 없는 Service:")
            for t in untested_services[:10]:  # 최대 10개만 표시
                report.append(f"   ❌ {t.service_name}")
            if len(untested_services) > 10:
                report.append(f"   ... 외 {len(untested_services) - 10}개")
            report.append("")

        # 요약 및 권장사항
        report.append("=" * 80)
        report.append("## 권장 작업 순서")
        report.append("=" * 80)
        report.append("")

        priority = 1

        if repositories:
            report.append(f"{priority}. N+1 문제 해결 (우선순위: 높음)")
            report.append("   → 성능에 직접적인 영향을 미치므로 우선 처리")
            report.append(f"   → 대상: {len(repositories)}개 Repository")
            report.append("")
            priority += 1

        if non_cqrs_services:
            report.append(f"{priority}. CQRS 패턴 적용 (우선순위: 중간)")
            report.append("   → 유지보수성 및 확장성 개선")
            report.append(f"   → 대상: {len(non_cqrs_services)}개 Service")
            report.append("")
            priority += 1

        if untested_services:
            report.append(f"{priority}. 테스트 작성 (우선순위: 중간)")
            report.append("   → 리팩토링 안정성 확보")
            report.append(f"   → 대상: {len(untested_services)}개 Service")
            report.append("")

        report.append("=" * 80)

        return "\n".join(report)


def main():
    """메인 함수"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python analyze_codebase.py <project-path>")
        print("Example: python analyze_codebase.py D:\\newIdeaWorkSpace\\cs-back")
        sys.exit(1)

    project_path = sys.argv[1]

    if not os.path.exists(project_path):
        print(f"Error: 프로젝트 경로를 찾을 수 없습니다: {project_path}")
        sys.exit(1)

    analyzer = CodebaseAnalyzer(project_path)
    report = analyzer.generate_report()

    print(report)

    # 파일로도 저장
    output_file = Path(project_path) / "refactoring-analysis.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n리포트가 저장되었습니다: {output_file}")


if __name__ == "__main__":
    main()
