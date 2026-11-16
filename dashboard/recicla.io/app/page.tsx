"use client";
import { useEffect } from "react";
import Script from "next/script";

export default function Home() {
  useEffect(() => {
    const init = () => {
      if (typeof window === "undefined") return;

      const CFG = { alturaLixeiraCm: 40, limiteQuaseCheia: 70, limiteCheia: 90, pontosLinha: 25 };
      const css = (n: string) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
      const C = { org: css("--org"), rec: css("--rec"), alert: css("--alert"), ink: css("--ink"), line: css("--line"), muted: css("--muted") };

      const state: {
        total: number; org: number; rec: number;
        history: { tipo: string; t: Date }[];
        bins: Record<string, { nome: string; cor: string; ocup: number | null; peso: number | null }>;
      } = {
        total: 0, org: 0, rec: 0, history: [],
        bins: {
          org: { nome: "Lixeira Orgânicos", cor: C.org, ocup: null, peso: null },
          rec: { nome: "Lixeira Recicláveis", cor: C.rec, ocup: null, peso: null },
        },
      };

      const fmtTime = (d: Date) => d.toLocaleTimeString("pt-BR", { hour12: false });
      const pct = (a: number, b: number) => b ? Math.round((a / b) * 100) : 0;
      const statusOf = (o: number): [string, string] =>
        o >= CFG.limiteCheia ? ["full", "Cheia"] : o >= CFG.limiteQuaseCheia ? ["warn", "Quase cheia"] : ["ok", "OK"];

      // Monta cartões das lixeiras
      const binsEl = document.getElementById("bins")!;
      for (const key of Object.keys(state.bins)) {
        const b = state.bins[key];
        binsEl.insertAdjacentHTML("beforeend", `
          <article class="card bin" id="bin-${key}">
            <div class="tank" aria-hidden="true">
              <div class="fill" id="fill-${key}" style="background:${b.cor}"></div>
              <div class="limit" style="bottom:${CFG.limiteCheia}%"></div>
            </div>
            <div class="bin-info">
              <div class="bin-head"><h3>${b.nome}</h3><span class="state" id="st-${key}">—</span></div>
              <div><span class="label">Ocupação</span><div class="big mono" id="oc-${key}">—</div></div>
              <div class="readings mono">
                <div><span>Distância (HC-SR04)</span><span id="dist-${key}">Indisponível</span></div>
                <div><span>Peso (HX711)</span><span id="peso-${key}">Indisponível</span></div>
              </div>
            </div>
          </article>`);
      }

      // @ts-expect-error Chart loaded via CDN
      const Chart = window.Chart;
      const hasChart = typeof Chart !== "undefined";
      const stubChart = () => ({ data: { labels: [] as string[], datasets: [{ data: [] as number[] }, { data: [] as number[] }] }, update() {} });
      if (!hasChart) document.querySelectorAll(".chart-box").forEach(el =>
        (el.innerHTML = '<p style="color:var(--muted);font-size:13px">Não foi possível carregar a biblioteca de gráficos.</p>'));
      else { Chart.defaults.font.family = "Geist, system-ui, sans-serif"; Chart.defaults.color = C.muted; }

      const pie = !hasChart ? stubChart() : new Chart(document.getElementById("pie"), {
        type: "doughnut",
        data: { labels: ["Orgânico", "Reciclável"], datasets: [{ data: [0, 0], backgroundColor: [C.org, C.rec], borderWidth: 0 }] },
        options: { maintainAspectRatio: false, cutout: "58%", plugins: { legend: { position: "bottom" },
          tooltip: { callbacks: { label: (c: { label: string; raw: number }) => `${c.label}: ${c.raw} (${pct(c.raw, state.total)}%)` } } } },
      });
      const line = !hasChart ? stubChart() : new Chart(document.getElementById("line"), {
        type: "line",
        data: { labels: [], datasets: [
          { label: "Orgânico", data: [], borderColor: C.org, backgroundColor: C.org, tension: .3, pointRadius: 2 },
          { label: "Reciclável", data: [], borderColor: C.rec, backgroundColor: C.rec, tension: .3, pointRadius: 2 },
        ] },
        options: { maintainAspectRatio: false, animation: { duration: 300 }, interaction: { mode: "index", intersect: false },
          plugins: { legend: { position: "bottom" } },
          scales: { x: { grid: { display: false }, ticks: { maxTicksLimit: 8 } }, y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: C.line } } } },
      });

      function render() {
        document.getElementById("cTotal")!.textContent = state.total ? String(state.total) : "—";
        document.getElementById("cOrg")!.textContent = state.total ? String(state.org) : "—";
        document.getElementById("cRec")!.textContent = state.total ? String(state.rec) : "—";
        const po = pct(state.org, state.total), pr = state.total ? 100 - po : 0;
        document.getElementById("pOrg")!.textContent = state.total ? po + "%" : "—";
        document.getElementById("pRec")!.textContent = state.total ? pr + "%" : "—";
        (document.getElementById("bOrg") as HTMLElement).style.width = po + "%";
        (document.getElementById("bRec") as HTMLElement).style.width = pr + "%";

        const cheias: string[] = [];
        for (const [k, b] of Object.entries(state.bins)) {
          if (b.ocup === null) {
            (document.getElementById("fill-" + k) as HTMLElement).style.height = "0%";
            document.getElementById("oc-" + k)!.textContent = "—";
            document.getElementById("dist-" + k)!.textContent = "Indisponível";
            document.getElementById("peso-" + k)!.textContent = "Indisponível";
            const st = document.getElementById("st-" + k)!;
            st.className = "state"; st.textContent = "—";
            continue;
          }
          const o = Math.round(b.ocup);
          const [cls, txt] = statusOf(o);
          (document.getElementById("fill-" + k) as HTMLElement).style.height = o + "%";
          document.getElementById("oc-" + k)!.textContent = o + "%";
          const dist = (CFG.alturaLixeiraCm * (1 - o / 100)).toFixed(1);
          document.getElementById("dist-" + k)!.textContent = dist + " cm";
          document.getElementById("peso-" + k)!.textContent = b.peso !== null ? b.peso.toFixed(2) + " kg" : "Indisponível";
          const st = document.getElementById("st-" + k)!;
          st.className = "state " + cls; st.textContent = txt;
          document.getElementById("bin-" + k)!.classList.toggle("full", cls === "full");
          if (cls === "full") cheias.push(k);
        }

        const alertEl = document.getElementById("alert")!;
        alertEl.classList.toggle("show", cheias.length > 0);
        if (cheias.length) {
          document.getElementById("alertTxt")!.textContent =
            `Atenção: ${cheias.map(k => state.bins[k].nome).join(" e ")} acima de ${CFG.limiteCheia}% — esvaziar.`;
          alertEl.dataset.bins = cheias.join(",");
        }

        document.getElementById("history")!.innerHTML = state.history.slice(0, 5).map(h =>
          `<li><span class="tag ${h.tipo}">${h.tipo === "org" ? "ORGÂNICO" : "RECICLÁVEL"}</span><span>${fmtTime(h.t)}</span></li>`).join("")
          || "<li><span style='color:var(--muted)'>Nenhum evento ainda</span></li>";

        pie.data.datasets[0].data = [state.org, state.rec];
        pie.update();
      }

      // Expõe para integração com ESP32 via API
      function registrarClassificacao(tipo: string, quando = new Date()) {
        state.total++;
        if (tipo === "org") state.org++; else state.rec++;
        state.history.unshift({ tipo, t: quando });

        const last = document.getElementById("last")!;
        last.className = "card last " + tipo;
        void last.offsetWidth; last.classList.add("flash");
        document.getElementById("lastResult")!.textContent = tipo === "org" ? "ORGÂNICO" : "RECICLÁVEL";
        document.getElementById("lastTime")!.textContent = fmtTime(quando) + " · " + quando.toLocaleDateString("pt-BR");
        document.getElementById("lastConf")!.textContent = "Objeto #" + state.total;

        line.data.labels.push(fmtTime(quando));
        line.data.datasets[0].data.push(state.org);
        line.data.datasets[1].data.push(state.rec);
        if (line.data.labels.length > CFG.pontosLinha) {
          line.data.labels.shift();
          line.data.datasets.forEach((d: { data: number[] }) => d.data.shift());
        }
        line.update();
        render();
      }

      function atualizarLixeira(k: string, { distanciaCm, pesoKg }: { distanciaCm?: number; pesoKg?: number } = {}) {
        const b = state.bins[k];
        if (distanciaCm != null) b.ocup = Math.max(0, Math.min(100, (1 - distanciaCm / CFG.alturaLixeiraCm) * 100));
        if (pesoKg != null) b.peso = pesoKg;
        render();
      }

      type W = Window & { registrarClassificacao: typeof registrarClassificacao; atualizarLixeira: typeof atualizarLixeira };
      (window as unknown as W).registrarClassificacao = registrarClassificacao;
      (window as unknown as W).atualizarLixeira = atualizarLixeira;

      document.getElementById("alertEmpty")!.onclick = () =>
        (document.getElementById("alert")!.dataset.bins || "").split(",").filter(Boolean).forEach(k => {
          state.bins[k].ocup = 0; state.bins[k].peso = 0; render();
        });

      // Sensores
      async function carregarSensores() {
        const grid = document.getElementById("sensores-grid");
        const status = document.getElementById("sensores-status");
        if (!grid || !status) return;
        try {
          const res = await fetch("/api/sensores");
          const { items } = await res.json();
          if (!items.length) {
            status.textContent = "Nenhum dispositivo cadastrado";
            grid.innerHTML = '<p style="color:var(--muted);font-size:13px">Nenhum sensor encontrado no banco.</p>';
            return;
          }
          const online = items.filter((d: { online: boolean }) => d.online).length;
          status.textContent = `${online} online · ${items.length} total`;
          grid.innerHTML = items.map((d: { nome: string; tipo: string; online: boolean; ultimaComunicacao: string | null }) => `
            <div class="sensor-item">
              <span class="sensor-dot ${d.online ? "online" : "offline"}"></span>
              <div class="sensor-info">
                <strong>${d.nome}</strong>
                <span>${d.tipo}${d.ultimaComunicacao ? " · " + new Date(d.ultimaComunicacao).toLocaleTimeString("pt-BR", { hour12: false }) : ""}</span>
              </div>
            </div>`).join("");
        } catch {
          status.textContent = "Offline";
          grid.innerHTML = '<div class="sensor-item"><span class="sensor-dot offline"></span><div class="sensor-info"><strong>API indisponível</strong><span>Aguardando conexão</span></div></div>';
        }
      }
      carregarSensores();
      setInterval(carregarSensores, 30_000);

      render();
    };

    if (typeof (window as Window & { Chart?: unknown }).Chart !== "undefined") {
      init();
    } else {
      (window as Window & { __dashboardInit?: () => void }).__dashboardInit = init;
    }
  }, []);

  return (
    <>
      <Script
        src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"
        strategy="afterInteractive"
        onLoad={() => {
          const w = window as Window & { __dashboardInit?: () => void };
          if (w.__dashboardInit) { w.__dashboardInit(); delete w.__dashboardInit; }
        }}
      />
      <div className="wrap">
        <header>
          <div>
            <h1>Lixeira Inteligente — Painel de Monitoramento</h1>
            <p>Classificação automática orgânico × reciclável</p>
          </div>
        </header>

        <div className="alert" id="alert" role="alert">
          <span id="alertTxt">Lixeira cheia</span>
          <button id="alertEmpty">Esvaziar agora</button>
        </div>

        <section className="top">
          <article className="card last" id="last" aria-live="polite">
            <span className="label">Última classificação</span>
            <div className="result" id="lastResult">Indisponível</div>
            <div className="meta mono">
              <span id="lastTime">--:--:--</span>
              <span id="lastConf">Objeto #—</span>
            </div>
          </article>

          <article className="card counters-wrap">
            <div className="counters">
              <div className="counter">
                <span className="label">Total</span>
                <span className="n mono" id="cTotal">—</span>
                <span className="pct">objetos classificados</span>
                <div className="bar"><span style={{ width: "100%", background: "var(--ink)" }}></span></div>
              </div>
              <div className="counter">
                <span className="label" style={{ color: "var(--org)" }}>Orgânicos</span>
                <span className="n mono" id="cOrg">—</span>
                <span className="pct mono" id="pOrg">—</span>
                <div className="bar"><span id="bOrg" style={{ width: 0, background: "var(--org)" }}></span></div>
              </div>
              <div className="counter">
                <span className="label" style={{ color: "var(--rec)" }}>Recicláveis</span>
                <span className="n mono" id="cRec">—</span>
                <span className="pct mono" id="pRec">—</span>
                <div className="bar"><span id="bRec" style={{ width: 0, background: "var(--rec)" }}></span></div>
              </div>
            </div>
            <div>
              <span className="label">Histórico recente</span>
              <ul className="history mono" id="history"></ul>
            </div>
          </article>
        </section>

        <article className="card" id="sensores-card">
          <div className="card-title"><h2>Sensores / Dispositivos</h2><span className="label" id="sensores-status">Carregando…</span></div>
          <div className="sensors-grid" id="sensores-grid"></div>
        </article>

        <section className="bins" id="bins" aria-label="Lixeiras"></section>

        <section className="charts">
          <article className="card">
            <div className="card-title"><h2>Orgânico × Reciclável</h2><span className="label">Distribuição</span></div>
            <div className="chart-box"><canvas id="pie" aria-label="Gráfico de pizza" role="img"></canvas></div>
          </article>
          <article className="card">
            <div className="card-title"><h2>Evolução ao longo do tempo</h2><span className="label">Acumulado</span></div>
            <div className="chart-box"><canvas id="line" aria-label="Gráfico de linha" role="img"></canvas></div>
          </article>
        </section>
      </div>
    </>
  );
}
