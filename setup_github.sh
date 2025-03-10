#!/bin/bash

# Script para configurar e publicar código no GitHub
# Criado em: $(date)

echo "=== Script de Configuração do GitHub para AgentOS ==="
echo "Este script tentará várias abordagens para publicar seu código no GitHub"
echo ""

# Configura cores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Diretório do projeto
PROJECT_DIR="/Users/voulezvous/CascadeProjects/AgentOS"
cd "$PROJECT_DIR"

# Verifica o estado atual do Git
echo -e "${YELLOW}Verificando configuração atual do Git...${NC}"
echo "Nome de usuário Git: $(git config --global user.name)"
echo "Email Git: $(git config --global user.email)"
echo "Remote Git: $(git remote -v | head -n 1)"
echo "Branch atual: $(git branch --show-current)"
echo ""

# Solicita informações do GitHub
echo -e "${YELLOW}Por favor, insira as informações do seu GitHub:${NC}"
read -p "Nome de usuário GitHub: " GITHUB_USERNAME
read -p "Email GitHub: " GITHUB_EMAIL

# Atualiza configuração do Git
echo -e "${YELLOW}Atualizando configuração global do Git...${NC}"
git config --global user.name "$GITHUB_USERNAME"
git config --global user.email "$GITHUB_EMAIL"
echo -e "${GREEN}Configuração do Git atualizada!${NC}"
echo ""

# Verifica se o repositório já existe no GitHub
echo -e "${YELLOW}Você já criou o repositório '$GITHUB_USERNAME/AgentOS' no GitHub? (s/n)${NC}"
read -p "> " REPO_EXISTS

if [ "$REPO_EXISTS" != "s" ]; then
    echo -e "${YELLOW}Por favor, crie o repositório no GitHub antes de continuar:${NC}"
    echo "1. Acesse https://github.com/new"
    echo "2. Nome do repositório: AgentOS"
    echo "3. Descrição (opcional): AI-driven operating system for enterprise management"
    echo "4. Escolha se o repositório será público ou privado"
    echo "5. NÃO inicialize com README, gitignore ou licença"
    echo "6. Clique em 'Create repository'"
    echo ""
    read -p "Pressione ENTER quando tiver criado o repositório... " CONTINUE
fi

# Configura o repositório remoto
echo -e "${YELLOW}Configurando o repositório remoto...${NC}"
git remote set-url origin "https://github.com/$GITHUB_USERNAME/AgentOS.git"
echo -e "${GREEN}Remote atualizado para: https://github.com/$GITHUB_USERNAME/AgentOS.git${NC}"
echo ""

# Tenta autenticação com Personal Access Token
echo -e "${YELLOW}Tentando publicar com Personal Access Token...${NC}"
echo "Para criar um token, acesse: https://github.com/settings/tokens"
echo "Escolha 'Generate new token (classic)'"
echo "Marque o escopo 'repo' e crie o token"
echo ""
read -p "Cole seu Personal Access Token: " GITHUB_TOKEN
echo ""

# Configurando credential helper para macOS
git config --global credential.helper osxkeychain

# Configura token no URL (temporariamente para o push)
REMOTE_URL_WITH_TOKEN="https://$GITHUB_USERNAME:$GITHUB_TOKEN@github.com/$GITHUB_USERNAME/AgentOS.git"
git remote set-url origin "$REMOTE_URL_WITH_TOKEN"

echo -e "${YELLOW}Tentando push com token...${NC}"
if git push -u origin main; then
    echo -e "${GREEN}Push realizado com sucesso usando token!${NC}"
    # Restaura URL sem o token para evitar expor o token no remote
    git remote set-url origin "https://github.com/$GITHUB_USERNAME/AgentOS.git"
    exit 0
else
    echo -e "${RED}Falha no push com token.${NC}"
    # Restaura URL sem o token
    git remote set-url origin "https://github.com/$GITHUB_USERNAME/AgentOS.git"
fi

# Tenta configuração SSH como alternativa
echo -e "${YELLOW}Tentando configurar SSH como alternativa...${NC}"

# Verifica se já existe uma chave SSH
if [ -f ~/.ssh/id_ed25519 ]; then
    echo "Chave SSH já existe."
    echo "Chave pública:"
    cat ~/.ssh/id_ed25519.pub
else
    echo "Gerando nova chave SSH..."
    ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -C "$GITHUB_EMAIL" -N ""
    echo -e "${GREEN}Chave SSH gerada!${NC}"
    echo "Chave pública:"
    cat ~/.ssh/id_ed25519.pub
fi

echo ""
echo "Adicione esta chave pública às suas chaves SSH no GitHub:"
echo "1. Acesse https://github.com/settings/keys"
echo "2. Clique em 'New SSH key'"
echo "3. Título: AgentOS MacOS"
echo "4. Cole a chave pública acima"
echo "5. Clique em 'Add SSH key'"
echo ""
read -p "Pressione ENTER quando tiver adicionado a chave... " CONTINUE

# Configura remote para usar SSH
echo -e "${YELLOW}Configurando remote para usar SSH...${NC}"
git remote set-url origin "git@github.com:$GITHUB_USERNAME/AgentOS.git"
echo -e "${GREEN}Remote atualizado para: git@github.com:$GITHUB_USERNAME/AgentOS.git${NC}"

# Tenta SSH
echo -e "${YELLOW}Testando conexão SSH com GitHub...${NC}"
ssh -T git@github.com || true
echo ""

echo -e "${YELLOW}Tentando push com SSH...${NC}"
if git push -u origin main; then
    echo -e "${GREEN}Push realizado com sucesso usando SSH!${NC}"
    exit 0
else
    echo -e "${RED}Falha no push com SSH.${NC}"
fi

echo ""
echo -e "${YELLOW}Recomendações finais:${NC}"
echo "1. Instale o GitHub Desktop: https://desktop.github.com/"
echo "2. Abra o projeto através do GitHub Desktop e tente publicar"
echo "   Ou"
echo "3. Crie um ZIP do projeto e faça upload manual no GitHub"
echo "   através da interface web em https://github.com/$GITHUB_USERNAME/AgentOS"

echo ""
echo -e "${YELLOW}Se ainda tiver problemas, crie um novo repositório com outro nome ou outro usuário.${NC}"
