import { useState } from "react";

interface LoginPageProps {
  onSuccess: (sessionToken: string, userId: string) => void;
}

export default function LoginPage({ onSuccess }: LoginPageProps) {
  const [step, setStep] = useState<"phone" | "otp">("phone");
  const [phoneEmail, setPhoneEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [displayOtp, setDisplayOtp] = useState(""); // For demo purposes

  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const formData = new FormData();
    formData.append("phone_email", phoneEmail);

    try {
      const res = await fetch(`${API_URL}/auth/send-otp`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (res.ok) {
        setDisplayOtp(data.otp); // Demo: show OTP
        setStep("otp");
      } else {
        setError(data.detail || "Failed to send OTP");
      }
    } catch (err) {
      setError((err as Error).message || "Network error");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const formData = new FormData();
    formData.append("phone_email", phoneEmail);
    formData.append("otp_code", otp);

    try {
      const res = await fetch(`${API_URL}/auth/verify-otp`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (res.ok) {
        onSuccess(data.session_token, data.user_id);
      } else {
        setError(data.detail || "Invalid OTP");
      }
    } catch (err) {
      setError((err as Error).message || "Network error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0c10] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo & Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                className="w-6 h-6 text-white"
                stroke="currentColor"
                strokeWidth="2"
              >
                <rect x="3" y="8" width="18" height="8" rx="2" />
                <circle cx="7" cy="12" r="1.5" fill="currentColor" stroke="none" />
                <circle cx="17" cy="12" r="1.5" fill="currentColor" stroke="none" />
                <path d="M7 16v2M17 16v2" strokeLinecap="round" />
              </svg>
            </div>
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
                ScanConvey
              </h1>
              <p className="text-xs text-gray-500 mt-0.5">Smart Conveyor Detection</p>
            </div>
          </div>
          <p className="text-gray-400 text-sm">Object counting & detection system</p>
        </div>

        {/* Auth Card */}
        <div className="bg-gray-900/60 border border-gray-800/60 rounded-2xl p-7 backdrop-blur-xl">
          {step === "phone" ? (
            <form onSubmit={handleSendOtp} className="space-y-5">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-2 uppercase tracking-wider">
                  Phone / Email
                </label>
                <input
                  type="text"
                  placeholder="+1 (555) 123-4567 or email@example.com"
                  value={phoneEmail}
                  onChange={(e) => setPhoneEmail(e.target.value)}
                  className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700/50 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all"
                  required
                  disabled={loading}
                />
              </div>

              {error && (
                <div className="bg-red-950/50 border border-red-700/60 rounded-lg p-3 text-sm text-red-300">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading || !phoneEmail}
                className="w-full py-3 px-4 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:from-gray-600 disabled:to-gray-700 disabled:opacity-50 text-white font-semibold rounded-lg transition-all duration-200 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Sending...
                  </>
                ) : (
                  "Send OTP"
                )}
              </button>

              <p className="text-xs text-gray-500 text-center">
                We'll send a one-time password to verify your identity
              </p>
            </form>
          ) : (
            <form onSubmit={handleVerifyOtp} className="space-y-5">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-2 uppercase tracking-wider">
                  Enter OTP
                </label>
                <input
                  type="text"
                  placeholder="000000"
                  maxLength={6}
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                  className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700/50 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all text-center text-2xl font-mono tracking-widest"
                  required
                  disabled={loading}
                />
              </div>

              {/* Demo: Show OTP */}
              {displayOtp && (
                <div className="bg-amber-950/50 border border-amber-700/60 rounded-lg p-3 text-sm text-amber-300">
                  📱 Demo OTP: <span className="font-mono font-bold">{displayOtp}</span>
                </div>
              )}

              {error && (
                <div className="bg-red-950/50 border border-red-700/60 rounded-lg p-3 text-sm text-red-300">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading || otp.length !== 6}
                className="w-full py-3 px-4 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:from-gray-600 disabled:to-gray-700 disabled:opacity-50 text-white font-semibold rounded-lg transition-all duration-200 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Verifying...
                  </>
                ) : (
                  "Verify & Login"
                )}
              </button>

              <button
                type="button"
                onClick={() => {
                  setStep("phone");
                  setOtp("");
                  setError("");
                }}
                className="w-full text-sm text-cyan-400 hover:text-cyan-300 font-medium"
              >
                ← Back to phone/email
              </button>
            </form>
          )}
        </div>

        {/* Footer */}
        <p className="text-xs text-gray-600 text-center mt-6">
          Powered by Secuodsoft Technologies
        </p>
      </div>
    </div>
  );
}
