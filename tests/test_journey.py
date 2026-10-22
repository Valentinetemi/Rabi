import json
import re
from datetime import date

from rabi.tools import journey

TODAY = date(2026, 10, 22)
DATA = {
    "name": "T",
    "hackathons": [
        {"name": "A", "date": "2026-06-01", "result": "won"},
        {"name": "B", "date": "2026-07-01", "result": "submitted"},
        {"name": "C", "date": "2026-10-21", "result": "not_selected"},
        {"name": "D", "date": "2026-10-10", "result": "pending"},
    ],
    "wins": [{"title": "Mentorship acceptance", "date": "2026-10-05"}],
    "upcoming_deadlines": [
        {"name": "Past thing", "date": "2026-10-01"},
        {"name": "Grad school", "date": "2026-12-15"},
        {"name": "Eval Hackathon", "date": "2026-10-30"},
    ],
}


def test_summary_counts_only_file_facts():
    s = journey.summarise(DATA, TODAY)
    assert s["hackathons_entered"] == 4
    assert s["projects_shipped"] == 3
    assert s["hackathon_wins"] == 1
    assert s["results_pending"] == 1
    assert s["next_deadline"]["name"] == "Eval Hackathon"


def test_reply_acknowledges_then_points_forward():
    text = journey.compose(journey.summarise(DATA, TODAY), "the Amazon hackathon", False, TODAY)
    assert text.startswith("I'm sorry about the Amazon hackathon. That stings")
    assert "Eval Hackathon, in 8 days" in text
    assert "friend" not in text


def test_every_number_in_reply_is_from_file():
    s = journey.summarise(DATA, TODAY)
    text = journey.compose(s, None, True, TODAY)
    allowed = {str(v) for v in s.values() if isinstance(v, int)} | {"8"}
    assert set(re.findall(r"\d+", text)) <= allowed
    assert "friend" in text


def test_empty_record_invents_nothing():
    s = journey.summarise({"name": "T", "hackathons": []}, TODAY)
    text = journey.compose(s, None, False, TODAY)
    assert not re.search(r"\d", text)
    assert "record" not in text


def test_reads_custom_file_and_falls_back_to_example(tmp_path, monkeypatch):
    f = tmp_path / "j.json"
    f.write_text(json.dumps(DATA))
    monkeypatch.setenv("RABI_JOURNEY_FILE", str(f))
    assert journey.my_journey()["summary"]["hackathons_entered"] == 4
    monkeypatch.delenv("RABI_JOURNEY_FILE")
    assert journey.journey_path().name in ("journey.json", "journey.example.json")


def test_missing_file_is_friendly(tmp_path, monkeypatch):
    monkeypatch.setenv("RABI_JOURNEY_FILE", str(tmp_path / "nope.json"))
    assert "journey file" in journey.my_journey()["text"]
