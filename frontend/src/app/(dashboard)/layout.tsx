"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { NavBar } from "@/components/NavBar";
import { isAuthenticated } from "@/lib/auth";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
    } else {
      setReady(true);
    }
  }, [router]);

  if (!ready) return null;

  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
    </div>
  );
}
