import { useState } from "react";
import UploadScreen from "./components/UploadScreen";
import AnalysisResult from "./components/AnalysisResult";
import LoginScreen from "./components/LoginScreen";
import { uploadContract, analyzeContract } from "./api";
import { useAuth } from "./useAuth";

export default function App() {
  const { session, loading, signOut } = useAuth();
  const [statusText, setStatusText] = useState(null);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const handleSubmit = async (file, provider) => {
    setError(null);
    try {
      setStatusText("Đang tải file lên...");
      const upload = await uploadContract(file);

      setStatusText("Đang chạy AI phân tích rủi ro & sai luật...");
      const analyzed = await analyzeContract(upload.contract_id, provider);

      setResult({ filename: upload.filename, analysis: analyzed.analysis, risks: analyzed.risks });
    } catch (err) {
      setError(err.message || "Đã xảy ra lỗi khi phân tích hợp đồng.");
    } finally {
      setStatusText(null);
    }
  };

  if (loading) {
    return <div className="min-h-screen bg-background" />;
  }

  if (!session) {
    return <LoginScreen />;
  }

  if (result) {
    return (
      <AnalysisResult
        filename={result.filename}
        analysis={result.analysis}
        risks={result.risks}
        onNewUpload={() => setResult(null)}
        onSignOut={signOut}
      />
    );
  }

  return <UploadScreen onSubmit={handleSubmit} statusText={statusText} error={error} onSignOut={signOut} />;
}
