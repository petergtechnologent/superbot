# Third-Party Libraries Documentation

## 1. Overview
Lists and describes all external libraries used in the AI-Powered App Generator, including on-prem AI (Ollama) and cloud AI (OpenAI).

## 2. Frontend

- **Next.js**: React-based framework with SSR/SSG.
- **Chakra UI**: Pre-built UI components, dark mode, accessibility.
- **React Query**: Data fetching, caching, and synchronization.
- **React Context (Built-in)**: Lightweight global state for user session.
- **SSE / WebSockets**: Live log streaming from the backend (native browser APIs).

## 3. Backend

- **FastAPI**: Python framework for RESTful APIs, async, built-in docs.
- **Pydantic**: Data modeling and validation.
- **Uvicorn** (or **Gunicorn** with Uvicorn workers): ASGI server.
- **MongoDB Driver** (Motor or PyMongo): Connection to MongoDB.
- **Okta / PyJWT**: Token validation for SSO and local authentication.

## 4. AI Providers & Integrations

### Ollama (On-Prem)
- Host: Typically http://10.60.4.77:11434 or http://10.60.4.78:11434
- Models with 64000 context length and 60000 max tokens, e.g.:
  - hhao/qwen2.5-coder-tools:32b
  - llama3.2-vision:11b-instruct-q8_0
  - qwen2.5-coder:7b-instruct-fp16
  - etc.

### OpenAI (Cloud)
- platform.openai.com
- Use official Python library (openai) or direct REST calls.
- GPT-4, GPT-3.5, or specialized models based on cost/performance needs.
- API key stored in sealed secrets or environment variables.

## 5. DevOps & Infrastructure

- **Docker / Docker Compose**: Containerization.
- **Flux CD**: GitOps tool for continuous deployment to k3s.
- **K3s**: Lightweight Kubernetes distribution for running services.
- **Sealed Secrets**: Encrypt and manage secrets in GitOps workflow.

## 6. Security & Compliance

- Check library licenses (MIT, Apache) to ensure compliance.
- Store credentials safely (OpenAI keys, Okta client secrets).
- Enforce TLS for external calls and Okta integrations.

## 7. Future or Optional Libraries

- Redis or RabbitMQ if advanced caching/queues needed.
- Redux or Zustand if global state becomes complex.
- Additional AI or ML libraries if new features demand them.

## 8. Summary & Next Steps
These third-party libraries form the foundation of the application’s architecture. Future expansions or additional AI integrations can be easily added.
