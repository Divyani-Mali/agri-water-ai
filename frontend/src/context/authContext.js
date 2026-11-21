import { createContext, useCallback, useContext } from "react";
import { translate } from "../i18n";

export const AuthContext = createContext(null);

export function useAuth() {
  return useContext(AuthContext);
}

export function useTranslate() {
  const { user, language } = useAuth();
  return useCallback(
    (text, values) => translate(text, user?.preferred_language || language || "en", values),
    [language, user?.preferred_language],
  );
}
