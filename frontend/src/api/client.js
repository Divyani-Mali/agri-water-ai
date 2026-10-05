import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000",
});

// attach the login token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// expired/invalid token -> back to login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const isLoginCall = err.config?.url?.includes("/api/auth/login");
    if (err.response?.status === 401 && !isLoginCall) {
      localStorage.removeItem("token");
      if (window.location.pathname !== "/login")
        window.location.href = "/login";
    }
    return Promise.reject(err);
  },
);

// turns any API error into a readable message
export function errorMessage(err) {
  if (!err.response) return "Cannot reach the server. Is the backend running?";
  const detail = err.response.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail[0].msg.replace("Value error, ", "");
  }
  return "Something went wrong. Please try again.";
}

export default api
