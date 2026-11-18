import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, FileText } from 'lucide-react';
import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import { useLang } from '../lib/i18n';
import { daysUntil, fileKind, fmtDate, inDays, relative, stripExt, TYPE_LABEL } from '../lib/format';
import { LangChip, SkeletonRows, StatusBadge, Tags } from '../components/ui';

export default function Dashboard() {
  const { user } = useAuth();
  const { t, lang } = useLang();
  const nav = useNavigate();
  const [stats, setStats] = useState(null);
  const [docs, setDocs] = useState(null);
  const [events, setEvents] = useState(null);
  const [q, setQ] = useState('');

  useEffect(() => {
    let timer;
    const load = async () => {
      const today = new Date(); today.setHours(0, 0, 0, 0);
      const [s, d, e] = await Promise.all([
        api.get('/documents/stats'),
        api.get('/documents', { params: { size: 6 } }),
        api.get('/documents/calendar', { params: { start: today.toISOString() } }),
      ]);
      setStats(s.data); setDocs(d.data.items); setEvents(e.data.slice(0, 7));
      if (s.data.processing > 0) timer = setTimeout(load, 2500);
    };
    load().catch(() => { setDocs([]); setEvents([]); });
    return () => clearTimeout(timer);
  }, []);

  const hour = new Date().getHours();
  const greet = t(hour < 12 ? 'dash.greeting.morning' : hour < 17 ? 'dash.greeting.afternoon' : 'dash.greeting.evening');
  const first = (user?.full_name || '').split(' ')[0];

  const ask = (e) => { e.preventDefault(); if (q.trim()) nav(`/ask?q=${encodeURIComponent(q.trim())}`); };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 style={{ fontSize: 36 }}>{greet}, {first}</h1>
          <p>{t('dash.sub')}</p>
        </div>
        <Link to="/library" className="btn">Upload documents</Link>
      </div>

      <div className="stats">
        <div className="stat">
          <div className="label">{t('dash.documents')}</div>
          <div className="value">{stats ? stats.documents : '–'}</div>
          <div className="sub">{stats ? `${stats.processed} ${t('dash.processed')}${stats.processing ? ` · ${stats.processing} in progress` : ''}` : ' '}</div>
        </div>
        <div className="stat">
          <div className="label">{t('dash.deadlines')}</div>
          <div className={`value ${stats?.high_urgency ? 'danger' : ''}`}>{stats ? stats.upcoming_deadlines : '–'}</div>
          <div className="sub">{stats ? `${stats.high_urgency} ${t('dash.urgent')}` : ' '}</div>
        </div>
        <div className="stat">
          <div className="label">{t('dash.connections')}</div>
          <div className="value accent">{stats ? stats.connections : '–'}</div>
          <div className="sub">{t('dash.connectionsSub')}</div>
        </div>
        <div className="stat">
          <div className="label">{t('dash.questions')}</div>
          <div className="value ok">{stats ? stats.questions_asked : '–'}</div>
          <div className="sub">{t('dash.questionsSub')}</div>
        </div>
      </div>

      <form onSubmit={ask} className="mt-32">
        <div className="section-title">{t('dash.ask')}</div>
        <div className="row" style={{ gap: 10 }}>
          <input className="input" style={{ height: 42, fontSize: 15 }} placeholder={t('dash.askPh')} value={q} onChange={(e) => setQ(e.target.value)} lang={lang} />
          <button className="btn btn-primary" style={{ height: 42, padding: '0 18px' }}>{t('ask.run')} <ArrowRight size={15} /></button>
        </div>
      </form>

      <div className="grid-2 mt-48">
        <section>
          <div className="section-title">{t('dash.recent')} <Link to="/library" className="aside link">View all</Link></div>
          {docs === null ? <SkeletonRows n={5} /> : docs.length === 0 ? (
            <p className="muted">No documents yet. <Link className="link" to="/library">Upload your first file</Link>.</p>
          ) : (
            <div className="list">
              {docs.map((d) => (
                <Link to={`/library/${d.id}`} key={d.id} className="list-row">
                  <FileText size={16} className="faint" style={{ flex: 'none' }} />
                  <div className="stack" style={{ minWidth: 0, flex: 1, gap: 3 }}>
                    <span className="truncate" style={{ fontSize: 13.5 }}>{stripExt(d.filename)}</span>
                    <span className="row xsmall faint" style={{ gap: 6 }}>
                      {fileKind(d.mime_type, d.filename)} <LangChip lang={d.language} /> · {relative(d.uploaded_at)}
                    </span>
                  </div>
                  {d.processing_status === 'completed' ? <Tags tags={d.detected_tags} max={2} /> : <StatusBadge status={d.processing_status} />}
                </Link>
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="section-title">{t('dash.coming')} <Link to="/calendar" className="aside link">Open calendar</Link></div>
          {events === null ? <SkeletonRows n={5} /> : events.length === 0 ? (
            <p className="muted">No upcoming dates found yet.</p>
          ) : (
            <div className="list">
              {events.map((e) => {
                const n = daysUntil(e.event_date);
                return (
                  <Link to={`/library/${e.document_id}`} key={e.id} className="list-row" style={{ alignItems: 'flex-start' }}>
                    <div style={{ width: 52, flex: 'none', textAlign: 'center', paddingTop: 1 }}>
                      <div className="serif" style={{ fontSize: 20, lineHeight: 1 }}>{fmtDate(e.event_date, { day: 'numeric', timeZone: 'UTC' })}</div>
                      <div className="xsmall muted">{fmtDate(e.event_date, { month: 'short', timeZone: 'UTC' })}</div>
                    </div>
                    <div className="stack" style={{ minWidth: 0, flex: 1, gap: 3 }}>
                      <span style={{ fontSize: 13.5, lineHeight: 1.4 }}>{e.event_title}</span>
                      <span className="row xsmall faint" style={{ gap: 6 }}>
                        <span className={`urgency ${e.urgency}`} /> {TYPE_LABEL[e.event_type] || 'Date'} · {inDays(n)}
                      </span>
                      <span className="xsmall faint truncate">{stripExt(e.document_filename)}</span>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </section>
      </div>

      {stats && (
        <section className="mt-48">
          <div className="section-title">{t('dash.system')}</div>
          <div className="four-col" style={{ marginTop: 0 }}>
            <div><div className="num">Language model</div><h4>{stats.engine.llm || 'Local fallback'}</h4><p>{stats.engine.llm ? 'Tags, classification and answers by Gemini.' : 'No Gemini key set: spaCy rules and extractive answers are used.'}</p></div>
            <div><div className="num">Database</div><h4>{stats.engine.database === 'mongodb' ? 'MongoDB' : 'In-memory'}</h4><p>{stats.engine.database === 'mongodb' ? 'Persistent document store via Beanie ODM.' : 'MongoDB not reachable; running on mongomock. Data resets on restart.'}</p></div>
            <div><div className="num">Vectors</div><h4>ChromaDB</h4><p>all-MiniLM-L6-v2 embeddings, cosine distance.</p></div>
            <div><div className="num">Languages</div><h4>{Object.entries(stats.languages).map(([k, v]) => `${k.toUpperCase()} ${v}`).join(' · ') || '—'}</h4><p>Documents by detected language.</p></div>
          </div>
        </section>
      )}
    </div>
  );
}
