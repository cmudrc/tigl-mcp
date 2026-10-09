"""Each CPACS header/updates entry names the session that wrote it (2026-10-08).

The aircraft-mcp gateway and the local agent publish their session-log id in
AIRCRAFT_SESSION_ID; the entry's modification text ends with it, so the file
alone says which session log holds the call. Outside a session it is unchanged.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from tigl_mcp import cpacs_adapter as a

_HEADER = (
    "<cpacs><header><name>t</name><creator>c</creator>"
    "<timestamp>2026-01-01T00:00:00</timestamp><version>0.1.0</version>"
    "<cpacsVersion>3.2</cpacsVersion></header></cpacs>"
)


def _last_modification(monkeypatch: pytest.MonkeyPatch) -> str:
    root = ET.fromstring(_HEADER)

    a._append_header_update(root, "wrote something", "test-creator 0.0")
    updates = root.findall("header/updates/update")
    return updates[-1].findtext("modification") or ""


def test_entry_names_the_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIRCRAFT_SESSION_ID", "20261008-020429-997463")
    text = _last_modification(monkeypatch)
    assert text == "wrote something [session 20261008-020429-997463]"


def test_entry_unchanged_outside_a_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AIRCRAFT_SESSION_ID", raising=False)
    assert _last_modification(monkeypatch) == "wrote something"


def test_an_unsafe_id_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIRCRAFT_SESSION_ID", "x</modification><evil>")
    assert _last_modification(monkeypatch) == "wrote something"
