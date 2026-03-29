#!/usr/bin/env python3
#
# media-tools
# Copyright (C) 2019-2024 Olivier Korach
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
"""Converts ruff --output-format=concise output to SonarQube generic external issues JSON format.

See https://docs.sonarsource.com/sonarqube-cloud/analyzing-source-code/importing-external-issues/generic-issue-data
"""

import sys
import json
import re

TOOLNAME = "ruff"

# Ruff concise line pattern: path:line:col: RULE_ID message  (optionally " [*]" fixable marker)
_ISSUE_RE = re.compile(r"^([^:]+):(\d+):(\d+): ([A-Z0-9]+)(?: \[\*\])? (.+)$")


def main() -> None:
    """Read ruff concise output from stdin and write SonarQube external issues JSON to stdout."""
    rules_dict: dict = {}
    issue_list: list = []
    current_issue: dict | None = None

    for line in sys.stdin.read().splitlines():
        m = _ISSUE_RE.match(line)
        if not m:
            continue
        # Flush the previous issue before starting a new one
        if current_issue is not None:
            issue_list.append(current_issue)

        file_path = m.group(1).replace("\\", "/")
        start_line = int(m.group(2))
        start_col = int(m.group(3)) - 1  # ruff is 1-based, Sonar expects 0-based
        rule_id = m.group(4)
        message = m.group(5)

        current_issue = {
            "ruleId": rule_id,
            "effortMinutes": 5,
            "primaryLocation": {
                "message": message,
                "filePath": file_path,
                "textRange": {
                    "startLine": start_line,
                    "endLine": start_line,
                    "startColumn": start_col,
                    "endColumn": start_col + 1,
                },
            },
        }

        # Keep one rule definition per rule_id (deduplicated by overwrite)
        rules_dict[rule_id] = {
            "id": rule_id,
            "name": rule_id,
            "description": message,
            "engineId": TOOLNAME,
            "cleanCodeAttribute": "LOGICAL",
            "impacts": [{"softwareQuality": "MAINTAINABILITY", "severity": "MEDIUM"}],
        }

    # Flush the last issue
    if current_issue is not None:
        issue_list.append(current_issue)

    print(json.dumps({"rules": list(rules_dict.values()), "issues": issue_list}, indent=2))


if __name__ == "__main__":
    main()
