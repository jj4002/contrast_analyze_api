const TABS = [
  { key: "overview", label: "Tổng quan", icon: "dashboard" },
  { key: "critical", label: "Sai luật", icon: "gavel" },
  { key: "warning", label: "Điểm cần chú ý", icon: "warning" },
  { key: "clauses", label: "Chi tiết điều khoản", icon: "list_alt" },
];

export default function Sidebar({ activeTab, onTabChange, onNewUpload, counts, onSignOut }) {
  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-surface-container-low border-r border-border-subtle flex flex-col py-6 px-4 gap-4 z-50">
      <div className="flex items-center gap-3 px-2 mb-4">
        <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center text-on-primary">
          <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>
            gavel
          </span>
        </div>
        <div>
          <h1 className="font-headline-sm text-headline-sm font-bold text-primary">ContractLens AI</h1>
          <p className="text-[10px] text-on-primary-container uppercase tracking-wider font-bold">Trợ lý Pháp lý Số</p>
        </div>
      </div>
      <button
        className="bg-primary text-on-primary py-3 px-4 rounded-lg font-label-bold text-label-bold hover:bg-primary-container transition-all flex items-center justify-center gap-2 mb-4 shadow-sm active:scale-95"
        onClick={onNewUpload}
      >
        <span className="material-symbols-outlined text-[20px]">upload_file</span>
        Tải hợp đồng mới
      </button>
      <nav className="flex-1 flex flex-col gap-1">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.key;
          const count = counts?.[tab.key];
          return (
            <button
              key={tab.key}
              onClick={() => onTabChange(tab.key)}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg font-label-bold text-label-bold transition-all text-left ${
                isActive
                  ? "bg-primary-fixed text-on-primary-fixed"
                  : "text-on-surface-variant hover:bg-surface-container-high"
              }`}
            >
              <span className="material-symbols-outlined" style={isActive ? { fontVariationSettings: "'FILL' 1" } : undefined}>
                {tab.icon}
              </span>
              <span className="flex-1">{tab.label}</span>
              {typeof count === "number" && count > 0 && (
                <span className="text-[11px] font-bold bg-white/60 rounded-full px-2 py-0.5">{count}</span>
              )}
            </button>
          );
        })}
      </nav>
      <button
        className="flex items-center gap-3 px-4 py-3 rounded-lg font-label-bold text-label-bold text-on-surface-variant hover:bg-surface-container-high transition-all text-left"
        onClick={onSignOut}
      >
        <span className="material-symbols-outlined">logout</span>
        Đăng xuất
      </button>
    </aside>
  );
}
