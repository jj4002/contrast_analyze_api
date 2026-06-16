const VARIANTS = {
  critical: {
    badgeBg: "bg-error-container",
    badgeText: "text-on-error-container",
    badgeLabel: "⚠️ SAI LUẬT",
    borderColor: "border-l-critical-red",
    barColor: "bg-critical-red",
    bannerBg: "bg-critical-red/10",
    bannerText: "text-critical-red",
    bannerLabel: "Cảnh báo nghiêm trọng",
    title: "Danh sách Sai luật",
    emptyText: "Không phát hiện vi phạm pháp luật nào trong hợp đồng này.",
  },
  warning: {
    badgeBg: "bg-tertiary-fixed",
    badgeText: "text-on-tertiary-fixed",
    badgeLabel: "🔔 CẦN CHÚ Ý",
    borderColor: "border-l-warning-gold",
    barColor: "bg-warning-gold",
    bannerBg: "bg-warning-gold/10",
    bannerText: "text-warning-gold",
    bannerLabel: "Cần đàm phán lại",
    title: "Điểm cần chú ý",
    emptyText: "Không phát hiện điều khoản cần lưu ý đặc biệt.",
  },
};

export default function RiskList({ variant, risks }) {
  const v = VARIANTS[variant];

  return (
    <div>
      <section className="mb-section-gap flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className={`inline-flex items-center gap-2 ${v.bannerBg} ${v.bannerText} px-3 py-1 rounded-full mb-3`}>
            <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>
              report
            </span>
            <span className="font-label-bold text-xs uppercase tracking-wider">{v.bannerLabel}</span>
          </div>
          <h3 className="font-display-lg text-display-lg text-primary mb-2">{v.title}</h3>
          <p className="text-on-surface-variant max-w-2xl">
            Phát hiện <span className={`font-bold ${v.bannerText}`}>{risks.length} mục</span> trong hợp đồng này.
          </p>
        </div>
      </section>

      {risks.length === 0 ? (
        <div className="border-2 border-dashed border-outline-variant rounded-xl h-40 flex items-center justify-center">
          <p className="text-on-surface-variant font-label-bold">{v.emptyText}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-gutter">
          {risks.map((risk, idx) => (
            <div
              key={idx}
              className={`bg-surface-container-lowest border border-border-subtle ${v.borderColor} border-l-[6px] rounded-xl overflow-hidden flex flex-col risk-card-shadow transition-all relative`}
            >
              <div className="p-card-padding flex flex-col h-full">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <span className={`${v.badgeBg} ${v.badgeText} px-2 py-0.5 rounded font-label-sm text-label-sm uppercase mb-2 inline-block`}>
                      {v.badgeLabel}
                    </span>
                    <h4 className="font-headline-md text-headline-md text-primary">{risk.clause_ref || "Điều khoản"}</h4>
                  </div>
                </div>
                <div className="bg-surface-container-low p-4 rounded-lg mb-4 border-l-4 border-primary/20">
                  <p className="font-label-bold text-on-surface-variant text-xs uppercase mb-1">Vấn đề:</p>
                  <p className="text-legal-text font-mono-legal leading-relaxed">{risk.issue}</p>
                </div>
                <div className="space-y-4 mt-auto">
                  {risk.legal_basis && (
                    <div>
                      <p className="font-label-bold text-on-surface-variant text-xs uppercase mb-1 flex items-center gap-1">
                        <span className="material-symbols-outlined text-sm">menu_book</span>
                        Căn cứ pháp lý
                      </p>
                      <p className="text-on-surface italic font-body-md">{risk.legal_basis}</p>
                    </div>
                  )}
                  {risk.recommendation && (
                    <div className="bg-success-green/5 border border-success-green/20 p-4 rounded-lg">
                      <p className="font-label-bold text-success-green text-xs uppercase mb-2 flex items-center gap-1">
                        <span className="material-symbols-outlined text-sm">auto_fix</span>
                        Phương án xử lý AI
                      </p>
                      <p className="text-on-surface font-body-md">{risk.recommendation}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
