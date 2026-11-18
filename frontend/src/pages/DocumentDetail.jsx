import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Download, MessageSquareText, RefreshCw, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { api, errorMessage } from '../lib/api';
import { bytes, daysUntil, fileKind, fmtDate, fmtDateTime, inDays, LANG_LABEL, stripExt, TYPE_LABEL } from '../lib/format';
import { Loading, Modal, StatusBadge, TraceList } from '../components/ui';

function TagEditor({ doc, onChange }) {
  const [adding, setAdding] = useState('');
  const save = async (tags) => {
    try {
      const { data } = await api.patch(`/documents/${doc.id}/tags`, { tags });
      onChange(data.detected_tags);
    } catch (e) { toast.error(errorMessage(e)); }
  };
  return (
    <div className="tags">
      {doc.detected_tags.map((t) => (
        <span key={t} className="tag">{t} <button className="x" aria-label={`Remove ${t}`} onClick={() => save(doc.detected_tags.filter((x) => x !== t))}>×</button></span>
      ))}
      <form className="tag-edit" onSubmit={(e) => { e.preventDefault(); if (adding.trim()) { save([...doc.detected_tags, adding.trim()]); setAdding(''); } }}>
        <input placeholder="+ add tag" value={adding} onChange={(e) => setAdding(e.target.value)} />
      </form>
    </div>
  );
}

export default function DocumentDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [doc, setDoc] = useState(null);
  const [text, setText] = useState(null);
  const [tab, setTab] = useState('original');
  const [confirm, setConfirm] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/documents/${id}`);
      setDoc(data);
      if (data.processing_status === 'completed') {
        const tx = await api.get(`/documents/${id}/text`);
        setText(tx.data);
      }
      return data;
    } catch (e) {
      setError(errorMessage(e, 'Document not found'));
    }
  }, [id]);

  useEffect(() => { setDoc(null); setText(null); load(); }, [load]);
  useEffect(() => {
    if (!doc || !['pending', 'processing'].includes(doc.processing_status)) return;
    const timer = setInterval(load, 1500);
    return () => clearInterval(timer);
  }, [doc, load]);

  const download = async () => {
    const { data } = await api.get(`/documents/${id}/file`, { responseType: 'blob' });
    const url = URL.createObjectURL(data);
    const a = Object.assign(document.createElement('a'), { href: url, download: doc.filename });
    a.click(); URL.revokeObjectURL(url);
  };
  const reprocess = async () => {
    await api.post(`/documents/${id}/reprocess`);
    toast.success('Reprocessing started');
    load();
  };
  const remove = async () => {
    try {
      await api.delete(`/documents/${id}`);
      toast.success('Document deleted');
      nav('/library');
    } catch (e) { toast.error(errorMessage(e)); }
  };

  if (error) return <div className="page"><h2>{error}</h2><Link to="/library" className="link mt-12" style={{ display: 'inline-block' }}>Back to documents</Link></div>;
  if (!doc) return <Loading />;

  const processing = ['pending', 'processing'].includes(doc.processing_status);

  return (
    <div className="page-wide">
      <Link to="/library" className="row small muted mb-16" style={{ gap: 6 }}><ArrowLeft size={14} /> Documents</Link>
      <div className="page-head" style={{ marginBottom: 22 }}>
        <div style={{ minWidth: 0 }}>
          <h1 style={{ fontSize: 30, wordBreak: 'break-word' }}>{stripExt(doc.filename)}</h1>
          <div className="row mt-8 small muted" style={{ gap: 10, flexWrap: 'wrap' }}>
            <StatusBadge status={doc.processing_status} />
            {doc.doc_type && <span style={{ textTransform: 'capitalize' }}>{doc.doc_type}</span>}
            {doc.department && <span>· {doc.department}</span>}
            {doc.language && <span>· {LANG_LABEL[doc.language] || doc.language}{doc.translated ? ' (translated)' : ''}</span>}
          </div>
        </div>
        <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
          <Link to={`/ask?doc=${doc.id}`} className="btn btn-primary"><MessageSquareText size={15} /> Ask about this</Link>
          <button className="btn" onClick={download}><Download size={15} /> Download</button>
          <button className="btn" onClick={reprocess} disabled={processing}><RefreshCw size={15} /> Reprocess</button>
          <button className="btn btn-danger" onClick={() => setConfirm(true)}><Trash2 size={15} /></button>
        </div>
      </div>

      <div className="doc-layout">
        {/* Left — file facts, like the "Imagery" panel in the reference */}
        <aside className="stack" style={{ gap: 24 }}>
          <section>
            <div className="section-title" style={{ fontSize: 17 }}>File</div>
            <div className="panel">
              <table className="kv">
                <tbody>
                  <tr><td>Name</td><td className="truncate" title={doc.filename} style={{ maxWidth: 150 }}>{doc.filename}</td></tr>
                  <tr><td>Format</td><td>{fileKind(doc.mime_type, doc.filename)}</td></tr>
                  <tr><td>Size</td><td>{bytes(doc.file_size)}</td></tr>
                  {doc.page_count ? <tr><td>Pages</td><td>{doc.page_count}</td></tr> : null}
                  <tr><td>Characters</td><td>{doc.char_count.toLocaleString()}</td></tr>
                  <tr><td>Chunks</td><td>{doc.chunk_count}</td></tr>
                  <tr><td>Language</td><td>{LANG_LABEL[doc.language] || doc.language || '—'}</td></tr>
                  <tr><td>Uploaded</td><td>{fmtDateTime(doc.uploaded_at)}</td></tr>
                </tbody>
              </table>
            </div>
          </section>
          <section>
            <div className="section-title" style={{ fontSize: 17 }}>Tags <span className="aside">AI-generated, editable</span></div>
            <TagEditor doc={doc} onChange={(tags) => setDoc({ ...doc, detected_tags: tags })} />
          </section>
          {doc.entities.length > 0 && (
            <section>
              <div className="section-title" style={{ fontSize: 17 }}>Entities</div>
              <div className="stack" style={{ gap: 2 }}>
                {doc.entities.slice(0, 14).map((e) => (
                  <div key={e.text} className="row small" style={{ justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid var(--line)' }}>
                    <span className="truncate">{e.text}</span><span className="xsmall faint">{e.label}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </aside>

        {/* Centre — summary and text */}
        <section style={{ minWidth: 0 }}>
          {doc.summary && (
            <div className="mb-24">
              <div className="eyebrow mb-8">Summary</div>
              <p className="serif" style={{ fontSize: 17, lineHeight: 1.6 }}>{doc.summary}</p>
            </div>
          )}
          {processing ? (
            <div className="panel panel-pad row muted"><span className="spinner" /> Reading and indexing this document. This page updates by itself.</div>
          ) : doc.processing_status === 'failed' ? (
            <div className="form-error">{doc.error_message || 'Processing failed.'}</div>
          ) : text && (
            <>
              <div className="tabs">
                <button className={tab === 'original' ? 'on' : ''} onClick={() => setTab('original')}>
                  Original{doc.language && doc.language !== 'en' ? ` · ${LANG_LABEL[doc.language] || doc.language}` : ''}
                </button>
                {text.english && <button className={tab === 'english' ? 'on' : ''} onClick={() => setTab('english')}>English translation</button>}
              </div>
              <div className="doc-text" lang={tab === 'original' ? doc.language : 'en'}>{tab === 'english' ? text.english : text.original}</div>
              <p className="note mt-8">Extracted text, exactly as the system indexed it. Answers and dates are computed from this text.</p>
            </>
          )}

          {doc.events.length > 0 && (
            <div className="mt-32">
              <div className="section-title">Dates found <Link to="/calendar" className="aside link">Calendar</Link></div>
              <div className="list">
                {doc.events.map((e) => (
                  <div key={e.id} className="list-row" style={{ alignItems: 'flex-start' }}>
                    <span className={`urgency ${e.urgency}`} style={{ marginTop: 7 }} />
                    <div className="stack" style={{ flex: 1, minWidth: 0, gap: 3 }}>
                      <span style={{ fontSize: 13.5 }}>{e.event_title}</span>
                      {e.description && <span className="xsmall faint" style={{ lineHeight: 1.5 }}>“{e.description.slice(0, 220)}{e.description.length > 220 ? '…' : ''}”</span>}
                    </div>
                    <div style={{ textAlign: 'right', flex: 'none' }}>
                      <div className="small">{fmtDate(e.event_date, { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })}</div>
                      <div className="xsmall faint">{TYPE_LABEL[e.event_type]} · {inDays(daysUntil(e.event_date))}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* Right — what the system did */}
        <aside className="doc-right stack" style={{ gap: 28 }}>
          <section>
            <div className="section-title">What the system did</div>
            {doc.processing_steps.length ? <TraceList steps={doc.processing_steps} /> : <p className="note">Waiting in the queue…</p>}
            {doc.processed_at && <p className="note mt-8">Finished {fmtDateTime(doc.processed_at)}.</p>}
          </section>
          <section>
            <div className="section-title">Related documents <Link to="/graph" className="aside link">Graph</Link></div>
            {doc.related.length === 0 ? <p className="note">No closely related documents yet.</p> : (
              <div className="list">
                {doc.related.map((r) => (
                  <Link key={r.id} to={`/library/${r.id}`} className="list-row" style={{ alignItems: 'flex-start' }}>
                    <div className="stack" style={{ flex: 1, minWidth: 0, gap: 4 }}>
                      <span className="truncate" style={{ fontSize: 13.5 }}>{stripExt(r.filename)}</span>
                      {r.shared.length > 0 && <span className="xsmall faint truncate">Shared: {r.shared.slice(0, 4).join(', ')}</span>}
                    </div>
                    <span className="small muted">{Math.round(r.weight * 100)}%</span>
                  </Link>
                ))}
              </div>
            )}
          </section>
        </aside>
      </div>

      {confirm && (
        <Modal
          title="Delete this document?"
          onClose={() => setConfirm(false)}
          actions={<><button className="btn" onClick={() => setConfirm(false)}>Cancel</button><button className="btn btn-primary" style={{ background: 'var(--danger)', borderColor: 'var(--danger)' }} onClick={remove}>Delete permanently</button></>}
        >
          “{doc.filename}” will be removed with its extracted text, embeddings, calendar dates and graph links. This cannot be undone.
        </Modal>
      )}
    </div>
  );
}
