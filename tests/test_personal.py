import pytest


class TestNormalize:
    @pytest.mark.parametrize("raw", ["2000-01-01", "2000.1.1", "20000101", "2000년 1월 1일"])
    def test_birth_formats(self, personal, raw):
        assert personal.norm_birth(raw) == "2000-01-01"

    @pytest.mark.parametrize("raw", ["2000-13-01", "00-01-01", "생일"])
    def test_birth_invalid(self, personal, raw):
        with pytest.raises(ValueError):
            personal.norm_birth(raw)

    @pytest.mark.parametrize("raw,expected", [("01012345678", "010-1234-5678"), ("010 123 4567", "010-123-4567")])
    def test_phone(self, personal, raw, expected):
        assert personal.norm_phone(raw) == expected

    @pytest.mark.parametrize("raw", ["123", "02-123-4567"])
    def test_phone_invalid(self, personal, raw):
        with pytest.raises(ValueError):
            personal.norm_phone(raw)

    def test_email(self, personal):
        assert personal.norm_email(" me@example.com ") == "me@example.com"
        with pytest.raises(ValueError):
            personal.norm_email("not-an-email")


class TestData:
    def test_link_replaces_same_label(self, personal):
        data = {"links": [{"label": "GitHub", "url": "https://github.com/old"}]}
        personal.put_link(data, "GitHub=https://github.com/new")
        assert data["links"] == [{"label": "GitHub", "url": "https://github.com/new"}]

    def test_missing_lists_required_fields_in_order(self, personal, tmp_path):
        data = {"name": "홍길동", "email": "a@b.co", "photo": str(tmp_path / "none.jpg")}
        assert personal.missing(data) == ["birth", "phone", "address", "photo"]

    def test_set_saves_and_reports_missing(self, personal, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        assert personal.main(["set", "--name", "홍길동", "--birth", "2000.1.1"]) == 1
        saved = (tmp_path / "profile/personal.json").read_text(encoding="utf-8")
        assert '"birth": "2000-01-01"' in saved
        assert "미입력: 휴대폰, 이메일, 주소, 사진 경로" in capsys.readouterr().out
