import { apiFetch } from './client'
import type { User } from './types'

/** Creates a new `annotator` user and sets the session cookie. */
export function signup(username: string): Promise<User> {
  return apiFetch<User>('/api/v1/auth/signup', {
    method: 'POST',
    body: JSON.stringify({ username }),
  })
}

/** Resolves the identity behind the current session cookie, if any. */
export function me(): Promise<User> {
  return apiFetch<User>('/api/v1/auth/me')
}

/** Clears the session cookie. */
export function logout(): Promise<void> {
  return apiFetch<void>('/api/v1/auth/logout', { method: 'POST' })
}
