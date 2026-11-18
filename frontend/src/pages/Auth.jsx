import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth, DEMO } from '../context/AuthContext';
import { useLang } from '../lib/i18n';

function Side() {
  return (
    <aside className="auth-side">
      <div className="eyebrow">Smart Document Hub</div>
      <blockquote>
        “Which of our circulars mention a deadline before the end of the month — and who do they apply to?”
        <div className="small muted mt-16" style={{ fontFamily: 'var(--sans)' }}>The kind of question this was built to answer, in English or Malayalam.</div>
      </blockquote>
      <div className="small faint">Built for Smart India Hackathon 2025 · PS SIH25080</div>
    </aside>
  );
}

export function Login() {
  const { login } = useAuth();
  const { t } = useLang();
  const nav = useNavigate();
  const loc = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e, creds) => {
    e?.preventDefault();
    setBusy(true); setError('');
    const r = await login(creds?.email ?? email, creds?.password ?? password);
    setBusy(false);
    if (r.ok) nav(loc.state?.from || '/dashboard', { replace: true });
    else setError(r.error);
  };

  return (
    <div className="auth">
      <Side />
      <div className="auth-form">
        <form onSubmit={submit} className="fade-up">
          <div>
            <h2>{t('auth.signin')}</h2>
            <p className="muted mt-8">Welcome back. Sign in to your workspace.</p>
          </div>
          <div className="demo-box">
            <span>Exploring? Use the demo account with sample documents.</span>
            <button type="button" className="btn btn-sm" disabled={busy} onClick={() => submit(null, DEMO)}>Use demo</button>
          </div>
          {error && <div className="form-error">{error}</div>}
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input id="password" className="input" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <button className="btn btn-primary" style={{ height: 38 }} disabled={busy}>{busy ? <span className="spinner" /> : t('auth.signin')}</button>
          <p className="small muted">No account yet? <Link to="/register" className="link">{t('auth.register')}</Link></p>
        </form>
      </div>
    </div>
  );
}

export function Register() {
  const { register } = useAuth();
  const { t } = useLang();
  const nav = useNavigate();
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    if (form.password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    setBusy(true); setError('');
    const r = await register(form.name, form.email, form.password);
    setBusy(false);
    if (r.ok) nav('/library');
    else setError(r.error);
  };

  return (
    <div className="auth">
      <Side />
      <div className="auth-form">
        <form onSubmit={submit} className="fade-up">
          <div>
            <h2>{t('auth.register')}</h2>
            <p className="muted mt-8">Your documents stay private to your account.</p>
          </div>
          {error && <div className="form-error">{error}</div>}
          <div className="field">
            <label htmlFor="name">Full name</label>
            <input id="name" className="input" required minLength={2} autoComplete="name" value={form.name} onChange={set('name')} />
          </div>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" className="input" type="email" required autoComplete="email" value={form.email} onChange={set('email')} />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input id="password" className="input" type="password" required autoComplete="new-password" value={form.password} onChange={set('password')} />
            <span className="xsmall faint">At least 8 characters.</span>
          </div>
          <button className="btn btn-primary" style={{ height: 38 }} disabled={busy}>{busy ? <span className="spinner" /> : t('auth.register')}</button>
          <p className="small muted">Already registered? <Link to="/login" className="link">{t('auth.signin')}</Link></p>
        </form>
      </div>
    </div>
  );
}
