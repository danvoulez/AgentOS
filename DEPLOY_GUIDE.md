# DEPLOY_GUIDE.md

## 🔧 Requisitos

- Docker + Docker Compose
- Porta 3000 (frontend) e 5000 (backend) disponíveis
- MongoDB Atlas ou local
- Stripe API Keys
- Redis (opcional)

## 🔨 Passos para Deploy

```bash
cp .env.example .env
docker-compose up --build
```

## 🌍 Produção no Railway

1. Conecte repositório ao Railway
2. Configure variáveis de ambiente manualmente (Stripe, JWT, MongoDB, etc)
3. Ative build automático nas branches `main` ou `prod`
4. Verifique endpoints após deploy:

- Frontend: `https://<your-app>.railway.app`
- Backend: `https://<your-api>.railway.app/api`

## ✅ Pós-deploy

- Crie usuário admin via API ou script
- Teste logins e pagamentos de teste
- Valide uploads e sessões JWT