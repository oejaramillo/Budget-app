import { useState } from 'react'

import CurrenciesManager from '../currencies/CurrenciesManager'
import OpsOverview from './OpsOverview'
import OperationsConsole from './OperationsConsole'
import UsersAdmin from './UsersAdmin'

const SECTIONS = [
  { id: 'overview', label: 'Overview' },
  { id: 'currencies', label: 'Currencies' },
  { id: 'operations', label: 'Operations' },
  { id: 'users', label: 'Tenants' },
]

/**
 * Superuser console.
 *
 * A sub-navigation inside the Superuser tab rather than another top-level tab set,
 * so the main tabs stay about the user's own money.
 *
 * Rendering this is not the security boundary: every endpoint it calls requires
 * `is_superuser`, and the parent tab is only shown to superusers.
 */
export default function SuperuserHub() {
  const [section, setSection] = useState('overview')

  return (
    <div>
      <div className="tabs mb-3" role="tablist">
        {SECTIONS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            className="tab"
            aria-selected={section === item.id}
            onClick={() => setSection(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {section === 'overview' && <OpsOverview />}
      {section === 'currencies' && <CurrenciesManager />}
      {section === 'operations' && <OperationsConsole />}
      {section === 'users' && <UsersAdmin />}
    </div>
  )
}
