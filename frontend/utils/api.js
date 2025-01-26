import axios from "axios";

const apiClient = axios.create({
  baseURL: "http://localhost:8000",
});

// Attach interceptors (as you already have)
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    console.log("[API] Request:", {
      method: config.method,
      url: config.url,
      headers: config.headers,
      data: config.data,
    });
    return config;
  },
  (error) => {
    console.error("[API] Request error:", error);
    return Promise.reject(error);
  }
);

apiClient.interceptors.response.use(
  (response) => {
    console.log("[API] Response:", {
      status: response.status,
      url: response.config.url,
      data: response.data,
    });
    return response;
  },
  (error) => {
    if (error.response) {
      console.error("[API] Response error:", {
        status: error.response.status,
        url: error.config.url,
        data: error.response.data,
      });
    } else {
      console.error("[API] Unexpected error:", error);
    }
    return Promise.reject(error);
  }
);

export async function createConversation(payload) {
  const { data } = await apiClient.post("/conversations", payload);
  return data;
}

export async function generateCode(payload) {
  const { data } = await apiClient.post("/ai/generate", payload);
  return data;
}

export async function startDeployment(payload) {
  // The all-important function for orchestrator
  const { data } = await apiClient.post("/deployments/start", payload);
  return data;
}

export async function loginUser(payload) {
  const { data } = await apiClient.post("/auth/login", payload);
  localStorage.setItem("access_token", data.access_token);
  console.log("[API] loginUser stored token:", data.access_token);
  return data;
}

export async function createNewUser(payload) {
  const { data } = await apiClient.post("/users", payload);
  return data;
}
