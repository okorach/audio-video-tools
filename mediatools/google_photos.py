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

"""OAuth2 authentication against Google, and access to the Google Photos Picker API, used by image_inventory's
--google option to inventory the photos of a Google Photos library instead of local files. The classic Photos
Library API (mediaItems.list/search) is restricted by Google, since 2025, to the media a third-party app itself
uploaded: it can no longer list an existing library. The Picker API is used instead: it lets the user pick, through
a Google-hosted browser page, the photos and/or albums of their own library to inventory (see
https://developers.google.com/photos/picker/guides/get-started)"""

from __future__ import annotations

import http.server
import json
import os
import sys
import threading
import time
import urllib.parse
import webbrowser
from typing import TYPE_CHECKING

import requests

import mediatools.utilities as util
from mediatools import log

if TYPE_CHECKING:
    from collections.abc import Iterator

AUTH_URL: str = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL: str = "https://oauth2.googleapis.com/token"  # noqa: S105 (a public endpoint URL, not a secret)
PICKER_API: str = "https://photospicker.googleapis.com/v1"
SCOPE: str = "https://www.googleapis.com/auth/photospicker.mediaitems.readonly"
PAGE_SIZE: int = 100
REQUEST_TIMEOUT: int = 60  # Seconds given to a single Google API call before giving up
DEFAULT_POLL_INTERVAL: float = 5.0  # Seconds between 2 polls of the picker session, used until it gives its own pollingConfig
SESSION_TIMEOUT: float = 1800.0  # Seconds given to the user to pick photos/albums in the browser before giving up


def _credentials_file() -> str:
    """Returns the path of the Google OAuth2 client credentials file (the one downloaded from the Google Cloud
    console for a Desktop app OAuth client with the Photos Picker API enabled), google.credentials_file property,
    defaulting to ~/.mediatools-google-credentials.json since a new property is not in the user's properties file"""
    return str(util.get_media_properties().get("google.credentials_file") or os.path.expanduser("~/.mediatools-google-credentials.json"))


def _token_file() -> str:
    """Returns the path where the OAuth2 tokens obtained from the user are cached, so the browser consent is only
    needed once, google.token_file property, defaulting to ~/.mediatools-google-token.json"""
    return str(util.get_media_properties().get("google.token_file") or os.path.expanduser("~/.mediatools-google-token.json"))


def _load_client_config() -> dict[str, str]:
    """Returns the {client_id, client_secret} of the OAuth2 client read from _credentials_file(), in the standard
    format the Google Cloud console generates for a Desktop app OAuth client
    ({"installed": {"client_id": ..., "client_secret": ...}}). Exits with code 1 if the file is missing or malformed"""
    path = _credentials_file()
    if not os.path.isfile(path):
        log.logger.error(
            "Google OAuth2 credentials file %s not found: create a Desktop app OAuth client in the Google Cloud "
            "console (with the Photos Picker API enabled) and download its credentials to that file, "
            "see docs/imagetool-inventory.md",
            path,
        )
        sys.exit(1)
    with open(path, encoding="utf-8") as fh:
        config = json.load(fh)
    client = config.get("installed") or config.get("web") or {}
    try:
        return {"client_id": client["client_id"], "client_secret": client["client_secret"]}
    except KeyError:
        log.logger.error("%s does not look like a Google OAuth2 Desktop app credentials file", path)
        sys.exit(1)


def _load_cached_token() -> dict[str, object] | None:
    """Returns the OAuth2 token cached in _token_file(), None if there is none yet"""
    path = _token_file()
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _save_token(token: dict[str, object]) -> None:
    """Caches the OAuth2 token to _token_file(), so the browser consent is only needed once"""
    with open(_token_file(), "w", encoding="utf-8") as fh:
        json.dump(token, fh)


class _RedirectHandler(http.server.BaseHTTPRequestHandler):
    """Catches the single OAuth2 redirect of _run_consent_flow(), storing the authorization code (or the error) it
    carries as a class attribute, since a new instance is created by http.server for each request"""

    code: str | None = None
    error: str | None = None

    def do_GET(self) -> None:
        """Stores the authorization code (or error) from the query string of the OAuth2 redirect, and tells the user
        to close the tab, since it's not meant to be a web page they stick around on"""
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _RedirectHandler.code = query.get("code", [None])[0]
        _RedirectHandler.error = query.get("error", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body>Authentication complete, you can close this tab.</body></html>")

    def log_message(self, *args: object) -> None:
        """Silences BaseHTTPRequestHandler's default per-request logging to stderr"""


def _run_consent_flow(client_id: str, client_secret: str) -> dict[str, object]:
    """Runs the interactive OAuth2 consent flow: opens the user's browser on Google's consent page, catches the
    redirect it sends back to a one-shot local HTTP server, and exchanges the authorization code it carries for an
    access and a refresh token. Exits with code 1 if the user denies consent or no redirect arrives within
    SESSION_TIMEOUT"""
    server = http.server.HTTPServer(("127.0.0.1", 0), _RedirectHandler)
    _RedirectHandler.code, _RedirectHandler.error = None, None
    redirect_uri = f"http://127.0.0.1:{server.server_port}"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    log.logger.info("Opening a browser to let you select the Google account and consent: %s", auth_url)
    webbrowser.open(auth_url)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    thread.join(SESSION_TIMEOUT)
    server.server_close()
    if _RedirectHandler.error:
        log.logger.error("Google OAuth2 consent was denied: %s", _RedirectHandler.error)
        sys.exit(1)
    if not _RedirectHandler.code:
        log.logger.error("No response received from the Google OAuth2 consent page within %d seconds", SESSION_TIMEOUT)
        sys.exit(1)
    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": _RedirectHandler.code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def _refresh_access_token(token: dict[str, object], client_id: str, client_secret: str) -> dict[str, object]:
    """Returns a fresh token obtained from the refresh_token of an expired/missing one, keeping that refresh_token
    (Google does not resend it on a refresh)"""
    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": token["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    refreshed = response.json()
    refreshed.setdefault("refresh_token", token["refresh_token"])
    return refreshed


def get_access_token() -> str:
    """Returns a valid OAuth2 access token for the Google Photos Picker API scope, running the interactive browser
    consent flow the first time, and silently refreshing the cached token (see _token_file()) on every later call"""
    client = _load_client_config()
    token = _load_cached_token()
    if token and "refresh_token" in token:
        try:
            token = _refresh_access_token(token, client["client_id"], client["client_secret"])
        except requests.RequestException as e:
            log.logger.warning("Could not refresh the cached Google token (%s), asking for consent again", e)
            token = None
    if not token:
        token = _run_consent_flow(client["client_id"], client["client_secret"])
    _save_token(token)
    return str(token["access_token"])


def _auth_header(access_token: str) -> dict[str, str]:
    """Returns the Authorization header carrying access_token, required on every Google Photos Picker API call"""
    return {"Authorization": f"Bearer {access_token}"}


def create_picker_session(access_token: str) -> dict[str, object]:
    """Creates a new Google Photos picker session, returns it as given by the API ({id, pickerUri, pollingConfig,
    expireTime...}), used to let the user pick, in their browser, the photos/albums to inventory"""
    response = requests.post(f"{PICKER_API}/sessions", headers=_auth_header(access_token), timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _poll_interval(session: dict[str, object]) -> float:
    """Returns the poll interval (in seconds) a picker session asks to be polled at (its pollingConfig.pollInterval,
    a string like '5s'), DEFAULT_POLL_INTERVAL if the session does not give one"""
    raw = str(session.get("pollingConfig", {}).get("pollInterval") or "").rstrip("s")
    try:
        return float(raw)
    except ValueError:
        return DEFAULT_POLL_INTERVAL


def wait_for_selection(access_token: str, session: dict[str, object]) -> dict[str, object]:
    """Prints the pickerUri of session and opens it in the browser, then blocks, polling the session at its own
    pollingConfig.pollInterval, until the user has finished picking photos/albums (mediaItemsSet becomes true), or
    SESSION_TIMEOUT is reached first. Returns the final, polled session. Exits with code 1 on a timeout"""
    print(f"Open this page and select the photos/albums to inventory, then click Done: {session['pickerUri']}")
    webbrowser.open(session["pickerUri"])
    session_id = session["id"]
    deadline = time.monotonic() + SESSION_TIMEOUT
    while time.monotonic() < deadline:
        time.sleep(_poll_interval(session))
        response = requests.get(f"{PICKER_API}/sessions/{session_id}", headers=_auth_header(access_token), timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        session = response.json()
        if session.get("mediaItemsSet"):
            return session
    log.logger.error("Timed out waiting for the photos/albums to be selected in the Google Photos picker")
    sys.exit(1)


def list_picked_media_items(access_token: str, session_id: str) -> Iterator[dict[str, object]]:
    """Yields the media items (photos) picked in session_id, as returned by the Google Photos Picker API, following
    its pagination (PAGE_SIZE items at a time)"""
    page_token = None
    while True:
        params = {"sessionId": session_id, "pageSize": PAGE_SIZE}
        if page_token:
            params["pageToken"] = page_token
        response = requests.get(f"{PICKER_API}/mediaItems", headers=_auth_header(access_token), params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        page = response.json()
        yield from page.get("mediaItems", [])
        page_token = page.get("nextPageToken")
        if not page_token:
            return


def delete_picker_session(access_token: str, session_id: str) -> None:
    """Deletes a picker session once its media items have been read, best effort: the session expires on its own
    anyway, so a failure here is only logged, not worth interrupting the inventory for"""
    try:
        requests.delete(f"{PICKER_API}/sessions/{session_id}", headers=_auth_header(access_token), timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        log.logger.debug("Could not delete the Google Photos picker session %s: %s", session_id, e)


def fetch_bytes(access_token: str, base_url: str, params: str) -> bytes | None:
    """Returns the bytes of base_url (a picked media item's mediaFile.baseUrl) with the given download/resize params
    appended (eg '=d' for the original file, '=w17-h16' for a thumbnail sized for compute_fingerprint_from_bytes()),
    None if the download fails"""
    try:
        response = requests.get(f"{base_url}{params}", headers=_auth_header(access_token), timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        log.logger.warning("Could not download %s%s: %s", base_url, params, e)
        return None


def fetch_size(access_token: str, base_url: str) -> int | None:
    """Returns the size in bytes of the original file behind base_url, read from the Content-Length header of a
    streamed request whose body is never read (so the file itself is not downloaded just to size it), None if it
    can't be determined"""
    try:
        with requests.get(f"{base_url}=d", headers=_auth_header(access_token), stream=True, timeout=REQUEST_TIMEOUT) as response:
            response.raise_for_status()
            length = response.headers.get("Content-Length")
            return int(length) if length is not None else None
    except requests.RequestException as e:
        log.logger.warning("Could not read the size of %s: %s", base_url, e)
        return None
