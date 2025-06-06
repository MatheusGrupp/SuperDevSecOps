pipeline {
    agent any

    environment {
        IMAGE_NAME = "andrejacopetti/lojaroupa"
        TAG = "latest"
        DOCKERHUB_CREDENTIALS = credentials('DOCKERHUB_CREDENTIALS') 
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    sh """
                        docker build -t $IMAGE_NAME:$TAG projeto-roupa-infantil
                    """
                }
            }
        }

        stage('Login to DockerHub') {
            steps {
                script {
                    sh """
                        echo "$DOCKERHUB_CREDENTIALS_PSW" | docker login -u "$DOCKERHUB_CREDENTIALS_USR" --password-stdin
                    """
                }
            }
        }

        stage('Push Image') {
            steps {
                script {
                    sh """
                        docker push $IMAGE_NAME:$TAG
                    """
                }
            }
        }

        //  stage('Deploy (Docker Compose)') {
        //     steps {
        //         script {
        //             // Parar containers antigos
        //             sh """
        //                 docker compose -f projeto-roupa-infantil/docker-compose.yml down
        //             """

        //             // Substituir build local pelo pull da imagem (em produção real)
        //             // Aqui estamos usando a imagem que acabamos de publicar
        //             // Para isso, altere docker-compose.yml conforme abaixo
        //             sh """
        //                 docker compose -f projeto-roupa-infantil/docker-compose.yml up -d
        //             """
        //         }
        //     }
        // }
    }

    post {
        always {
            sh "docker logout"
        }
    }
}