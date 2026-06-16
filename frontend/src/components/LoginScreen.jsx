import { useState } from "react";
import { useAuth } from "../useAuth";

export default function LoginScreen() {
  const { signIn, signUp } = useAuth();
  const [mode, setMode] = useState("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setBusy(true);
    try {
      const { error: authError } =
        mode === "signin" ? await signIn(email, password) : await signUp(email, password);
      if (authError) {
        setError(authError.message);
      } else if (mode === "signup") {
        setInfo("Đăng ký thành công. Vui lòng kiểm tra email để xác nhận (nếu được yêu cầu).");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-on-surface flex items-center justify-center px-container-padding">
      <div className="w-full max-w-md">
        <div className="text-center mb-section-gap">
          <span className="font-display-lg text-display-lg text-primary">ContractLens</span>
          <p className="font-body-md text-body-md text-on-surface-variant mt-2">
            {mode === "signin" ? "Đăng nhập để rà soát hợp đồng của bạn" : "Tạo tài khoản mới"}
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-surface-container-lowest border border-border-subtle rounded-xl p-card-padding shadow-sm flex flex-col gap-4"
        >
          <div>
            <label className="block font-label-bold text-label-bold text-on-surface-variant mb-1" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-border-subtle bg-surface-container-low text-on-surface focus:outline-none focus:ring-2 focus:ring-secondary"
              placeholder="ban@congty.com"
            />
          </div>
          <div>
            <label className="block font-label-bold text-label-bold text-on-surface-variant mb-1" htmlFor="password">
              Mật khẩu
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-border-subtle bg-surface-container-low text-on-surface focus:outline-none focus:ring-2 focus:ring-secondary"
              placeholder="••••••••"
            />
          </div>

          {error && <p className="text-error font-label-bold text-label-bold">{error}</p>}
          {info && <p className="text-success-green font-label-bold text-label-bold">{info}</p>}

          <button
            type="submit"
            disabled={busy}
            className="mt-2 px-6 py-3 bg-primary text-on-primary font-label-bold text-label-bold rounded-lg hover:opacity-90 transition-all disabled:opacity-50"
          >
            {busy ? "Đang xử lý..." : mode === "signin" ? "Đăng nhập" : "Đăng ký"}
          </button>
        </form>

        <p className="text-center mt-4 font-body-md text-body-md text-on-surface-variant">
          {mode === "signin" ? "Chưa có tài khoản?" : "Đã có tài khoản?"}{" "}
          <button
            type="button"
            className="text-secondary font-label-bold hover:underline"
            onClick={() => {
              setMode(mode === "signin" ? "signup" : "signin");
              setError(null);
              setInfo(null);
            }}
          >
            {mode === "signin" ? "Đăng ký ngay" : "Đăng nhập"}
          </button>
        </p>
      </div>
    </div>
  );
}
