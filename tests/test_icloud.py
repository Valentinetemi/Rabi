from types import SimpleNamespace

from rabi.tools import icloud


def make_tree(tmp_path):
    (tmp_path / "Desktop" / "ml-project" / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / "Desktop" / "ml-project" / "requirements.txt").write_text("torch\n")
    (tmp_path / "Desktop" / "ml-project" / ".venv" / "lib" / "torch.py").write_text("")
    (tmp_path / "Desktop" / "ml-project" / "train.py").write_text("")
    (tmp_path / "Documents" / "notes").mkdir(parents=True)
    (tmp_path / "Documents" / "notes" / "todo.txt").write_text("")
    (tmp_path / "Documents" / "web").mkdir()
    (tmp_path / "Documents" / "web" / "package.json").write_text("{}")
    return tmp_path


def test_find_projects_only_marked_folders(tmp_path):
    make_tree(tmp_path)
    found = {p.name for p in icloud.find_projects(tmp_path / "Desktop")} | {p.name for p in icloud.find_projects(tmp_path / "Documents")}
    assert found == {"ml-project", "web"}


def test_reports_percent_offloaded(tmp_path, monkeypatch):
    make_tree(tmp_path)
    # Pretend iCloud evicted every .py file (the venv module and train.py).
    monkeypatch.setattr(icloud, "is_dataless", lambda path: path.endswith(".py"))
    out = icloud.icloud_stuck_projects([str(tmp_path / "Desktop"), str(tmp_path / "Documents")])
    top = out["projects"][0]
    assert top["project"].endswith("ml-project")
    assert top["files_offloaded"] == 2 and top["percent_offloaded"] == round(200 / 3, 1)
    assert out["projects_with_offloaded_files"] == 1
    assert "~/dev" in out["recommendation"]


def test_is_dataless_false_without_st_flags(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("x")
    # Linux stat has no st_flags; must not crash.
    assert icloud.is_dataless(str(f)) in (False, True)
    assert icloud.is_dataless(str(tmp_path / "missing")) is False


def test_is_dataless_reads_flag(monkeypatch):
    monkeypatch.setattr(icloud.os, "lstat", lambda p: SimpleNamespace(st_flags=icloud.SF_DATALESS | 0x20))
    assert icloud.is_dataless("x") is True
    monkeypatch.setattr(icloud.os, "lstat", lambda p: SimpleNamespace(st_flags=0x20))
    assert icloud.is_dataless("x") is False
