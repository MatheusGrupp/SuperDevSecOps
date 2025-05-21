pipeline {
    agent any

    environment {
        DOCKER_REPO = 'k1cornelsenp/projeto-ecommerce'
        DOCKER_IMAGE_APP = "${DOCKER_REPO}:latest"
        DOCKER_IMAGE_DB = "k1cornelsenp/projeto-ecommerce-db:latest"
        K8S_DIR = 'k8s/'
        SQL_DIR = 'sql/'
        SNYK_TOKEN = credentials('SNYK_AUTH')
        DOCKER_HUB = credentials('DOCKER_HUB')
    }

    stages {
        stage('Clone Repository') {
            steps {
                git url: 'https://github.com/k1cornelsen/projeto-ecommerce.git'
            }
        }

        stage('Snyk Docker Image Scan - App') {
            steps {
                sh '''
                    snyk auth --auth-type=token ${SNYK_TOKEN}
                    snyk container test ${DOCKER_IMAGE_APP} --severity-threshold=medium --file=/var/www/html/projeto-ecommerce/Dockerfile --exclude-base-image-vulns
                '''
            }
        }

        stage('Snyk Docker Image Scan - Database') {
            steps {
                sh """
                    snyk container test ${DOCKER_IMAGE_DB} --severity-threshold=medium --file=/var/www/html/projeto-ecommerce/sql/Dockerfile --exclude-base-image-vulns
                """
            }
        }

        stage('Build Docker Image - Database') {
            steps {
                dir(SQL_DIR) {
                    sh "docker build --no-cache -t ${DOCKER_IMAGE_DB} ."
                }
            }
        }

        stage('Push Docker Image - Database') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'DOCKER_HUB', usernameVariable: 'DOCKER_HUB_USR', passwordVariable: 'DOCKER_HUB_PSW')]) {
                    sh '''
                        echo $DOCKER_HUB_PSW | docker login -u $DOCKER_HUB_USR --password-stdin
                        docker push ${DOCKER_IMAGE_DB}
                    '''
                }
            }
        }

        stage('Build Docker Image - App') {
            steps {
                sh "docker build --no-cache -t ${DOCKER_IMAGE_APP} -f Dockerfile ."
            }
        }

        stage('Push Docker Image - App') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'DOCKER_HUB', usernameVariable: 'DOCKER_HUB_USR', passwordVariable: 'DOCKER_HUB_PSW')]) {
                    sh '''
                        echo $DOCKER_HUB_PSW | docker login -u $DOCKER_HUB_USR --password-stdin
                        docker push ${DOCKER_IMAGE_APP}
                    '''
                }
            }
        }
        stage('Deploy to Kubernetes') {
            steps {
                withCredentials([file(credentialsId: 'KUBE_CONFIG', variable: 'KUBECONFIG')]) {
                    sh '''
                        microk8s kubectl apply -f ${K8S_DIR}/banco-pv.yaml
                        microk8s kubectl apply -f ${K8S_DIR}/create-db.yaml
                        microk8s kubectl apply -f ${K8S_DIR}/deploy-banco.yaml
                        microk8s kubectl apply -f ${K8S_DIR}/deploy-svc-banco.yaml
                        microk8s kubectl apply -f ${K8S_DIR}/deploy.yaml
                        microk8s kubectl apply -f ${K8S_DIR}/deploy-svc.yaml
                    '''
                }
            }
        }
    }

    post {
        success {
            echo 'Deploy realizado com sucesso!'
        }
        failure {
            echo 'A pipeline falhou!'
        }
    }
}

