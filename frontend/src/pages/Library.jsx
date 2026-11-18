import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search as SearchIcon } from 'lucide-react';
import { api } from '../lib/api';
import { useLang } from '../lib/i18n';
import { bytes, fileKind, relative, stripExt } from '../lib/format';
import UploadZone from '../components/UploadZone';
import { Empty, LangChip, SkeletonRows, StatusBadge, Tags } from '../components/ui';

export default function Library() {
  const { t } = useLang();
  const nav = useNavigate();
  const [params, setParams] = useSearchParams();
  const [docs, setDocs] = useState(null);
  const [tags, setTags] = useState([]);
  const [q, setQ] = useState('');
  const tag = params.get('tag') || '';
  const language = params.get('language') || '';
  const status = params.get('status') || '';

  const load = useCallback(async () => {
    const [d, tg] = await Promise.all([
      api.get('/documents', { params: { size: 100, tag: tag || undefined, language: language || undefined, status: status || undefined } }),
      api.get('/documents/tags'),
    ]);
    setDocs(d.data.items);
    setTags(tg.data);
  }, [tag, language, status]);

  useEffect(() => { load().catch(() => setDocs([])); }, [load]);

  // Poll while anything is still being processed.
  const busy = docs?.some((d) => d.processing_status === 'pending' || d.processing_status === 'processing');
  useEffect(() => {
    if (!busy) return;
    const id = setInterval(() => load().catch(() => {}), 2000);
    return () => clearInterval(id);
  }, [busy, load]);

  const shown = useMemo(() => (docs || []).filter((d) => !q || d.filename.toLowerCase().includes(q.toLowerCase())), [docs, q]);
  const setFilter = (k, v) => {
    const p = new URLSearchParams(params);
    if (v) p.set(k, v); else p.delete(k);
    setParams(p, { replace: true });
  };

  return (
    <div className="page-wide">
      <div className="page-head">
        <div>
          <h1 style={{ fontSize: 34 }}>{t('lib.title')}</h1>
          <p>{t('lib.sub')}</p>
        </div>
      </div>

      <div className="lib-layout">
        <aside className="stack" style={{ gap: 24 }}>
          <section>
            <div className="section-title" style={{ fontSize: 17 }}>Upload</div>
            <UploadZone onUploaded={load} />
          </section>
          <section>
            <div className="section-title" style={{ fontSize: 17 }}>Filter</div>
            <div className="stack" style={{ gap: 10 }}>
              <div className="field">
                <label>Language</label>
                <select className="select" value={language} onChange={(e) => setFilter('language', e.target.value)}>
                  <option value="">Any language</option>
                  <option value="en">English</option>
                  <option value="ml">Malayalam</option>
                </select>
              </div>
              <div className="field">
                <label>Status</label>
                <select className="select" value={status} onChange={(e) => setFilter('status', e.target.value)}>
                  <option value="">Any status</option>
                  <option value="completed">Ready</option>
                  <option value="processing">Processing</option>
                  <option value="failed">Failed</option>
                </select>
              </div>
            </div>
          </section>
          {tags.length > 0 && (
            <section>
              <div className="section-title" style={{ fontSize: 17 }}>Tags <span className="aside">{tags.length}</span></div>
              <div className="tags">
                {tags.slice(0, 28).map(({ tag: tg, count }) => (
                  <button key={tg} className={`tag ${tag === tg ? 'on' : ''}`} onClick={() => setFilter('tag', tag === tg ? '' : tg)}>
                    {tg} <span className="count">{count}</span>
                  </button>
                ))}
              </div>
            </section>
          )}
        </aside>

        <section style={{ minWidth: 0 }}>
          <div className="row mb-12" style={{ gap: 10 }}>
            <div className="row" style={{ flex: 1, border: '1px solid var(--line-2)', borderRadius: 6, padding: '0 10px', height: 34 }}>
              <SearchIcon size={14} className="faint" />
              <input style={{ border: 0, outline: 'none', flex: 1, fontSize: 13.5, background: 'none' }} placeholder="Filter by name" value={q} onChange={(e) => setQ(e.target.value)} />
            </div>
            <span className="small muted nowrap">{shown.length} {shown.length === 1 ? 'document' : 'documents'}</span>
          </div>

          {docs === null ? <SkeletonRows n={6} h={28} /> : shown.length === 0 ? (
            <Empty title={docs.length ? 'Nothing matches' : 'No documents yet'}>
              {docs.length ? 'Try clearing the filters.' : 'Upload a PDF, Word file, text file or scan to get started. It will be processed in a few seconds.'}
            </Empty>
          ) : (
            <div className="panel" style={{ overflowX: 'auto' }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th className="hide-sm">Type</th>
                    <th>Tags</th>
                    <th>Status</th>
                    <th className="hide-sm" style={{ textAlign: 'right' }}>Uploaded</th>
                  </tr>
                </thead>
                <tbody>
                  {shown.map((d) => (
                    <tr key={d.id} onClick={() => nav(`/library/${d.id}`)}>
                      <td style={{ maxWidth: 380 }}>
                        <div className="truncate" style={{ fontSize: 13.5 }}>{stripExt(d.filename)}</div>
                        <div className="xsmall faint truncate">{d.summary || (d.processing_status === 'completed' ? '' : 'Reading the document…')}</div>
                      </td>
                      <td className="hide-sm nowrap">
                        <span className="row" style={{ gap: 6 }}><span className="pill-type">{fileKind(d.mime_type, d.filename)}</span><LangChip lang={d.language} /></span>
                        <div className="xsmall faint mt-8" style={{ marginTop: 3 }}>{bytes(d.file_size)}</div>
                      </td>
                      <td><Tags tags={d.detected_tags} max={3} onClick={(tg) => setFilter('tag', tg)} active={[tag]} /></td>
                      <td className="nowrap"><StatusBadge status={d.processing_status} /></td>
                      <td className="hide-sm nowrap small muted" style={{ textAlign: 'right' }}>{relative(d.uploaded_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
