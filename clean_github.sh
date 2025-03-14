#!/bin/bash

# Script para limpar o repositório GitHub e enviar os novos arquivos
# Este script remove todos os arquivos antigos e adiciona os novos

echo "=== Script de Limpeza e Atualização do GitHub para AgentOS ==="
echo "Este script irá remover todos os arquivos antigos do repositório e adicionar os novos."
echo ""

# Configura cores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Diretório do projeto
PROJECT_DIR="/Users/Amarilho/AgentOS"
cd "$PROJECT_DIR"

# Verifica o estado atual do Git
echo -e "${YELLOW}Verificando configuração atual do Git...${NC}"
echo "Remote Git: $(git remote -v | head -n 1)"
echo "Branch atual: $(git branch --show-current)"
echo ""

# Confirma com o usuário
echo -e "${RED}ATENÇÃO: Este script irá remover TODOS os arquivos do repositório GitHub e enviar os novos.${NC}"
echo -e "${RED}Esta operação não pode ser desfeita facilmente.${NC}"
echo -e "${YELLOW}Deseja continuar? (s/n)${NC}"
read -p "> " CONTINUE

if [ "$CONTINUE" != "s" ]; then
    echo -e "${YELLOW}Operação cancelada pelo usuário.${NC}"
    exit 0
fi

# Cria um branch temporário
echo -e "${YELLOW}Criando branch temporário...${NC}"
git checkout --orphan temp_branch
echo -e "${GREEN}Branch temporário criado!${NC}"

# Adiciona todos os arquivos
echo -e "${YELLOW}Adicionando todos os arquivos...${NC}"
git add .

# Commit
echo -e "${YELLOW}Criando commit...${NC}"
git commit -m "Reorganização completa para arquitetura de microserviços"
echo -e "${GREEN}Commit criado!${NC}"

# Deleta a branch main
echo -e "${YELLOW}Deletando branch main...${NC}"
git branch -D main
echo -e "${GREEN}Branch main deletada!${NC}"

# Renomeia a branch temporária para main
echo -e "${YELLOW}Renomeando branch temporária para main...${NC}"
git branch -m main
echo -e "${GREEN}Branch renomeada para main!${NC}"

# Force push
echo -e "${YELLOW}Enviando para o GitHub com force push...${NC}"
echo -e "${RED}ATENÇÃO: Esta operação irá sobrescrever completamente o repositório remoto.${NC}"
echo -e "${YELLOW}Deseja continuar? (s/n)${NC}"
read -p "> " CONTINUE_PUSH

if [ "$CONTINUE_PUSH" != "s" ]; then
    echo -e "${YELLOW}Push cancelado pelo usuário.${NC}"
    exit 0
fi

git push -f origin main
echo -e "${GREEN}Push realizado com sucesso!${NC}"

echo ""
echo -e "${GREEN}Repositório GitHub limpo e atualizado com sucesso!${NC}"
echo "Acesse https://github.com/danvoulez/AgentOS para verificar as mudanças."
