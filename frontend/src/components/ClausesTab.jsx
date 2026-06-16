export default function ClausesTab({ clauses }) {
  return (
    <div>
      <section className="mb-section-gap">
        <h3 className="font-display-lg text-display-lg text-primary mb-2">Chi tiết điều khoản</h3>
        <p className="text-on-surface-variant max-w-2xl">
          Tóm tắt toàn bộ {clauses.length} điều khoản được trích xuất từ hợp đồng.
        </p>
      </section>

      {clauses.length === 0 ? (
        <div className="border-2 border-dashed border-outline-variant rounded-xl h-40 flex items-center justify-center">
          <p className="text-on-surface-variant font-label-bold">Không trích xuất được điều khoản nào.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-gutter">
          {clauses.map((clause) => (
            <div
              key={clause.clause_number}
              className="bg-surface-container-lowest border border-border-subtle rounded-xl p-card-padding"
            >
              <div className="flex items-center gap-3 mb-2">
                <span className="w-9 h-9 rounded-lg bg-primary-fixed text-primary flex items-center justify-center font-label-bold text-label-bold shrink-0">
                  {clause.clause_number}
                </span>
                <h4 className="font-headline-sm text-headline-sm text-primary">{clause.title || `Điều ${clause.clause_number}`}</h4>
              </div>
              <p className="text-legal-text font-body-md leading-relaxed">{clause.summary}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
