"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const nav = [
  { href: "/", label: "Painel", icon: "▦" },
  { href: "/historico", label: "Histórico", icon: "☰" },
];

export default function Sidebar() {
  const path = usePathname();
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-logo">♻</div>
        <div>
          <div className="sidebar-title">Recicla.io</div>
          <div className="sidebar-sub">Monitoramento</div>
        </div>
      </div>
      <nav className="sidebar-nav">
        {nav.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={"sidebar-link" + (path === item.href ? " active" : "")}
          >
            <span className="sidebar-icon">{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="sidebar-footer">
        <span>Arduino → ESP32 → API</span>
        <span>Dados reais, do sensor ao painel.</span>
      </div>
    </aside>
  );
}
