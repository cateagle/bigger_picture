import { apiFetch } from './client'
import type { UserSummary } from './types'

/** Admin only - lists every registered user. */
export function listUsers(): Promise<UserSummary[]> {
  return apiFetch<{ users: UserSummary[] }>('/api/v1/admin/users').then((res) => res.users)
}
