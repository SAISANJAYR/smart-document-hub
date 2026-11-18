import { Fragment, useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Search as SearchIcon, X } from 'lucide-react';
import { api } from '../lib/api';
import { useLang } from '../lib/i18n';
import { fileKind, relative, stripExt } from '../lib/format';
import { Empty, LangChip, Meter, SkeletonRows, Tags } from '../components/ui';

function Highlight({ text, q }) {
  const words = q.toLowerCase().split(/\s+/).filter((w) => w.length > 2).map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  if (!words.length) return text;
  const re = new RegExp(`(${words.join('|')})`, 'gi');
  return text.split(re).map((p, i) => (i % 2 ? <mark key={i}>{p}</mark> : <Fragment key={i}>{p}</Fragment>));
}

export default function Search() {
  const { t } = useLang();
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState(params.get('q') || '');
  const [selTags, setSelTags] = useState(() => (params.get('tags') ? params.get('tags').split(',') : []));
  const [allTags, setAllTags] = useState([]);
  const [res, setRes] = useState(null);
  const [loading, setLoading] = useState(false);
  const debounce = useRef();

  useEffect(() => { api.get('/documents/tags').then(({ data }) => setAllTags(data)).catch(() => {}); }, []);

  useEffect(() => {
    clearTimeout(debounce.current);
    debounce.current = setTimeout(async () => {
      const p = {};
      if (q) p.q = q;
      if (selTags.length) p.tags = selTags.join(',');
      setParams(p, { replace: true });
      if (!q.trim() && !selTags.length) { setRes(null); return; }
      setLoading(true);
      try {
        const { data } = await api.get('/documents/search', { params: { q, tags: selTags.join(',') || undefined, top_k: 20 } });
        setRes(data);
      } finally { setLoading(false); }
    }, 280);
    return () => clearTimeout(debounce.current);
  }, [q, selTags, setParams]);

  const toggle = (tag) => setSelTags((s) => (s.includes(tag) ? s.filter((x) => x !== tag) : [...s, tag]));

  return (
    <div className="page">
      <div className="page-head" style={{ marginBottom: 16 }}>
        <div>
          <h1 style={{ fontSize: 34 }}>{t('search.title')}</h1>
          <p>Meaning-based search over every passage, combined with keyword matching and AI-generated tags.</p>
        </div>
      </div>

      <div className="searchbar">
        <SearchIcon size={22} className="faint" />
        <input autoFocus placeholder={t('search.ph')} value={q} onChange={(e) => setQ(e.target.value)} />
        {q && <button className="btn btn-ghost btn-sm" onClick={() => setQ('')} aria-label="Clear"><X size={16} /></button>}
      </div>

      <div className="mt-16">
        <div className="small muted mb-8">{t('search.tags')}{selTags.length > 0 && <> · <button className="text-btn link" onClick={() => setSelTags([])}>clear</button></>}</div>
        <div className="tags">
          {allTags.slice(0, 40).map(({ tag, count }) => (
            <button key={tag} className={`tag ${selTags.includes(tag) ? 'on' : ''}`} onClick={() => toggle(tag)}>{tag} <span className="count">{count}</span></button>
          ))}
        </div>
      </div>

      <div className="mt-32">
        {loading && !res ? <SkeletonRows n={5} h={22} /> : !res ? (
          <Empty title="Search across everything">
            Try “flood relief”, “payment schedule” or “contractor obligations” — search understands meaning, not just exact words. Or pick tags above.
          </Empty>
        ) : res.hits.length === 0 ? (
          <Empty title="No matches">Try fewer tags or different words.</Empty>
        ) : (
          <>
            <div className="small muted mb-8">
              {res.hits.length} {res.hits.length === 1 ? 'document' : 'documents'} · {res.took_ms} ms{res.cached ? ' · cached' : ''}
            </div>
            <div style={{ borderTop: '1px solid var(--line)' }}>
              {res.hits.map(({ document: d, score, matched_by, snippets }) => (
                <div key={d.id} className="hit fade-up">
                  <div style={{ minWidth: 0 }}>
                    <h3><Link to={`/library/${d.id}`}>{stripExt(d.filename)}</Link></h3>
                    <div className="row xsmall faint mt-8" style={{ gap: 8, marginTop: 4, flexWrap: 'wrap' }}>
                      <span className="pill-type">{fileKind(d.mime_type, d.filename)}</span>
                      <LangChip lang={d.language} />
                      {d.department && <span>{d.department}</span>}
                      <span>· {relative(d.uploaded_at)}</span>
                      <span>· matched by {matched_by.join(' + ')}</span>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>{q && <Meter value={score} />}</div>
                  {(snippets[0] || d.summary) && <p className="snip"><Highlight text={snippets[0] || d.summary} q={q} /></p>}
                  <div style={{ gridColumn: '1 / -1' }}><Tags tags={d.detected_tags} max={6} onClick={toggle} active={selTags} /></div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
