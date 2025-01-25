# Frontend Documentation

## 1. Overview
Describes the frontend architecture, UI components, styling, and state management. Primary goals:
- Seamless chat interface for users to enter app ideas.
- Real-time activity log for transparency.
- Dark mode UI by default.
- Easy navigation for chat history, settings, and future pages.

## 2. Framework & Libraries

### 2.1 Next.js (React-Based)
- Provides server-side rendering (SSR) and static site generation (SSG).
- Strong community support, easy routing, and a great developer experience.

### 2.2 Chakra UI
- Built-in dark mode theming.
- Pre-built, accessible components (buttons, inputs, layouts).
- Quick to customize for branding or design guidelines.

### 2.3 React Query
- Manages server state, caching, and background refetching.
- Simplifies data-fetching logic for chat messages, deployments, etc.

## 3. Application Structure
(frontend/
  ├─ pages/
  │  ├─ _app.js                 # Custom Next.js App (ChakraProvider, global config)
  │  ├─ index.js                # Home page: chat interface
  │  ├─ history.js              # Page for past prompts/ideas
  │  └─ settings.js             # (Optional) user or admin settings
  ├─ components/
  │  ├─ ChatInterface.js        # Main chat component
  │  ├─ ActivityLog.js          # Real-time log view
  │  ├─ Layout.js               # Layout (header, navigation, footer)
  ├─ theme/
  │  └─ index.js                # Chakra UI custom theme/dark mode
  ├─ utils/
  │  └─ api.js                  # Helper functions for API calls
  └─ ...
)

## 4. Navigation Structure
- Layout-based with a top-level Layout component.
- Menu items: Home (Chat), History, Settings (optional).
- Dark mode set as default in theme config.

## 5. Forms
- Chat input is the primary “form” element.
- (Optional) login form if not using a separate Okta flow or if local users sign up.

## 6. Real-Time Logs
- SSE or WebSockets to display AI generation or deployment logs as they happen.
- Possibly shown in ActivityLog.js or a dedicated panel.

## 7. Summary & Next Steps
- Next.js + Chakra UI + React Query + SSE (or WebSockets) for real-time logs.
- Implementation involves hooking up the relevant endpoints from the backend.
