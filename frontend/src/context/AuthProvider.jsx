import { useEffect, useState } from "react";
import api, { errorMessage } from "../api/client";
import { AuthContext } from "./authContext";

export default function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(
    Boolean(localStorage.getItem("token")),
  );
  const [restoreError, setRestoreError] = useState("");

  // on page refresh, restore the session from the saved token
  useEffect(() => {
    if (!localStorage.getItem("token")) return;
    api
      .get("/api/auth/me")
      .then((res) => {
        setUser(res.data);
        setRestoreError("");
      })
      .catch((err) => {
        if ([401, 403].includes(err.response?.status)) {
          localStorage.removeItem("token");
          return;
        }
        setRestoreError(errorMessage(err));
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    setRestoreError("");
    // the login endpoint expects form-urlencoded fields, not JSON
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);
    const { data } = await api.post("/api/auth/login", form);
    localStorage.setItem("token", data.access_token);
    try {
      const me = await api.get("/api/auth/me");
      setUser(me.data);
      setRestoreError("");
    } catch (err) {
      if ([401, 403].includes(err.response?.status)) {
        localStorage.removeItem("token");
      } else {
        setRestoreError(errorMessage(err));
      }
      throw err;
    }
  };

  const register = async (fullName, email, password) => {
    await api.post("/api/auth/register", {
      full_name: fullName,
      email,
      password,
    });
    await login(email, password);
  };

  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
    setRestoreError("");
  };

  return (
    <AuthContext.Provider value={{ user, loading, restoreError, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
