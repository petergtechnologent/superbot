# Backend Documentation (Text to Flex)

## 1. Overview
Backend is a FastAPI application that:
1. Transforms user text into a “Flex Spec.”
2. Generates FastAPI microservice code from that spec.
3. Deploys the container, checks logs, and fixes code if needed.
4. Stores conversation history, user accounts, and deployment data.

## 2. Core Components
- **/auth**: Login, token creation.
- **/users**: User CRUD (admin only).
- **/conversations**: Store conversation messages and specs.
- **/ai**:
  - `POST /ai/transform_flex_spec` → transform raw text into a structured spec.
  - `POST /ai/generate` → initial code generation from the conversation or spec.
- **/deployments**: Start the orchestrator pipeline, watch logs, track status.
- **/ws**: WebSocket endpoints for real-time logs streaming.

## 3. Database (MongoDB)
- `users`: user accounts (email, role, hashed_password).
- `conversations`: messages, final specs, timestamps.
- `deployments`: status, logs, container iteration data.

## 4. DevOps & Infrastructure
- Docker-based container for FastAPI.
- Docker Compose for local dev with MongoDB.
- Optionally K8s for production scaling.
- On-prem AI (Ollama) or OpenAI calls for transformation and code generation.

## 5. Iterative Deployment
The “orchestrator” logic in `app/api/orchestrator.py`:
1. Build Docker image from generated code.
2. Run container on the user’s chosen port.
3. If container fails or times out, parse logs, feed them back to the LLM for a fix.
4. Repeat until success or max iterations reached.

## 6. Security & Logging
- JWT tokens for auth, role checks in each route.
- WebSocket logs broadcast real-time from the orchestrator to the frontend.

## 7. Summary
The backend orchestrates the entire flow, from receiving user input to handing off a running container. It leverages LLM calls for spec transformation and code generation, storing everything in MongoDB for historical tracking.
