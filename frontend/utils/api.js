// File: frontend/utils/api.js

import axios from "axios";

const apiClient = axios.create({
  baseURL: "http://localhost:8000",
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// --- Transform to Flex Spec ---
export async function transformFlexSpec(payload) {
  // payload = { userIdea: string }
  const { data } = await apiClient.post("/ai/transform_flex_spec", payload);
  return data;
}

// --- Auth: login ---
export async function loginUser(payload) {
  const { data } = await apiClient.post("/auth/login", payload);
  return data;
}

// --- Auth: create user ---
export async function createNewUser(payload) {
  const { data } = await apiClient.post("/users", payload);
  return data;
}

// --- Conversations ---
export async function createConversation(payload) {
  const { data } = await apiClient.post("/conversations", payload);
  return data;
}

export async function getConversations() {
  const { data } = await apiClient.get("/conversations");
  return data;
}

// --- AI code generation ---
export async function generateCode(payload) {
  // payload = { conversation_id, prompt }
  const { data } = await apiClient.post("/ai/generate", payload);
  return data;
}

// --- Deployments ---
export async function startDeployment(payload) {
  // payload includes: conversation_id, app_name, max_iterations, port_number, trouble_mode
  const { data } = await apiClient.post("/deployments/start", payload);
  return data;
}

export async function getRunningServices() {
  const { data } = await apiClient.get("/deployments/running-services");
  return data;
}

export async function stopService(payload) {
  // payload = { deployment_id }
  const { data } = await apiClient.post("/deployments/stop", payload);
  return data;
}
