import { Link, useNavigate } from 'react-router-dom';
import { useAuth, DEMO } from '../context/AuthContext';
import { useLang } from '../lib/i18n';
import toast from 'react-hot-toast';

const plus = (n) => {
  const d = new Date(); d.setDate(d.getDate() + n);
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
};

function Specimen() {
  return (
    <div>
      <div className="specimen-meta">
        <div><span className="eyebrow">Document</span><b>Finance circular</b></div>
        <div><span className="eyebrow">Language</span><b>English · മലയാളം</b></div>
        <div><span className="eyebrow">Found</span><b>3 dates · 6 tags</b></div>
        <div><span className="eyebrow">Linked to</span><b>4 related files</b></div>
      </div>
      <div className="specimen">
        <div className="doc-title">Government of Kerala — Finance (Budget) Department</div>
        <div className="doc-sub">Circular No. FIN/B2/482/2026</div>
        <p className="doc-line">
          All Heads of Departments are informed that grants-in-aid released during the first two quarters must be
          accounted for through <mark className="m-tag">utilisation certificates</mark> in the prescribed form.
          Certificates for grants above Rs. 5 lakh must be submitted on or before{' '}
          <mark className="m-date">{plus(12)}</mark> to the <mark className="m-ent">Finance (Budget) Department</mark>{' '}
          through the BIMS portal. A review meeting of Drawing and Disbursing Officers will be held on{' '}
          <mark className="m-date">{plus(5)}</mark>. Unspent balances must be remitted to the treasury.
        </p>
        <div className="found">
          <div><i className="m-date" /><b>Deadline · high urgency</b><span>added to the calendar</span></div>
          <div><i className="m-ent" /><b>Entity · Finance Dept.</b><span>links 3 other files</span></div>
          <div><i className="m-tag" /><b>Tag · utilisation certificate</b><span>generated, not typed</span></div>
        </div>
        <div className="quote">“യൂട്ടിലൈസേഷൻ സർട്ടിഫിക്കറ്റുകൾ എന്നാണ് സമർപ്പിക്കേണ്ടത്?”</div>
      </div>
      <div className="specimen-caption">
        <span>A sample circular, as the system reads it. Ask in Malayalam, get the answer with its source.</span>
        <span className="nowrap">Sample data</span>
      </div>
    </div>
  );
}

function MiniCalendar() {
  const cells = Array.from({ length: 35 }, (_, i) => i - 2);
  const marks = { 6: 'm', 9: 'h', 13: 'h', 17: 'm', 22: 'l', 26: 'h' };
  return (
    <svg viewBox="0 0 320 190" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
      {cells.map((d, i) => {
        const x = 40 + (i % 7) * 36, y = 18 + Math.floor(i / 7) * 32;
        const m = marks[d];
        return (
          <g key={i}>
            <rect x={x} y={y} width="32" height="28" rx="3" fill="#fff" stroke="#e9e9ee" />
            {d > 0 && d < 31 && <text x={x + 5} y={y + 11} fontSize="8" fill="#9d9da6" fontFamily="Noto Sans">{d}</text>}
            {m && <rect x={x + 4} y={y + 16} width="24" height="6" rx="1.5" fill={m === 'h' ? '#f4d9d6' : m === 'm' ? '#f3e5c6' : '#e9e9ee'} />}
            {m && <rect x={x + 4} y={y + 16} width="2" height="6" fill={m === 'h' ? '#b3261e' : m === 'm' ? '#9a6512' : '#9d9da6'} />}
          </g>
        );
      })}
    </svg>
  );
}

function MiniGraph() {
  const n = [[70, 60], [150, 40], [230, 70], [110, 130], [200, 140], [270, 125], [40, 140]];
  const e = [[0, 1], [1, 2], [0, 3], [3, 4], [1, 4], [2, 5], [4, 5], [3, 6]];
  const c = ['#3a2f8f', '#2f7a4d', '#9a6512', '#3a2f8f', '#b3261e', '#2f7a4d', '#6e6e78'];
  return (
    <svg viewBox="0 0 310 180" width="100%" height="100%">
      {e.map(([a, b], i) => <line key={i} x1={n[a][0]} y1={n[a][1]} x2={n[b][0]} y2={n[b][1]} stroke="#c9c9d2" strokeWidth={1 + (i % 3) * 0.7} />)}
      {n.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={i === 1 || i === 4 ? 9 : 6.5} fill={c[i]} stroke="#fff" strokeWidth="2" />)}
    </svg>
  );
}

function MiniTags() {
  const tags = [['circular', 1], ['finance', 1], ['utilisation certificate', 0], ['tender', 0], ['disaster management', 0], ['payment', 0], ['public works', 0], ['monsoon', 0], ['scholarship', 0]];
  return (
    <div style={{ padding: '28px 24px', display: 'flex', flexWrap: 'wrap', gap: 6, alignContent: 'center', height: '100%' }}>
      {tags.map(([t, on]) => <span key={t} className={`tag ${on ? 'on' : ''}`}>{t}</span>)}
      <div className="small muted" style={{ width: '100%', marginTop: 10 }}>2 tags selected · 3 documents · 4 ms</div>
    </div>
  );
}

function MiniBilingual() {
  return (
    <div style={{ padding: '22px 24px', display: 'grid', gap: 10, alignContent: 'center', height: '100%' }}>
      <div style={{ fontFamily: 'var(--serif)', fontSize: 15 }} lang="ml">കിറ്റ് വിതരണം എപ്പോൾ ആരംഭിക്കും?</div>
      <div className="small muted">Detected Malayalam → translated → retrieved → answered → translated back</div>
      <div style={{ borderLeft: '2px solid var(--accent)', paddingLeft: 10, fontSize: 13.5 }} lang="ml">
        കിറ്റ് വിതരണം റേഷൻ കടകൾ വഴി ആരംഭിക്കും <span className="cite">1</span>
      </div>
    </div>
  );
}

export default function Landing() {
  const { t } = useLang();
  const { isAuthenticated, login } = useAuth();
  const nav = useNavigate();

  const demo = async () => {
    const r = await login(DEMO.email, DEMO.password);
    if (r.ok) nav('/dashboard');
    else toast.error(r.error);
  };

  const steps = [
    ['Read', 'PDFs, Word files, plain text and scanned images. Text is extracted page by page; scans go through OCR.'],
    ['Understand', 'Language is detected. Malayalam is translated for indexing. Gemini (or local spaCy rules) writes tags, a summary and entities.'],
    ['Connect', 'Each file is chunked and embedded into ChromaDB. Cosine similarity links it to the documents it talks about.'],
    ['Answer', 'Ask in English or Malayalam. The answer cites the exact passages it used, with every step timed and shown.'],
  ];

  const usps = [
    ['01 · Dynamic calendar', 'Deadlines find you', 'spaCy finds every date, the model decides what it means: a submission deadline, a payment, a meeting. Each lands on the calendar with an urgency.', <MiniCalendar key="c" />],
    ['02 · Knowledge graph', 'See what relates to what', 'Documents become vectors. Files that discuss the same scheme, contractor or district are linked, and the link says why.', <MiniGraph key="g" />],
    ['03 · Tag-based search', 'Search the way you file', 'Structured tags are generated on upload: type, department, topics. Combine tags with meaning-based search to narrow thousands of files in milliseconds.', <MiniTags key="t" />],
    ['04 · Bilingual by design', 'English and Malayalam, both ways', 'Upload Malayalam circulars and ask in Malayalam. The question is translated for retrieval and the answer is translated back, with its sources.', <MiniBilingual key="b" />],
  ];

  return (
    <>
      <div className="page" style={{ paddingTop: 8 }}>
        <section className="hero">
          <div className="fade-up">
            <h1>{t('landing.title')}</h1>
            <p className="lede">{t('landing.lede')}</p>
            <div className="cta">
              <Link to={isAuthenticated ? '/ask' : '/login'} className="btn btn-primary btn-pill">{t('landing.open')}</Link>
              {!isAuthenticated && <button className="text-btn" style={{ fontSize: 13.5 }} onClick={demo}>{t('landing.demo')}</button>}
            </div>
          </div>
          <div className="fade-up" style={{ animationDelay: '.08s' }}><Specimen /></div>
        </section>

        <section className="landing-section">
          <div className="intro">
            <h2>{t('landing.problem')}</h2>
            <p>{t('landing.problemBody')}</p>
          </div>
        </section>

        <section className="landing-section">
          <h2>{t('landing.how')}</h2>
          <div className="four-col">
            {steps.map(([h, p], i) => (
              <div key={h}>
                <div className="num">{String(i + 1).padStart(2, '0')}</div>
                <h4>{h}</h4>
                <p>{p}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="landing-section">
          <h2>{t('landing.does')}</h2>
          <div className="usp-grid">
            {usps.map(([eyebrow, title, body, visual]) => (
              <article className="usp" key={eyebrow}>
                <div className="visual">{visual}</div>
                <div className="body">
                  <span className="eyebrow">{eyebrow}</span>
                  <h3>{title}</h3>
                  <p>{body}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section">
          <h2>Under the hood</h2>
          <div className="four-col">
            <div><div className="num">API</div><h4>FastAPI</h4><p>Async Python, JWT access and refresh tokens, role checks, rate limiting.</p></div>
            <div><div className="num">Data</div><h4>MongoDB · ChromaDB</h4><p>Beanie ODM for documents and events; ChromaDB for chunk embeddings.</p></div>
            <div><div className="num">AI</div><h4>Gemini · spaCy</h4><p>Gemini for tags, classification and answers, with deterministic spaCy fallbacks.</p></div>
            <div><div className="num">Ops</div><h4>Docker · Redis</h4><p>One compose file runs the stack; Redis caches search and backs rate limits.</p></div>
          </div>
        </section>
      </div>
      <footer className="footer">
        <div className="footer-inner">
          <span>Smart Document Hub · built for Smart India Hackathon 2025 (PS SIH25080)</span>
          <span>
            <a className="link" href="https://github.com/SAISANJAYR/smart-document-hub" target="_blank" rel="noreferrer">Source on GitHub</a>
          </span>
        </div>
      </footer>
    </>
  );
}
