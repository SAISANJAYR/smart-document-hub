import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { LogOut, Menu, User as UserIcon, BookOpen } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useLang } from '../lib/i18n';
import { healthUrl } from '../lib/api';

export function BrandMark({ size = 22 }) {
  return (
    <span className="brand-mark" style={{ width: size, height: size }} aria-hidden>
      <svg width={size * 0.62} height={size * 0.62} viewBox="0 0 16 16" fill="none">
        <path d="M3.5 1.5h5.5l3.5 3.5v9.5h-9z" stroke="#fff" strokeWidth="1.4" strokeLinejoin="round" />
        <path d="M6 9h4.5M6 11.6h3" stroke="#fff" strokeWidth="1.4" strokeLinecap="round" />
      </svg>
    </span>
  );
}

function useHealth() {
  const [online, setOnline] = useState(true);
  useEffect(() => {
    let alive = true;
    const check = () => fetch(healthUrl).then((r) => alive && setOnline(r.ok)).catch(() => alive && setOnline(false));
    check();
    const id = setInterval(check, 30000);
    return () => { alive = false; clearInterval(id); };
  }, []);
  return online;
}

export function LangSwitch() {
  const { lang, setLang } = useLang();
  return (
    <div className="lang-switch" role="group" aria-label="Interface language">
      <button className={lang === 'en' ? 'on' : ''} onClick={() => setLang('en')} lang="en">English</button>
      <span className="sep">/</span>
      <button className={lang === 'ml' ? 'on' : ''} onClick={() => setLang('ml')} lang="ml">മലയാളം</button>
    </div>
  );
}

const NAV = [
  ['/dashboard', 'nav.dashboard'],
  ['/library', 'nav.library'],
  ['/ask', 'nav.ask'],
  ['/search', 'nav.search'],
  ['/calendar', 'nav.calendar'],
  ['/graph', 'nav.graph'],
  ['/history', 'nav.history'],
];

export default function Header() {
  const { user, logout } = useAuth();
  const { t } = useLang();
  const online = useHealth();
  const [menu, setMenu] = useState(false);
  const [mobile, setMobile] = useState(false);
  const ref = useRef(null);
  const nav = useNavigate();
  const loc = useLocation();

  useEffect(() => { setMobile(false); setMenu(false); }, [loc.pathname]);
  useEffect(() => {
    const close = (e) => ref.current && !ref.current.contains(e.target) && setMenu(false);
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);

  const initials = (user?.full_name || '?').split(' ').map((s) => s[0]).slice(0, 2).join('').toUpperCase();

  return (
    <header className="topbar">
      <div className="topbar-inner">
        {user && (
          <button className="btn btn-ghost btn-sm hamburger" onClick={() => setMobile((v) => !v)} aria-label="Menu">
            <Menu size={18} />
          </button>
        )}
        <Link to={user ? '/dashboard' : '/'} className="brand">
          <BrandMark /> Smart Document Hub
        </Link>
        {user && (
          <nav className={`nav ${mobile ? 'open' : ''}`}>
            {NAV.map(([to, key]) => (
              <NavLink key={to} to={to} className={({ isActive }) => (isActive ? 'active' : '')}>{t(key)}</NavLink>
            ))}
          </nav>
        )}
        <div className="top-right">
          <span className={`status-dot ${online ? '' : 'off'}`}>{online ? t('status.online') : t('status.offline')}</span>
          <LangSwitch />
          {user ? (
            <div className="user-chip" ref={ref}>
              <button onClick={() => setMenu((v) => !v)} aria-haspopup="menu" aria-expanded={menu}>
                <span className="avatar">{initials}</span>
                <span className="who"><b>{user.full_name}</b><span>{user.role}</span></span>
              </button>
              {menu && (
                <div className="menu fade-up" role="menu">
                  <div className="menu-head">
                    <div style={{ fontWeight: 500 }}>{user.full_name}</div>
                    <div className="small muted">{user.email}</div>
                  </div>
                  <Link to="/" role="menuitem"><BookOpen size={14} /> About this project</Link>
                  <a href="/docs" target="_blank" rel="noreferrer" role="menuitem">
                    <UserIcon size={14} /> API reference
                  </a>
                  <button className="menu-item" role="menuitem" onClick={() => { logout(); nav('/'); }}>
                    <LogOut size={14} /> {t('auth.signout')}
                  </button>
                </div>
              )}
            </div>
          ) : (
            loc.pathname !== '/login' && <Link to="/login" className="btn btn-sm">{t('auth.signin')}</Link>
          )}
        </div>
      </div>
    </header>
  );
}
