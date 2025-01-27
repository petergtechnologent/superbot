// File: frontend/utils/api.js
import axios from "axios";

// Adjust baseURL for your environment
const apiClient = axios.create({
  baseURL: "http://localhost:8000",
});

// Optional: token interceptor if you use localStorage
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ----------------------
// Auth: loginUser
// ----------------------
export async function loginUser(payload) {
  // payload = { email, password }
  const { data } = await apiClient.post("/auth/login", payload);
  return data; // { access_token, token_type }
}

// ----------------------
// Auth: createNewUser (for signup)
// ----------------------
export async function createNewUser(payload) {
  // payload = { username, email, role, password }
  const { data } = await apiClient.post("/users", payload);
  return data; // { id, email }
}

// ----------------------
// Conversations
// ----------------------
export async function createConversation(payload) {
  // e.g. payload = { messages: [ { role: "user", content: prompt } ] }
  const { data } = await apiClient.post("/conversations", payload);
  return data; // { conversation_id }
}

export async function getConversations() {
  // For listing conversation history
  const { data } = await apiClient.get("/conversations");
  return data; // Array of conversation objects
}

// ----------------------
// AI code generation
// ----------------------
export async function generateCode(payload) {
  // payload = { conversation_id, prompt }
  const { data } = await apiClient.post("/ai/generate", payload);
  return data; // { generated_code }
}

// ----------------------
// Deployments
// ----------------------
export async function startDeployment(payload) {
  // payload = { conversation_id, app_name, max_iterations, app_type }
  const { data } = await apiClient.post("/deployments/start", payload);
  return data; // { deployment_id, status }
}
