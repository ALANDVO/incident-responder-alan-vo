import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { 
  LayoutDashboard, 
  FileText, 
  Plus, 
  LogOut, 
  User, 
  Settings,
  Menu,
  X,
  ChevronDown
} from 'lucide-react';
import { useState } from 'react';
import clsx from 'clsx';

export function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/incidents', label: 'Incidents', icon: FileText },
    { path: '/incidents/new', label: 'New Incident', icon: Plus },
  ];

  return (
    <div className="min-h-screen flex flex-col">
      {/* Top Navigation */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
        <div className="container mx-auto px-4">
          <div className="flex h-16 items-center justify-between">
            {/* Logo and Desktop Nav */}
            <div className="flex items-center gap-8">
              <Link to="/" className="flex items-center gap-2 font-semibold text-slate-900" aria-label="Incident Responder Home">
                <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span className="hidden sm:block">Incident Responder</span>
              </Link>

              <nav className="hidden md:flex items-center gap-1" aria-label="Main navigation">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = location.pathname === item.path || 
                    (item.path !== '/' && location.pathname.startsWith(item.path));
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={clsx(
                        'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                        isActive
                          ? 'bg-blue-50 text-blue-700'
                          : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                      )}
                      aria-current={isActive ? 'page' : undefined}
                    >
                      <Icon className="w-4 h-4" aria-hidden="true" />
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </nav>
            </div>

            {/* User Menu */}
            <div className="flex items-center gap-4">
              <div className="relative" role="region" aria-label="User menu">
                <button
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
                  aria-expanded={userMenuOpen}
                  aria-haspopup="true"
                >
                  <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                    <User className="w-4 h-4 text-blue-600" aria-hidden="true" />
                  </div>
                  <span className="hidden sm:block">{user?.email || 'User'}</span>
                  <ChevronDown className="w-4 h-4" aria-hidden="true" />
                </button>

                {userMenuOpen && (
                  <>
                    <div 
                      className="fixed inset-0 z-20" 
                      onClick={() => setUserMenuOpen(false)} 
                      aria-hidden="true"
                    />
                    <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-slate-200 py-1 z-30" role="menu">
                      <div className="px-3 py-2 border-b border-slate-100">
                        <p className="text-sm font-medium text-slate-900">{user?.full_name || user?.email}</p>
                        <p className="text-xs text-slate-500 capitalize">{user?.role}</p>
                      </div>
                      <Link
                        to="/settings"
                        className="flex items-center gap-2 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
                        role="menuitem"
                        onClick={() => setUserMenuOpen(false)}
                      >
                        <Settings className="w-4 h-4" aria-hidden="true" />
                        Settings
                      </Link>
                      <button
                        onClick={logout}
                        className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-slate-50"
                        role="menuitem"
                      >
                        <LogOut className="w-4 h-4" aria-hidden="true" />
                        Sign out
                      </button>
                    </div>
                  </>
                )}
              </div>

              {/* Mobile menu button */}
              <button
                className="md:hidden p-2 rounded-lg text-slate-600 hover:bg-slate-100"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                aria-expanded={mobileMenuOpen}
                aria-controls="mobile-menu"
                aria-label="Toggle menu"
              >
                {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Nav */}
        {mobileMenuOpen && (
          <div id="mobile-menu" className="md:hidden border-t border-slate-200 bg-white animate-slideDown">
            <nav className="px-4 py-3 space-y-1" aria-label="Mobile navigation">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path || 
                  (item.path !== '/' && location.pathname.startsWith(item.path));
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={() => setMobileMenuOpen(false)}
                    className={clsx(
                      'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium',
                      isActive
                        ? 'bg-blue-50 text-blue-700'
                        : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                    )}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <Icon className="w-5 h-5" aria-hidden="true" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className="flex-1 container mx-auto px-4 py-6 w-full">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white">
        <div className="container mx-auto px-4 py-4">
          <p className="text-center text-sm text-slate-500">
            Incident Responder — AI Incident Response Copilot | Built by Alan Vo
          </p>
        </div>
      </footer>
    </div>
  );
}