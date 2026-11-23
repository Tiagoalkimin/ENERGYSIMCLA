"""Demonstração de palco do EnergySim. Cálculos preservados em core/demo.py.

A interface usa HTML/CSS próprios (ui/theme.css) e pequenos scripts de animação
executados no navegador: números que contam até o novo valor, o disco do medidor
girando conforme a potência e o gráfico de potência e temperatura sendo desenhado
a cada etapa. Todos os valores vêm do modelo; o JavaScript só anima a transição.
"""
import html
import json

import streamlit as st

from core.demo import QuickDemo
from core.energy import cost_projection
from models.computer import hardware_details

STAGES = ("normal", "waste", "optimized")
SEGMENT_S = QuickDemo.SETTLE_S
GAUGE_MAX_W = 200  # escala da faixa "esperado x agora"
ALERT_MARGIN = 1.15  # mesma tolerância do detector (core/recommendations.detect_anomaly)


def br(value, digits=1):
    return f"{value:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def scale_savings(tariff, computers):
    """Economia de eliminar o consumo extra em vários computadores.

    A otimização remove exatamente a parcela extra (QuickDemo.WASTE_W), mantendo a
    carga útil. Usa a mesma projeção da demonstração: 8 h por dia, 30 dias.
    """
    month = cost_projection(QuickDemo.WASTE_W, tariff)["30d"]
    return {
        "pc_month_brl": month["custo"],
        "pc_year_brl": month["custo"] * 12,
        "year_kwh": month["kwh"] * 12 * computers,
        "year_brl": month["custo"] * 12 * computers,
    }


# ------------------------------------------------------------------ animação
_COUNT_JS = """
<script>
(function () {
  const root = document.getElementById("%(id)s");
  if (!root) return;
  const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  root.querySelectorAll("[data-to]").forEach(function (el) {
    const from = parseFloat(el.dataset.from), to = parseFloat(el.dataset.to);
    const dec = parseInt(el.dataset.dec || "0", 10);
    const fmt = function (v) {
      return v.toLocaleString("pt-BR", {minimumFractionDigits: dec, maximumFractionDigits: dec});
    };
    if (still || document.hidden || from === to) { el.textContent = fmt(to); return; }
    const t0 = performance.now(), dur = 1100;
    el.textContent = fmt(from);
    function frame(now) {
      const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3);
      el.textContent = fmt(from + (to - from) * e);
      if (p < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
    // Garantia: se o navegador pausar a animação (aba em segundo plano), fica o valor final.
    setTimeout(function () { el.textContent = fmt(to); }, dur + 150);
  });
})();
</script>
"""


def counter(key, value, digits):
    """Número que conta do valor anterior até o atual (o texto final já vem pronto do servidor)."""
    prev = st.session_state.setdefault("_prev_values", {})
    start = prev.get(key, 0.0 if key == "watts" else value)
    prev[key] = value
    return (f'<span class="count" data-from="{start:.4f}" data-to="{value:.4f}" '
            f'data-dec="{digits}">{br(value, digits)}</span>')


def animated(block_id, body):
    st.html(f'<div id="{block_id}">{body}</div>' + _COUNT_JS % {"id": block_id},
            unsafe_allow_javascript=True)


_CHART_JS = """
<script>
(function () {
  // Observação: o Streamlit sanitiza o HTML e descarta scripts cujo texto contenha
  // marcações HTML literais. Por isso as tags são montadas com LT (o sinal de menor).
  const LT = String.fromCharCode(60);
  function el(name, attrs, inner) {
    let s = LT + name;
    for (const k in attrs) s += " " + k + '="' + attrs[k] + '"';
    return inner === undefined ? s + "/>" : s + ">" + inner + LT + "/" + name + ">";
  }
  const root = document.getElementById("es-chart");
  if (!root) return;
  const D = %(data)s;
  const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches || document.hidden;
  const n = D.t.length;
  const num = (v, d) => v.toLocaleString("pt-BR", {minimumFractionDigits: d, maximumFractionDigits: d});
  let shown = n;
  function draw(k) {
    shown = k;
    const W = Math.max(root.clientWidth, 300), H = 252;
    const L = 46, R = 14, T1 = 34, H1 = 76, T2 = 150, H2 = 72;
    const x = t => L + (W - L - R) * t / D.total;
    const yP = v => T1 + H1 - H1 * v / D.pMax;
    const yT = v => T2 + H2 - H2 * (v - D.tMin) / (D.tMax - D.tMin);
    let s = "";
    D.phases.forEach(function (ph) {
      s += el("rect", {x: x(ph.t0), y: 6, width: x(ph.t1) - x(ph.t0), height: H - 30, "class": "band " + ph.kind});
      s += el("text", {x: x(ph.t0) + 8, y: 21, "class": "band-label " + ph.kind}, ph.label);
    });
    [0, D.pMax / 2, D.pMax].forEach(function (v) {
      s += el("line", {x1: L, x2: W - R, y1: yP(v), y2: yP(v), "class": "grid"});
      s += el("text", {x: L - 8, y: yP(v) + 4, "class": "tick", "text-anchor": "end"}, Math.round(v) + " W");
    });
    [D.tMin, (D.tMin + D.tMax) / 2, D.tMax].forEach(function (v) {
      s += el("line", {x1: L, x2: W - R, y1: yT(v), y2: yT(v), "class": "grid"});
      s += el("text", {x: L - 8, y: yT(v) + 4, "class": "tick", "text-anchor": "end"}, Math.round(v) + "°");
    });
    for (let m = 0; m * 60 <= D.total; m += 1) {
      s += el("text", {x: x(m * 60), y: H - 6, "class": "tick", "text-anchor": "middle"}, m + " min");
    }
    if (k > 1) {
      let p = "M" + x(D.t[0]) + " " + yP(D.p[0]);
      let q = "M" + x(D.t[0]) + " " + yT(D.temp[0]);
      for (let i = 1; i !== k; i++) {
        p += " H" + x(D.t[i]) + " V" + yP(D.p[i]);
        q += " L" + x(D.t[i]) + " " + yT(D.temp[i]);
      }
      s += el("path", {d: p, "class": "line-power"});
      s += el("path", {d: q, "class": "line-temp"});
      const j = k - 1, lx = Math.min(x(D.t[j]) + 9, W - R - 72);
      s += el("circle", {cx: x(D.t[j]), cy: yP(D.p[j]), r: 4.5, "class": "dot-power"});
      s += el("circle", {cx: x(D.t[j]), cy: yT(D.temp[j]), r: 4.5, "class": "dot-temp"});
      s += el("text", {x: lx, y: yP(D.p[j]) - 9, "class": "val power"}, num(D.p[j], 1) + " W");
      s += el("text", {x: lx, y: yT(D.temp[j]) - 9, "class": "val temp"}, num(D.temp[j], 1) + " °C");
    }
    root.innerHTML = el("svg", {width: W, height: H, role: "img", "aria-label": D.label}, s);
  }
  root.__redraw = function () { draw(shown); };
  if (!window.__esChartResize) {
    window.__esChartResize = true;
    window.addEventListener("resize", function () {
      const c = document.getElementById("es-chart");
      if (c && c.__redraw) c.__redraw();
    });
  }
  const start = Math.max(2, D.animateFrom);
  if (still || start >= n) { draw(n); return; }
  const t0 = performance.now(), dur = 2400;
  draw(start);
  (function frame(now) {
    const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 2);
    draw(Math.max(2, Math.round(start + (n - start) * e)));
    if (p !== 1) requestAnimationFrame(frame);
  })(t0);
  setTimeout(function () { if (shown !== n) draw(n); }, dur + 200);
})();
</script>
"""


def chart_block(demo, stage):
    hist = demo.sim.real.history
    t = [round(h["t"], 1) for h in hist]
    phases = [
        {"t0": 0, "t1": SEGMENT_S, "label": "Uso normal", "kind": "normal"},
        {"t0": SEGMENT_S, "t1": 2 * SEGMENT_S, "label": "Consumo extra", "kind": "waste"},
        {"t0": 2 * SEGMENT_S, "t1": 3 * SEGMENT_S, "label": "Otimizado", "kind": "optimized"},
    ]
    # O gráfico só redesenha com animação o trecho novo, uma vez por etapa.
    animate = st.session_state.get("_chart_stage") != stage
    st.session_state["_chart_stage"] = stage
    segment_start = STAGES.index(stage) * SEGMENT_S
    first_new = next((i for i, v in enumerate(t) if v > segment_start), len(t))
    data = {
        "t": t,
        "p": [h["power"] for h in hist],
        "temp": [h["temp"] for h in hist],
        "total": 3 * SEGMENT_S,
        "pMax": 200,
        "tMin": 25,
        "tMax": 65,
        "phases": phases,
        "animateFrom": first_new if animate else len(t),
        "label": "Potência e temperatura ao longo do tempo simulado",
    }
    st.html(
        '<section class="chart-card"><div class="chart-head"><h3>O que acontece ao longo do tempo</h3>'
        '<div class="legend"><span class="lg power">Potência (W)</span><span class="lg temp">Temperatura (°C)</span></div></div>'
        '<p class="chart-note">A potência muda na hora; a temperatura sobe e desce aos poucos. '
        'Cada etapa equivale a três minutos simulados.</p>'
        '<div id="es-chart" class="chart"></div></section>'
        + _CHART_JS % {"data": json.dumps(data)},
        unsafe_allow_javascript=True,
    )


# ------------------------------------------------------------------ blocos da página
def meter_and_label(demo, snap, stage):
    power = snap["power"]["total_w"]
    month = cost_projection(power, demo.tariff)["30d"]
    low, high = snap["anomaly"]["esperado_min"], snap["anomaly"]["esperado_max"]
    limit = high * ALERT_MARGIN
    pos = lambda w: min(100.0, max(0.0, w / GAUGE_MAX_W * 100))
    now_pos = pos(power)
    prev_pos = st.session_state.get("_prev_gauge_pos", now_pos)
    st.session_state["_prev_gauge_pos"] = now_pos
    over = power > limit
    spin = max(0.6, 200 / power) if power else 0
    if over:
        verdict = (f'<b class="up">{br(power - high, 1)} W acima</b> do máximo esperado para a tarefa')
    else:
        verdict = "Dentro do esperado para a tarefa"
    kwh_digits = f"{month['kwh']:07.2f}".replace(".", "")
    register = "".join(f'<i class="{"dec" if i >= len(kwh_digits) - 2 else ""}">{d}</i>' for i, d in enumerate(kwh_digits))

    body = (
        '<div class="hero">'
        '<div class="hero-text">'
        '<h1>Quanto custa a energia que você não vê?</h1>'
        '<p class="lede">Programas esquecidos em segundo plano fazem o computador gastar mais, mesmo quando '
        'a sua tarefa não muda. Simule o problema, encontre o excesso e veja quanto se economiza ao cortá-lo.</p>'
        '<p class="scenario">PC intermediário com navegador e documentos abertos</p>'
        f'<div class="gauge {"over" if over else ""}">'
        '<div class="gauge-head"><b>Esperado x agora</b>'
        f'<span>{verdict}</span></div>'
        '<div class="gauge-track">'
        f'<div class="gauge-ok" style="left:{pos(low):.2f}%;width:{pos(high) - pos(low):.2f}%"></div>'
        f'<div class="gauge-tol" style="left:{pos(high):.2f}%;width:{pos(limit) - pos(high):.2f}%"></div>'
        f'<div class="gauge-now" style="--from:{prev_pos:.2f}%;--to:{now_pos:.2f}%"><span>{br(power, 1)} W</span></div>'
        '</div>'
        '<div class="gauge-scale"><span>0 W</span><span>100 W</span><span>200 W</span></div>'
        '<p class="gauge-legend"><i class="ok"></i>esperado para navegador e documentos: '
        f'{br(low)} a {br(high)} W <i class="tol"></i>tolerância até {br(limit)} W</p>'
        '</div></div>'
        f'<div class="meter {"hot" if stage == "waste" else ""}">'
        '<div class="meter-head"><span>Medidor de energia</span>'
        f'<span class="meter-state">{ {"normal": "Normal", "waste": "Consumo extra", "optimized": "Otimizado"}[stage] }</span></div>'
        '<div class="meter-main">'
        f'<div class="disc" style="--spin:{spin:.2f}s" aria-hidden="true"><span></span></div>'
        f'<div><div class="watts">{counter("watts", power, 1)}<small>W</small></div>'
        '<div class="watts-cap">potência neste momento</div></div></div>'
        '<div class="register"><div class="reg-label">Em 30 dias de uso</div>'
        f'<div class="reg-digits" aria-label="{br(month["kwh"], 2)} kWh">{register}<em>kWh</em></div></div>'
        f'<div class="bill"><span>Na conta de luz</span><b>R$ {counter("month_brl", month["custo"], 2)}</b></div>'
        '<p class="meter-note">8 horas por dia, 30 dias, tarifa de '
        f'R$ {br(demo.tariff, 2)}/kWh. O disco gira mais rápido quanto maior a potência.</p>'
        '</div></div>'
    )
    animated("es-hero", body)


def steps_block(stage):
    index = STAGES.index(stage)
    names = [("Observe", "o computador em uso normal"), ("Identifique", "o que consome a mais"),
             ("Compare", "o resultado da otimização")]
    items = "".join(
        f'<li class="{"done" if i < index else "on" if i == index else ""}"><span>{i + 1}</span>'
        f'<div><b>{t}</b><small>{d}</small></div></li>'
        for i, (t, d) in enumerate(names)
    )
    st.html(f'<ol class="steps" style="--progress:{index / 2:.2f}">{items}</ol>')


def kpis_block(demo, snap, stage):
    base = st.session_state.setdefault("_normal_snapshot", {"temp": snap["temp"], "power": snap["power"]["total_w"]})
    temp = snap["temp"]
    d_temp = temp - base["temp"]
    if stage == "waste":
        temp_note = f'<b class="up">+{br(d_temp, 1)} °C</b> em relação ao uso normal'
    elif stage == "optimized":
        temp_note = "voltando ao normal aos poucos"
    else:
        temp_note = "estável, com a refrigeração dando conta"
    waste_w = snap["power"]["waste_w"]
    extra_month = cost_projection(waste_w, demo.tariff)["30d"]["custo"] if waste_w else 0.0
    cards = [
        ("Temperatura do processador", f'{counter("temp", temp, 1)}<small>°C</small>', temp_note),
        ("Carga da sua tarefa", f'{counter("cpu", snap["cpu_util"], 0)}<small>% da CPU</small>',
         f'placa de vídeo em {br(snap["gpu_util"], 0)}%. Não muda: o extra vem de processos em segundo plano'),
        ("Consumo sem utilidade", f'{counter("waste", waste_w, 0)}<small>W</small>',
         f'<b class="up">R$ {br(extra_month, 2)}</b> por mês jogados fora' if waste_w
         else "nenhum processo desnecessário ativo"),
    ]
    body = '<div class="kpis">' + "".join(
        f'<div class="kpi {"alert" if stage == "waste" and i != 1 else ""}"><div class="kpi-l">{label}</div>'
        f'<div class="kpi-v">{value}</div><div class="kpi-n">{note}</div></div>'
        for i, (label, value, note) in enumerate(cards)
    ) + "</div>"
    animated("es-kpis", body)


def story_block(demo, snap, stage):
    anomaly = snap["anomaly"]
    limit = anomaly["esperado_max"] * 1.15
    if stage == "normal":
        kind, title, text = ("ok", "Tudo dentro do esperado",
                             f'Para navegador e documentos, o esperado é entre {br(anomaly["esperado_min"])} e '
                             f'{br(anomaly["esperado_max"])} W. Agora vamos ligar processos que consomem energia sem '
                             "contribuir para o trabalho.")
    elif stage == "waste":
        kind, title, text = ("alert", "Alerta: consumo acima do esperado",
                             f'O medidor marca {br(anomaly["atual"])} W, acima do limite de alerta de {br(limit)} W. '
                             f'A tarefa é a mesma: os {br(snap["power"]["waste_w"], 0)} W a mais vêm de abas esquecidas, '
                             "programas abertos sozinhos ou sincronizações desnecessárias.")
    else:
        kind, title, text = ("done", "Mesmo trabalho, menos energia",
                             "A otimização simulada removeu só o consumo desnecessário. A carga da sua tarefa continua "
                             "a mesma. Veja abaixo quanto isso representa.")
    icon = {"ok": "✓", "alert": "!", "done": "✓"}[kind]
    st.html(f'<div class="story {kind}"><span class="story-icon" aria-hidden="true">{icon}</span>'
            f'<div><h3>{html.escape(title)}</h3><p>{html.escape(text)}</p></div></div>')


def result_block(demo):
    result = demo.comparison()
    if not result:
        return
    ratio = result["after_w"] / result["before_w"] * 100 if result["before_w"] else 0
    body = (
        '<div class="result"><div class="result-bars"><h3>Antes e depois</h3>'
        f'<div class="rb-row"><span>Com consumo desnecessário</span><b>{br(result["before_w"])} W</b></div>'
        '<div class="rb-track"><div class="rb-fill before" style="--w:100%"></div></div>'
        f'<div class="rb-row"><span>Depois da otimização</span><b>{br(result["after_w"])} W</b></div>'
        f'<div class="rb-track"><div class="rb-fill after" style="--w:{ratio:.2f}%"></div></div>'
        '<dl class="rb-facts">'
        f'<div><dt>Temperatura</dt><dd>{br(result["before_temp"])} → {br(result["after_temp"])} °C</dd></div>'
        f'<div><dt>Custo em 30 dias</dt><dd>R$ {br(result["before_month"]["custo"], 2)} → '
        f'R$ {br(result["after_month"]["custo"], 2)}</dd></div></dl></div>'
        '<div class="savings">'
        f'<div class="sv-big">{counter("reduction", result["reduction_pct"], 1)}<small>%</small></div>'
        '<div class="sv-cap">menos potência para fazer o mesmo trabalho</div>'
        f'<div class="sv-money">R$ {counter("saved_brl", result["saved_brl"], 2)} <small>por mês</small></div>'
        f'<div class="sv-cap">{br(result["saved_kwh"], 2)} kWh a menos no mesmo período de uso</div>'
        '</div></div>'
    )
    animated("es-result", body)


def render_scale(tariff):
    st.html(
        '<div class="section"><h2>E em grande escala?</h2>'
        '<p>Um computador parece pouco. Em uma escola, um escritório ou um laboratório, '
        'o mesmo desperdício se repete em cada máquina ligada.</p></div>'
    )
    col, _ = st.columns([1, 2])
    computers = col.number_input("Quantidade de computadores", min_value=1, max_value=10000,
                                 value=30, step=1, key="scale_pcs")
    s = scale_savings(tariff, computers)
    body = (
        '<div class="scale">'
        f'<div class="scale-main"><div class="sc-l">Economia por ano com {br(computers, 0)} computadores</div>'
        f'<div class="sc-v">R$ {counter("scale_brl", s["year_brl"], 0)}</div>'
        f'<div class="sc-n">eliminando {br(QuickDemo.WASTE_W, 0)} W de consumo extra em cada um</div></div>'
        f'<div class="scale-side"><div class="sc-l">Energia poupada por ano</div>'
        f'<div class="sc-v">{counter("scale_kwh", s["year_kwh"], 0)} <small>kWh</small></div>'
        '<div class="sc-n">energia que deixaria de ser gasta sem nenhum benefício</div></div>'
        f'<div class="scale-side"><div class="sc-l">Por computador</div>'
        f'<div class="sc-v">R$ {br(s["pc_year_brl"], 2)}</div>'
        f'<div class="sc-n">por ano, ou R$ {br(s["pc_month_brl"], 2)} por mês</div></div>'
        '</div>'
    )
    animated("es-scale", body)


def render_actions(tariff):
    saved = cost_projection(QuickDemo.WASTE_W, tariff)["30d"]["custo"]
    actions = [
        ("Encerrar o que não está em uso",
         f"Feche no gerenciador de tarefas os programas esquecidos. No cenário simulado, isso economiza "
         f"R$ {br(saved, 2)} por mês."),
        ("Desativar a inicialização automática",
         "Impeça que atualizadores e aplicativos pouco usados abram sozinhos toda vez que o computador liga."),
        ("Acompanhar o consumo",
         "Comparar o consumo com o esperado para a tarefa, como faz o EnergySim, revela o desperdício que não "
         "aparece na tela."),
    ]
    st.html(
        '<div class="section"><h2>O que fazer no dia a dia</h2></div><ol class="actions">'
        + "".join(f"<li><b>{html.escape(t)}</b><p>{html.escape(d)}</p></li>" for t, d in actions)
        + "</ol>"
    )


# ------------------------------------------------------------------ página
def render_demo():
    if "quick_demo" not in st.session_state:
        st.session_state.quick_demo = QuickDemo()
    demo = st.session_state.quick_demo
    snap = demo.snapshot()
    stage = demo.stage

    st.html('<header class="mast"><span class="brand"><span class="bolt" aria-hidden="true"></span>EnergySim</span>'
            '<span class="mast-note">Simulação educativa de consumo de energia</span></header>')
    meter_and_label(demo, snap, stage)
    steps_block(stage)
    story_block(demo, snap, stage)

    c1, c2, c3 = st.columns([2, 2, 1])
    c1.button("1. Mostrar consumo extra", type="primary" if stage == "normal" else "secondary",
              disabled=stage != "normal", on_click=demo.inject_waste, width="stretch", icon=":material/bolt:")
    c2.button("2. Simular otimização", type="primary" if stage == "waste" else "secondary",
              disabled=stage != "waste", on_click=demo.optimize, width="stretch", icon=":material/auto_fix_high:")

    def reset():
        st.session_state.quick_demo = QuickDemo(demo.tariff)

    c3.button("Recomeçar", on_click=reset, width="stretch", icon=":material/restart_alt:", disabled=stage == "normal")

    kpis_block(demo, snap, stage)
    result_block(demo)
    chart_block(demo, stage)

    render_scale(demo.tariff)
    render_actions(demo.tariff)

    with st.expander("Premissas da simulação e tarifa"):
        st.markdown(f'<div class="el-disclaimer">Demonstração educativa, sem leitura de sensores nem alteração de processos reais. Projeção: 8 h por dia, durante 30 dias, com tarifa ilustrativa de R$ {br(demo.tariff,2)} por kWh e consumo constante. Cada etapa térmica representa três minutos simulados. Os 90 W adicionais são uma hipótese de teste, não uma medida de aplicativos específicos.</div>', unsafe_allow_html=True)
        st.write("Esta é uma simulação controlada. A intervenção aplica a ação 'verificar processos' do modelo, sem encerrar nenhum programa real. O alerta compara a potência total com uma faixa esperada da tarefa, acrescida de 15% de tolerância. A economia compara a mesma carga útil e as mesmas 240 horas mensais antes e depois.")
        st.write("Atualizações, sincronizações e backups nem sempre são desperdício: o excesso precisa ser confirmado em uma implementação com sensores e processos reais. A temperatura varia ao longo do tempo e não cai imediatamente em hardware físico.")
        tariff = st.number_input("Tarifa utilizada no exemplo (R$/kWh)", min_value=0.10, max_value=3.0, value=demo.tariff, step=0.05, key="demo_tariff")
        if tariff != demo.tariff:
            demo.tariff = tariff
            demo.sim.tarifa_kwh = tariff
            st.rerun()
    with st.expander("Ficha técnica do computador"):
        specs = hardware_details(demo.sim.computer)
        cards = ''.join(
            f'<div class="el-spec"><small>{html.escape(label)}</small><b>{html.escape(value)}</b></div>'
            for label, value in specs
        )
        st.markdown('<div class="el-hardware"><h3>Computador desta simulação</h3><div class="el-specs">' + cards + '</div><p>Configuração de referência. Não é uma detecção do seu computador. Turbo é um limite eventual; consumo, temperatura e clock são estimativas didáticas.</p></div>', unsafe_allow_html=True)
    st.write("O modo completo inclui seleção de computadores e atividades, relatórios, testes de estresse e experimentos.")
    if st.button("Explorar o modo completo"):
        st.session_state.screen = "intro_problema"
        st.rerun()
