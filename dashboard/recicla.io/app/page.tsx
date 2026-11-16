"use client";
import { useEffect } from "react";
import Script from "next/script";

export default function Home() {
  useEffect(() => {
    // Aguarda o Chart.js carregar antes de inicializar
    const init = () => {
      if (typeof window === "undefined") return;

      const CFG = { alturaLixeiraCm: 40, limiteQuaseCheia: 70, limiteCheia: 90, pesoMaxKg: 5, intervaloMs: 3500, pontosLinha: 25 };
      const css = (n: string) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
      const C = { org: css("--org"), rec: css("--rec"), alert: css("--alert"), ink: css("--ink"), line: css("--line"), muted: css("--muted") };

      const state: {
        total: number; org: number; rec: number; history: {tipo: string; t: Date}[];
        weight: boolean; running: boolean;
        bins: Record<string, {nome: string; cor: string; ocup: number; peso: number}>;
      } = {
        total: 0, org: 0, rec: 0, history: [], weight: true, running: true,
        bins: {
          org: { nome: "Lixeira Orgânicos", cor: C.org, ocup: 18, peso: 0.6 },
          rec: { nome: "Lixeira Recicláveis", cor: C.rec, ocup: 32, peso: 0.4 },
        },
      };

      const fmtTime = (d: Date) => d.toLocaleTimeString("pt-BR", { hour12: false });
      const pct = (a: number, b: number) => b ? Math.round((a / b) * 100) : 0;
      const statusOf = (o: number): [string, string] => o >= CFG.limiteCheia ? ["full", "Cheia"] : o >= CFG.limiteQuaseCheia ? ["warn", "Quase cheia"] : ["ok", "OK"];

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
              <div class="bin-head"><h3>${b.nome}</h3><span class="state" id="st-${key}">OK</span></div>
              <div><span class="label">Ocupação</span><div class="big mono" id="oc-${key}">0%</div></div>
              <div class="readings mono">
                <div><span>Distância (HC-SR04)</span><span id="dist-${key}">—</span></div>
                <div><span>Peso (HX711)</span><span id="peso-${key}">—</span></div>
              </div>
              <button class="empty-btn" data-empty="${key}">Esvaziar</button>
            </div>
          </article>`);
      }
      binsEl.addEventListener("click", (e) => {
        const k = (e.target as HTMLElement).dataset.empty;
        if (k) esvaziar(k);
      });

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
          tooltip: { callbacks: { label: (c: {label: string; raw: number}) => `${c.label}: ${c.raw} (${pct(c.raw, state.total)}%)` } } } },
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
        document.getElementById("cTotal")!.textContent = String(state.total);
        document.getElementById("cOrg")!.textContent = String(state.org);
        document.getElementById("cRec")!.textContent = String(state.rec);
        const po = pct(state.org, state.total), pr = state.total ? 100 - po : 0;
        document.getElementById("pOrg")!.textContent = po + "%";
        document.getElementById("pRec")!.textContent = pr + "%";
        (document.getElementById("bOrg") as HTMLElement).style.width = po + "%";
        (document.getElementById("bRec") as HTMLElement).style.width = pr + "%";

        const cheias: string[] = [];
        for (const [k, b] of Object.entries(state.bins)) {
          const o = Math.round(b.ocup);
          const [cls, txt] = statusOf(o);
          (document.getElementById("fill-" + k) as HTMLElement).style.height = o + "%";
          document.getElementById("oc-" + k)!.textContent = o + "%";
          const dist = (CFG.alturaLixeiraCm * (1 - o / 100)).toFixed(1);
          document.getElementById("dist-" + k)!.textContent = dist + " cm";
          document.getElementById("peso-" + k)!.textContent = state.weight ? b.peso.toFixed(2) + " kg" : "Não instalado";
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
          || "<li><span>Nenhum objeto ainda</span></li>";

        pie.data.datasets[0].data = [state.org, state.rec];
        pie.update();
      }

      function registrarClassificacao(tipo: string, quando = new Date()) {
        state.total++; if (tipo === "org") state.org++; else state.rec++;
        state.history.unshift({ tipo, t: quando });
        const b = state.bins[tipo];
        b.ocup = Math.min(100, b.ocup + 3 + Math.random() * 5);
        b.peso = Math.min(CFG.pesoMaxKg, b.peso + (tipo === "org" ? .08 + Math.random() * .15 : .02 + Math.random() * .06));

        const last = document.getElementById("last")!;
        last.className = "card last " + tipo;
        void last.offsetWidth; last.classList.add("flash");
        document.getElementById("lastResult")!.textContent = tipo === "org" ? "ORGÂNICO" : "RECICLÁVEL";
        document.getElementById("lastTime")!.textContent = fmtTime(quando) + " · " + quando.toLocaleDateString("pt-BR");
        document.getElementById("lastConf")!.textContent = "Objeto #" + state.total;

        line.data.labels.push(fmtTime(quando));
        line.data.datasets[0].data.push(state.org);
        line.data.datasets[1].data.push(state.rec);
        if (line.data.labels.length > CFG.pontosLinha) { line.data.labels.shift(); line.data.datasets.forEach((d: {data: number[]}) => d.data.shift()); }
        line.update();
        render();
      }

      function atualizarLixeira(k: string, { distanciaCm, pesoKg }: {distanciaCm?: number; pesoKg?: number} = {}) {
        const b = state.bins[k];
        if (distanciaCm != null) b.ocup = Math.max(0, Math.min(100, (1 - distanciaCm / CFG.alturaLixeiraCm) * 100));
        if (pesoKg != null) b.peso = pesoKg;
        render();
      }

      function esvaziar(k: string) { state.bins[k].ocup = 2; state.bins[k].peso = 0; render(); }

      (window as Window & typeof globalThis & {registrarClassificacao: typeof registrarClassificacao; atualizarLixeira: typeof atualizarLixeira}).registrarClassificacao = registrarClassificacao;
      (window as Window & typeof globalThis & {registrarClassificacao: typeof registrarClassificacao; atualizarLixeira: typeof atualizarLixeira}).atualizarLixeira = atualizarLixeira;

      let timer: ReturnType<typeof setInterval>;
      const tick = () => registrarClassificacao(Math.random() < .55 ? "org" : "rec");
      function setRunning(on: boolean) {
        state.running = on; clearInterval(timer);
        if (on) timer = setInterval(tick, CFG.intervaloMs);
        document.getElementById("live")!.classList.toggle("paused", !on);
        document.getElementById("liveTxt")!.textContent = on ? "Ao vivo (simulação)" : "Pausado";
        document.getElementById("toggleSim")!.textContent = on ? "Pausar" : "Retomar";
      }

      document.getElementById("toggleSim")!.onclick = () => setRunning(!state.running);
      document.getElementById("manualOrg")!.onclick = () => registrarClassificacao("org");
      document.getElementById("manualRec")!.onclick = () => registrarClassificacao("rec");
      document.getElementById("toggleWeight")!.onclick = (e) => {
        state.weight = !state.weight;
        (e.target as HTMLButtonElement).textContent = "HX711: " + (state.weight ? "ligado" : "desligado");
        (e.target as HTMLButtonElement).setAttribute("aria-pressed", String(state.weight));
        render();
      };
      document.getElementById("alertEmpty")!.onclick = () =>
        (document.getElementById("alert")!.dataset.bins || "").split(",").filter(Boolean).forEach(esvaziar);

      // Carrega sensores do banco
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
          const online = items.filter((d: {online: boolean}) => d.online).length;
          status.textContent = `${online} online · ${items.length} total`;
          grid.innerHTML = items.map((d: {nome: string; tipo: string; online: boolean; ultimaComunicacao: string | null}) => `
            <div class="sensor-item">
              <span class="sensor-dot ${d.online ? 'online' : 'offline'}"></span>
              <div class="sensor-info">
                <strong>${d.nome}</strong>
                <span>${d.tipo}${d.ultimaComunicacao ? ' · ' + new Date(d.ultimaComunicacao).toLocaleTimeString('pt-BR', {hour12:false}) : ''}</span>
              </div>
            </div>`).join("");
        } catch {
          status.textContent = "Erro ao carregar";
        }
      }
      carregarSensores();
      setInterval(carregarSensores, 30_000);

      const now = Date.now();
      for (let i = 8; i > 0; i--) registrarClassificacao(Math.random() < .55 ? "org" : "rec", new Date(now - i * 60000));
      setRunning(true);
    };

    // Se Chart.js já carregou, inicializa direto; senão aguarda o onLoad do Script
    if (typeof (window as Window & {Chart?: unknown}).Chart !== "undefined") {
      init();
    } else {
      (window as Window & {__dashboardInit?: () => void}).__dashboardInit = init;
    }
  }, []);

  return (
    <>
      <Script
        src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"
        strategy="afterInteractive"
        onLoad={() => {
          const w = window as Window & {__dashboardInit?: () => void};
          if (w.__dashboardInit) { w.__dashboardInit(); delete w.__dashboardInit; }
        }}
      />
      <div className="wrap">
        <header>
          <div>
            <h1>Lixeira Inteligente — Painel de Monitoramento</h1>
            <p>Classificação automática orgânico × reciclável</p>
          </div>
          <div className="controls">
            <span className="live" id="live" aria-live="polite"><span className="dot"></span><span id="liveTxt">Ao vivo (simulação)</span></span>
            <button id="toggleSim">Pausar</button>
            <button id="manualOrg">+ Orgânico</button>
            <button id="manualRec">+ Reciclável</button>
            <button id="toggleWeight" aria-pressed="true">HX711: ligado</button>
          </div>
        </header>

        <div className="alert" id="alert" role="alert">
          <span id="alertTxt">Lixeira cheia</span>
          <button id="alertEmpty">Esvaziar agora</button>
        </div>

        <section className="top">
          <article className="card last" id="last" aria-live="polite">
            <span className="label">Última classificação</span>
            <div className="result" id="lastResult">Aguardando…</div>
            <div className="meta mono">
              <span id="lastTime">--:--:--</span>
              <span id="lastConf">Objeto #—</span>
            </div>
          </article>

          <article className="card counters-wrap">
            <div className="counters">
              <div className="counter">
                <span className="label">Total</span>
                <span className="n mono" id="cTotal">0</span>
                <span className="pct">100% dos objetos</span>
                <div className="bar"><span style={{width:"100%",background:"var(--ink)"}}></span></div>
              </div>
              <div className="counter">
                <span className="label" style={{color:"var(--org)"}}>Orgânicos</span>
                <span className="n mono" id="cOrg">0</span>
                <span className="pct mono" id="pOrg">0%</span>
                <div className="bar"><span id="bOrg" style={{width:0,background:"var(--org)"}}></span></div>
              </div>
              <div className="counter">
                <span className="label" style={{color:"var(--rec)"}}>Recicláveis</span>
                <span className="n mono" id="cRec">0</span>
                <span className="pct mono" id="pRec">0%</span>
                <div className="bar"><span id="bRec" style={{width:0,background:"var(--rec)"}}></span></div>
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
            <div className="chart-box"><canvas id="pie" aria-label="Gráfico de pizza da distribuição de orgânicos e recicláveis" role="img"></canvas></div>
          </article>
          <article className="card">
            <div className="card-title"><h2>Evolução ao longo do tempo</h2><span className="label">Acumulado</span></div>
            <div className="chart-box"><canvas id="line" aria-label="Gráfico de linha com a evolução acumulada das classificações" role="img"></canvas></div>
          </article>
        </section>
      </div>
    </>
  );
}
