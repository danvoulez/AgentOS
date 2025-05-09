# AgentOS

AgentOS is a full-stack application featuring a Next.js frontend, a Python FastAPI backend, and utilizes MongoDB for data storage and Redis for caching and task queuing with Celery. The entire application is containerized using Docker for ease of deployment and development.

## Features

*   **Modern Web Interface:** Built with Next.js, React, TypeScript, and styled with Tailwind CSS.
*   **Robust Backend API:** Developed with Python and FastAPI, providing a high-performance asynchronous API.
*   **Task Queuing:** Asynchronous tasks are managed by Celery with Redis as the message broker.
*   **Database Integration:** MongoDB is used as the primary data store.
*   **Containerized Deployment:** Docker and Docker Compose are used for consistent environments and simplified deployment.
*   **Real-time Communication:** WebSocket support for interactive features.
*   **Modular Backend Design:** Organized into modules for different functionalities (e.g., agreements, banking, sales).

## Tech Stack

*   **Frontend:**
    *   Next.js
    *   React
    *   TypeScript
    *   Tailwind CSS
    *   Vite (for the original `frontend` service, now integrated or replaced by Next.js structure)
    *   Shadcn/ui (based on `components.json` and `components/ui`)
*   **Backend:**
    *   Python 3.x
    *   FastAPI
    *   Celery
*   **Database:**
    *   MongoDB
*   **Cache/Message Broker:**
    *   Redis
*   **Containerization:**
    *   Docker
    *   Docker Compose

## Prerequisites

Before you begin, ensure you have the following installed:

*   [Node.js](https://nodejs.org/) (LTS version recommended)
*   [pnpm](https://pnpm.io/installation) (Package manager for Node.js)
*   [Python](https://www.python.org/downloads/) (Version 3.8+ recommended)
*   [Docker](https://www.docker.com/get-started)
*   [Docker Compose](https://docs.docker.com/compose/install/)

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/danvoulez/AgentOS.git
cd AgentOS
```

### 2. Environment Configuration

This project uses `.env` files for managing environment variables.

**A. Root `.env` file (for Docker Compose):**

Create a `.env` file in the root of the project (`/workspaces/AgentOS/.env`) for variables used by `docker-compose.yml`.

```env
# .env (in project root)

# MongoDB Credentials (used by mongodb service and to construct MONGODB_URI)
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=password

# Port Configuration (optional, defaults are provided in docker-compose.yml)
BACKEND_PORT=8000
FRONTEND_PORT=3000

# Backend Secrets (used by backend and worker services)
SECRET_KEY=a_very_secure_secret_key_for_jwt_32_bytes_long_replace_me
OPENAI_API_KEY=your_openai_api_key_here # IMPORTANT: Replace with your actual OpenAI API key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Add any other variables referenced directly by docker-compose.yml environment sections
# For example, if you have ANTHROPIC_API_KEY, SENTRY_DSN, etc., that are not in backend/.env.example
# but are needed by the docker-compose setup.
```

**B. Backend `.env` file:**

Navigate to the backend directory and create a `.env` file by copying the example.

```bash
cd backend
cp .env.example .env
cd ..
```

Now, edit `backend/.env` and fill in the required values, especially for external services like OpenAI, Anthropic, and Sentry if you plan to use them.
The `MONGODB_URL` and `REDIS_HOST`/`REDIS_PORT` in `backend/.env` are typically configured for local development without Docker. When using Docker Compose, the `MONGODB_URI` and `REDIS_URL` environment variables for the `backend` and `worker` services are constructed using the service names (`mongodb`, `redis`) as hostnames, as defined in `docker-compose.yml`.

**Note on API Keys:**
The `OPENAI_API_KEY` is crucial for the application's functionality. Ensure it's set in the root `.env` file so Docker Compose can pass it to the backend and worker services. If you are running the backend service locally without Docker, ensure `OPENAI_API_KEY` is set in `backend/.env`.

### 3. Install Dependencies

*   **Frontend (Next.js - root directory):**
    ```bash
    pnpm install
    ```
*   **Backend (Python - `backend` directory):**
    It's recommended to use a Python virtual environment.
    ```bash
    cd backend
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    pip install -r requirements.txt
    cd ..
    ```

## Running the Application

### Using Docker (Recommended)

This is the easiest way to get all services up and running.

1.  **Ensure your root `.env` file is configured**, especially with `OPENAI_API_KEY`.
2.  Build and start the services:
    ```bash
    docker-compose up --build -d
    ```
    (Use `-d` to run in detached mode)
3.  To view logs:
    ```bash
    docker-compose logs -f
    ```
    Or for a specific service:
    ```bash
    docker-compose logs -f backend
    ```

*   **Frontend** will be accessible at: `http://localhost:${FRONTEND_PORT:-3000}` (default: `http://localhost:3000`)
*   **Backend API** will be accessible at: `http://localhost:${BACKEND_PORT:-8000}` (default: `http://localhost:8000`)

### Running Locally (Without Docker)

You'll need to run each service in a separate terminal.

1.  **Start MongoDB and Redis:**
    Ensure you have MongoDB and Redis instances running locally or use the Docker versions:
    ```bash
    docker-compose up -d mongodb redis
    ```

2.  **Start the Backend API:**
    *   Navigate to the `backend` directory.
    *   Activate the Python virtual environment: `source venv/bin/activate`
    *   Ensure `backend/.env` is configured for local MongoDB/Redis if not using Docker for them.
    *   Run the FastAPI server:
        ```bash
        uvicorn app.main:app --reload --host 0.0.0.0 --port ${BACKEND_PORT:-8000}
        ```
        (Default port is 8000)

3.  **Start the Celery Worker:**
    *   Navigate to the `backend` directory (if not already there).
    *   Activate the Python virtual environment.
    *   Run the Celery worker:
        ```bash
        celery -A app.worker.celery_app worker --loglevel=info
        ```

4.  **Start the Frontend Development Server:**
    *   Navigate to the project root directory.
    *   Run the Next.js development server:
        ```bash
        pnpm dev
        ```
        The frontend will typically be available at `http://localhost:3000`.

## Available Scripts (Frontend - `package.json`)

In the project root directory:

*   `pnpm dev`: Starts the Next.js development server.
*   `pnpm build`: Builds the Next.js application for production.
*   `pnpm start`: Starts the Next.js production server (after building).
*   `pnpm lint`: Lints the Next.js application.

## Project Structure Overview

```
/
├── app/                  # Next.js app directory (frontend)
│   ├── layout.tsx
│   └── page.tsx
├── backend/              # FastAPI backend application
│   ├── app/              # Core backend application code
│   │   ├── api/          # API endpoints
│   │   ├── core/         # Core components (config, db, security)
│   │   ├── db/           # Database schemas and client
│   │   ├── models/       # Pydantic models
│   │   ├── modules/      # Business logic modules
│   │   ├── services/     # External service integrations (LLM, etc.)
│   │   ├── worker/       # Celery worker and tasks
│   │   └── main.py       # FastAPI application entry point
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── components/           # Shared React components (Shadcn/ui)
├── frontend/             # Original Vite frontend (may be deprecated or parts reused)
│   ├── src/
│   └── Dockerfile
├── public/               # Static assets for Next.js
├── docker-compose.yml    # Docker Compose configuration
├── next.config.mjs       # Next.js configuration
├── package.json          # Frontend Node.js dependencies and scripts
├── pnpm-lock.yaml        # pnpm lock file
├── README.md             # This file
└── ... (other configuration files)
```

## Environment Variables Reference

### Root `.env` (for Docker Compose)

*   `MONGO_INITDB_ROOT_USERNAME`: MongoDB root username.
*   `MONGO_INITDB_ROOT_PASSWORD`: MongoDB root password.
*   `BACKEND_PORT`: Port for the backend service.
*   `FRONTEND_PORT`: Port for the frontend service.
*   `SECRET_KEY`: Secret key for JWT and other security functions in the backend.
*   `OPENAI_API_KEY`: API key for OpenAI services.
*   `ACCESS_TOKEN_EXPIRE_MINUTES`: Expiration time for JWT access tokens.

### `backend/.env`

Refer to `backend/.env.example` for a full list of backend-specific environment variables. Key variables include:

*   `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `ALGORITHM`: For JWT authentication.
*   `OPENAI_API_KEY`, `OPENAI_ORG_ID`: For OpenAI integration.
*   `ANTHROPIC_API_KEY`: For Anthropic (Claude) integration.
*   `MONGODB_URL`, `DATABASE_NAME`: For MongoDB connection (when running backend locally).
*   `API_V1_STR`, `BACKEND_CORS_ORIGINS`: API configuration.
*   `LOG_LEVEL`, `LOG_FORMAT`: Logging configuration.
*   `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`: For Redis connection (when running backend locally).
*   `DEFAULT_LLM_PROVIDER`, `DEFAULT_LLM_MODEL`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`: LLM configuration.
*   `SENTRY_DSN`, `ENABLE_METRICS`: Monitoring.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.

(Consider adding guidelines for development, commit messages, etc., if you plan to have multiple contributors.)

## License

(Specify a license if you have one, e.g., MIT, Apache 2.0. If not, you can state "All rights reserved.")

---

This README provides a good starting point. You can expand on specific sections, add more details about the project's purpose, or include a "Troubleshooting" section as needed.
## 🖋️ Assinatura

**Arquitetura**: [@danvoulez](https://github.com/danvoulez)  
Assistência técnica por **OpenAI GPT-4o** e **Gemini 2.5**  
© 2025 [VoulezVous.ai](https://voulezvous.ai) – Todos os direitos reservados

> Este sistema é construído sob princípios de responsabilidade computável, clareza institucional e fluidez operacional.