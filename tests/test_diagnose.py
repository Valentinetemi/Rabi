from rabi.tools import diagnose


def test_why_is_my_mac_slow_combines_checks(monkeypatch):
    monkeypatch.setattr(diagnose, "system_health", lambda: {"memory_pressure": "critical"})
    monkeypatch.setattr(diagnose, "heavy_apps", lambda limit: {"top_by_memory": [{"app": "Xcode", "memory_mb": 8192}]})
    monkeypatch.setattr(diagnose, "disk_space", lambda: {"low_space": False})
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    out = diagnose.why_is_my_mac_slow()
    assert out["source"] == "template"
    assert "Xcode" in out["text"] and "critical" in out["text"]
    assert set(out["data"]) == {"system_health", "heavy_apps", "disk_space"}


def test_explain_check_rejects_unknown():
    out = diagnose.explain_check("rm_rf")
    assert "don't have" in out["text"] and "unpushed_work" in out["available"]
