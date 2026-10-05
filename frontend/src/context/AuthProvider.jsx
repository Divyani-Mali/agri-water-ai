import { useEffect, useState } from "react";
import api from "../api/client";
import { AuthContext } from "./authContext";

export default function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(
    Boolean(localStorage.getItem("token")),
  );

  // on page refresh, restore the session from the saved token
  useEffect(() => {
    if (!localStorage.getItem("token")) return;
    api
      .get("/api/auth/me")
      .then((res) => setUser(res.data))
      .catch(() => localStorage.removeItem("token"))
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);
    const { data } = await api.post("/api/auth/login", form);
    localStorage.setItem("token", data.access_token);
    const me = await api.get("/api/auth/me");
    setUser(me.data);
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
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
