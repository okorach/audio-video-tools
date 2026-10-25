#
# media-tools
# Copyright (C) 2019-2021 Olivier Korach
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

"""Tests of the project version that the CI pipelines pass to the sonar-scanner"""

import os
import re
import shutil
import subprocess
from pathlib import Path
import pytest
import yaml
from mediatools import version

ROOT = Path(__file__).parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "build.yml"
JENKINSFILE = ROOT / "Jenkinsfile"
PROJECT_VERSION_ARG = "-Dsonar.projectVersion="


def pyproject_version(text: str) -> str | None:
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return m.group(1) if m else None


def workflow_steps() -> list[dict]:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["scan"]["steps"]


def version_step() -> dict:
    return next(s for s in workflow_steps() if s.get("id") == "project-version")


def test_version_of_the_package_and_of_pyproject_are_the_same():
    assert pyproject_version((ROOT / "pyproject.toml").read_text(encoding="utf-8")) == version.MEDIA_TOOLS_VERSION


def test_workflow_passes_the_version_to_the_scanner():
    scan = next(s for s in workflow_steps() if "sonarqube-scan-action" in s.get("uses", ""))
    assert f"{PROJECT_VERSION_ARG}${{{{ steps.project-version.outputs.version }}}}" in scan["with"]["args"]


def test_workflow_does_not_patch_sonar_project_properties():
    """Appending the version to sonar-project.properties silently failed: the last line of the file is a comment without end of line"""
    assert "sonar-project.properties" not in "".join(s.get("run", "") for s in workflow_steps())


def test_sonar_project_properties_has_no_version():
    lines = (ROOT / "sonar-project.properties").read_text(encoding="utf-8").splitlines()
    assert not [line for line in lines if line.strip().startswith("sonar.projectVersion")]


def test_jenkins_passes_the_version_to_the_scanner():
    scanner_calls = [line for line in JENKINSFILE.read_text(encoding="utf-8").splitlines() if "bin/sonar-scanner" in line]
    assert len(scanner_calls) == 2
    assert all(f"{PROJECT_VERSION_ARG}${{projectVersion()}}" in line for line in scanner_calls)


# The script of the workflow that gets the version is run in a temporary folder


@pytest.fixture
def run_version_step(tmp_path):
    bash = shutil.which("bash")
    if bash is None or shutil.which("sed") is None:
        pytest.skip("bash and sed are required")

    def run(pyproject_content: str) -> tuple[int, str]:
        (tmp_path / "pyproject.toml").write_text(pyproject_content, encoding="utf-8", newline="")
        output = tmp_path / "github_output"
        output.write_text("", encoding="utf-8")
        result = subprocess.run(
            [bash, "-c", version_step()["run"]],
            cwd=tmp_path,
            env={"GITHUB_OUTPUT": str(output.as_posix()), "PATH": os.environ["PATH"]},
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode, output.read_text(encoding="utf-8").strip()

    return run


def test_version_step_extracts_the_version_of_pyproject(run_version_step):
    code, output = run_version_step('[project]\nname = "x"\nversion = "1.23.4"\n\n[tool.ruff]\ntarget-version = "py310"\n')
    assert code == 0
    assert output == "version=1.23.4"


def test_version_step_with_the_real_pyproject(run_version_step):
    code, output = run_version_step((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert code == 0
    assert output == f"version={version.MEDIA_TOOLS_VERSION}"


def test_version_step_with_windows_line_ends(run_version_step):
    code, output = run_version_step('[project]\r\nname = "x"\r\nversion = "2.0"\r\n')
    assert code == 0
    assert output == "version=2.0"


def test_version_step_fails_without_version(run_version_step):
    code, output = run_version_step('[project]\nname = "x"\n')
    assert code == 1
    assert output == ""
