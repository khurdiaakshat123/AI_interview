import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
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
            theme: "outline",
            size: "large",
            text: "continue_with",
            shape: "rectangular",
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

  return createPortal(
    <div className="fixed inset-0 z-[9999] bg-black/50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="w-full max-w-md p-6 sm:p-8 rounded-[12px] bg-surface border border-border relative space-y-5">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-1.5 rounded-md text-text-muted hover:text-text hover:bg-surface-hover transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="text-center space-y-1.5">
          <h2 className="font-serif text-2xl text-text font-normal tracking-tight">
            Welcome to intervyn<span className="text-accent">.</span>
          </h2>
          <p className="text-xs text-text-muted">
            Sign in to save your mock interviews, resume context, and benchmark scores.
          </p>
        </div>

        {error && (
          <div className="p-3 rounded-md bg-danger-subtle border border-danger/40 flex items-center gap-2.5 text-danger text-xs">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="flex justify-center my-2">
          <div id="google-gis-btn" />
        </div>

        <div className="relative flex items-center justify-center">
          <div className="border-t border-border w-full" />
          <span className="bg-surface px-3 text-[11px] text-text-muted uppercase tracking-widest font-mono">
            or with email
          </span>
          <div className="border-t border-border w-full" />
        </div>

        <div className="flex rounded-md bg-bg p-1 border border-border">
          <button
            type="button"
            onClick={() => setActiveTab("signin")}
            className={"flex-1 py-1.5 text-xs font-medium rounded transition-colors " + (activeTab === "signin" ? "bg-surface text-text" : "text-text-muted hover:text-text")}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("signup")}
            className={"flex-1 py-1.5 text-xs font-medium rounded transition-colors " + (activeTab === "signup" ? "bg-surface text-text" : "text-text-muted hover:text-text")}
          >
            Create Account
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3.5">
          {activeTab === "signup" && (
            <div>
              <label className="block text-[11px] font-mono uppercase tracking-[0.04em] text-text-muted mb-1">Full Name</label>
              <div className="relative">
                <UserIcon className="w-4 h-4 text-text-muted absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Akshat Khurdia"
                  className="w-full pl-9 pr-3 py-2 rounded-md bg-bg border border-border text-xs text-text placeholder-text-dim focus:border-accent focus:outline-none"
                  required={activeTab === "signup"}
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-[11px] font-mono uppercase tracking-[0.04em] text-text-muted mb-1">Email Address</label>
            <div className="relative">
              <Mail className="w-4 h-4 text-text-muted absolute left-3 top-2.5" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="candidate@intervyn.ai"
                className="w-full pl-9 pr-3 py-2 rounded-md bg-bg border border-border text-xs text-text placeholder-text-dim focus:border-accent focus:outline-none"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-mono uppercase tracking-[0.04em] text-text-muted mb-1">Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-text-muted absolute left-3 top-2.5" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-9 pr-3 py-2 rounded-md bg-bg border border-border text-xs text-text placeholder-text-dim focus:border-accent focus:outline-none"
                required
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full h-10 rounded-md font-medium text-xs bg-accent hover:bg-accent-hover text-accent-contrast flex items-center justify-center gap-2 transition-colors disabled:opacity-50 mt-4"
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

        <p className="text-[11px] text-text-muted text-center font-mono">
          Securely encrypted & powered by Supabase PostgreSQL.
        </p>
      </div>
    </div>,
    document.body
  );
};
