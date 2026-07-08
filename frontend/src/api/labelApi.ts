import { apiFetch } from './client'
import type { Label } from './types'

/** Real endpoint: GET /api/v1/annotate/labels. */
export function fetchLabels(): Promise<Label[]> {
  return apiFetch<{ labels: Label[] }>('/api/v1/annotate/labels').then((res) => res.labels)
}

/** Scientist/admin only - real endpoint: POST /api/v1/dataset/labels/create. */
export function createLabel(input: { scope: string; title: string; description?: string | null }): Promise<Label> {
  return apiFetch<Label>('/api/v1/dataset/labels/create', {
    method: 'POST',
    body: JSON.stringify({ uuid: crypto.randomUUID(), ...input }),
  })
}

/** Scientist/admin only - real endpoint: POST /api/v1/dataset/labels/update. */
export function updateLabel(
  uuid: string,
  input: { scope?: string; title?: string; description?: string | null },
): Promise<Label> {
  return apiFetch<Label>('/api/v1/dataset/labels/update', {
    method: 'POST',
    body: JSON.stringify({ uuid, ...input }),
  })
}
