# Frontend Documentation (Text to Flex)

## 1. Overview
Next.js application using Chakra UI for styling and React Query for data fetching. Key pages:
- **`/login`** and **`/signup`**: Authentication.
- **`/`** (Home): Main interface for describing your service, generating code, and deploying.
- **`/history`**: View past conversations and deployments.

## 2. Workflow
1. User enters a **conversational idea** on the Home page.
2. The frontend calls **`POST /ai/transform_flex_spec`** to get a structured “Flex Spec.”
3. The app automatically creates a new conversation with that spec, then calls **`POST /ai/generate`**.
4. The user can then **start a deployment** with `POST /deployments/start` specifying the target port.
5. **ActivityLog** listens for logs via WebSocket to display real-time build/run feedback.

## 3. Chakra UI & Dark Mode
- The theme is configured in `frontend/theme/index.js`.
- Dark mode is default.

## 4. State Management
- **React Query** for all server interactions (login, conversation, logs).
- Minimal React state for prompt input, user token management, etc.

## 5. Future Enhancements
- More guided forms for user input or advanced spec definition.
- Display the final running service’s URL in the UI.

## 6. Conclusion
The frontend offers a simple, chat-like approach, behind which a more sophisticated orchestrator transforms text to service code and automatically deploys it.
