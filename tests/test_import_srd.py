import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import split_pages


def configure_import(monkeypatch, tmp_path, english="# INTRODUCTION\n\nEnglish content"):
    project = Path(tmp_path)
    source = project / "src"
    pages = source / "pages"
    pages.mkdir(parents=True)
    (pages / "old.txt").write_text("old version", encoding="utf-8")
    data = project / "data"
    data.mkdir()
    manifest = {"pages": [{"path": "introduction", "title": {"zh": "介绍", "en": "Introduction"}}]}
    toc = data / "srd.yaml"
    toc.write_text(yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8")
    cn = source / "DH-SRD-CN.md"
    en = source / "DH-SRD-EN.md"
    cn.write_text("# 介绍\n\n中文内容", encoding="utf-8")
    en.write_text(english, encoding="utf-8")
    monkeypatch.setattr(split_pages, "PROJECT_DIR", str(project))
    monkeypatch.setattr(split_pages, "SRC_DIR", str(source))
    monkeypatch.setattr(split_pages, "PAGES_DIR", str(pages))
    monkeypatch.setattr(split_pages, "TOC_FILE", str(toc))
    monkeypatch.setattr(split_pages, "CN_FILE", str(cn))
    monkeypatch.setattr(split_pages, "EN_FILE", str(en))
    return pages


def test_complete_major_version_replaces_pages(monkeypatch, tmp_path):
    pages = configure_import(monkeypatch, tmp_path)
    assert split_pages.main() == 0
    assert not (pages / "old.txt").exists()
    assert (pages / "introduction" / "zh.md").read_text(encoding="utf-8").strip() == "中文内容"
    assert (pages / "introduction" / "en.md").read_text(encoding="utf-8").strip() == "English content"


def test_incomplete_major_version_keeps_current_pages(monkeypatch, tmp_path):
    pages = configure_import(monkeypatch, tmp_path, english="# SOMETHING ELSE\n\nMissing")
    assert split_pages.main() == 1
    assert (pages / "old.txt").read_text(encoding="utf-8") == "old version"
