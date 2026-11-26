"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Recycle,
  LayoutDashboard,
  History,
  BookOpen,
  LogOut,
  ArrowUpRight,
  Cpu,
} from "lucide-react";
import { BASE } from "@/lib/types";
import { useState } from "react";
export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [error, setError] = useState(false);
  const [leaving, setLeaving] = useState(false);
  async function logout() {
    setLeaving(true);
    setError(false);
    try {
      const r = await fetch(BASE + "/api/auth/logout", { method: "POST" });
      if (!r.ok) throw Error();
      window.location.assign(BASE + "/login");
    } catch {
      setError(true);
      setLeaving(false);
    }
  }
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" href="/" aria-label="Smart Recycling — painel">
          <span className="brand-icon">
            <Recycle size={20} />
          </span>
          <span>
            Smart Recycling<small>MONITORAMENTO</small>
          </span>
        </Link>
        <nav aria-label="Navegação principal">
          <Link
            className={!path.includes("historico") ? "active" : ""}
            href="/"
          >
            <LayoutDashboard size={16} />
            Painel
          </Link>
          <Link
            className={path.includes("historico") ? "active" : ""}
            href="/historico/"
          >
            <History size={16} />
            Histórico
          </Link>
          <a href={BASE + "/tutorial"}>
            <BookOpen size={16} />
            Tutorial da API
            <ArrowUpRight size={12} className="external" />
          </a>
          <a href={BASE + "/integracao"}>
            <Cpu size={16} />
            Conectar equipamentos
          </a>
        </nav>
        <div className="sidebar-bottom">
          <span className="sidebar-caption">PROJETO INTEGRADOR V</span>
          <p>
            Arduino · ESP32 · API
            <br />
            Dados reais, do sensor ao painel.
          </p>
          <button onClick={logout} disabled={leaving}>
            <LogOut size={14} />
            {leaving ? "Saindo…" : "Sair da conta"}
          </button>
          {error && <p role="alert">Não foi possível sair. Tente novamente.</p>}
        </div>
      </aside>
      <main className="workspace">{children}</main>
    </div>
  );
}
