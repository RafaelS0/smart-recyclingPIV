"use client";
import dynamic from "next/dynamic";
import Link from "next/link";
import {
  Activity,
  ArrowUpRight,
  Check,
  Cpu,
  Leaf,
  Recycle,
  Search,
  WifiOff,
} from "lucide-react";
import { useState } from "react";
import {
  BinState,
  DashboardData,
  DeviceState,
  Reading,
  materials,
  number,
  timestamp,
} from "@/lib/types";
import { useTelemetry } from "./use-telemetry";
const Charts = dynamic(() => import("./charts").then((m) => m.Charts), {
  ssr: false,
  loading: () => <div className="chart-loading">Carregando gráficos…</div>,
});
function Bin({
  kind,
  state,
  apiOnline,
}: {
  kind: "organic" | "recyclable";
  state?: BinState;
  apiOnline: boolean;
}) {
  const organic = kind === "organic";
  const fill = apiOnline ? state?.ocupacao_pct : null;
  const weight = apiOnline ? state?.peso_gramas : null;
  const distance = apiOnline ? state?.distancia_cm : null;
  const full = fill != null && fill >= 90;
  return (
    <section
      className={`panel bin-panel ${organic ? "organic" : "recyclable"}`}
    >
      <div
        className="bin-vessel"
        aria-label={
          fill == null ? "Ocupação desconhecida" : `Ocupação ${fill}%`
        }
      >
        <div
          className="bin-water"
          style={{
            height:
              fill == null ? "0%" : Math.max(0, Math.min(100, fill)) + "%",
          }}
        />
        <div className="bin-threshold" />
        <span>{organic ? <Leaf size={21} /> : <Recycle size={21} />}</span>
      </div>
      <div className="bin-details">
        <div className="panel-heading">
          <h2>Lixeira {organic ? "Orgânicos" : "Recicláveis"}</h2>
          <span
            className={`bin-state ${full ? "full" : ""}`}
            title={
              fill == null
                ? distance != null ? "Distância medida. Ocupação sem calibração." : "Sem medição recente"
                : full
                  ? "Próxima da capacidade"
                  : "Medição recente"
            }
          >
            {fill == null ? "—" : full ? "!" : <Check size={12} />}
          </span>
        </div>
        <span className="eyebrow">OCUPAÇÃO</span>
        <strong className="bin-value">
          {fill == null ? "—" : number(fill, "%")}
        </strong>
        <div className="bin-metrics">
          <div>
            <span>Distância (HC-SR04)</span>
            <strong>{number(distance, " cm")}</strong>
          </div>
          <div>
            <span>Peso (HX711)</span>
            <strong>{number(weight, " g")}</strong>
          </div>
        </div>
        {full && (
          <p className="capacity-warning">Atenção: ocupação de 90% ou mais.</p>
        )}
      </div>
    </section>
  );
}
const componentNames: Record<string, string> = {
  sensor_indutivo: "Sensor indutivo",
  sensor_cor: "Sensor de cor",
  sensor_ir: "Sensor infravermelho",
  raspberry: "Raspberry Pi",
  servo_topo: "Servo do topo",
  servo_calha: "Servo da calha",
};

function Sensors({
  latest,
  fresh,
  apiOnline,
  socketOnline,
  devices,
}: {
  latest: Reading | null;
  fresh: boolean;
  apiOnline: boolean;
  socketOnline: boolean;
  devices: DeviceState[];
}) {
  const sensors =
    fresh && latest
      ? [
          { name: latest.device_id, value: "Telemetria recebida", icon: Cpu },
          {
            name: "Indutivo",
            value:
              latest.metal == null
                ? "Não informado"
                : latest.metal
                  ? "Metal detectado"
                  : "Sem metal",
            icon: Activity,
          },
          {
            name: "Infravermelho",
            value: number(latest.infrared),
            icon: Activity,
          },
          {
            name: "TCS230 · RGB",
            value: [latest.color_r, latest.color_g, latest.color_b]
              .map((v) => number(v))
              .join(" / "),
            icon: Activity,
          },
          {
            name: "HC-SR04 · objeto",
            value: number(latest.distance_cm, " cm"),
            icon: Activity,
          },
          {
            name: "Esteira · estado informado",
            value:
              latest.conveyor_running == null
                ? "Não informado"
                : latest.conveyor_running
                  ? "Ativa"
                  : "Parada",
            icon: Activity,
          },
        ]
      : [
          {
            name: !apiOnline
              ? "API indisponível"
              : latest
                ? "Sem dados recentes"
                : "Dispositivo desconectado",
            value: !apiOnline
              ? "Tentando reconectar"
              : latest
                ? "Verifique a comunicação"
                : "Aguardando dados reais",
            icon: WifiOff,
          },
        ];
  return (
    <section className="panel sensors-panel">
      <div className="panel-heading">
        <h2>Sensores / Dispositivos</h2>
        <span className={fresh ? "online-label" : ""}>
          {!apiOnline ? "API OFFLINE" : fresh ? "ONLINE" : "SEM TELEMETRIA"}
        </span>
      </div>
      <div className="sensor-list">
        {sensors.map((s) => (
          <div className={`sensor-chip ${fresh ? "live" : ""}`} key={s.name}>
            <s.icon size={15} />
            <div>
              <strong>{s.name}</strong>
              <small>{s.value}</small>
            </div>
          </div>
        ))}
      </div>
      {devices.length > 0 && (
        <div className="device-presence">
          {devices.map((d) => (
            <span
              key={d.device_id}
              title={"Última comunicação: " + timestamp(d.last_seen)}
            >
              <i className={apiOnline && d.online ? "online" : ""} />
              {d.role === "raspberry_pi"
                ? "Raspberry Pi"
                : d.role === "arduino"
                  ? "Arduino"
                  : "ESP32"}{" "}
              · {d.device_id} ·{" "}
              {apiOnline && d.online ? "conectado" : "sem comunicação recente"}
            </span>
          ))}
        </div>
      )}
      {devices.map((device) => device.component_status && (
        <div className="sensor-list" key={device.device_id} aria-label="Estado informado dos componentes">
          {Object.entries(componentNames).map(([key, label]) => {
            const status = apiOnline && device.components_current ? device.component_status?.[key] : null;
            return (
              <div className={'sensor-chip' + (status ? ' live' : '')} key={key}>
                <Activity size={15} />
                <div>
                  <strong>{label}</strong>
                  <small>{status == null ? 'Sem confirmação' : status ? 'Operante' : 'Indisponível'}</small>
                </div>
              </div>
            );
          })}
        </div>
      ))}
      <p className="sensor-note">
        {fresh
          ? "Última comunicação: " + timestamp(latest?.timestamp)
          : apiOnline && devices.some((device) => device.online)
            ? "Dispositivo conectado. Aguardando leituras de classificação."
            : "DISPOSITIVO DESCONECTADO — AGUARDANDO DADOS REAIS"}
        <span>
          {socketOnline
            ? "Tempo real conectado"
            : "Reconectando atualização ao vivo"}
        </span>
      </p>
    </section>
  );
}
export function Dashboard({
  initial,
  history = false,
}: {
  initial: DashboardData;
  history?: boolean;
}) {
  const { data, apiOnline, socketOnline, fresh } = useTelemetry(initial);
  const { summary, readings } = data;
  const latest = summary.latest;
  const classification =
    summary.latest_classification === undefined
      ? latest
      : summary.latest_classification;
  const [filter, setFilter] = useState("all"),
    [search, setSearch] = useState("");
  const filtered = readings.filter(
    (r) =>
      (filter === "all" || r.material === filter) &&
      r.device_id.toLowerCase().includes(search.toLowerCase()),
  );
  const hasData = summary.total > 0;
  return (
    <>
      <header className="page-heading">
        <div>
          <div className="page-kicker">
            SMART RECYCLING <span>/</span> MONITORAMENTO
          </div>
          <h1>
            {history
              ? "Histórico de classificações"
              : "Lixeira Inteligente — Painel de Monitoramento"}
          </h1>
          <p>
            {history
              ? "Rastreabilidade das últimas leituras recebidas."
              : "Classificação automática orgânico × reciclável"}
          </p>
        </div>
        <span className="page-badge">
          <i className={apiOnline ? "" : "offline"} />
          {apiOnline ? "API conectada" : "API indisponível"}
        </span>
      </header>
      {!history ? (
        <>
          <div className="overview-grid">
            <section className="classification-card">
              <span className="eyebrow">ÚLTIMA CLASSIFICAÇÃO</span>
              <div
                className={
                  "classification-value " +
                  (classification ? "has-classification" : "")
                }
              >
                {classification
                  ? materials[classification.material]
                  : "Indisponível"}
              </div>
              <div className="classification-footer">
                <span>{timestamp(classification?.timestamp)}</span>
                <span
                  title={
                    classification?.object_id ||
                    String(classification?.id || "")
                  }
                >
                  {classification
                    ? "Objeto #" +
                      (classification.object_id || classification.id)
                    : "Objeto #—"}
                </span>
              </div>
              {classification &&
                (!fresh || classification.data_current === false) && (
                  <span className="historical-note">
                    Último registro histórico · sem telemetria atual
                  </span>
                )}
            </section>
            <section className="panel summary-panel">
              <div className="stat-grid">
                {[
                  {
                    label: "TOTAL",
                    value: summary.total,
                    color: "total",
                    caption: "classificações registradas",
                  },
                  {
                    label: "ORGÂNICOS",
                    value: summary.organic,
                    color: "organic",
                    caption: hasData
                      ? number((summary.organic / summary.total) * 100, "%")
                      : "—",
                  },
                  {
                    label: "RECICLÁVEIS",
                    value: summary.recyclable,
                    color: "recyclable",
                    caption: hasData
                      ? number((summary.recyclable / summary.total) * 100, "%")
                      : "—",
                  },
                ].map((s) => (
                  <div className={"stat " + s.color} key={s.label}>
                    <span className="eyebrow">{s.label}</span>
                    <strong data-testid={"stat-" + s.color}>
                      {hasData ? number(s.value) : "—"}
                    </strong>
                    <small>{s.caption}</small>
                    <div className="stat-track">
                      <i
                        style={{
                          width: hasData
                            ? (s.color === "total"
                                ? 100
                                : (s.value / summary.total) * 100) + "%"
                            : "0%",
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <div className="recent-heading">
                <span className="eyebrow">HISTÓRICO RECENTE</span>
                <Link href="/historico/">
                  Ver todos <ArrowUpRight size={11} />
                </Link>
              </div>
              {readings.length ? (
                <div className="mini-events">
                  {readings.slice(0, 2).map((r) => (
                    <div key={r.id}>
                      <span>
                        <i className={"category-dot " + r.material} />
                        {materials[r.material]}
                      </span>
                      <time>{timestamp(r.timestamp)}</time>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="no-events">Nenhum evento ainda</p>
              )}
            </section>
          </div>
          <Sensors
            latest={latest}
            fresh={fresh}
            apiOnline={apiOnline}
            socketOnline={socketOnline}
            devices={data.devices || []}
          />
          <div className="bins-grid">
            <Bin kind="organic" state={data.bins?.find((bin) => bin.codigo === "organicos")} apiOnline={apiOnline} />
            <Bin kind="recyclable" state={data.bins?.find((bin) => bin.codigo === "reciclaveis")} apiOnline={apiOnline} />
          </div>
          <Charts data={data} />
        </>
      ) : (
        <section className="panel history-panel">
          <div className="history-toolbar">
            <div>
              <h2>Leituras recebidas</h2>
              <p>Até 200 registros mais recentes · horário de Brasília</p>
            </div>
            <div className="history-filters">
              <label>
                <span className="sr-only">Categoria</span>
                <select
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                >
                  <option value="all">Todas as categorias</option>
                  <option value="organico">Orgânicos</option>
                  <option value="reciclavel">Recicláveis</option>
                  <option value="indefinido">Não identificados</option>
                </select>
              </label>
              <label className="search-input">
                <Search size={15} />
                <span className="sr-only">Buscar dispositivo</span>
                <input
                  placeholder="Buscar dispositivo"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </label>
            </div>
          </div>
          <div className="history-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>REGISTRO</th>
                  <th>RECEBIDO EM</th>
                  <th>CLASSIFICAÇÃO</th>
                  <th>DISPOSITIVO</th>
                  <th>CONFIANÇA</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr key={r.id}>
                    <td>#{r.id}</td>
                    <td>{timestamp(r.timestamp)}</td>
                    <td>
                      <span className="category-tag">
                        <i className={"category-dot " + r.material} />
                        {materials[r.material]}
                      </span>
                    </td>
                    <td>{r.device_id}</td>
                    <td>
                      {r.confidence == null
                        ? "Não informada"
                        : number(r.confidence * 100, "%")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!filtered.length && (
            <div className="history-empty">
              <HistoryIcon />
              <h3>
                {readings.length
                  ? "Nenhum resultado para estes filtros"
                  : "Nenhuma classificação registrada"}
              </h3>
              <p>
                {readings.length
                  ? "Altere a categoria ou o dispositivo pesquisado."
                  : "Os dados enviados pelo equipamento aparecerão aqui."}
              </p>
            </div>
          )}
          <div className="history-count">
            {filtered.length} registro(s) exibido(s)
          </div>
        </section>
      )}
      <footer className="page-footer">
        <span>
          Somente dados reais ·{" "}
          {hasData
            ? number(summary.total) + " classificações registradas"
            : "Nenhuma classificação registrada"}
        </span>
        <span>
          {(summary.legacy_readings || 0) > 0
            ? "Inclui leituras do protocolo legado."
            : "Eventos de classificação deduplicados por objeto."}{" "}
          {history
            ? "Confiança não representa acurácia validada."
            : "Evolução acumulada nas últimas 200 leituras."}
        </span>
      </footer>
    </>
  );
}
function HistoryIcon() {
  return <Activity size={26} strokeWidth={1.3} />;
}
