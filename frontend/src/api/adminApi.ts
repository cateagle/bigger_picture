import { apiFetch } from './client'
import type { Role, UserSummary } from './types'

/** Admin only - lists every registered user. */
export function listUsers(): Promise<UserSummary[]> {
  return apiFetch<{ users: UserSummary[] }>('/api/v1/admin/users').then((res) => res.users)
}

/** Admin only - real endpoint: POST /api/v1/admin/users/create. */
export function createUser(input: { username: string; role: Role; expert_level: number }): Promise<UserSummary> {
  return apiFetch<UserSummary>('/api/v1/admin/users/create', {
    method: 'POST',
    body: JSON.stringify({ uuid: crypto.randomUUID(), ...input }),
  })
}

/** Admin only - real endpoint: POST /api/v1/admin/users/update. */
export function updateUser(
  uuid: string,
  input: { username?: string; role?: Role; expert_level?: number },
): Promise<UserSummary> {
  return apiFetch<UserSummary>('/api/v1/admin/users/update', {
    method: 'POST',
    body: JSON.stringify({ uuid, ...input }),
  })
}
