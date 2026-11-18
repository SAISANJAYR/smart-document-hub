import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, errorMessage, setLogoutHandler, tokens } from '../lib/api';

const AuthContext = createContext(null);

export const DEMO = { email: 'demo@dochub.dev', password: 'demo12345' };

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  const logout = useCallback(() => {
    tokens.clear();
    setUser(null);
  }, []);

  useEffect(() => {
    setLogoutHandler(() => setUser(null));
    if (!tokens.access) { setReady(true); return; }
    api.get('/auth/me')
      .then(({ data }) => setUser(data))
      .catch(() => tokens.clear())
      .finally(() => setReady(true));
  }, []);

  const login = useCallback(async (email, password) => {
    try {
      const { data } = await api.post('/auth/login', { email, password });
      tokens.set(data.access_token, data.refresh_token);
      setUser(data.user);
      return { ok: true };
    } catch (e) {
      return { ok: false, error: errorMessage(e, 'Sign in failed') };
    }
  }, []);

  const register = useCallback(async (full_name, email, password) => {
    try {
      await api.post('/auth/register', { full_name, email, password });
    } catch (e) {
      return { ok: false, error: errorMessage(e, 'Could not create the account') };
    }
    return login(email, password);
  }, [login]);

  const value = useMemo(() => ({ user, ready, login, register, logout, isAuthenticated: !!user }), [user, ready, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
