import { useEffect, useState } from "react";
import api, { errorMessage, updatePreferredLanguage } from "../api/client";
import { AuthContext } from "./authContext";

export default function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [language, setLanguage] = useState(() => localStorage.getItem("ui-language") || "en");
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
        const preferred = res.data.preferred_language || "en";
        setLanguage(preferred);
        localStorage.setItem("ui-language", preferred);
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

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

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
      let signedInUser = me.data;
      const pendingLanguage = localStorage.getItem("pending-preferred-language");
      if (pendingLanguage && ["en", "hi", "mr"].includes(pendingLanguage)) {
        try {
          const { data: updatedUser } = await updatePreferredLanguage(pendingLanguage);
          signedInUser = updatedUser;
          localStorage.removeItem("pending-preferred-language");
        } catch (err) {
          setRestoreError(errorMessage(err));
        }
      }
      setUser(signedInUser);
      const preferred = signedInUser.preferred_language || "en";
      setLanguage(preferred);
      localStorage.setItem("ui-language", preferred);
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
      preferred_language: language,
    });
    await login(email, password);
  };

  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
    setRestoreError("");
  };

  const setGuestLanguage = (preferredLanguage) => {
    setLanguage(preferredLanguage);
    localStorage.setItem("ui-language", preferredLanguage);
    localStorage.setItem("pending-preferred-language", preferredLanguage);
  };

  const updateLanguage = async (preferredLanguage) => {
    const { data } = await updatePreferredLanguage(preferredLanguage);
    setUser(data);
    setLanguage(data.preferred_language);
    localStorage.setItem("ui-language", data.preferred_language);
    localStorage.removeItem("pending-preferred-language");
    return data;
  };

  return (
    <AuthContext.Provider value={{ user, loading, restoreError, login, register, logout, updateLanguage, language, setGuestLanguage }}>
      {children}
    </AuthContext.Provider>
  );
}
