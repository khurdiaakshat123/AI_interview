import React, { useState, useEffect } from "react";
import { X, Sparkles, Mail, Lock, User as UserIcon, Loader2, AlertCircle } from "lucide-react";
import { api } from "../services/api";

declare global {
  interface Window {
    google?: any;
  }
}

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (user: any, token: string) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [activeTab, setActiveTab] = useState<"signin" | "signup">("signin");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const googleClientId = (import.meta as any).env?.VITE_GOOGLE_CLIENT_ID;

  useEffect(() => {
    if (!isOpen || !googleClientId) return;

    const loadGoogleScript = () => {
      if (document.getElementById("google-jssdk")) {
        initGoogleButton();
        return;
      }
      const script = document.createElement("script");
      script.id = "google-jssdk";
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      script.onload = initGoogleButton;
      document.body.appendChild(script);
    };

    const initGoogleButton = () => {
      if (window.google?.accounts?.id) {
        window.google.accounts.id.initialize({
          client_id: googleClientId,
          callback: handleGoogleCredentialResponse,
          auto_select: false
        });
        const btnContainer = document.getElementById("google-gis-btn");
        if (btnContainer) {
          window.google.accounts.id.renderButton(btnContainer, {
            theme: "filled_blue",
            size: "large",
            text: "continue_with",
            shape: "pill",
            width: 320
          });
        }
      }
    };

    loadGoogleScript();
  }, [isOpen, googleClientId]);

  const handleGoogleCredentialResponse = async (response: any) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.loginWithGoogle(response.credential);
      localStorage.setItem("intervyn_token", res.access_token);
      localStorage.setItem("intervyn_user", JSON.stringify(res.user));
      onSuccess(res.user, res.access_token);
      onClose();
    } catch (err: any) {
      setError(err.message || "Google authentication failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSimulatedGoogleLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const demoEmail = email.trim() || "candidate.google@gmail.com";
      const demoName = name.trim() || demoEmail.split("@")[0].replace(".", " ").replace(/\b\w/g, (c: string) => c.toUpperCase());
      const res = await api.loginWithGoogle("demo_google_credential_instant", {
        email: demoEmail,
        name: demoName,
        picture: "https://api.dicebear.com/7.x/avataaars/svg?seed=" + encodeURIComponent(demoEmail)
      });

      localStorage.setItem("intervyn_token", res.access_token);
      localStorage.setItem("intervyn_user", JSON.stringify(res.user));
      onSuccess(res.user, res.access_token);
      onClose();
    } catch (err: any) {
      setError(err.message || "Google login failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      let res;
      if (activeTab === "signup") {
        if (!name.trim()) throw new Error("Please enter your name");
        res = await api.signup(name.trim(), email.trim(), password);
      } else {
        res = await api.login(email.trim(), password);
      }

      localStorage.setItem("intervyn_token", res.access_token);
      localStorage.setItem("intervyn_user", JSON.stringify(res.user));
      onSuccess(res.user, res.access_token);
      onClose();
    } catch (err: any) {
      setError(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="w-full max-w-md p-6 sm:p-8 rounded-3xl bg-slate-900 border border-slate-800 shadow-2xl relative space-y-6">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-brand-600 to-indigo-600 flex items-center justify-center mx-auto shadow-lg shadow-brand-500/20">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <h2 className="text-2xl font-black text-white tracking-tight">
            Welcome to <span className="bg-gradient-to-r from-brand-400 to-indigo-300 bg-clip-text text-transparent">Intervyn</span>
          </h2>
          <p className="text-xs text-slate-400">
            Sign in with Google to save your mock interviews, resume context, and AI benchmark reports.
          </p>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center gap-2.5 text-rose-400 text-xs">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="space-y-3">
          {googleClientId ? (
            <div className="flex justify-center my-2">
              <div id="google-gis-btn" />
            </div>
          ) : null}

          <button
            type="button"
            onClick={handleSimulatedGoogleLogin}
            disabled={loading}
            className="w-full py-3 px-4 rounded-xl font-bold text-sm bg-white hover:bg-slate-100 text-slate-900 flex items-center justify-center gap-3 transition-all shadow-md shadow-white/5 active:scale-[0.99] disabled:opacity-60"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
            </svg>
            <span>Continue with Google</span>
          </button>
        </div>

        <div className="relative flex items-center justify-center">
          <div className="border-t border-slate-800 w-full" />
          <span className="bg-slate-900 px-3 text-[11px] text-slate-500 uppercase tracking-widest font-mono">
            or with email
          </span>
          <div className="border-t border-slate-800 w-full" />
        </div>

        <div className="flex rounded-xl bg-slate-950 p-1 border border-slate-800">
          <button
            type="button"
            onClick={() => setActiveTab("signin")}
            className={"flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all " + (activeTab === "signin" ? "bg-slate-800 text-white shadow" : "text-slate-400 hover:text-slate-200")}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("signup")}
            className={"flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all " + (activeTab === "signup" ? "bg-slate-800 text-white shadow" : "text-slate-400 hover:text-slate-200")}
          >
            Create Account
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3.5">
          {activeTab === "signup" && (
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Full Name</label>
              <div className="relative">
                <UserIcon className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Akshat Khurdia"
                  className="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-600 focus:border-brand-500 focus:outline-none"
                  required={activeTab === "signup"}
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Email Address</label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="candidate@intervyn.ai"
                className="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-600 focus:border-brand-500 focus:outline-none"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-600 focus:border-brand-500 focus:outline-none"
                required
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-xl font-bold text-xs bg-brand-600 hover:bg-brand-500 text-white flex items-center justify-center gap-2 shadow-lg shadow-brand-500/25 transition-all disabled:opacity-50 mt-4"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Authenticating...</span>
              </>
            ) : activeTab === "signup" ? (
              "Create Account"
            ) : (
              "Sign In"
            )}
          </button>
        </form>

        <p className="text-[11px] text-slate-500 text-center">
          Securely encrypted & powered by Supabase PostgreSQL.
        </p>
      </div>
    </div>
  );
};
