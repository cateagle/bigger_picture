import { apiFetch } from './client'
import type { Role, UserSummary } from './types'

/** Admin only - lists every registered user. */
export function listUsers(): Promise<UserSummary[]> {
  return apiFetch<{ users: UserSummary[] }>('/api/v1/admin/users').then((res) => res.users)
}

/**
 * Admin only - real endpoint: POST /api/v1/admin/users/create.
 * `password` is required when role is scientist/admin, and must be omitted
 * when role is annotator (annotator accounts never have a password).
 */
export function createUser(
  input: { username: string; role: Role; expert_level: number; password?: string },
): Promise<UserSummary> {
  return apiFetch<UserSummary>('/api/v1/admin/users/create', {
    method: 'POST',
    body: JSON.stringify({ uuid: crypto.randomUUID(), ...input }),
  })
}

/**
 * Admin only - real endpoint: POST /api/v1/admin/users/update.
 * `password` sets/replaces the stored credential; omit to leave it untouched.
 */
export function updateUser(
  uuid: string,
  input: { username?: string; role?: Role; expert_level?: number; password?: string },
): Promise<UserSummary> {
  return apiFetch<UserSummary>('/api/v1/admin/users/update', {
    method: 'POST',
    body: JSON.stringify({ uuid, ...input }),
  })
}
