import { useRef, useState } from 'react';
import toast from 'react-hot-toast';
import { api, errorMessage } from '../lib/api';
import { useLang } from '../lib/i18n';

const ACCEPT = '.pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.webp,.tif,.tiff';

export default function UploadZone({ onUploaded }) {
  const { t } = useLang();
  const input = useRef(null);
  const [drag, setDrag] = useState(false);
  const [queue, setQueue] = useState([]);

  const upload = async (files) => {
    const list = Array.from(files);
    if (!list.length) return;
    setQueue((q) => [...q, ...list.map((f) => ({ name: f.name, pct: 0 }))]);
    for (const file of list) {
      const fd = new FormData();
      fd.append('file', file);
      try {
        await api.post('/documents/upload', fd, {
          onUploadProgress: (e) => setQueue((q) => q.map((x) => (x.name === file.name ? { ...x, pct: e.total ? e.loaded / e.total : 0.5 } : x))),
        });
        toast.success(`${file.name} uploaded — processing`);
        onUploaded?.();
      } catch (e) {
        toast.error(`${file.name}: ${errorMessage(e, 'upload failed')}`);
      } finally {
        setQueue((q) => q.filter((x) => x.name !== file.name));
      }
    }
  };

  return (
    <div>
      <label
        className={`dropzone ${drag ? 'drag' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); upload(e.dataTransfer.files); }}
      >
        <input ref={input} type="file" multiple accept={ACCEPT} hidden onChange={(e) => { upload(e.target.files); e.target.value = ''; }} />
        {t('lib.drop')} <span className="link">{t('lib.browse')}</span>
        <div className="hint">{t('lib.hint')}</div>
      </label>
      {queue.map((q) => (
        <div key={q.name} className="mt-8">
          <div className="upload-item"><span className="spinner" style={{ width: 12, height: 12 }} /> <span className="truncate">{q.name}</span></div>
          <div className="progress"><i style={{ width: `${Math.round(q.pct * 100)}%` }} /></div>
        </div>
      ))}
    </div>
  );
}
