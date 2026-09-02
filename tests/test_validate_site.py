import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_site import ValidationError, validate_site


def make_public(tmp_path, link):
    public = Path(tmp_path) / "public"
    (public / "generated").mkdir(parents=True)
    (public / "core").mkdir()
    (public / "other").mkdir()
    (public / "edit").mkdir()
    (public / "admin").mkdir()
    (public / "css").mkdir()
    (public / "js").mkdir()
    site = {
        "pages": [
            {"path": "core", "headings": {"zh": [{"anchor": "rule"}], "en": [{"anchor": "rule"}]}},
            {"path": "other", "headings": {"zh": [{"anchor": "target"}], "en": [{"anchor": "target"}]}},
        ]
    }
    (public / "generated" / "site-index.json").write_text(json.dumps(site), encoding="utf-8")
    (public / "generated" / "search-index.json").write_text('{"records": []}', encoding="utf-8")
    (public / "core" / "index.html").write_text(f'<h2 id="rule">Rule</h2><a href="{link}">link</a>', encoding="utf-8")
    (public / "other" / "index.html").write_text('<h2 id="target">Target</h2>', encoding="utf-8")
    for required in ("index.html", "edit/index.html", "admin/index.html", "css/site.css", "js/app.js", "js/search-core.js"):
        target = public / required
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()
    return public


def test_validator_accepts_existing_internal_page_and_anchor(tmp_path):
    validate_site(make_public(tmp_path, "/SRD/other/#target"))


@pytest.mark.parametrize("link", ["/SRD/missing/", "/SRD/other/#missing"])
def test_validator_rejects_broken_internal_links(tmp_path, link):
    with pytest.raises(ValidationError, match="站内链接"):
        validate_site(make_public(tmp_path, link))
