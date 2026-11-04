import json

import pytest


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """사실 출처 하나와 빈 기업 폴더가 있는 작업 디렉터리."""
    write(tmp_path / "profile/notion_profile.md", "약관 ETL 52.6분 → 30.4분, 2026-05-01 시작, 1,234건 처리, Recall 0.950")
    (tmp_path / "companies/x").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def deck(workspace, slides, name="deck.json", key="slides", **extra):
    write(workspace / "companies/x" / name, json.dumps({key: slides, **extra}, ensure_ascii=False))


class TestNumbers:
    def test_decimal_and_arrow(self, check_facts):
        assert check_facts.numbers("52.6분 → 30.4분") == ["52.6", "30.4"]

    def test_date_split_into_parts(self, check_facts):
        assert check_facts.numbers("2026.03 ~ 2027.07") == ["2026", "3", "2027", "7"]

    def test_comma_and_trailing_zero_normalized(self, check_facts):
        assert check_facts.numbers("1,234건, 0.950") == ["1234", "0.95"]


class TestMain:
    def test_pass_when_all_numbers_in_source(self, workspace, check_facts):
        deck(workspace, [{"type": "star", "result": ["52.6분 → 30.4분", "1,234건"]}])
        assert check_facts.main(["companies/x"]) == 0

    def test_fail_on_number_missing_from_source(self, workspace, check_facts, capsys):
        deck(workspace, [{"type": "star", "result": ["처리량 3배"]}, {"type": "cover", "headline": "99% 개선"}])
        assert check_facts.main(["companies/x"]) == 1
        assert "출처에 없음: 슬라이드 2" in capsys.readouterr().out

    def test_derived_value_passes_with_sourced_basis(self, workspace, check_facts):
        deck(workspace, [{"type": "star", "result": ["−42.2%"]}], derived=[{"value": "42.2", "from": "52.6분 → 30.4분"}])
        assert check_facts.main(["companies/x"]) == 0

    def test_derived_with_unsourced_basis_fails(self, workspace, check_facts):
        deck(workspace, [{"type": "star", "result": ["−50%"]}], derived=[{"value": "50", "from": "100분 → 50분"}])
        assert check_facts.main(["companies/x"]) == 1

    def test_skip_keys_are_ignored(self, workspace, check_facts):
        deck(workspace, [{"type": "image", "no": "07", "path": "assets/img-404.png", "caption": "구조도"}])
        assert check_facts.main(["companies/x"]) == 0

    def test_resume_file_checks_sections(self, workspace, check_facts, capsys):
        deck(workspace, [{"type": "projects", "title": "프로젝트", "items": [{"bullets": ["77% 단축"]}]}],
             name="resume.json", key="sections")
        assert check_facts.main(["companies/x", "--file", "resume.json"]) == 1
        assert "출처에 없음: 섹션 1" in capsys.readouterr().out

    def test_find_reports_slide_number_ignoring_spaces(self, workspace, check_facts, capsys):
        deck(workspace, [{"type": "cover", "headline": "가"}, {"type": "star", "context": "측정 장치부터 만든다"}])
        assert check_facts.main(["companies/x", "--find", "측정장치부터"]) == 0
        assert "슬라이드 2" in capsys.readouterr().out

    def test_usage_error_when_file_missing(self, workspace, check_facts):
        assert check_facts.main(["companies/x"]) == 2
        assert check_facts.main([]) == 2
