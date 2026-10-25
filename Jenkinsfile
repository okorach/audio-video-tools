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