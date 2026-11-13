import json

import pytest


@pytest.fixture
def company(tmp_path, monkeypatch):
    (tmp_path / "companies/x").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path / "companies/x"


def put(company, name, data):
    (company / name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


class TestEnding:
    @pytest.mark.parametrize("text", ["처리 시간을 52.6분에서 30.4분으로 **42.2%** 줄였다",
                                      "정리 중에도 새 위반을 막았다 (ArchUnit)",
                                      "하네스를 만들고 CI를 붙였다 · github.com/me/repo"])
    def test_resume_ok(self, check_style, text):
        assert check_style.ending_issue(text, "resume") is None

    def test_resume_noun_ending(self, check_style):
        assert "명사" in check_style.ending_issue("롤백 후 검수 실행을 방지", "resume")

    def test_resume_number_ending_keeps_trailing_metric(self, check_style):
        # 앞이 명사면 괄호를 걷지 않는다: "30.4분 (−42.2%)"는 수치로 끝난 문장
        assert "수치" in check_style.ending_issue("52.6분 → 30.4분 (−42.2%)", "resume")

    def test_resume_rejects_polite_style(self, check_style):
        assert "~니다" in check_style.ending_issue("병목을 찾았습니다", "resume")

    def test_deck_ok_and_plain_style(self, check_style):
        assert check_style.ending_issue("병목을 찾았습니다", "deck") is None
        assert "덱은" in check_style.ending_issue("측정 가능한 환경을 만든다", "deck")


class TestTerms:
    def test_jargon_with_hint(self, check_style):
        assert check_style.jargon_hits("groundedness 검사를 통과해야 채택") == ["groundedness→원문 근거 검사"]

    def test_gloss_in_parentheses_is_explained(self, check_style):
        assert check_style.jargon_hits("기존 위반은 기록해 두고(freeze) 새 위반만 막았다") == []

    def test_code_identifier(self, check_style):
        assert check_style.jargon_hits("SET LOCAL force_custom_plan 적용") == ["force_custom_plan(코드 식별자)"]

    def test_acronym_with_lowercase_prefix_is_not_identifier(self, check_style):
        assert check_style.jargon_hits("vLLM은 여러 요청을 디코딩한다") == []

    def test_latin_count_skips_common_and_gloss(self, check_style):
        assert check_style.latin_terms("PR마다 CI와 API를 검사(tsvector, trigram)") == []


class TestTitle:
    def test_label_title_allowed(self, check_style):
        assert check_style.title_issue("기술 스택") == []

    def test_claim_title_needs_predicate(self, check_style):
        assert check_style.title_issue("psql에선 10ms인 쿼리가 부하에선 DB CPU 99%, 원인은 실행 계획")


class TestMain:
    def test_warn_only_by_default(self, company, check_style, capsys):
        put(company, "resume.json", {"sections": [{"type": "projects", "items": [{"name": "p", "bullets": ["캐시 적용"]}]}]})
        assert check_style.main(["companies/x"]) == 0
        assert "경고 1건" in capsys.readouterr().out

    def test_strict_fails_on_warning(self, company, check_style):
        put(company, "resume.json", {"sections": [{"type": "text", "items": ["캐시 적용"]}]})
        assert check_style.main(["companies/x", "--strict"]) == 1

    def test_clean_deck(self, company, check_style, capsys):
        put(company, "deck.json", {"slides": [{"type": "star", "title": "병목 하나만 고쳤습니다", "action": ["단계마다 시간을 쟀습니다"],
                                               "stack": ["Python"], "metrics": [{"value": "-42.2%", "label": "약관 ETL"}]}]})
        assert check_style.main(["companies/x", "--strict"]) == 0
        assert "경고 없음" in capsys.readouterr().out

    def test_phrase_fields_skip_ending(self, company, check_style, capsys):
        fit = {"type": "fit", "items": [{"value": "Focus", "desc": "가장 중요한 한 가지에 집중", "evidence": "42.2% 줄였습니다"}]}
        req = {"type": "requirements", "rows": [{"req": "자동화", "evidence": "CI/CD 구축"}]}
        put(company, "deck.json", {"slides": [fit, req]})
        assert check_style.main(["companies/x", "--strict"]) == 0

    def test_only_from_limits_to_touched_fields(self, company, check_style, capsys, tmp_path):
        put(company, "resume.json", {"sections": [{"type": "text", "items": ["캐시 적용", "인덱스 추가"]}]})
        (tmp_path / "only.txt").write_text('"인덱스 추가"', encoding="utf-8")
        check_style.main(["companies/x", "--only-from", str(tmp_path / "only.txt")])
        out = capsys.readouterr().out
        assert "인덱스 추가" in out and "캐시 적용" not in out

    def test_no_files(self, company, check_style):
        assert check_style.main(["companies/x"]) == 2


class TestHookTargets:
    def test_edit_on_deck(self, style_hook):
        found, only = style_hook.targets("Edit", {"file_path": "/repo/companies/toss/deck.json", "new_string": "abc"})
        assert found == {"toss": {"deck.json"}} and only == "abc"

    def test_build_command(self, style_hook):
        found, only = style_hook.targets("Bash", {"command": "node scripts/build_resume.js companies/toss && node scripts/build_deck.js companies/toss"})
        assert found == {"toss": {"resume.json", "deck.json"}} and only is None

    def test_read_only_bash_ignored(self, style_hook):
        assert style_hook.targets("Bash", {"command": "cat companies/toss/deck.json"})[0] == {}

    def test_other_files_ignored(self, style_hook):
        assert style_hook.targets("Write", {"file_path": "/repo/README.md"})[0] == {}
