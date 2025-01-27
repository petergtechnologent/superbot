# Third-Party Libraries (Text to Flex)

## 1. Frontend
- **Next.js**: Routing & SSR.
- **Chakra UI**: Theming and component library.
- **React Query**: Handling data fetch/mutations to the backend.
- **Axios**: Simple HTTP client for the `api.js` utility.

## 2. Backend
- **FastAPI**: Python web framework.
- **Motor** / **PyMongo**: MongoDB async driver.
- **Passlib** / **JWT**: Password hashing and auth tokens.
- **Requests** / **OpenAI**: For calling on-prem or cloud AI.

## 3. AI & Model Providers
- **Ollama** (on-prem) or **OpenAI** (cloud). 
- The system calls the relevant endpoint or API to:
  - Transform user text into a spec.
  - Generate (or fix) code.

## 4. DevOps
- **Docker**: Container builds and runs.
- **Docker Compose**: Local dev environment.
- **K8s** (optional for production).

## 5. Summary
Libraries chosen for simplicity, modular design, and fast iteration. They cover the entire pipeline: from UI and data fetching, to AI calls and container orchestration.
