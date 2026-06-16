import { useCallback, useEffect, useRef, useState } from "react";
import { fetchModels } from "../api";

const ACCEPTED_EXTENSIONS = [".docx", ".doc"];

function isAccepted(file) {
  const name = file.name.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext));
}

export default function UploadScreen({ onSubmit, statusText, error, onSignOut }) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [localError, setLocalError] = useState(null);
  const [models, setModels] = useState([]);
  const [provider, setProvider] = useState("");
  const inputRef = useRef(null);
  const busy = Boolean(statusText);

  useEffect(() => {
    fetchModels()
      .then((list) => {
        setModels(list);
        if (list.length) setProvider(list[0].provider);
      })
      .catch(() => setModels([]));
  }, []);

  const pickFile = useCallback((file) => {
    if (!file) return;
    if (!isAccepted(file)) {
      setLocalError("Chỉ hỗ trợ tệp .DOCX hoặc .DOC");
      return;
    }
    setLocalError(null);
    setSelectedFile(file);
  }, []);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragActive(false);
      if (busy) return;
      pickFile(e.dataTransfer.files?.[0]);
    },
    [busy, pickFile]
  );

  return (
    <div className="min-h-screen bg-background text-on-surface">
      <nav className="flex justify-between items-center px-container-padding h-16 w-full fixed top-0 z-50 bg-surface-container-lowest border-b border-border-subtle">
        <span className="font-display-lg text-display-lg text-primary">ContractLens</span>
        <button
          className="flex items-center gap-2 font-label-bold text-label-bold text-on-surface-variant hover:text-primary transition-colors"
          onClick={onSignOut}
        >
          <span className="material-symbols-outlined text-[20px]">logout</span>
          Đăng xuất
        </button>
      </nav>
      <main className="pt-24 pb-16 max-w-[900px] mx-auto px-container-padding">
        <div className="text-center mb-section-gap">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-primary-fixed text-on-primary-fixed rounded-full mb-4">
            <span className="material-symbols-outlined text-[18px]" style={{ fontVariationSettings: "'FILL' 1" }}>
              auto_awesome
            </span>
            <span className="font-label-sm text-label-sm">AI Legal Assistant</span>
          </div>
          <h1 className="font-display-lg text-display-lg text-primary leading-tight mb-3">
            Hệ thống AI tự động <br />
            <span className="text-secondary">rà soát rủi ro Hợp đồng</span>
          </h1>
          <p className="font-body-lg text-body-lg text-on-surface-variant max-w-xl mx-auto">
            Tải hợp đồng lên để AI tự động trích xuất thông tin và phát hiện rủi ro pháp lý chỉ trong vài giây.
          </p>
        </div>

        <div
          className={`upload-zone relative p-12 border-2 border-dashed rounded-xl flex flex-col items-center justify-center transition-all cursor-pointer group bg-surface-container-lowest ${
            dragActive ? "border-secondary" : "border-outline-variant"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            if (!busy) setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          onClick={() => !busy && inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".doc,.docx"
            className="hidden"
            onChange={(e) => pickFile(e.target.files?.[0])}
          />
          <div className="glow-cloud w-20 h-20 bg-primary-fixed rounded-full flex items-center justify-center mb-6 transition-transform group-hover:scale-110">
            <span className="material-symbols-outlined text-[40px] text-primary">cloud_upload</span>
          </div>
          {selectedFile ? (
            <>
              <h2 className="font-headline-sm text-headline-sm text-primary mb-2">{selectedFile.name}</h2>
              <p className="font-body-md text-body-md text-on-surface-variant mb-6">
                Nhấn để chọn tệp khác, hoặc bấm "Phân tích ngay" để tiếp tục
              </p>
            </>
          ) : (
            <>
              <h2 className="font-headline-sm text-headline-sm text-primary mb-2">Tải hợp đồng của bạn lên</h2>
              <p className="font-body-md text-body-md text-on-surface-variant mb-6">
                Kéo và thả tệp hoặc nhấn để chọn từ máy tính
              </p>
            </>
          )}
          <div className="flex gap-4">
            <div className="flex items-center gap-2 px-4 py-2 bg-surface-container rounded-lg border border-border-subtle">
              <span className="material-symbols-outlined text-secondary" style={{ fontVariationSettings: "'FILL' 1" }}>
                description
              </span>
              <span className="font-label-bold text-label-bold text-on-surface">.DOCX</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 bg-surface-container rounded-lg border border-border-subtle">
              <span className="material-symbols-outlined text-secondary" style={{ fontVariationSettings: "'FILL' 1" }}>
                description
              </span>
              <span className="font-label-bold text-label-bold text-on-surface">.DOC</span>
            </div>
          </div>

          {busy && (
            <div className="absolute inset-0 bg-white/90 backdrop-blur-sm flex flex-col items-center justify-center rounded-xl z-20">
              <div className="w-64 h-2 bg-surface-container rounded-full overflow-hidden">
                <div className="h-full w-1/3 bg-gradient-to-r from-secondary to-primary animate-progress-sweep" />
              </div>
              <p className="mt-4 font-label-bold text-label-bold text-primary">{statusText}</p>
            </div>
          )}
        </div>

        {(localError || error) && (
          <p className="mt-4 text-center text-error font-label-bold text-label-bold">{localError || error}</p>
        )}

        {models.length > 0 && (
          <div className="mt-6 flex justify-center items-center gap-3">
            <label className="font-label-bold text-label-bold text-on-surface-variant" htmlFor="model-select">
              Model AI:
            </label>
            <select
              id="model-select"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              disabled={busy}
              className="px-3 py-2 rounded-lg border border-border-subtle bg-surface-container-lowest text-on-surface font-label-bold text-label-bold focus:outline-none focus:ring-2 focus:ring-secondary"
            >
              {models.map((m) => (
                <option key={m.provider} value={m.provider}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="mt-6 flex justify-center">
          <button
            className="px-6 py-3 bg-primary text-on-primary font-label-bold text-label-bold rounded-lg hover:opacity-90 transition-all flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
            disabled={!selectedFile || busy}
            onClick={() => onSubmit(selectedFile, provider)}
          >
            Phân tích ngay
            <span className="material-symbols-outlined">arrow_forward</span>
          </button>
        </div>
      </main>
    </div>
  );
}
