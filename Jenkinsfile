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
                script {
                    env.GIT_SHA = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
                }
                sh '''
                    docker build \
                        -t ${IMAGE_NAME}:${IMAGE_TAG} \
                        -t ${IMAGE_NAME}:${GIT_SHA} \
                        -t ${IMAGE_NAME}:latest .
                '''
                // Record a build artefact (image tags, digest, size) for traceability.
                sh '''
                    {
                      echo "image: ${IMAGE_NAME}"
                      echo "build: ${IMAGE_TAG}"
                      echo "git_sha: ${GIT_SHA}"
                      echo "digest: $(docker image inspect ${IMAGE_NAME}:${IMAGE_TAG} --format '{{.Id}}')"
                      echo "size: $(docker image inspect ${IMAGE_NAME}:${IMAGE_TAG} --format '{{.Size}}') bytes"
                      echo "built: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
                    } > build-info.txt
                    cat build-info.txt
                '''
                archiveArtifacts artifacts: 'build-info.txt', fingerprint: true
            }
        }

        stage('Test') {
            steps {
                // Run inside the image we just built (deps already installed), adding
                // pytest. --volumes-from shares Jenkins' workspace with the sibling
                // container (bind mounts don't work under Docker-out-of-Docker).
                sh '''
                    docker run --rm --volumes-from jenkins -w "${WORKSPACE}" \
                        ${IMAGE_NAME}:${IMAGE_TAG} \
                        sh -c "pip install --quiet pytest && ruff check . && pytest -q --junitxml=test-results.xml"
                '''
            }
            post {
                always {
                    junit 'test-results.xml'
                }
            }
        }

        stage('Code Quality') {
            steps {
                // Scanner runs on sonar-net (reaches the SonarQube server by name) and
                // shares Jenkins' workspace. qualitygate.wait fails the build if the gate fails.
                withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
                    sh '''
                        docker run --rm --network sonar-net --volumes-from jenkins -w "${WORKSPACE}" \
                            sonarsource/sonar-scanner-cli \
                            -Dsonar.projectBaseDir=${WORKSPACE} \
                            -Dsonar.host.url=http://sonarqube:9000 \
                            -Dsonar.login=${SONAR_TOKEN} \
                            -Dsonar.qualitygate.wait=true
                    '''
                }
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
