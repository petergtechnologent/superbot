# User Flow Documentation

## 1. Overview
Describes the step-by-step journey a user experiences, from login to generating and deploying apps, including error handling and real-time logs.

## 2. Flowchart (Text Version)

flowchart LR
    A[Open App] --> B{Login Method?}
    B -->|Okta Login| C[Redirect to Okta SSO - Authenticate - Return with Token]
    B -->|Local Login| D[Enter Email/Password]
    C --> E1[Backend Validates Token - Assign Role: Admin/User]
    D --> E2[Backend Checks Credentials - Assign Role: Admin/User]
    E1 --> F[Home Page - Chat Interface]
    E2 --> F
    F --> G["Enter Idea in Chat (POST Conversations)"]
    G --> H["AI Processes Idea (Backend + AI Services)"]
    H --> I["Logs Stream in Real-Time (SSE/WebSockets)"]
    I -->|Success| J[App Generated - Deployment Option]
    J --> K[Deploy Container via Docker Compose or K8s]
    J --> L[View or Edit Generated Code]
    K --> M[View Deployment Logs in Real-Time]
    M -->|Deployed| N[User Accesses Running App]
    M -->|Error| O[Retry/Debug]
    N --> P["History Page (View Past Chats/Deployments)"]
    P --> F[Return to Home - Chat]


## 3. Onboarding Flow
- **Okta SSO** or local credentials for MVP.
- Assign user role upon login (Administrator, User).
- Store tokens securely (cookies, session).

## 4. Core User Journey
1. User enters an idea in the chat.
2. AI generates code, logs progress. 
3. On success, user triggers deployment.
4. Logs continue to stream. If deployment succeeds, user can open the new app.

## 5. Page Interactions
- **Home/Chat**: Main page for prompts and partial logs.
- **History**: List past chats and deployments, plus “revisit or clone” older ideas.
- **Settings**: Admin tasks, user management, advanced config.

## 6. Error Handling & Edge Cases
- Invalid login: Show error, prompt retry.
- AI generation failure: Logs show errors, user sees final error state if auto-fix fails.
- Deployment failure: Real-time logs highlight build or config issues.
- Network issues: SSE/WebSockets attempt reconnection.

## 7. Alternative Flows
- Guest mode (future).
- Partial deploy: Generate code but skip auto-deploy.
- Shared “demo” accounts for quick sales calls.

## 8. User Permissions
- **Administrator**: Full access to user management, all logs.
- **User**: Limited to own conversations and deployments.

## 9. Notifications (Future)
- Email or push alerts on successful or failed deployments.
- Webhooks to integrate with other systems.

## 10. Summary & Next Steps
User logs in, enters an idea, the AI churns out code with real-time logs, user deploys, and the system updates logs and status. History page for references. Role-based permissions control who can do what.
