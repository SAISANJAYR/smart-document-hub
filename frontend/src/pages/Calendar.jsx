import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Download } from 'lucide-react';
import { api } from '../lib/api';
import { useLang } from '../lib/i18n';
import { dayKey, daysUntil, fmtDate, inDays, localDayKey, stripExt, TYPE_LABEL } from '../lib/format';
import { Empty, Loading } from '../components/ui';

const DOW = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function buildICS(events) {
  const pad = (s) => s.replace(/[,;\\]/g, (c) => `\\${c}`).replace(/\n/g, ' ');
  const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Smart Document Hub//EN', 'CALSCALE:GREGORIAN'];
  for (const e of events) {
    const d = dayKey(e.event_date).replace(/-/g, '');
    lines.push('BEGIN:VEVENT', `UID:${e.id}@smart-document-hub`, `DTSTART;VALUE=DATE:${d}`, `SUMMARY:${pad(e.event_title)}`,
      `DESCRIPTION:${pad(`${e.document_filename} — ${e.description || ''}`).slice(0, 900)}`, 'END:VEVENT');
  }
  lines.push('END:VCALENDAR');
  return lines.join('\r\n');
}

export default function Calendar() {
  const { t, lang } = useLang();
  const [events, setEvents] = useState(null);
  const [cursor, setCursor] = useState(() => { const d = new Date(); d.setDate(1); return d; });
  const [selected, setSelected] = useState(null);
  const [types, setTypes] = useState([]);
  const [showPast, setShowPast] = useState(false);

  useEffect(() => { api.get('/documents/calendar').then(({ data }) => setEvents(data)).catch(() => setEvents([])); }, []);

  const filtered = useMemo(() => (events || []).filter((e) => !types.length || types.includes(e.event_type)), [events, types]);
  const byDay = useMemo(() => {
    const m = {};
    for (const e of filtered) (m[dayKey(e.event_date)] ||= []).push(e);
    return m;
  }, [filtered]);

  const cells = useMemo(() => {
    const first = new Date(cursor);
    const offset = (first.getDay() + 6) % 7;
    const start = new Date(first); start.setDate(1 - offset);
    return Array.from({ length: 42 }, (_, i) => { const d = new Date(start); d.setDate(start.getDate() + i); return d; });
  }, [cursor]);

  const todayKey = localDayKey(new Date());
  const agenda = useMemo(() => {
    let list = filtered;
    if (selected) list = list.filter((e) => dayKey(e.event_date) === selected);
    else if (!showPast) list = list.filter((e) => daysUntil(e.event_date) >= 0);
    const groups = {};
    for (const e of list) (groups[dayKey(e.event_date)] ||= []).push(e);
    return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b));
  }, [filtered, selected, showPast]);

  const counts = useMemo(() => {
    const c = {};
    for (const e of events || []) c[e.event_type] = (c[e.event_type] || 0) + 1;
    return c;
  }, [events]);

  const exportICS = () => {
    const blob = new Blob([buildICS(filtered)], { type: 'text/calendar' });
    const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: 'document-deadlines.ics' });
    a.click(); URL.revokeObjectURL(a.href);
  };

  const move = (n) => { const d = new Date(cursor); d.setMonth(d.getMonth() + n); setCursor(d); setSelected(null); };
  const locale = lang === 'ml' ? 'ml-IN' : 'en-IN';

  if (events === null) return <Loading />;

  return (
    <div className="page-wide">
      <div className="page-head">
        <div>
          <h1 style={{ fontSize: 34 }}>{t('cal.title')}</h1>
          <p>{t('cal.sub')}</p>
        </div>
        <button className="btn" onClick={exportICS} disabled={!filtered.length}><Download size={15} /> Export .ics</button>
      </div>

      {events.length === 0 ? (
        <Empty title="No dates found yet" action={<Link to="/library" className="btn">Upload documents</Link>}>
          When a document mentions a deadline, meeting, payment or expiry, it will appear here automatically.
        </Empty>
      ) : (
        <div className="cal-layout">
          <section style={{ minWidth: 0 }}>
            <div className="row mb-12" style={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
              <div className="row" style={{ gap: 6 }}>
                <button className="btn btn-sm" onClick={() => move(-1)} aria-label="Previous month"><ChevronLeft size={15} /></button>
                <button className="btn btn-sm" onClick={() => move(1)} aria-label="Next month"><ChevronRight size={15} /></button>
                <h2 style={{ fontSize: 22, marginLeft: 8 }}>{cursor.toLocaleDateString(locale, { month: 'long', year: 'numeric' })}</h2>
                <button className="text-btn" style={{ marginLeft: 10 }} onClick={() => { const d = new Date(); d.setDate(1); setCursor(d); setSelected(null); }}>Today</button>
              </div>
              <div className="tags">
                {Object.entries(counts).map(([type, n]) => (
                  <button key={type} className={`tag ${types.includes(type) ? 'on' : ''}`} onClick={() => setTypes((s) => (s.includes(type) ? s.filter((x) => x !== type) : [...s, type]))}>
                    {TYPE_LABEL[type] || type} <span className="count">{n}</span>
                  </button>
                ))}
              </div>
            </div>
            <div className="cal">
              {DOW.map((d) => <div key={d} className="dow">{d}</div>)}
              {cells.map((d) => {
                const key = localDayKey(d);
                const evs = byDay[key] || [];
                const out = d.getMonth() !== cursor.getMonth();
                return (
                  <div key={key} className={`day ${out ? 'out' : ''} ${key === todayKey ? 'today' : ''} ${selected === key ? 'sel' : ''} ${evs.length ? 'has' : ''}`} onClick={() => setSelected(selected === key ? null : key)}>
                    <span className="d">{d.getDate()}</span>
                    {evs.slice(0, 3).map((e) => <span key={e.id} className={`ev ${e.urgency}`} title={e.event_title}>{e.event_title.replace(/^[^·]+·\s*/, '')}</span>)}
                    {evs.length > 3 && <span className="more">+{evs.length - 3} more</span>}
                  </div>
                );
              })}
            </div>
            <div className="row mt-12 xsmall muted" style={{ gap: 14 }}>
              <span className="row" style={{ gap: 5 }}><span className="urgency high" /> High urgency</span>
              <span className="row" style={{ gap: 5 }}><span className="urgency medium" /> Medium</span>
              <span className="row" style={{ gap: 5 }}><span className="urgency low" /> Low</span>
            </div>
          </section>

          <aside>
            <div className="section-title">
              {selected ? fmtDate(`${selected}T00:00:00Z`, { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'UTC' }, locale) : 'Agenda'}
              {selected ? <button className="aside text-btn" onClick={() => setSelected(null)}>Show all</button>
                : <button className="aside text-btn" onClick={() => setShowPast((v) => !v)}>{showPast ? 'Hide past' : 'Show past'}</button>}
            </div>
            {agenda.length === 0 ? <p className="note">Nothing scheduled{selected ? ' on this day' : ''}.</p> : agenda.map(([day, evs]) => (
              <div key={day}>
                <div className="agenda-day">
                  <span>{fmtDate(`${day}T00:00:00Z`, { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' }, locale)}</span>
                  <span>{inDays(daysUntil(`${day}T00:00:00Z`))}</span>
                </div>
                {evs.map((e) => (
                  <div key={e.id} className="agenda-item">
                    <span className={`urgency ${e.urgency}`} />
                    <div style={{ minWidth: 0 }}>
                      <div className="title">{e.event_title}</div>
                      <div className="xsmall faint mt-8" style={{ marginTop: 3 }}>
                        {TYPE_LABEL[e.event_type] || 'Date'} · <Link className="link" to={`/library/${e.document_id}`}>{stripExt(e.document_filename)}</Link>
                      </div>
                      {e.description && <div className="xsmall muted" style={{ marginTop: 5, lineHeight: 1.5 }}>“{e.description.slice(0, 160)}{e.description.length > 160 ? '…' : ''}”</div>}
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </aside>
        </div>
      )}
    </div>
  );
}
