import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { LANG_SHORT } from '../lib/format';

export function StatusBadge({ status }) {
  const label = { completed: 'Ready', processing: 'Processing', pending: 'Queued', failed: 'Failed' }[status] || status;
  return <span className={`badge ${status}`}>{label}</span>;
}

export function LangChip({ lang }) {
  if (!lang) return null;
  return <span className="lang-chip" title={lang}>{LANG_SHORT[lang] || lang.toUpperCase()}</span>;
}

export function Tags({ tags = [], max = 4, onClick, active = [] }) {
  const shown = tags.slice(0, max);
  return (
    <span className="tags">
      {shown.map((t) =>
        onClick ? (
          <button key={t} className={`tag ${active.includes(t) ? 'on' : ''}`} onClick={(e) => { e.stopPropagation(); onClick(t); }}>{t}</button>
        ) : (
          <span key={t} className="tag">{t}</span>
        )
      )}
      {tags.length > max && <span className="tag faint">+{tags.length - max}</span>}
    </span>
  );
}

export function Meter({ value = 0, low = 0.5 }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <span className={`meter ${value < low ? 'low' : ''}`}>
      <span className="track"><span className="fill" style={{ width: `${pct}%` }} /></span>
      {pct}%
    </span>
  );
}

export function Empty({ title, children, action }) {
  return (
    <div className="empty fade-up">
      <h3>{title}</h3>
      <p className="muted" style={{ maxWidth: 420, margin: '0 auto' }}>{children}</p>
      {action && <div className="mt-16">{action}</div>}
    </div>
  );
}

export function Loading({ label = 'Loading…' }) {
  return <div className="row muted small" style={{ padding: '32px 0', justifyContent: 'center' }}><span className="spinner" /> {label}</div>;
}

export function SkeletonRows({ n = 4, h = 18 }) {
  return (
    <div className="stack" style={{ gap: 12 }}>
      {Array.from({ length: n }).map((_, i) => <div key={i} className="skeleton" style={{ height: h, width: `${90 - i * 8}%` }} />)}
    </div>
  );
}

export function Modal({ title, children, onClose, actions }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose?.();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
  return (
    <div className="modal-back" onMouseDown={(e) => e.target === e.currentTarget && onClose?.()}>
      <div className="modal" role="dialog" aria-modal="true">
        <h3>{title}</h3>
        <div className="muted">{children}</div>
        <div className="actions">{actions}</div>
      </div>
    </div>
  );
}

export function TraceList({ steps = [], numbered = true }) {
  return (
    <div className="timeline">
      {steps.map((s, i) => (
        <div key={`${s.key}-${i}`} className={`timeline-row ${s.status}`}>
          <span className="n">{numbered ? String(i + 1).padStart(2, '0') : ''}</span>
          <span className="dot" />
          <span>{s.label}</span>
          <span className="ms">{s.ms == null ? '' : s.ms >= 1000 ? `${(s.ms / 1000).toFixed(1)} s` : `${s.ms} ms`}</span>
          {s.detail && <span className="detail">{s.detail}</span>}
        </div>
      ))}
    </div>
  );
}

export function DocLink({ id, children }) {
  return <Link to={`/library/${id}`} className="link">{children}</Link>;
}
