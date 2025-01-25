# Backend Documentation

## 1. Overview
A FastAPI-based service that handles:
- Code generation requests
- Deployments
- Real-time logging
- Authentication and role-based access

## 2. Framework & Language
- Python 3, FastAPI, Pydantic for data validation.
- Uvicorn or Gunicorn for ASGI hosting.

## 3. Database
- MongoDB via PyMongo or Motor (async).
- Collections for users, conversations, deployments, etc.

## 4. Authentication & Authorization
- Okta SSO for primary logins, with local user fallback for testing/admin.
- Role-based access (Administrator, User) enforced at route level.

## 5. API Design (RESTful)
1. **/auth**: login (local), Okta callbacks, logout
2. **/users**: manage user accounts (admin only), get current user
3. **/conversations**: create chat sessions, add messages
4. **/deployments**: trigger app deployment, view status/logs
5. **/ai**: orchestrates code generation with on-prem or cloud models

## 6. On-Prem & Cloud AI Integration
- **On-Prem (Ollama)**:
  - Models (examples):
    - hhao/qwen2.5-coder-tools:32b
    - llama3.2-vision:11b-instruct-q8_0
    - etc.
  - Typically hosted at http://10.60.4.77:11434 or http://10.60.4.78:11434
  - 64000 context length, 60000 max tokens.
- **Cloud (OpenAI)**:
  - Accessed via platform.openai.com or the official OpenAI Python library.
  - Use different models depending on cost/performance (e.g. GPT-4, GPT-3.5).

## 7. Deployment & DevOps
- Docker-based container for FastAPI.
- Flux CD (GitOps) for k3s environment.
- Sealed secrets for storing credentials (Okta secrets, AI keys).

## 8. Real-Time Logs
- SSE or WebSocket endpoints (e.g., /deployments/{id}/logs/stream).
- Streams code generation status, build logs, error messages.

## 9. Security & Compliance
- SSL/TLS for external communication.
- Strict role checks for admin operations.
- Rate limiting or usage quotas for AI endpoints to control costs.

## 10. Summary & Next Steps
- Backend can switch between on-prem and cloud AI providers for code generation.
- Set up environment variables or a config file for each provider’s base URL and API key.
- Integrate SSE or WebSockets into the frontend for live logs.
