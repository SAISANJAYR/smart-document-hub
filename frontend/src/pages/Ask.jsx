import { Fragment, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { api, errorMessage } from '../lib/api';
import { useLang } from '../lib/i18n';
import { LANG_LABEL, stripExt } from '../lib/format';
import { LangChip, Meter, TraceList } from '../components/ui';

const SUGGEST = {
  en: [
    'When is the last date to submit utilisation certificates?',
    'What must local bodies finish before the monsoon?',
    'How much is the EMD for the road resurfacing tender?',
    'When does the measles-rubella vaccination drive begin?',
  ],
  ml: [
    'ദുരിതാശ്വാസ കിറ്റ് വിതരണം എപ്പോൾ ആരംഭിക്കും?',
    'ടെൻഡർ സമർപ്പിക്കാനുള്ള അവസാന തീയതി എന്താണ്?',
    'ദുരിതാശ്വാസ കിറ്റിൽ എന്തെല്ലാം ഉൾപ്പെടുത്തണം?',
  ],
};

function AnswerText({ text, active, onCite }) {
  const parts = text.split(/(\[\d+\])/g);
  return (
    <p className="answer-text">
      {parts.map((p, i) => {
        const m = p.match(/^\[(\d+)\]$/);
        if (!m) return <Fragment key={i}>{p}</Fragment>;
        const n = Number(m[1]);
        return <button key={i} className={`cite ${active === n ? 'on' : ''}`} onClick={() => onCite(n)} aria-label={`Source ${n}`}>{n}</button>;
      })}
    </p>
  );
}

export default function Ask() {
  const { t, lang } = useLang();
  const [params] = useSearchParams();
  const [docs, setDocs] = useState([]);
  const [selected, setSelected] = useState(() => (params.get('doc') ? [params.get('doc')] : []));
  const [answerLang, setAnswerLang] = useState('auto');
  const [question, setQuestion] = useState(params.get('q') || '');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [activeCite, setActiveCite] = useState(null);
  const sourceRefs = useRef({});
  const autoRan = useRef(false);

  useEffect(() => {
    api.get('/documents', { params: { size: 100, status: 'completed' } }).then(({ data }) => setDocs(data.items)).catch(() => {});
  }, []);

  const run = async (q = question) => {
    if (!q.trim() || q.trim().length < 3) return;
    setBusy(true); setResult(null); setActiveCite(null);
    try {
      const { data } = await api.post('/documents/query', { question: q.trim(), document_ids: selected.length ? selected : null, answer_language: answerLang });
      setResult(data);
    } catch (e) {
      toast.error(errorMessage(e, 'Could not get an answer'));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (!autoRan.current && params.get('q')) { autoRan.current = true; run(params.get('q')); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const cite = (n) => {
    setActiveCite(n);
    sourceRefs.current[n]?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  };

  const sources = useMemo(() => {
    if (!result) return [];
    const cited = new Set(result.citations.map((c) => c.n));
    return result.all_citations.filter((c) => cited.has(c.n));
  }, [result]);

  const toggle = (id) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  const totalMs = result?.trace.reduce((a, s) => a + s.ms, 0) || 0;

  const downloadTrace = () => {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
    const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: `answer-trace-${result.id || 'latest'}.json` });
    a.click(); URL.revokeObjectURL(a.href);
  };

  return (
    <div className="page-wide">
      <div className="workspace">
        {/* Left: scope */}
        <aside className="ws-col">
          <div className="section-title" style={{ fontSize: 19 }}>{t('ask.scope')}</div>
          <div className="scope-list">
            <label className="scope-item">
              <input type="checkbox" checked={selected.length === 0} onChange={() => setSelected([])} />
              <span><b style={{ fontWeight: 500 }}>{t('ask.all')}</b><div className="xsmall faint">{docs.length} ready</div></span>
            </label>
            {docs.map((d) => (
              <label key={d.id} className="scope-item">
                <input type="checkbox" checked={selected.includes(d.id)} onChange={() => toggle(d.id)} />
                <span style={{ minWidth: 0 }}>
                  <span style={{ display: 'block', lineHeight: 1.4 }}>{stripExt(d.filename)}</span>
                  <span className="row xsmall faint" style={{ gap: 6, marginTop: 2 }}><LangChip lang={d.language} />{d.doc_type}</span>
                </span>
              </label>
            ))}
          </div>
          <p className="note mt-12">Answers are drawn only from the documents in scope. Each claim cites the passage it came from.</p>
        </aside>

        {/* Centre: question + answer */}
        <section className="ws-col">
          <div className="panel panel-pad">
            <div className="row" style={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
              <span className="small muted">{t('ask.answerIn')}</span>
              <div className="segmented" role="group">
                {[['auto', t('ask.auto')], ['en', 'English'], ['ml', 'മലയാളം']].map(([v, l]) => (
                  <button key={v} className={answerLang === v ? 'on' : ''} onClick={() => setAnswerLang(v)}>{l}</button>
                ))}
              </div>
            </div>
            <div className="small mt-8" style={{ color: 'var(--accent-text)' }}>
              {answerLang === 'auto' ? 'Auto: the answer comes back in the language you ask in.' : `Answers will be written in ${LANG_LABEL[answerLang]}.`}
            </div>
          </div>

          <div className="mt-16">
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <div className="section-title" style={{ marginBottom: 8 }}>{t('ask.question')}</div>
            </div>
            <textarea
              className="textarea"
              rows={3}
              lang={lang}
              placeholder={t('ask.placeholder')}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey || !e.shiftKey)) { e.preventDefault(); run(); } }}
              style={{ fontSize: 15 }}
            />
            <div className="row mt-8">
              <span className="xsmall faint">Enter to ask · Shift+Enter for a new line</span>
              <span className="spacer" />
              <button className="btn btn-primary" onClick={() => run()} disabled={busy || question.trim().length < 3}>
                {busy ? <><span className="spinner" style={{ borderTopColor: '#fff', width: 13, height: 13 }} /> {t('ask.running')}</> : t('ask.run')}
              </button>
            </div>
          </div>

          {!result && !busy && (
            <div className="mt-24">
              <div className="small muted mb-8">{t('ask.try')}</div>
              <div className="suggestions">
                {[...SUGGEST[lang === 'ml' ? 'ml' : 'en'], ...(lang === 'ml' ? SUGGEST.en.slice(0, 1) : SUGGEST.ml.slice(0, 1))].map((s) => (
                  <button key={s} className="suggestion" onClick={() => { setQuestion(s); run(s); }}>{s}</button>
                ))}
              </div>
            </div>
          )}

          {busy && (
            <div className="answer-card mt-24">
              <div className="stack" style={{ gap: 10 }}>
                <div className="skeleton" style={{ height: 16, width: '92%' }} />
                <div className="skeleton" style={{ height: 16, width: '84%' }} />
                <div className="skeleton" style={{ height: 16, width: '60%' }} />
              </div>
            </div>
          )}

          {result && (
            <div className="mt-24 fade-up">
              <div className="answer-card">
                <div className="row mb-12" style={{ justifyContent: 'space-between' }}>
                  <h3>{t('ask.answer')}</h3>
                  <span className="small muted">{t('ask.confidence')} <b style={{ color: result.confidence < 0.5 ? 'var(--warn)' : 'var(--text)', fontWeight: 500 }}>{Math.round(result.confidence * 100)}%</b></span>
                </div>
                {result.confidence < 0.5 && result.all_citations.length > 0 && (
                  <div className="callout"><b>{t('ask.lowConf')}</b><p>{t('ask.lowConfBody')}</p></div>
                )}
                <div className="small muted mb-8">
                  {t('ask.readAs')} · {LANG_LABEL[result.question_language]} → {LANG_LABEL[result.language]}
                  {result.question_language !== 'en' && <> · <span title="Question as used for retrieval">“{result.question_en}”</span></>}
                </div>
                <div lang={result.language}>
                  <AnswerText text={result.answer} active={activeCite} onCite={cite} />
                </div>
                {result.language !== 'en' && result.answer_en !== result.answer && (
                  <details className="mt-12">
                    <summary className="small muted" style={{ cursor: 'pointer' }}>Show the English answer</summary>
                    <div className="mt-8"><AnswerText text={result.answer_en} active={activeCite} onCite={cite} /></div>
                  </details>
                )}
                <div className="answer-actions">
                  <button onClick={() => { navigator.clipboard?.writeText(result.answer); toast.success('Copied'); }}>{t('ask.copy')}</button>
                  <button onClick={downloadTrace}>{t('ask.trace')}</button>
                  <button onClick={() => { setResult(null); setQuestion(''); }}>{t('ask.another')}</button>
                </div>
              </div>

              {sources.length > 0 && (
                <div className="mt-24">
                  <div className="section-title">{t('ask.sources')} <span className="aside">{sources.length} cited of {result.all_citations.length} retrieved</span></div>
                  <div className="stack" style={{ gap: 8 }}>
                    {sources.map((c) => (
                      <div key={c.n} ref={(el) => { sourceRefs.current[c.n] = el; }} className={`source ${activeCite === c.n ? 'on' : ''}`} onClick={() => setActiveCite(c.n)}>
                        <div className="row" style={{ gap: 8 }}>
                          <span className="cite">{c.n}</span>
                          <Link to={`/library/${c.document_id}`} className="truncate" style={{ fontWeight: 500, fontSize: 13.5, flex: 1 }}>{stripExt(c.filename)}</Link>
                          <Meter value={c.similarity_score || 0} />
                        </div>
                        <p className="snippet">{c.text_snippet}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </section>

        {/* Right: trace */}
        <aside className="ws-col ws-trace">
          <div className="ws-sticky">
            <div className="section-title">{t('ask.how')}</div>
            {!result ? (
              <p className="note">{t('ask.howEmpty')}</p>
            ) : (
              <>
                <div className="steps">
                  {result.trace.map((s, i) => (
                    <div key={s.key} className={`step-card ${s.status}`}>
                      <div className="head">
                        <span className="n">{i + 1}</span><span className="dot" /><span>{s.label}</span>
                        <span className="ms">{s.ms >= 1000 ? `${(s.ms / 1000).toFixed(1)} s` : `${s.ms} ms`}</span>
                      </div>
                      {s.detail && <div className="detail">{s.detail}</div>}
                      {s.engine && <div className="detail"><span className="faint">{t('ask.engine')} ·</span> {s.engine}</div>}
                    </div>
                  ))}
                </div>
                <div className="row mt-12 small muted" style={{ justifyContent: 'space-between' }}>
                  <span>Total {totalMs >= 1000 ? `${(totalMs / 1000).toFixed(1)} s` : `${totalMs} ms`}</span>
                  <span className="row" style={{ gap: 12 }}>
                    <button className="text-btn" onClick={() => { navigator.clipboard?.writeText(result.trace.map((s, i) => `${i + 1}. ${s.label} (${s.ms} ms) ${s.detail}`).join('\n')); toast.success('Trace copied'); }}>Copy trace</button>
                    <button className="text-btn" onClick={downloadTrace}>JSON</button>
                  </span>
                </div>
                <div className="mt-24">
                  <div className="section-title" style={{ fontSize: 16 }}>Retrieved passages</div>
                  <TraceList numbered={false} steps={result.all_citations.map((c) => ({ key: c.n, label: `[${c.n}] ${stripExt(c.filename)}`, status: result.citations.some((x) => x.n === c.n) ? 'done' : 'skipped', ms: null, detail: `chunk ${c.chunk_index} · similarity ${(c.similarity_score || 0).toFixed(2)}` }))} />
                </div>
              </>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
