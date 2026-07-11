# Soybean Admin authentication flow

Use login, attach access token, refresh with `/auth/refresh` before expiry and revoke with `/auth/logout`. A 401 requires re-authentication; a 403 is a learner-boundary or role restriction.
