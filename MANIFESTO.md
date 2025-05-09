# AgentOS & Fusion App

> Infraestrutura institucional + Interface semântica
> Autenticação, pagamentos, chat inteligente, uploads e modularidade total

---

## ⬜ AgentOS (backend)

**AgentOS** é a plataforma de execução institucional. Cada ação é validada, cada operação é rastreável. Estável, modular, viva.

### ⚙️ Tech Stack

- Express.js + Node.js
- MongoDB com Mongoose
- JWT Auth + Redis (opcional)
- Stripe API
- Docker Compose
- Upload de arquivos
- Pronto para LLM Dispatcher futuro

### 📁 Estrutura

```
backend/
├── routes/
├── controllers/
├── models/
├── utils/
└── server.js
```

### 🔐 Autenticação

- Sessões JWT
- Papéis: admin, cliente, operador
- Proteção de rotas no backend e frontend

### 💳 Pagamentos

- Stripe integrado
- Webhooks funcionando
- Criação de planos, assinaturas, transações

### 🧪 Setup

```bash
cp .env.example .env
docker-compose up --build
```

- Frontend: http://localhost:3000  
- Backend API: http://localhost:5000/api

---

## ⬛ Fusion App (frontend)

**Fusion App** é a interface institucional do sistema. Tudo se comunica via linguagem. Chat, tema, upload, dados renderizados.

### 💻 Tech Stack

- Next.js + React
- Tailwind CSS + CSS Variables (tema via Mosaic Engine)
- Zustand para estado
- Socket/REST ready
- Componentes visuais inteligentes: KeyValue, DataList, DataCard, DataTable

### 📁 Estrutura

```
frontend/
├── pages/           # /login, /dashboard, /
├── components/      # InputBar, MessageRenderer, ThemeDesigner
├── hooks/           # useAuth, useSession, useTheme
├── lib/             # integração com API
└── styles/          # temas e variáveis
```

### 🔥 Destaques

- Mosaic Engine: engine de temas por emoção (quente, ousado, moderno…)
- Chat central com LLM (pronto para conectar ao dispatcher)
- Uploads de arquivos direto no chat
- Mensagens com renderizadores dinâmicos (dados viram cards, tabelas ou blocos)

### 🚀 Para rodar

```bash
cd frontend
yarn install
yarn dev
```

### 🧠 Exemplo de mensagem no Fusion:

```
> quero saber o saldo do cliente Lucas

🧠 → { intent: "get_balance", entity: "lucas" }

💬 → Lucas tem R$ 350,00 disponíveis.
```

---

## 🖋️ Assinatura

**Arquitetura**: [@danvoulez](https://github.com/danvoulez)  
Assistência técnica por **OpenAI GPT-4o** e **Gemini 2.5**  
© 2025 [VoulezVous.ai](https://voulezvous.ai) – Todos os direitos reservados

> Este sistema é construído sob princípios de responsabilidade computável, clareza institucional e fluidez operacional.