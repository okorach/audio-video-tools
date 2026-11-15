#
# media-tools
# Copyright (C) 2019-2026 Olivier Korach
# mailto:olivier.korach AT gmail DOT com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

"""Tests of the Google OAuth2 authentication and Google Photos Picker API access (mediatools.google_photos),
used by imagetool inventory --google. All the Google HTTP calls are mocked: there is no live counterpart to run
these against in CI"""

# The fixtures are the arguments of the tests that use them
# pylint: disable=redefined-outer-name

import json
from pathlib import Path
from unittest import mock

import pytest
import requests

from mediatools import google_photos


def _mock_response(json_data: dict | None = None, headers: dict | None = None, content: bytes | None = None) -> mock.MagicMock:
    """Returns a mock requests.Response usable both directly and as a context manager (for the streamed calls)"""
    response = mock.MagicMock()
    response.json.return_value = json_data or {}
    response.headers = headers or {}
    response.content = content
    response.raise_for_status = mock.MagicMock()
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


@pytest.fixture
def credentials_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Points google.credentials_file to a valid Desktop app OAuth2 client credentials file"""
    path = tmp_path / "credentials.json"
    path.write_text(json.dumps({"installed": {"client_id": "the-id", "client_secret": "the-secret"}}), encoding="utf-8")
    monkeypatch.setattr(google_photos.util, "get_media_properties", lambda: {"google.credentials_file": str(path)})
    return path


@pytest.fixture
def token_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credentials_file: Path) -> Path:
    """Points google.token_file to a (not yet existing) token cache file, on top of credentials_file"""
    path = tmp_path / "token.json"

    def props() -> dict:
        return {"google.credentials_file": str(credentials_file), "google.token_file": str(path)}

    monkeypatch.setattr(google_photos.util, "get_media_properties", props)
    return path


def test_credentials_and_token_file_default_to_the_home_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without the google.credentials_file/google.token_file properties, the default paths are used"""
    monkeypatch.setattr(google_photos.util, "get_media_properties", dict)
    assert google_photos._credentials_file().endswith("mediatools-google-credentials.json")
    assert google_photos._token_file().endswith("mediatools-google-token.json")


def test_load_client_config_exits_when_the_file_is_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing credentials file exits instead of crashing on a later Google call"""
    monkeypatch.setattr(google_photos.util, "get_media_properties", lambda: {"google.credentials_file": str(tmp_path / "missing.json")})
    with pytest.raises(SystemExit):
        google_photos._load_client_config()


def test_load_client_config_exits_when_the_file_is_malformed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A credentials file without client_id/client_secret exits with a clear message rather than a KeyError"""
    path = tmp_path / "credentials.json"
    path.write_text(json.dumps({"installed": {}}), encoding="utf-8")
    monkeypatch.setattr(google_photos.util, "get_media_properties", lambda: {"google.credentials_file": str(path)})
    with pytest.raises(SystemExit):
        google_photos._load_client_config()


def test_load_client_config_reads_the_installed_app_credentials(credentials_file: Path) -> None:
    """The {client_id, client_secret} are read from the 'installed' key of the Google-generated credentials file"""
    assert google_photos._load_client_config() == {"client_id": "the-id", "client_secret": "the-secret"}


def test_token_cache_round_trips(token_file: Path) -> None:
    """A token saved with _save_token() is read back identically by _load_cached_token(), None before it is ever saved"""
    assert google_photos._load_cached_token() is None
    google_photos._save_token({"access_token": "abc", "refresh_token": "def"})
    assert google_photos._load_cached_token() == {"access_token": "abc", "refresh_token": "def"}


def test_get_access_token_runs_the_consent_flow_when_there_is_no_cached_token(token_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Without a cached token, the interactive consent flow is run, and its result is cached"""
    monkeypatch.setattr(google_photos, "_run_consent_flow", lambda _client_id, _client_secret: {"access_token": "new-token"})
    assert google_photos.get_access_token() == "new-token"
    assert google_photos._load_cached_token() == {"access_token": "new-token"}


def test_get_access_token_refreshes_a_cached_token(token_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A cached token with a refresh_token is silently refreshed, without running the interactive consent flow again"""
    google_photos._save_token({"access_token": "old", "refresh_token": "rt"})
    monkeypatch.setattr(google_photos, "_run_consent_flow", lambda *_a: pytest.fail("Should not re-run the consent flow"))
    monkeypatch.setattr(google_photos, "_refresh_access_token", lambda _token, _cid, _secret: {"access_token": "refreshed", "refresh_token": "rt"})
    assert google_photos.get_access_token() == "refreshed"


def test_get_access_token_falls_back_to_consent_flow_when_the_refresh_fails(token_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A refresh failure (eg a revoked token) falls back to the interactive consent flow instead of crashing"""
    google_photos._save_token({"access_token": "old", "refresh_token": "rt"})

    def failing_refresh(*_args: object) -> dict:
        raise requests.RequestException("revoked")

    monkeypatch.setattr(google_photos, "_refresh_access_token", failing_refresh)
    monkeypatch.setattr(google_photos, "_run_consent_flow", lambda *_a: {"access_token": "new-token"})
    assert google_photos.get_access_token() == "new-token"


def test_refresh_access_token_keeps_the_refresh_token_when_not_resent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Google does not resend the refresh_token on a refresh: the previous one is kept"""
    monkeypatch.setattr(google_photos.requests, "post", lambda *_a, **_k: _mock_response({"access_token": "new"}))
    refreshed = google_photos._refresh_access_token({"refresh_token": "rt"}, "cid", "secret")
    assert refreshed == {"access_token": "new", "refresh_token": "rt"}


def test_auth_header_carries_the_bearer_token() -> None:
    """The Authorization header is a standard OAuth2 Bearer token"""
    assert google_photos._auth_header("abc") == {"Authorization": "Bearer abc"}


@pytest.mark.parametrize(
    ("session", "expected"),
    [
        ({"pollingConfig": {"pollInterval": "5s"}}, 5.0),
        ({"pollingConfig": {"pollInterval": "2.5s"}}, 2.5),
        ({}, google_photos.DEFAULT_POLL_INTERVAL),
        ({"pollingConfig": {"pollInterval": "not-a-duration"}}, google_photos.DEFAULT_POLL_INTERVAL),
    ],
)
def test_poll_interval(session: dict, expected: float) -> None:
    """The session's own pollInterval is used when given and parseable, DEFAULT_POLL_INTERVAL otherwise"""
    assert google_photos._poll_interval(session) == expected


def test_create_picker_session_returns_the_api_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_picker_session() returns the session as given by the API"""
    monkeypatch.setattr(
        google_photos.requests, "post", lambda *_a, **_k: _mock_response({"id": "s1", "pickerUri": "https://photos.google.com/pick/s1"})
    )
    session = google_photos.create_picker_session("token")
    assert session == {"id": "s1", "pickerUri": "https://photos.google.com/pick/s1"}


def test_wait_for_selection_polls_until_media_items_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """wait_for_selection() polls the session until mediaItemsSet becomes true, without actually sleeping or opening a browser"""
    monkeypatch.setattr(google_photos.webbrowser, "open", lambda _url: None)
    monkeypatch.setattr(google_photos.time, "sleep", lambda _seconds: None)
    responses = [
        _mock_response({"id": "s1", "mediaItemsSet": False}),
        _mock_response({"id": "s1", "mediaItemsSet": True}),
    ]
    monkeypatch.setattr(google_photos.requests, "get", lambda *_a, **_k: responses.pop(0))
    session = {"id": "s1", "pickerUri": "https://photos.google.com/pick/s1"}
    result = google_photos.wait_for_selection("token", session)
    assert result == {"id": "s1", "mediaItemsSet": True}
    assert not responses


def test_wait_for_selection_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    """wait_for_selection() exits instead of polling forever when the picker session is never completed"""
    monkeypatch.setattr(google_photos, "SESSION_TIMEOUT", 0)
    monkeypatch.setattr(google_photos.webbrowser, "open", lambda _url: None)
    with pytest.raises(SystemExit):
        google_photos.wait_for_selection("token", {"id": "s1", "pickerUri": "https://photos.google.com/pick/s1"})


def test_list_picked_media_items_follows_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_picked_media_items() yields every item across all the pages of the Picker API"""
    responses = [
        _mock_response({"mediaItems": [{"id": "1"}, {"id": "2"}], "nextPageToken": "p2"}),
        _mock_response({"mediaItems": [{"id": "3"}]}),
    ]
    monkeypatch.setattr(google_photos.requests, "get", lambda *_a, **_k: responses.pop(0))
    items = list(google_photos.list_picked_media_items("token", "s1"))
    assert [item["id"] for item in items] == ["1", "2", "3"]


def test_delete_picker_session_swallows_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failure to delete the picker session is only logged, not raised: it is not worth failing the inventory for"""

    def failing_delete(*_args: object, **_kwargs: object) -> None:
        raise requests.RequestException("gone")

    monkeypatch.setattr(google_photos.requests, "delete", failing_delete)
    google_photos.delete_picker_session("token", "s1")  # Must not raise


def test_fetch_bytes_returns_the_content(monkeypatch: pytest.MonkeyPatch) -> None:
    """fetch_bytes() returns the downloaded bytes on success"""
    monkeypatch.setattr(google_photos.requests, "get", lambda *_a, **_k: _mock_response(content=b"\xff\xd8"))
    assert google_photos.fetch_bytes("token", "https://example/base", "=d") == b"\xff\xd8"


def test_fetch_bytes_returns_none_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """fetch_bytes() returns None, instead of raising, when the download fails"""

    def failing_get(*_args: object, **_kwargs: object) -> None:
        raise requests.RequestException("boom")

    monkeypatch.setattr(google_photos.requests, "get", failing_get)
    assert google_photos.fetch_bytes("token", "https://example/base", "=d") is None


def test_fetch_size_reads_the_content_length_header(monkeypatch: pytest.MonkeyPatch) -> None:
    """fetch_size() returns the Content-Length header as an int, without reading the response body"""
    response = _mock_response(headers={"Content-Length": "12345"})
    monkeypatch.setattr(google_photos.requests, "get", lambda *_a, **_k: response)
    assert google_photos.fetch_size("token", "https://example/base") == 12345
    response.iter_content.assert_not_called()


def test_fetch_size_returns_none_when_the_header_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """fetch_size() returns None, rather than raising, when the server does not send a Content-Length header"""
    monkeypatch.setattr(google_photos.requests, "get", lambda *_a, **_k: _mock_response(headers={}))
    assert google_photos.fetch_size("token", "https://example/base") is None


def test_fetch_size_returns_none_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """fetch_size() returns None, instead of raising, when the request fails"""

    def failing_get(*_args: object, **_kwargs: object) -> None:
        raise requests.RequestException("boom")

    monkeypatch.setattr(google_photos.requests, "get", failing_get)
    assert google_photos.fetch_size("token", "https://example/base") is None
