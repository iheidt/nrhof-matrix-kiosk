"""Test event payload type definitions."""

from nrhof.core.event_payloads import (
    LanguageChangedPayload,
    NowPlayingPayload,
    SceneChangedPayload,
)


def test_now_playing_payload_shape():
    """Test NowPlayingPayload has correct structure."""
    payload: NowPlayingPayload = {
        "track": "Test Track",
        "artist": "Test Artist",
        "album": "Test Album",
        "duration_ms": 180000,
        "progress_ms": 60000,
        "source": "spotify",
        "is_playing": True,
    }

    assert payload["duration_ms"] > 0
    assert payload["progress_ms"] >= 0
    assert payload["source"] in ["spotify", "sonos", "unknown"]
    assert isinstance(payload["is_playing"], bool)


def test_language_changed_payload_shape():
    """Test LanguageChangedPayload has correct structure."""
    payload: LanguageChangedPayload = {
        "old": "en",
        "new": "jp",
    }

    assert len(payload["old"]) > 0
    assert len(payload["new"]) > 0


def test_scene_changed_payload_shape():
    """Test SceneChangedPayload has correct structure."""
    payload: SceneChangedPayload = {
        "from_scene": "MenuScene",
        "to_scene": "NR38Scene",
        "use_transition": True,
    }

    assert payload["from_scene"].endswith("Scene")
    assert payload["to_scene"].endswith("Scene")
    assert isinstance(payload["use_transition"], bool)


def test_partial_now_playing_payload():
    """Test NowPlayingPayload works with partial data (total=False)."""
    # Should work with minimal fields
    payload: NowPlayingPayload = {
        "track": "Test",
        "artist": "Artist",
    }

    assert "track" in payload
    assert "artist" in payload
