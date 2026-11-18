import axios from 'axios';

// Same-origin in dev (Vite proxy) and in Docker (nginx). Override with VITE_API_URL if hosted separately.
const API_ROOT = import.meta.env.VITE_API_URL || '';

export const api = axios.create({ baseURL: `${API_ROOT}/api/v1` });

const TOKEN = 'sdh.access';
const REFRESH = 'sdh.refresh';

export const tokens = {
  get access() { try { return localStorage.getItem(TOKEN); } catch { return null; } },
  get refresh() { try { return localStorage.getItem(REFRESH); } catch { return null; } },
  set(access, refresh) {
    try {
      localStorage.setItem(TOKEN, access);
      if (refresh) localStorage.setItem(REFRESH, refresh);
    } catch { /* storage unavailable */ }
  },
  clear() {
    try { localStorage.removeItem(TOKEN); localStorage.removeItem(REFRESH); } catch { /* ignore */ }
  },
};

api.interceptors.request.use((config) => {
  const t = tokens.access;
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

// On 401, try the refresh token once, then replay the request.
let refreshing = null;
let onLogout = () => {};
export const setLogoutHandler = (fn) => { onLogout = fn; };

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    const isAuthCall = original?.url?.startsWith('/auth/');
    if (error.response?.status === 401 && !original._retried && !isAuthCall && tokens.refresh) {
      original._retried = true;
      try {
        refreshing = refreshing || axios.post(`${API_ROOT}/api/v1/auth/refresh`, { refresh_token: tokens.refresh });
        const { data } = await refreshing;
        tokens.set(data.access_token, data.refresh_token);
        return api(original);
      } catch {
        tokens.clear();
        onLogout();
      } finally {
        refreshing = null;
      }
    } else if (error.response?.status === 401 && !isAuthCall) {
      tokens.clear();
      onLogout();
    }
    return Promise.reject(error);
  }
);

export const errorMessage = (e, fallback = 'Something went wrong') => {
  const d = e?.response?.data?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d) && d[0]?.msg) return d[0].msg.replace(/^Value error, /, '');
  if (e?.code === 'ERR_NETWORK') return 'Cannot reach the server. Is the API running?';
  return fallback;
};

export const healthUrl = `${API_ROOT}/health`;
