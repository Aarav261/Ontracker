// Ontracker CI/CD pipeline (SIT223/SIT753 7.3HD)
// Scaffold: all 7 stages present as stubs. Each stage is filled in one at a time.
pipeline {
    agent any

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 30, unit: 'MINUTES')
    }

    environment {
        IMAGE_NAME = 'ontracker'
        IMAGE_TAG  = "${env.BUILD_NUMBER}"
    }

    stages {
        stage('Build') {
            steps {
                echo "TODO: docker build -> ${IMAGE_NAME}:${IMAGE_TAG}"
            }
        }

        stage('Test') {
            steps {
                echo 'TODO: ruff check + pytest --junitxml'
            }
        }

        stage('Code Quality') {
            steps {
                echo 'TODO: SonarQube scan + quality gate'
            }
        }

        stage('Security') {
            steps {
                echo 'TODO: bandit + pip-audit + trivy image scan'
            }
        }

        stage('Deploy') {
            steps {
                echo 'TODO: docker compose up -d (staging) + health check'
            }
        }

        stage('Release') {
            steps {
                echo 'TODO: git tag + push image to GHCR'
            }
        }

        stage('Monitoring') {
            steps {
                echo 'TODO: Prometheus + Grafana + alert; Sentry already live'
            }
        }
    }

    post {
        success { echo 'Pipeline succeeded.' }
        failure { echo 'Pipeline failed.' }
        always  { echo "Build #${env.BUILD_NUMBER} finished." }
    }
}
