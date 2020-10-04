pipeline {
  agent any
  stages {
    stage('SCM') {
      git 'https://github.com/okorach/audio-video-tools.git'
    }
    stage('SonarQube LTS analysis') {
      def scannerHome = tool 'SonarScanner';
      withSonarQubeEnv('SQ LTS') { // If you have configured more than one global server connection, you can specify its name
        sh "${scannerHome}/bin/sonar-scanner"
      }
    }
    stage("SonarQube LTS Quality Gate"){
      timeout(time: 1, unit: 'HOURS') { // Just in case something goes wrong, pipeline will be killed after a timeout
        def qg = waitForQualityGate() // Reuse taskId previously collected by withSonarQubeEnv
        if (qg.status != 'OK') {
          echo "Quality gate failed: ${qg.status}, proceeding anyway"
        }
      }
    }
    stage('SonarQube LATEST analysis') {
      def scannerHome = tool 'SonarScanner';
      withSonarQubeEnv('SQ Latest') { // If you have configured more than one global server connection, you can specify its name
        sh "${scannerHome}/bin/sonar-scanner"
      }
    }
    stage("SonarQube LATEST Quality Gate"){
      timeout(time: 1, unit: 'HOURS') { // Just in case something goes wrong, pipeline will be killed after a timeout
        def qg = waitForQualityGate() // Reuse taskId previously collected by withSonarQubeEnv
        if (qg.status != 'OK') {
          echo "Quality gate failed: ${qg.status}, proceeding anyway"
        }
      }
    }
  }
}