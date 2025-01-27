# User Flow Documentation (Text to Flex)

## 1. Overview
Describes how a user goes from **plain text idea** to a **deployed FastAPI service**.

## 2. Flowchart (Text Version)

flowchart LR
    A[User inputs idea (conversational)] --> B[Transform to Flex Spec (AI step)]
    B --> C[Create Conversation & Store Spec]
    C --> D[Generate Code from Spec]
    D --> E[Deploy Container]
    E --> F[Logs and Error Checking]
    F -->|Success| G[Service Running on Port X]
    F -->|Error| H[Auto-Fix & Retry]
    G --> I[History Page for Past Deployments]

## 3. Onboarding Flow
- **Login**: Local credentials or admin-provided account.
- **Role**: Admin can manage users; normal users can create their own services.

## 4. Core Journey
1. **Enter Conversational Prompt**: e.g., “I need an inventory service with GET/POST endpoints on port 9080.”
2. **Transformation**: System calls LLM to produce a structured spec (title, port, routes).
3. **Code Generation**: The orchestrator requests code from the LLM, storing the results in the conversation.
4. **Deploy**: Docker container is built and run. If errors occur, logs are passed back to the LLM for fixes.
5. **History**: Users can review logs and re-check or re-deploy older specs.

## 5. Error Handling
- Transformation might fail if user’s prompt is too vague. Return user-friendly message.
- Code generation errors handled by iterative fix loop using Docker logs.
- Deployment errors returned via real-time WebSocket logs.

## 6. Conclusion
Text to Flex offers a streamlined path from user story to a fully functional, containerized FastAPI service. The system’s iterative approach ensures minimal manual debugging.
