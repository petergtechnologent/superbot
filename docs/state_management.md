# State Management Documentation

## 1. Overview
How the frontend manages application state (local, global, server) for the AI-Powered App Generator.

## 2. Proposed Libraries & Approaches

### 2.1 Local State (React Hooks)
- useState, useReducer for simple UI interactions (chat input, toggles).
- No extra library needed for small-scale local state.

### 2.2 Global State (React Context)
- Store user session, roles, or theme toggles in a Context.
- If complexity grows, consider migrating to Zustand or Redux.

### 2.3 Server State (React Query)
- Caching, background refetch, and synchronization with the FastAPI backend.
- Ideal for conversation data, deployment statuses, user profiles.

### 2.4 Real-Time Logs
- SSE or WebSockets for streaming new log messages to the UI.
- React Query can handle standard GET/POST requests, but real-time data is handled via event listeners or a separate hook.

### 2.5 Persistence
- Auth tokens in secure cookies (or sessionStorage).
- Non-sensitive user preferences can go in localStorage if needed.

## 3. Data Flows & Examples
- Chat: local input -> React Query mutation -> On success, refetch conversation data.
- Deployment Logs: SSE -> event listener -> update local state -> display logs in real time.

## 4. Potential Gotchas
- SSE + Next.js: Must ensure the client side handles streaming.
- Role-based UI: Always enforce roles in backend as well to prevent unauthorized actions.

## 5. Summary
- Minimal approach using React Hooks, Context, React Query.
- Real-time logs handled by SSE or WebSockets.  
- Enough for an MVP without unnecessary complexity.
