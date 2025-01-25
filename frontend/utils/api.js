import axios from "axios";

// Adjust the baseURL as needed (localhost or real domain)
const apiClient = axios.create({
  baseURL: "http://localhost:8000",
});

apiClient.interceptors.request.use((config) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function createConversation(payload) {
  const { data } = await apiClient.post("/conversations", payload);
  return data;
}

export async function generateCode(payload) {
  const { data } = await apiClient.post("/ai/generate", payload);
  return data;
}

export async function getConversations() {
  const { data } = await apiClient.get("/conversations");
  return data;
}

export async function loginUser(payload) {
  const { data } = await apiClient.post("/auth/login", payload);
  // Store token in localStorage
  localStorage.setItem("access_token", data.access_token);
  return data;
}

export async function createNewUser(payload) {
  const { data } = await apiClient.post("/users", payload);
  return data;
}
