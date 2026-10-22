import pytest

from rabi.tools import close_app as ca


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    ca._pending.clear()
    monkeypatch.setattr(ca, "_running_app", lambda name: ("Simulator", 3) if name.lower() == "simulator" else None)
    monkeypatch.setattr(ca, "is_macos", lambda: True)
    calls = []
    monkeypatch.setattr(ca, "run", lambda cmd, timeout=5: calls.append(cmd) or "")
    return calls


def test_first_call_never_acts(setup):
    out = ca.close_app("simulator")
    assert out["status"] == "needs_confirmation" and out["app"] == "Simulator"
    assert out["confirm_token"] and setup == []


def test_second_call_quits_gracefully(setup):
    token = ca.close_app("Simulator")["confirm_token"]
    out = ca.close_app("Simulator", confirm_token=token)
    assert out["status"] == "quit_requested"
    assert setup == [["osascript", "-e", 'quit app "Simulator"']]
    assert not any("kill" in " ".join(c) for c in setup)


def test_token_is_single_use(setup):
    token = ca.close_app("Simulator")["confirm_token"]
    ca.close_app("Simulator", confirm_token=token)
    assert ca.close_app("Simulator", confirm_token=token)["status"] == "invalid_token"


def test_token_expires(setup, monkeypatch):
    token = ca.close_app("Simulator")["confirm_token"]
    real_time = ca.time.time
    monkeypatch.setattr(ca.time, "time", lambda: real_time() + ca.TOKEN_TTL_SECONDS + 1)
    assert ca.close_app("Simulator", confirm_token=token)["status"] == "invalid_token"
    assert setup == []


def test_token_bound_to_app(setup, monkeypatch):
    token = ca.close_app("Simulator")["confirm_token"]
    assert ca.close_app("Xcode", confirm_token=token)["status"] == "invalid_token"


@pytest.mark.parametrize("name", ["Finder", "WindowServer", "loginwindow", "Dock", "kernel_task", "finder.app"])
def test_refuses_system_apps(setup, name):
    assert ca.close_app(name)["status"] == "refused"
    assert setup == []


def test_not_running(setup):
    assert ca.close_app("Photoshop")["status"] == "not_running"


def test_quotes_escaped(setup, monkeypatch):
    monkeypatch.setattr(ca, "_running_app", lambda name: ('Evil" & do shell script "x', 1))
    token = ca.close_app('Evil" & do shell script "x')["confirm_token"]
    ca.close_app('Evil" & do shell script "x', confirm_token=token)
    assert setup[0][2] == 'quit app "Evil\\" & do shell script \\"x"'
