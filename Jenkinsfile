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
                sh 'mkdir -p security-reports'
                // bandit (SAST, report-only) + pip-audit. pip-audit GATES the build on our
                // own application dependencies (requirements.txt) — the vulns we control.
                sh '''
                    docker run --rm --volumes-from jenkins -w "${WORKSPACE}" ${IMAGE_NAME}:${IMAGE_TAG} sh -c '
                        pip install --quiet bandit pip-audit &&
                        bandit -r . -x ./venv,./tests,./Ontrack -ll -f txt -o security-reports/bandit.txt || true;
                        pip-audit -r requirements.txt > security-reports/pip-audit.txt 2>&1; rc=$?;
                        echo "--- pip-audit ---"; cat security-reports/pip-audit.txt;
                        [ $rc -eq 0 ]
                    '
                '''
                // Full image scan (Trivy): reported + archived (base-image posture). Base-image
                // and setuptools-vendored CVEs are outside our control and handled by mitigation
                // (.trivyignore + SECURITY-FINDINGS.md), so this scan is non-gating to keep the
                // pipeline stable against daily vuln-DB churn. --volumes-from exposes .trivyignore.
                sh '''
                    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache/ \
                        --volumes-from jenkins \
                        aquasec/trivy image --severity HIGH,CRITICAL --ignore-unfixed --no-progress \
                        --ignorefile "${WORKSPACE}/.trivyignore" \
                        ${IMAGE_NAME}:${IMAGE_TAG} | tee security-reports/trivy.txt
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'security-reports/**', allowEmptyArchive: true
                }
            }
        }

        stage('Deploy') {
            steps {
                // Deploy the built image to a staging stack (web + Postgres) via compose,
                // then gate on a health check hit from inside the compose network.
                sh '''
                    docker compose -p ontracker-staging -f docker-compose.staging.yml up -d --force-recreate
                    echo "Waiting for staging health..."
                    ok=0
                    for i in $(seq 1 30); do
                        code=$(docker run --rm --network ontracker-staging_default curlimages/curl:latest \
                            -s -o /dev/null -w "%{http_code}" http://web:8000/api/version 2>/dev/null || true)
                        if [ "$code" = "200" ]; then echo "Staging healthy ($code)"; ok=1; break; fi
                        echo "waiting ($code)..."; sleep 3
                    done
                    [ "$ok" = "1" ]
                '''
            }
        }

        stage('Release') {
            steps {
                // Promote the tested image to versioned + stable tags, then run it as a
                // separate production instance with production config (env promotion).
                sh '''
                    RELEASE_VERSION="1.13.${BUILD_NUMBER}"
                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:v${RELEASE_VERSION}
                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:stable

                    docker rm -f ontracker-prod 2>/dev/null || true
                    docker run -d --name ontracker-prod -p 8100:8000 \
                        -e SECRET_KEY=prod-not-secret -e ENVIRONMENT=production \
                        -e RESEND_DRY_RUN=true -e PORT=8000 ${IMAGE_NAME}:stable

                    ok=0
                    for i in $(seq 1 20); do
                        code=$(docker run --rm --network container:ontracker-prod curlimages/curl:latest \
                            -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/version 2>/dev/null || true)
                        if [ "$code" = "200" ]; then echo "Production healthy ($code) — v${RELEASE_VERSION}"; ok=1; break; fi
                        echo "waiting ($code)..."; sleep 3
                    done
                    [ "$ok" = "1" ]

                    { echo "release: v${RELEASE_VERSION}";
                      echo "image: ${IMAGE_NAME}:stable (also ${IMAGE_NAME}:v${RELEASE_VERSION})";
                      echo "git_sha: ${GIT_SHA}";
                      echo "released: $(date -u +%Y-%m-%dT%H:%M:%SZ)"; } > release-info.txt
                    cat release-info.txt
                '''
                archiveArtifacts artifacts: 'release-info.txt', fingerprint: true
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
