pipeline {
   agent any

   environment {
       IMAGE_NAME = "andrejacopetti/lojaroupa"
       TAG = "latest"
       DOCKERHUB_CREDENTIALS = credentials('DOCKERHUB_CREDENTIALS') // você cria isso no Jenkins
   }

   stages {
       stage('Checkout') {
           steps {
               checkout scm
           }
       }

       stage('SAST') {
           steps {
               script {
                   sh """
                       # Análise estática com SonarQube
                       sonar-scanner \
                         -Dsonar.projectKey=lojaroupa \
                         -Dsonar.sources=projeto-roupa-infantil
                   """
               }
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

       stage('DAST') {
           steps {
               script {
                   sh """
                       # Iniciar container para teste
                       docker run -d --name lojaroupa-test -p 8080:80 $IMAGE_NAME:$TAG
                       sleep 10

                       # OWASP ZAP scan
                       docker run --rm --network host \
                         owasp/zap2docker-stable \
                         zap-baseline.py -t http://localhost:8080

                       # Parar container de teste
                       docker stop lojaroupa-test
                       docker rm lojaroupa-test
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