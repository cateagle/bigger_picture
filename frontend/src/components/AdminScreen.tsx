import { useState } from 'react'
import { createLabel, fetchLabels, updateLabel } from '../api/labelApi'
import type { RegionMetadataInput } from '../api/regionApi'
import { createRegion, fetchRegions, updateRegion } from '../api/regionApi'
import type { User } from '../api/types'
import SimpleEntityAdmin from './admin/SimpleEntityAdmin'
import UsersAdmin from './admin/UsersAdmin'
import './AdminScreen.css'

/**
 * SimpleEntityAdmin builds its create/update payload dynamically from a field
 * config, so it only knows the input shape as `Record<string, unknown>`. The
 * real API functions want a narrower, specific input type; these adapters
 * bridge that gap in one place instead of loosening SimpleEntityAdmin's types.
 */
function createRegionAdapter(input: Record<string, unknown>) {
  return createRegion(input as { title: string; description?: string | null; metadata?: RegionMetadataInput | null })
}
function updateRegionAdapter(uuid: string, input: Record<string, unknown>) {
  return updateRegion(uuid, input as { title?: string; description?: string | null; metadata?: RegionMetadataInput | null })
}
function createLabelAdapter(input: Record<string, unknown>) {
  return createLabel(input as { scope: string; title: string; description?: string | null })
}
function updateLabelAdapter(uuid: string, input: Record<string, unknown>) {
  return updateLabel(uuid, input as { scope?: string; title?: string; description?: string | null })
}

type Tab = 'regions' | 'labels' | 'users'

const REGION_FIELDS = [
  { key: 'title', label: 'Title', type: 'text', required: true } as const,
  { key: 'description', label: 'Description', type: 'textarea' } as const,
  { key: 'metadata', label: 'Metadata (JSON)', type: 'json' } as const,
]

const LABEL_FIELDS = [
  { key: 'scope', label: 'Scope', type: 'text', required: true } as const,
  { key: 'title', label: 'Title', type: 'text', required: true } as const,
  { key: 'description', label: 'Description', type: 'textarea' } as const,
]

export default function AdminScreen({ user, onBack }: { user: User; onBack: () => void }) {
  const [tab, setTab] = useState<Tab>('regions')
  const isAdmin = user.role === 'admin'

  return (
    <div className="game-screen">
      <header className="game-header">
        <button type="button" className="back-link" onClick={onBack}>
          ← Back to games
        </button>
        <h1>Admin</h1>
        <p>Manage regions, labels{isAdmin ? ', and users' : ''}.</p>
      </header>

      <div className="admin-tab-bar">
        <button type="button" className={`btn${tab === 'regions' ? ' btn-primary' : ''}`} onClick={() => setTab('regions')}>
          Regions
        </button>
        <button type="button" className={`btn${tab === 'labels' ? ' btn-primary' : ''}`} onClick={() => setTab('labels')}>
          Labels
        </button>
        {isAdmin && (
          <button type="button" className={`btn${tab === 'users' ? ' btn-primary' : ''}`} onClick={() => setTab('users')}>
            Users
          </button>
        )}
      </div>

      {tab === 'regions' && (
        <SimpleEntityAdmin
          entityName="Regions"
          fields={REGION_FIELDS}
          fetchList={fetchRegions}
          create={createRegionAdapter}
          update={updateRegionAdapter}
        />
      )}
      {tab === 'labels' && (
        <SimpleEntityAdmin
          entityName="Labels"
          fields={LABEL_FIELDS}
          fetchList={fetchLabels}
          create={createLabelAdapter}
          update={updateLabelAdapter}
        />
      )}
      {tab === 'users' && isAdmin && <UsersAdmin currentUserUuid={user.uuid} />}
    </div>
  )
}
