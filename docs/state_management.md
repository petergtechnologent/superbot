# State Management Documentation

## 1. Overview
Text to Flex uses a small, focused state management approach:
- **Local State**: React Hooks for prompt inputs and UI toggles.
- **React Query**: Manages server-side data (conversations, deployments, logs).
- **Context**: (Optional) for global user session data, but this example mainly uses tokens in localStorage.

## 2. Key Data Flows
- **Conversational Input**: Local UI state → `transform_flex_spec` → store spec in conversation.
- **Deployment**: Start with `POST /deployments/start`, then watch logs via WebSocket. React Query or direct calls for final status.

## 3. Real-Time Logging
- Uses a WebSocket. The `ActivityLog` component listens to new messages and appends them to the UI state.

## 4. Edge Cases
- If transformation fails (LLM can’t parse user text), show an error message. 
- If container deploy fails multiple times, eventually mark the deployment as error.

## 5. Future
- Possibly unify user session in a React Context if the app grows or add Redux if more complexity is needed.

