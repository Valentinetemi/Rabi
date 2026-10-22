from rabi import explain as ex
from rabi.templates import template_explanation


class FakeClient:
    def __init__(self, fail=False):
        self.fail, self.kwargs = fail, None

    def converse(self, **kwargs):
        if self.fail:
            raise RuntimeError("AccessDeniedException")
        self.kwargs = kwargs
        return {"output": {"message": {"role": "assistant", "content": [{"text": "Xcode is heavy. Close the Simulator."}]}}}


def test_template_when_not_configured(monkeypatch):
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    out = ex.explain("unpushed_work", {"repos_with_unsaved_work": []})
    assert out["source"] == "template" and "pushed" in out["text"]


def test_uses_converse_when_configured(monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_ID", "test-model")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    fake = FakeClient()
    monkeypatch.setattr(ex, "_client", lambda: fake)
    out = ex.explain("slow_mac", {"x": 1})
    assert out == {"text": "Xcode is heavy. Close the Simulator.", "source": "bedrock"}
    assert fake.kwargs["modelId"] == "test-model"
    assert fake.kwargs["system"][0]["text"] == ex.SYSTEM_PROMPT
    assert '"x": 1' in fake.kwargs["messages"][0]["content"][0]["text"]


def test_falls_back_when_bedrock_fails(monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_ID", "test-model")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setattr(ex, "_client", lambda: FakeClient(fail=True))
    assert ex.explain("slow_mac", {})["source"] == "template"


def test_slow_mac_template_mentions_top_app():
    data = {
        "system_health": {"memory_pressure": "warning"},
        "heavy_apps": {"top_by_memory": [{"app": "Xcode", "memory_mb": 6144}]},
        "disk_space": {"low_space": False},
    }
    text = template_explanation("slow_mac", data)
    assert "Xcode" in text and "warning" in text and "6.0 gigabytes" in text


def test_icloud_template():
    data = {"projects_with_offloaded_files": 1, "projects": [{"project": "~/Desktop/ml", "percent_offloaded": 80.0}]}
    assert "80 percent" in template_explanation("icloud_stuck_projects", data)


def test_unknown_topic_is_safe():
    assert template_explanation("nope", {})
