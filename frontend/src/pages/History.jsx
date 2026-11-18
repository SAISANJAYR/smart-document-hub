import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import { useLang } from '../lib/i18n';
import { fmtDateTime, LANG_LABEL, stripExt } from '../lib/format';
import { Empty, Loading, TraceList } from '../components/ui';

export default function History() {
  const { t } = useLang();
  const [items, setItems] = useState(null);
  const [open, setOpen] = useState(null);

  useEffect(() => { api.get('/documents/queries').then(({ data }) => setItems(data)).catch(() => setItems([])); }, []);

  if (items === null) return <Loading />;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 style={{ fontSize: 34 }}>{t('history.title')}</h1>
          <p>{t('history.sub')}</p>
        </div>
        <Link to="/ask" className="btn btn-primary">{t('ask.run')}</Link>
      </div>

      {items.length === 0 ? (
        <Empty title="No questions yet" action={<Link to="/ask" className="btn">Ask your first question</Link>}>Questions you ask, and how they were answered, are kept here.</Empty>
      ) : (
        <div className="list">
          {items.map((it) => (
            <div key={it.id} style={{ borderBottom: '1px solid var(--line)' }}>
              <button className="list-row" style={{ borderBottom: 0, alignItems: 'flex-start' }} onClick={() => setOpen(open === it.id ? null : it.id)}>
                <div className="stack" style={{ flex: 1, minWidth: 0, gap: 4 }}>
                  <span className="serif" style={{ fontSize: 16.5 }} lang={it.question_language}>{it.question}</span>
                  <span className="small muted" style={{ display: '-webkit-box', WebkitLineClamp: open === it.id ? 'unset' : 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }} lang={it.answer_language}>
                    {it.answer}
                  </span>
                </div>
                <div style={{ textAlign: 'right', flex: 'none' }} className="xsmall faint">
                  <div>{fmtDateTime(it.created_at)}</div>
                  <div className="mt-8" style={{ marginTop: 3 }}>{LANG_LABEL[it.question_language]} → {LANG_LABEL[it.answer_language]}</div>
                  <div style={{ marginTop: 3, color: it.confidence < 0.5 ? 'var(--warn)' : undefined }}>{Math.round(it.confidence * 100)}% confidence</div>
                </div>
              </button>
              {open === it.id && (
                <div className="grid-2 fade-up" style={{ padding: '4px 2px 20px' }}>
                  <div>
                    <div className="eyebrow mb-8">How it was answered · {it.engine}</div>
                    <TraceList steps={it.trace} />
                  </div>
                  <div>
                    <div className="eyebrow mb-8">Cited sources</div>
                    {it.citations.map((c) => (
                      <div key={c.n} className="source mb-8">
                        <div className="row" style={{ gap: 8 }}>
                          <span className="cite">{c.n}</span>
                          <Link className="truncate small" style={{ fontWeight: 500 }} to={`/library/${c.document_id}`}>{stripExt(c.filename)}</Link>
                        </div>
                        <p className="snippet">{c.text_snippet}</p>
                      </div>
                    ))}
                    <Link to={`/ask?q=${encodeURIComponent(it.question)}`} className="btn btn-sm mt-8">Ask again</Link>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
