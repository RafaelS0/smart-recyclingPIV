"use client";
import { useEffect, useState, useCallback } from "react";

type Evento = {
  id: string;
  classe: string;
  origem: string;
  confianca: number | null;
  timestamp: string;
  dispositivo: { nome: string; codigo: string } | null;
  lixeira: { nome: string } | null;
};

const PER_PAGE = 50;

export default function Historico() {
  const [items, setItems] = useState<Evento[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (p: number) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/historico?page=${p}&limit=${PER_PAGE}`);
      const data = await res.json();
      setItems(data.items ?? []);
      setTotal(data.total ?? 0);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(page); }, [page, load]);

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));
  const fmt = (s: string) => new Date(s).toLocaleString("pt-BR", { hour12: false });

  return (
    <div className="wrap">
      <header>
        <div>
          <h1>Histórico de Classificações</h1>
          <p>{total} eventos registrados no banco de dados</p>
        </div>
      </header>

      <article className="card">
        {loading ? (
          <p style={{ color: "var(--muted)", fontSize: 13 }}>Carregando…</p>
        ) : items.length === 0 ? (
          <p style={{ color: "var(--muted)", fontSize: 13 }}>Nenhum evento encontrado.</p>
        ) : (
          <div className="hist-table-wrap">
            <table className="hist-table mono">
              <thead>
                <tr>
                  <th>Horário</th>
                  <th>Classe</th>
                  <th>Origem</th>
                  <th>Confiança</th>
                  <th>Dispositivo</th>
                  <th>Lixeira</th>
                </tr>
              </thead>
              <tbody>
                {items.map((ev) => (
                  <tr key={ev.id}>
                    <td>{fmt(ev.timestamp)}</td>
                    <td><span className={"tag " + (ev.classe === "ORGANICO" ? "org" : "rec")}>{ev.classe}</span></td>
                    <td style={{ color: "var(--muted)" }}>{ev.origem}</td>
                    <td>{ev.confianca != null ? (ev.confianca * 100).toFixed(1) + "%" : "—"}</td>
                    <td>{ev.dispositivo?.nome ?? "—"}</td>
                    <td>{ev.lixeira?.nome ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {totalPages > 1 && (
          <div className="hist-pagination">
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>← Anterior</button>
            <span className="label">Página {page} de {totalPages}</span>
            <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}>Próxima →</button>
          </div>
        )}
      </article>
    </div>
  );
}
