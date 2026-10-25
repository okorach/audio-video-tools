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

"""Tests of ruff2sonar, the converter of the ruff report to the Sonar external issues format"""

import io
import json
import sys

import pytest

import ruff2sonar

REPORT = """\
mediatools/foo.py:10:5: B904 Within an `except` clause, raise exceptions with `raise ... from err`
   |
 9 |         except ValueError:
10 |             raise Exception("x")
   |             ^^^^^^^^^^^^^^^^^^^^ B904
   |
mediatools/bar.py:3:1: I001 [*] Import block is un-sorted or un-formatted
  |
3 | / import sys
4 | | import os
  | |_________^ I001
  |
mediatools/baz.py:7:9: RUF012 [*] Mutable class attributes should be annotated with `typing.ClassVar`
  |
7 |       x = []
8 | |
  | |____^ RUF012
"""


def run(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], report: str, *args: object) -> str:
    monkeypatch.setattr(sys, "argv", ["ruff2sonar.py", *args])
    monkeypatch.setattr(sys, "stdin", io.StringIO(report))
    ruff2sonar.main()
    return capsys.readouterr().out


def test_issues(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    result = json.loads(run(monkeypatch, capsys, REPORT))
    issues = result["issues"]
    assert [i["ruleId"] for i in issues] == ["B904", "I001", "RUF012"]
    assert [i["primaryLocation"]["filePath"] for i in issues] == ["mediatools/foo.py", "mediatools/bar.py", "mediatools/baz.py"]
    assert issues[0]["primaryLocation"]["message"] == "Within an `except` clause, raise exceptions with `raise ... from err`"
    assert all(i["engineId"] == "ruff" and i["effortMinutes"] == 5 for i in issues)


def test_inline_range_marker(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    text_range = json.loads(run(monkeypatch, capsys, REPORT))["issues"][0]["primaryLocation"]["textRange"]
    assert text_range["startLine"] == 10
    assert text_range["endLine"] == 10
    assert text_range["endColumn"] - text_range["startColumn"] == len("^" * 20)


def test_multi_line_range_of_the_imports(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """The range of the sorting of the imports covers whole lines, without columns"""
    text_range = json.loads(run(monkeypatch, capsys, REPORT))["issues"][1]["primaryLocation"]["textRange"]
    assert text_range["startLine"] == 3
    assert text_range["endLine"] == 3
    assert "startColumn" not in text_range
    assert "endColumn" not in text_range


def test_rules(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    rules = json.loads(run(monkeypatch, capsys, REPORT))["rules"]
    assert sorted(r["id"] for r in rules) == ["B904", "I001", "RUF012"]
    assert all(r["engineId"] == "ruff" and r["impacts"] == [{"softwareQuality": "MAINTAINABILITY", "severity": "MEDIUM"}] for r in rules)


def test_v1_format(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    result = json.loads(run(monkeypatch, capsys, REPORT, "v1"))
    assert "rules" not in result
    assert all(i["severity"] == "MAJOR" and i["type"] == "CODE_SMELL" for i in result["issues"])


def test_no_issue(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(monkeypatch, capsys, "All checks passed!\n") == ""


def test_range_marker_with_an_end_line() -> None:
    issue_range = {"startLine": 3, "endLine": 3, "startColumn": 0, "endColumn": 1}
    ruff2sonar.apply_range_marker(issue_range, "RUF012", 5, 2, 9)
    assert issue_range == {"startLine": 3, "endLine": 5, "startColumn": 2, "endColumn": 9}


def test_range_marker_of_the_imports() -> None:
    issue_range = {"startLine": 3, "endLine": 3, "startColumn": 0, "endColumn": 1}
    ruff2sonar.apply_range_marker(issue_range, "I001", 6, 2, 9)
    assert issue_range == {"startLine": 3, "endLine": 5}


@pytest.mark.parametrize("columns", [(None, None), (4, None), (None, 8)])
def test_range_marker_with_missing_columns(columns: tuple) -> None:
    issue_range = {"startLine": 3, "endLine": 3, "startColumn": 0, "endColumn": 1}
    ruff2sonar.apply_range_marker(issue_range, "B904", None, *columns)
    assert issue_range["endLine"] == 3
    assert issue_range["startColumn"] == (columns[0] if columns[0] is not None else 0)
    assert issue_range["endColumn"] == (columns[1] if columns[1] is not None else 1)
