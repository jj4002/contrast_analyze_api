const PARTY_STYLES = [
  { headerBg: "bg-primary-fixed-dim", headerText: "text-on-primary-fixed", icon: "corporate_fare" },
  { headerBg: "bg-secondary-fixed-dim", headerText: "text-on-secondary-fixed", icon: "person" },
];

function InfoCard({ icon, label, value }) {
  return (
    <div className="flex items-start gap-4 p-4 rounded-lg bg-surface-container-low border border-border-subtle hover:border-primary-container transition-colors">
      <div className="w-10 h-10 rounded-lg bg-primary-fixed flex items-center justify-center text-primary shrink-0">
        <span className="material-symbols-outlined">{icon}</span>
      </div>
      <div>
        <p className="text-label-sm font-label-bold text-on-surface-variant uppercase mb-1">{label}</p>
        <p className="font-body-lg text-body-lg text-primary font-bold">{value || "Không xác định"}</p>
      </div>
    </div>
  );
}

export default function OverviewTab({ analysis, filename, criticalCount, warningCount }) {
  const duration =
    analysis.start_date && analysis.end_date ? `${analysis.start_date} – ${analysis.end_date}` : analysis.duration;

  return (
    <div>
      <section className="mb-section-gap">
        <div className="bg-primary-container text-on-primary-fixed-variant p-6 rounded-xl border border-outline-variant shadow-sm relative overflow-hidden">
          <div className="absolute top-0 left-0 w-1 h-full bg-primary" />
          <div className="flex justify-between items-end flex-wrap gap-4">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="material-symbols-outlined text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>
                  check_circle
                </span>
                <h2 className="font-headline-md text-headline-md text-primary">Đã phân tích: {filename}</h2>
              </div>
              <p className="text-on-surface-variant font-body-md text-body-md">
                Hệ thống đã rà soát {analysis.clauses?.length || 0} điều khoản pháp lý trong hợp đồng.
              </p>
            </div>
            <div className="text-right">
              <span className="font-display-lg text-display-lg text-primary">100%</span>
              <p className="text-label-sm font-label-bold text-success-green uppercase">Hoàn tất</p>
            </div>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-gutter mb-section-gap">
        <div className="md:col-span-2 bg-surface-container-lowest p-card-padding rounded-xl border border-border-subtle shadow-sm">
          <div className="flex items-center gap-2 mb-6 border-b border-border-subtle pb-4">
            <span className="material-symbols-outlined text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>
              info
            </span>
            <h3 className="font-headline-sm text-headline-sm text-primary">Thông tin cốt lõi</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <InfoCard icon="description" label="Loại hợp đồng" value={analysis.contract_type} />
            <InfoCard icon="payments" label="Giá trị" value={analysis.contract_value} />
            <InfoCard icon="calendar_today" label="Thời hạn" value={duration} />
            <InfoCard icon="gavel" label="Luật áp dụng" value={analysis.governing_law} />
          </div>
          <div className="mt-6 p-4 rounded-lg bg-surface-container flex items-center gap-3 flex-wrap">
            <span className="material-symbols-outlined text-secondary">balance</span>
            <span className="text-label-bold font-label-bold text-on-surface">Giải quyết tranh chấp:</span>
            <span className="text-body-md font-body-md text-primary italic">
              {analysis.dispute_resolution || "Không xác định"}
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-gutter">
          <div className="bg-surface-container-lowest p-card-padding rounded-xl border border-border-subtle shadow-sm flex-1">
            <p className="text-label-sm font-label-bold text-on-surface-variant uppercase mb-4">Mức độ rủi ro</p>
            <div className="flex items-center gap-4 mb-6">
              <div className="w-16 h-16 rounded-full border-4 border-critical-red flex items-center justify-center">
                <span className="text-headline-sm font-bold text-critical-red">
                  {String(criticalCount).padStart(2, "0")}
                </span>
              </div>
              <div>
                <p className="font-label-bold text-label-bold text-primary">Rủi ro cao</p>
                <p className="text-label-sm text-on-surface-variant">Cần xử lý ngay lập tức</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full border-4 border-warning-gold flex items-center justify-center">
                <span className="text-headline-sm font-bold text-warning-gold">
                  {String(warningCount).padStart(2, "0")}
                </span>
              </div>
              <div>
                <p className="font-label-bold text-label-bold text-primary">Cần lưu ý</p>
                <p className="text-label-sm text-on-surface-variant">Rủi ro trung bình</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <section>
        <h3 className="font-headline-sm text-headline-sm text-primary flex items-center gap-2 mb-4">
          <span className="material-symbols-outlined">groups</span>
          Các bên tham gia
        </h3>
        {analysis.parties?.length ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-gutter">
            {analysis.parties.map((party, idx) => {
              const style = PARTY_STYLES[idx % PARTY_STYLES.length];
              return (
                <div
                  key={idx}
                  className="bg-surface-container-lowest rounded-xl border border-border-subtle overflow-hidden hover:shadow-md transition-shadow"
                >
                  <div className={`${style.headerBg} px-card-padding py-3 border-b border-border-subtle flex justify-between items-center`}>
                    <span className={`font-label-bold text-label-bold ${style.headerText} uppercase tracking-wide`}>
                      {party.role}
                    </span>
                    <span className="material-symbols-outlined text-primary">{style.icon}</span>
                  </div>
                  <div className="p-card-padding space-y-4">
                    <div className="flex justify-between border-b border-surface-container-high pb-2 gap-4">
                      <span className="text-on-surface-variant text-label-bold shrink-0">Tên/Họ tên:</span>
                      <span className="font-label-bold text-primary text-right">{party.name}</span>
                    </div>
                    {party.tax_id && (
                      <div className="flex justify-between border-b border-surface-container-high pb-2 gap-4">
                        <span className="text-on-surface-variant text-label-bold shrink-0">MST / CMND:</span>
                        <span className="font-mono text-label-bold text-primary">{party.tax_id}</span>
                      </div>
                    )}
                    {party.representative && (
                      <div className="flex justify-between border-b border-surface-container-high pb-2 gap-4">
                        <span className="text-on-surface-variant text-label-bold shrink-0">Đại diện:</span>
                        <span className="font-label-bold text-primary text-right">{party.representative}</span>
                      </div>
                    )}
                    {party.address && (
                      <div className="flex justify-between gap-4">
                        <span className="text-on-surface-variant text-label-bold shrink-0">Địa chỉ:</span>
                        <span className="text-label-sm text-right text-primary">{party.address}</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-on-surface-variant">Không trích xuất được thông tin các bên tham gia.</p>
        )}
      </section>
    </div>
  );
}
