import { localStg } from '@/utils/storage';

const HANDOFF_PREFIX = 'HERBWISE_ADMIN_AUTH:';
const ACCESS_TOKEN_KEY = 'herbwise.access_token';
const REFRESH_TOKEN_KEY = 'herbwise.refresh_token';

interface AdminHandoff {
  accessToken: string;
  refreshToken: string;
}

function persistTokens(payload: AdminHandoff) {
  localStg.set('token', payload.accessToken);
  localStg.set('refreshToken', payload.refreshToken);
  localStorage.setItem(ACCESS_TOKEN_KEY, payload.accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, payload.refreshToken);
}

export function consumeAdminHandoff() {
  const raw = window.name;
  window.name = '';

  if (raw.startsWith(HANDOFF_PREFIX)) {
    try {
      const payload = JSON.parse(atob(raw.slice(HANDOFF_PREFIX.length))) as AdminHandoff;
      if (payload.accessToken && payload.refreshToken) {
        persistTokens(payload);
        return true;
      }
    } catch {
      // Invalid handoffs are handled by the normal authentication guard.
    }
  }

  const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (accessToken && refreshToken && !localStg.get('token')) {
    persistTokens({ accessToken, refreshToken });
    return true;
  }

  return false;
}

export function portalLoginUrl() {
  const portal = import.meta.env.VITE_PORTAL_URL || 'http://localhost:5173';
  return `${portal.replace(/\/$/, '')}/login?role=admin`;
}

export function portalLogoutUrl() {
  const portal = import.meta.env.VITE_PORTAL_URL || 'http://localhost:5173';
  return `${portal.replace(/\/$/, '')}/login?role=admin&logout=1`;
}

export function portalHomeUrl() {
  return (import.meta.env.VITE_PORTAL_URL || 'http://localhost:5173').replace(/\/$/, '');
}
