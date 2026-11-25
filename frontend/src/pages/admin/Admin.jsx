import { Link, NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../../auth'
import { Loading, PageTitle } from '../../components/ui'

const TABS = [
  { to: '/admin', label: 'Products', end: true },
  { to: '/admin/listings', label: 'Listings' },
  { to: '/admin/stores', label: 'Stores' },
  { to: '/admin/users', label: 'Users' },
]

export default function Admin() {
  const { user, isAdmin, checking } = useAuth()

  if (checking) return <Loading />
  if (!isAdmin) {
    return (
      <div>
        <PageTitle>Admin</PageTitle>
        <p>
          {user ? 'Admin access is required. ' : ''}
          <Link to="/login" state={{ from: '/admin' }} className="link">Log in as an administrator</Link>.
        </p>
      </div>
    )
  }

  return (
    <div>
      <PageTitle>Admin</PageTitle>
      <nav className="mb-4 flex flex-wrap border-b border-line" aria-label="Admin sections">
        {TABS.map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            end={t.end}
            className={({ isActive }) =>
              `-mb-px border-b-2 px-3 py-2 font-semibold ${
                isActive ? 'border-action text-ink' : 'border-transparent text-link hover:underline'
              }`
            }
          >
            {t.label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  )
}
