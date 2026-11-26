"use client";
import {
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import { DashboardData, timestamp } from "@/lib/types";
const palette = {
  organic: "#617f28",
  recyclable: "#326bc5",
  undefined: "#9aa7a0",
};
export function Charts({ data }: { data: DashboardData }) {
  const s = data.summary;
  const pie = [
    { name: "Orgânico", value: s.organic, color: palette.organic },
    { name: "Reciclável", value: s.recyclable, color: palette.recyclable },
    ...(s.undefined
      ? [
          {
            name: "Não identificado",
            value: s.undefined,
            color: palette.undefined,
          },
        ]
      : []),
  ];
  let organic = 0,
    recyclable = 0;
  const points = [...data.readings].reverse().map((r) => {
    if (r.material === "organico") organic++;
    if (r.material === "reciclavel") recyclable++;
    return { time: timestamp(r.timestamp), organic, recyclable };
  });
  return (
    <div className="charts-grid">
      <section className="panel chart-panel">
        <div className="panel-heading">
          <h2>Orgânico × Reciclável</h2>
          <span>DISTRIBUIÇÃO</span>
        </div>
        <div
          className="chart-wrap"
          role="img"
          aria-label={`Distribuição: ${s.organic} orgânicos, ${s.recyclable} recicláveis, ${s.undefined} não identificados`}
        >
          {s.total > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pie}
                  dataKey="value"
                  nameKey="name"
                  innerRadius="58%"
                  outerRadius="80%"
                  stroke="none"
                  isAnimationActive={false}
                >
                  {pie.map((p) => (
                    <Cell key={p.name} fill={p.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="chart-empty">
              <span className="empty-ring" />
              <p>Aguardando classificações</p>
            </div>
          )}
        </div>
        <div className="chart-legend">
          <span>
            <i style={{ background: palette.organic }} />
            Orgânico
          </span>
          <span>
            <i style={{ background: palette.recyclable }} />
            Reciclável
          </span>
          {s.undefined > 0 && (
            <span>
              <i style={{ background: palette.undefined }} />
              Não identificado
            </span>
          )}
        </div>
      </section>
      <section className="panel chart-panel">
        <div className="panel-heading">
          <h2>Evolução ao longo do tempo</h2>
          <span>ÚLTIMAS {data.readings.length || 200} LEITURAS</span>
        </div>
        <div
          className="chart-wrap"
          role="img"
          aria-label="Contagem acumulada dentro das últimas 200 leituras"
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={points}
              margin={{ top: 12, right: 8, left: -24, bottom: 0 }}
            >
              <CartesianGrid vertical={false} stroke="#e8edeb" />
              <XAxis
                dataKey="time"
                tick={{ fontSize: 10, fill: "#7d8983" }}
                minTickGap={70}
                tickLine={false}
                axisLine={{ stroke: "#d8dfdb" }}
              />
              <YAxis
                allowDecimals={false}
                domain={[0, "auto"]}
                tick={{ fontSize: 10, fill: "#7d8983" }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip />
              <Line
                name="Orgânico"
                dataKey="organic"
                type="monotone"
                stroke={palette.organic}
                strokeWidth={2}
                dot={points.length < 2}
                isAnimationActive={false}
              />
              <Line
                name="Reciclável"
                dataKey="recyclable"
                type="monotone"
                stroke={palette.recyclable}
                strokeWidth={2}
                dot={points.length < 2}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
          {!points.length && (
            <div className="plot-empty">Nenhuma leitura no período</div>
          )}
        </div>
        <div className="chart-legend">
          <span>
            <i style={{ background: palette.organic }} />
            Orgânico
          </span>
          <span>
            <i style={{ background: palette.recyclable }} />
            Reciclável
          </span>
        </div>
      </section>
    </div>
  );
}
