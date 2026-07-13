import { request } from '../request';

interface BackendUser {
  id: number;
  username: string;
  display_name: string;
  learner_id: string | null;
  roles: string[];
  permissions: string[];
}

interface BackendTokenPair {
  access_token: string;
  refresh_token: string;
  user: BackendUser;
}

function mapUser(info: BackendUser): Api.Auth.UserInfo {
  localStorage.setItem('herbwise.user', JSON.stringify(info));
  return {
    userId: String(info.id),
    userName: info.display_name || info.username,
    roles: info.roles.includes('admin') ? ['R_SUPER', 'R_ADMIN'] : ['R_DENIED'],
    buttons: info.permissions || []
  };
}

/** Fallback login for direct API use. The main portal remains the canonical login entry. */
export async function fetchLogin(userName: string, password: string) {
  const result = await request<BackendTokenPair>({
    url: '/auth/login',
    method: 'post',
    data: { username: userName, password }
  });
  if (result.error) return result;
  mapUser(result.data.user);
  return {
    ...result,
    data: {
      token: result.data.access_token,
      refreshToken: result.data.refresh_token
    }
  };
}

/** Get and normalize the current HerbWise administrator. */
export async function fetchGetUserInfo() {
  const result = await request<BackendUser>({ url: '/auth/me' });
  if (result.error) return result;
  return { ...result, data: mapUser(result.data) };
}

/** Refresh the shared backend session. */
export async function fetchRefreshToken(refreshToken: string) {
  const result = await request<BackendTokenPair>({
    url: '/auth/refresh',
    method: 'post',
    data: { refresh_token: refreshToken }
  });
  if (result.error) return result;
  mapUser(result.data.user);
  return {
    ...result,
    data: {
      token: result.data.access_token,
      refreshToken: result.data.refresh_token
    }
  };
}

/** Retained for Soybean's unused request-example view. */
export function fetchCustomBackendError(code: string, msg: string) {
  return request({ url: '/auth/error', params: { code, msg } });
}
