import { useState } from 'react'
import { createLabel, fetchLabels, updateLabel } from '../api/labelApi'
import type { User } from '../api/types'
import DatasetAdmin from './admin/DatasetAdmin'
import RegionsAdmin from './admin/RegionsAdmin'
import SimpleEntityAdmin from './admin/SimpleEntityAdmin'
import UsersAdmin from './admin/UsersAdmin'
import './AdminScreen.css'

/**
 * SimpleEntityAdmin builds its create/update payload dynamically from a field
 * config, so it only knows the input shape as `Record<string, unknown>`. The
 * real API functions want a narrower, specific input type; these adapters
 * bridge that gap in one place instead of loosening SimpleEntityAdmin's types.
 */
function createLabelAdapter(input: Record<string, unknown>) {
  return createLabel(input as { scope: string; title: string; description?: string | null })
}
function updateLabelAdapter(uuid: string, input: Record<string, unknown>) {
  return updateLabel(uuid, input as { scope?: string; title?: string; description?: string | null })
}

type Tab = 'regions' | 'labels' | 'users' | 'dataset'

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
        <p>Manage regions, labels, and the dataset{isAdmin ? ', and users' : ''}.</p>
      </header>

      <div className="admin-tab-bar">
        <button type="button" className={`btn${tab === 'regions' ? ' btn-primary' : ''}`} onClick={() => setTab('regions')}>
          Regions
        </button>
        <button type="button" className={`btn${tab === 'labels' ? ' btn-primary' : ''}`} onClick={() => setTab('labels')}>
          Labels
        </button>
        <button type="button" className={`btn${tab === 'dataset' ? ' btn-primary' : ''}`} onClick={() => setTab('dataset')}>
          Dataset
        </button>
        {isAdmin && (
          <button type="button" className={`btn${tab === 'users' ? ' btn-primary' : ''}`} onClick={() => setTab('users')}>
            Users
          </button>
        )}
      </div>

      {tab === 'regions' && <RegionsAdmin />}
      {tab === 'labels' && (
        <SimpleEntityAdmin
          entityName="Labels"
          fields={LABEL_FIELDS}
          fetchList={fetchLabels}
          create={createLabelAdapter}
          update={updateLabelAdapter}
        />
      )}
      {tab === 'dataset' && <DatasetAdmin />}
      {tab === 'users' && isAdmin && <UsersAdmin currentUserUuid={user.uuid} />}
    </div>
  )
}
