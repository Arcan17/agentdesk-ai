"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { saveTokens } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [org, setOrg] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const tokens =
        mode === "login"
          ? await api.login(email, password)
          : await api.register(org, email, password);
      saveTokens(tokens);
      router.push("/tickets");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-bold text-brand">
          AgentDesk<span className="text-slate-900"> AI</span>
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Human-in-the-loop AI SupportOps
        </p>

        <form onSubmit={submit} className="mt-6 space-y-4">
          {mode === "register" && (
            <Field
              label="Organization"
              value={org}
              onChange={setOrg}
              placeholder="Acme Inc."
            />
          )}
          <Field
            label="Email"
            type="email"
            value={email}
            onChange={setEmail}
            placeholder="you@company.com"
          />
          <Field
            label="Password"
            type="password"
            value={password}
            onChange={setPassword}
            placeholder="••••••••"
          />

          {error && <p className="text-sm text-rose-600">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-brand px-4 py-2 text-sm font-semibold text-white hover:bg-brand-dark disabled:opacity-50"
          >
            {loading ? "Please wait…" : mode === "login" ? "Log in" : "Create account"}
          </button>
        </form>

        <button
          onClick={() => {
            setMode(mode === "login" ? "register" : "login");
            setError(null);
          }}
          className="mt-4 w-full text-center text-sm text-slate-500 hover:text-slate-900"
        >
          {mode === "login"
            ? "Need an organization? Register"
            : "Already have an account? Log in"}
        </button>
      </div>
    </main>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-700">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
      />
    </label>
  );
}
