"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearTokens } from "@/lib/auth";

const LINKS = [
  { href: "/tickets", label: "Tickets" },
  { href: "/documents", label: "Knowledge Base" },
  { href: "/metrics", label: "Metrics" },
];

export function NavBar() {
  const pathname = usePathname();
  const router = useRouter();

  function logout() {
    clearTokens();
    router.push("/login");
  }

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <div className="flex items-center gap-6">
          <Link href="/tickets" className="text-lg font-bold text-brand">
            AgentDesk<span className="text-slate-900"> AI</span>
          </Link>
          <nav className="flex gap-1">
            {LINKS.map((l) => {
              const active = pathname.startsWith(l.href);
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                    active
                      ? "bg-brand/10 text-brand"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  {l.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <button
          onClick={logout}
          className="text-sm font-medium text-slate-500 hover:text-slate-900"
        >
          Log out
        </button>
      </div>
    </header>
  );
}
