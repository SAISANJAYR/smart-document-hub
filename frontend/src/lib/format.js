export const LANG_LABEL = { en: 'English', ml: 'മലയാളം', hi: 'हिन्दी', ta: 'தமிழ்' };
export const LANG_SHORT = { en: 'EN', ml: 'ML', hi: 'HI', ta: 'TA' };

export function bytes(n) {
  if (!n && n !== 0) return '—';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${Math.round(n / 1024)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

// API timestamps are naive UTC; make sure the browser parses them as UTC.
export function toDate(s) {
  if (!s) return null;
  if (s instanceof Date) return s;
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? s : `${s}Z`);
}

export function fmtDate(s, opts = { day: 'numeric', month: 'short', year: 'numeric' }, locale = 'en-IN') {
  const d = toDate(s);
  return d ? d.toLocaleDateString(locale, opts) : '—';
}

export function fmtDateTime(s, locale = 'en-IN') {
  const d = toDate(s);
  return d ? d.toLocaleString(locale, { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' }) : '—';
}

export function relative(s) {
  const d = toDate(s);
  if (!d) return '—';
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 45) return 'just now';
  if (diff < 3600) return `${Math.round(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)} h ago`;
  if (diff < 86400 * 7) return `${Math.round(diff / 86400)} d ago`;
  return fmtDate(s);
}

// Calendar dates (event_date) are stored as date-at-midnight; compare on calendar day, not instant.
export function dayKey(s) {
  const d = toDate(s);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')}`;
}
export function localDayKey(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export function daysUntil(s) {
  const [y, m, d] = dayKey(s).split('-').map(Number);
  const target = new Date(y, m - 1, d);
  const today = new Date(); today.setHours(0, 0, 0, 0);
  return Math.round((target - today) / 86400000);
}

export function inDays(n) {
  if (n === 0) return 'today';
  if (n === 1) return 'tomorrow';
  if (n === -1) return 'yesterday';
  return n > 0 ? `in ${n} days` : `${-n} days ago`;
}

export function fileKind(mime = '', name = '') {
  if (mime.includes('pdf')) return 'PDF';
  if (mime.includes('word') || name.endsWith('.docx')) return 'DOCX';
  if (mime.startsWith('image/')) return 'Image';
  if (mime.startsWith('text/')) return 'Text';
  return 'File';
}

export const stripExt = (name = '') => name.replace(/\.(pdf|docx?|txt|md|png|jpe?g|webp|tiff?)$/i, '');

export const TYPE_LABEL = {
  deadline: 'Deadline', payment: 'Payment', meeting: 'Meeting', hearing: 'Hearing',
  expiry: 'Expiry', effective: 'Takes effect', date: 'Date',
};
