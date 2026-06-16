import { useState } from "react";
import Sidebar from "./Sidebar";
import OverviewTab from "./OverviewTab";
import RiskList from "./RiskList";
import ClausesTab from "./ClausesTab";

export default function AnalysisResult({ filename, analysis, risks, onNewUpload, onSignOut }) {
  const [activeTab, setActiveTab] = useState("overview");

  const criticalRisks = risks.filter((r) => r.severity === "critical");
  const warningRisks = risks.filter((r) => r.severity === "warning");

  const counts = {
    critical: criticalRisks.length,
    warning: warningRisks.length,
    clauses: analysis.clauses?.length || 0,
  };

  return (
    <div className="min-h-screen bg-background text-on-surface flex">
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onNewUpload={onNewUpload}
        counts={counts}
        onSignOut={onSignOut}
      />
      <main className="flex-1 ml-64 min-h-screen">
        <header className="flex items-center gap-4 px-container-padding h-16 w-full bg-surface-container-lowest border-b border-border-subtle sticky top-0 z-40">
          <span className="text-on-surface-variant font-label-bold text-label-bold">Hợp đồng:</span>
          <span className="bg-secondary-fixed text-on-secondary-fixed px-3 py-1 rounded-full text-label-sm font-label-bold">
            {filename}
          </span>
        </header>
        <div className="p-container-padding max-w-[1440px] mx-auto">
          {activeTab === "overview" && (
            <OverviewTab
              analysis={analysis}
              filename={filename}
              criticalCount={criticalRisks.length}
              warningCount={warningRisks.length}
            />
          )}
          {activeTab === "critical" && <RiskList variant="critical" risks={criticalRisks} />}
          {activeTab === "warning" && <RiskList variant="warning" risks={warningRisks} />}
          {activeTab === "clauses" && <ClausesTab clauses={analysis.clauses || []} />}
        </div>
      </main>
    </div>
  );
}
