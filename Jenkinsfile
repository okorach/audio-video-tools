pipeline {
  agent any
  stages {
    stage('Build') {
      steps {
        withSonarQubeEnv('SQ Latest') {
          withMaven(maven: 'Maven') {
            script {
              //sh "printenv"
              // fetch master from origin so sonar scanner comparison works
              sh "git fetch --no-tags ${GIT_URL} +refs/heads/master:refs/remotes/origin/master"
              if (env.CHANGE_ID) {
                // build like a pull request
                sh "mvn -Dmaven.test.failure.ignore clean verify sonar:sonar -Dsonar.pullrequest.branch=${CHANGE_BRANCH} -Dsonar.pullrequest.key=${CHANGE_ID} -Dsonar.pullrequest.base=master"
              } else if (env.BRANCH_NAME=="master") {
                sh "mvn -Dmaven.test.failure.ignore clean verify sonar:sonar"
              } else {
                // build like a branch
                sh "mvn -Dmaven.test.failure.ignore clean verify sonar:sonar -Dsonar.branch.name=${BRANCH_NAME}"
              }
            }
          }
        }
      }
    }
  }
}