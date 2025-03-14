#!/bin/bash
# scripts/deploy.sh

echo "Iniciando o deploy do AgentOS..."
docker-compose up --build -d
echo "Deploy concluído com sucesso!"
