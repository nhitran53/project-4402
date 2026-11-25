import { useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth'

function navClass({ isActive }) {
  return `flex items-center border-b-2 px-2.5 py-3 font-medium lg:px-3 ${isActive
    ? 'border-sky-300 text-white'
    : 'border-transparent text-slate-300 hover:text-white'}`
}

export default function Layout() {
  const { user, isAdmin, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()

  return (
    <div className="flex min-h-screen flex-col">
      <header className="bg-nav text-white">
        <div className="mx-auto flex max-w-[1360px] flex-wrap items-center gap-x-6 px-4 sm:px-6">
          <Link to="/" className="py-3.5 text-lg font-semibold" onClick={() => setMenuOpen(false)}>
            PC Parts
          </Link>
          <button type="button" className="ml-auto px-2 py-2 lg:hidden" onClick={() => setMenuOpen(!menuOpen)}
            aria-expanded={menuOpen} aria-controls="main-nav">
            {menuOpen ? 'Close menu' : 'Menu'}
          </button>
          <nav id="main-nav" aria-label="Main navigation"
            className={`${menuOpen ? 'flex' : 'hidden'} w-full flex-wrap self-stretch lg:flex lg:w-auto lg:flex-1`}
            onClick={() => setMenuOpen(false)}>
            <NavLink to="/" end className={navClass}>Build</NavLink>
            <NavLink to="/products" className={navClass}>Browse parts</NavLink>
            <NavLink to="/stores" className={navClass}>Stores</NavLink>
            {user && <NavLink to="/builds" className={navClass}>My builds</NavLink>}
            {isAdmin && <NavLink to="/admin" className={navClass}>Admin</NavLink>}
            <div className="flex w-full items-center gap-3 border-t border-slate-600 px-2.5 py-3 lg:ml-auto lg:w-auto lg:border-0 lg:px-0">
              {user ? (
                <>
                  <span className="break-all text-slate-300">{user.username}</span>
                  <button type="button" className="shrink-0 font-medium hover:underline" onClick={logout}>Log out</button>
                </>
              ) : (
                <Link to="/login" state={{ from: location.pathname + location.search }} className="font-medium hover:underline">
                  Log in
                </Link>
              )}
            </div>
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1360px] flex-1 px-4 py-6 sm:px-6">
        <Outlet />
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-[1360px] flex-wrap justify-between gap-x-4 gap-y-1 px-4 py-4 text-xs text-muted sm:px-6">
          <span>CSC 4402 Database Management Systems · Louisiana State University</span>
          <span>Prices and availability are sample data.</span>
        </div>
      </footer>
    </div>
  )
}
