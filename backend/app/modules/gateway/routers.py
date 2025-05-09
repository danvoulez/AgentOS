\# AgentOS Core \- Backend v2.0

Backend principal para o sistema AgentOS / VoulezVous, implementado com FastAPI, MongoDB, Redis e Celery, incorporando um núcleo cognitivo (Semantic LLM Engine) e funcionalidades avançadas de gestão operacional e comunicação.

\#\# Visão Geral

Este backend fornece a API RESTful e o servidor WebSocket que alimentam o frontend \`fusion-app\` (React) e outros possíveis clientes. Ele orquestra a lógica de negócios, interações com IA, persistência de dados e tarefas assíncronas para os seguintes módulos principais:

\*   \*\*People:\*\* Gestão de usuários (clientes, staff, motoristas, etc.), perfis, roles, autenticação (JWT) e controle de acesso. Preparado para tags RFID.  
\*   \*\*Sales:\*\* Catálogo de produtos (preços múltiplos, kits), fluxo de pedidos (rascunhos, confirmação), cálculo de margem.  
\*   \*\*Stock:\*\* Gerenciamento de itens de estoque individuais com tags RFID (cadastro bulk, consulta, atualização de status via eventos \- base).  
\*   \*\*Reservations:\*\* Serviço de reserva de estoque com Redis+TTL integrado ao fluxo de pedidos.  
\*   \*\*Delivery:\*\* Criação de entregas a partir de pedidos, atualização de status, rastreamento (base), atribuição de motorista.  
\*   \*\*Banking:\*\* Registro simples de transações financeiras (receita de vendas, etc.).  
\*   \*\*Finance:\*\* Geração de relatórios básicos (Vendas agregadas com custo/margem, Comissões \- base).  
\*   \*\*Agreements:\*\* Sistema para formalização de acordos/decisões extraordinárias com testemunhas.  
\*   \*\*Tasks:\*\* Sistema simples de gerenciamento de tarefas (criação, atribuição, status).  
\*   \*\*Office:\*\* Gestão de configurações do sistema (com cache Redis) e Logs de Auditoria detalhados.  
\*   \*\*WhatsApp:\*\* Gateway para receber e enviar mensagens via API Oficial da Meta, gestão de chats e modo Human/Agent (base), AutoResponder contextual.  
\*   \*\*Advisor:\*\* Histórico persistente para conversas com a IA.  
\*   \*\*Gateway (Semantic LLM Engine):\*\* Ponto central de processamento de linguagem natural, interpretação de intenção, execução de ferramentas internas (Tool Proxy com permissões), busca em memória semântica (requer índice Atlas), fallback multi-LLM (base), modo explicador e sugestão de emoção.  
\*   \*\*WebSocket:\*\* Comunicação em tempo real com o frontend (novas mensagens WA, status, hints).

\#\# Tecnologias Principais

\*   \*\*Framework:\*\* FastAPI  
\*   \*\*Linguagem:\*\* Python 3.10+  
\*   \*\*Banco de Dados:\*\* MongoDB (com Motor para async)  
\*   \*\*Cache/Broker:\*\* Redis  
\*   \*\*Tarefas Assíncronas:\*\* Celery  
\*   \*\*ORM/Validação:\*\* Pydantic v2  
\*   \*\*Logging:\*\* Loguru  
\*   \*\*Autenticação:\*\* JWT (python-jose), OAuth2PasswordBearer (FastAPI)  
\*   \*\*LLM:\*\* OpenAI API (com suporte a fallback básico para outros)  
\*   \*\*Embeddings:\*\* OpenAI API  
\*   \*\*Busca Vetorial:\*\* MongoDB Atlas Search (requer configuração externa)  
\*   \*\*Testes:\*\* Pytest, HTTPX  
\*   \*\*Containerização:\*\* Docker, Docker Compose

\#\# Configuração do Ambiente de Desenvolvimento

1\.  \*\*Pré-requisitos:\*\*  
    \*   Python 3.10 ou superior  
    \*   Poetry (recomendado para gerenciamento de dependências) ou pip  
    \*   Docker e Docker Compose (para rodar DBs/Cache/Worker facilmente)  
    \*   Conta OpenAI API (para LLM e Embeddings)  
    \*   (Opcional) Conta Meta Developer com App WhatsApp configurado (para funcionalidade WA completa)  
    \*   (Opcional) Cluster MongoDB Atlas com capacidade de Atlas Search (para Memória Semântica)

2\.  \*\*Clonar o repositório:\*\*
