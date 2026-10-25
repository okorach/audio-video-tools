//
// media-tools
// Copyright (C) 2019-2026 Olivier Korach
// mailto:olivier.korach AT gmail DOT com
//
// This program is free software; you can redistribute it and/or
// modify it under the terms of the GNU Lesser General Public
// License as published by the Free Software Foundation; either
// version 3 of the License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
// Lesser General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public License
// along with this program; if not, write to the Free Software Foundation,
// Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
//

// The version of the project is the one of pyproject.toml
def projectVersion() {
  return sh(returnStdout: true, script: '''grep -m1 '^version' pyproject.toml | sed -E 's/^version *= *"([^"]+)".*/\\1/' | tr -d '\\r\\n' ''').trim()
}

pipeline {
  agent any
  stages {
    stage('SonarQube LTS analysis') {
      steps {
          withSonarQubeEnv('SQ LTS') {
            script {
              def scannerHome = tool 'SonarScanner';
              sh "${scannerHome}/bin/sonar-scanner -Dsonar.projectVersion=${projectVersion()}"
            }
          }
      }
    }
    stage("SonarQube LTS Quality Gate") {
      steps {
          timeout(time: 5, unit: 'MINUTES') {
            script {
              def qg = waitForQualityGate() // Reuse taskId previously collected by withSonarQubeEnv
              if (qg.status != 'OK') {
                echo "Quality gate failed: ${qg.status}, proceeding anyway"
              }
            }
          }
      }
    }
    stage('SonarQube LATEST analysis') {
      steps {
          withSonarQubeEnv('SQ Latest') {
            script {
              def scannerHome = tool 'SonarScanner';
              sh "${scannerHome}/bin/sonar-scanner -Dsonar.projectVersion=${projectVersion()}"
            }
          }
      }
    }
    stage("SonarQube LATEST Quality Gate") {
      steps {
          timeout(time: 5, unit: 'MINUTES') {
            script {
              def qg = waitForQualityGate()
              if (qg.status != 'OK') {
                echo "Quality gate failed: ${qg.status}, proceeding anyway"
              }
            }
          }
      }
    }
  }
}