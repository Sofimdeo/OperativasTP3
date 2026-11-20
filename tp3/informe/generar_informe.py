"""
Genera el informe (HTML y PDF) a partir de ../resultados/resultados.json.
Requiere haber ejecutado antes main.py. El PDF se imprime con Chromium (Playwright);
si Playwright no está disponible, queda el HTML para imprimir desde el navegador.
"""
import base64
import json
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
RES = AQUI.parent / "resultados"
R = json.loads((RES / "resultados.json").read_text())
P = R["parametros"]
PL = R["plan"]
FC = R["pronostico"]


def f(x, d=0):
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, d=1):
    return f(100 * x, d) + "%"


def img(nombre):
    b = base64.b64encode((RES / nombre).read_bytes()).decode()
    return f'<img src="data:image/png;base64,{b}">'


def tabla(df, cols, encabezados, formatos, clase=""):
    h = "".join(f"<th>{e}</th>" for e in encabezados)
    filas = []
    for _, r in df.iterrows():
        celdas = []
        for c, fm in zip(cols, formatos):
            v = r[c]
            celdas.append(f"<td>{fm(v) if fm else v}</td>")
        filas.append("<tr>" + "".join(celdas) + "</tr>")
    return f'<table class="{clase}"><thead><tr>{h}</tr></thead><tbody>{"".join(filas)}</tbody></table>'


# ---------------------------------------------------------------- datos
ns = pd.DataFrame(R["nivel_servicio"])
ev = R["evaluacion_plan"]
st = R["stocks_esperados"]
c2, c3 = R["C2"], R["C3"]
comp = pd.DataFrame(R["comparacion_planes"])
rob = pd.DataFrame(R["robustez"])
sens = pd.DataFrame(R["sensibilidad"])
reps = pd.DataFrame(R["replicas"])
val = {s: pd.read_csv(RES / f"validacion_{s}.csv") for s in ("di", "de", "tc")}
tc_n, tc_d = FC["tc"]["nov"], FC["tc"]["dic"]


def g(mes, prod, mk, col):
    return ns.query("mes==@mes and producto==@prod and mercado==@mk")[col].iloc[0]


# márgenes por t de almidón (ARS) con el TC pronosticado
def margenes(e):
    return [("Jarabe interno", 750_000 - 35 * e), ("Almidón interno", 640_000),
            ("Jarabe externo", (365 - 35) * e), ("Almidón externo", 300 * e)]


Pn = P["almidon_noviembre_t"]
S0 = P["stock_inicial_almidon_t"]
Pd = PL["Pd"]
costo_alm_anticipo = 1.5 * 171_500 + 95 * tc_d
costo_alm_spot = 245 * tc_d

# ---------------------------------------------------------------- HTML
css = """
@page { size: A4; margin: 16mm 15mm 16mm 15mm; }
:root { --tinta:#1b1b1a; --tinta2:#52514e; --linea:#dddcd7; --acento:#2a78d6; --fondo:#f5f4f0; }
body { font-family: 'DejaVu Sans', Arial, sans-serif; font-size: 9.6pt; line-height: 1.45; color: var(--tinta); background:#fff; }
h1 { font-size: 19pt; margin: 0 0 2mm 0; }
h2 { font-size: 13pt; margin: 7mm 0 2mm 0; padding-bottom: 1mm; border-bottom: 1.5px solid var(--acento); break-after: avoid; }
h3 { font-size: 10.5pt; margin: 4mm 0 1.5mm 0; break-after: avoid; }
p { margin: 1.2mm 0 2mm 0; text-align: justify; }
.sub { color: var(--tinta2); margin-bottom: 5mm; }
table { border-collapse: collapse; width: 100%; margin: 2mm 0 3mm 0; font-size: 8.4pt; break-inside: avoid; }
th { background: var(--fondo); text-align: left; font-weight: bold; border-bottom: 1px solid #bbb; padding: 1.2mm 1.6mm; }
td { border-bottom: 1px solid var(--linea); padding: 1mm 1.6mm; }
td:not(:first-child), th:not(:first-child) { text-align: right; }
table.izq td, table.izq th { text-align: left; }
.caja { background: var(--fondo); border-left: 3px solid var(--acento); padding: 2.5mm 4mm; margin: 3mm 0; break-inside: avoid; }
.decision { display: grid; grid-template-columns: repeat(4, 1fr); gap: 3mm; margin: 3mm 0 4mm; }
.decision div { border: 1px solid var(--linea); border-radius: 4px; padding: 2.5mm; }
.decision b { display:block; font-size: 14pt; margin-top: 1mm; }
.decision span { color: var(--tinta2); font-size: 8pt; }
img { width: 100%; margin: 2mm 0; break-inside: avoid; }
code, .mono { font-family: 'DejaVu Sans Mono', monospace; font-size: 8.4pt; }
.form { font-family: 'DejaVu Sans Mono', monospace; font-size: 8.6pt; background: var(--fondo); padding: 3mm 4mm; white-space: pre-wrap; }
ul { margin: 1mm 0 2mm 0; padding-left: 5mm; } li { margin: 0.8mm 0; }
.nota { color: var(--tinta2); font-size: 8.2pt; }
.salto { break-before: page; }
"""

v = R["formulario"]
html = []
A = html.append
A(f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>TP3 Gestión integrada de stocks</title>
<style>{css}</style></head><body>
<h1>Gestión integrada de stocks — empresa agroindustrial</h1>
<div class="sub">Investigación Operativa · Trabajo Práctico 3 · Padrón terminado en <b>5</b> (hoja <i>Digito_5</i>) ·
Plan formulado al comienzo de noviembre de 2026 con información hasta octubre de 2026</div>

<h2>1. Recomendación a la gerencia</h2>
<div class="decision">
 <div><span>1 · Jarabe a producir en noviembre</span><b>{f(PL['Jn'])} t</b><span>t equivalentes de materia seca</span></div>
 <div><span>2 · Maíz a comprar para diciembre</span><b>{f(PL['maiz_dic'])} t</b><span>= {f(Pd)} t de almidón a obtener</span></div>
 <div><span>3 · Jarabe a producir en diciembre</span><b>{f(PL['Jd'])} t</b><span>t equivalentes de materia seca</span></div>
 <div><span>4 · Anticipo (fijar y pagar en nov.)</span><b>{f(PL['F'],2)} t</b><span>todo lo que permite la caja</span></div>
</div>
<p><b>Política.</b> Noviembre está condicionado por el pedido de maíz heredado: se obtienen {f(Pn)} t de almidón que, sumadas al stock inicial de {f(S0)} t,
dan {f(S0+Pn)} t disponibles frente a una demanda esperada de {f(FC['di']['nov']+FC['de']['nov'])} t: <b>noviembre es un mes de escasez estructural</b> que ninguna
decisión tomada hoy puede corregir. La escasez se administra con la regla económica: el mercado interno de ambos productos se atiende al 100% y el faltante se concentra
en el externo (primero en almidón externo, el destino de menor margen). En diciembre se compra maíz para obtener {f(Pd)} t de almidón, cerca del límite de horas de planta
({f(PL['horas_dic'])} de 60.000 h), dimensionado como un “newsvendor” sobre la demanda total: producir una tonelada más rinde 300 USD si se vende al exterior pero sólo
172 USD (180 de continuidad − 8 de conservación) si queda en depósito, contra un costo de 245 USD. El jarabe, que no se puede stockear (72 h), se planifica algo por debajo
de su demanda esperada para que el riesgo de vencimiento sea bajo; el almidón no usado en jarabe se vende como almidón. <b>Todo el maíz de diciembre que alcanza la caja
({f(PL['F'],2)} t) se fija y paga ya a 171.500 ARS/t</b>, porque el tipo de cambio esperado para diciembre ({f(tc_d)} ARS/USD) supera el de octubre y el anticipo además
elimina el riesgo de precio del maíz y del tipo de cambio sobre ese volumen.</p>

<h3>Calendario de fijación y pago del maíz de diciembre</h3>
<table class="izq"><thead><tr><th>Momento</th><th>Concepto</th><th>Cantidad</th><th>Precio</th><th>Importe</th></tr></thead><tbody>
<tr><td>Ya realizado</td><td>Pedido heredado de noviembre (hundido)</td><td>{f(P['maiz_noviembre_t'])} t</td><td>171.500 ARS/t</td><td>{f(P['maiz_noviembre_t']*171500/1e6)} M ARS</td></tr>
<tr><td>Comienzo de noviembre</td><td>Anticipo: se fija y paga parte de la compra de diciembre</td><td>{f(PL['F'],2)} t</td><td>171.500 ARS/t</td><td>{f(PL['anticipo_ARS']/1e6,1)} M ARS (caja disponible: {f(P['caja_para_anticipo_ARS']/1e6,1)} M)</td></tr>
<tr><td>Diciembre, al recibir</td><td>Saldo de la compra de diciembre</td><td>{f(PL['Q_spot'],2)} t</td><td>100 USD/t × TC dic.</td><td>≈ {f(PL['pago_dic_esperado_ARS']/1e6,0)} M ARS (con TC {f(tc_d)})</td></tr>
</tbody></table>

<h3>Producción, ventas y stocks esperados</h3>
<table><thead><tr><th></th><th>Noviembre</th><th>Diciembre</th></tr></thead><tbody>
<tr><td>Almidón obtenido del maíz (t)</td><td>{f(Pn)}</td><td>{f(Pd)}</td></tr>
<tr><td>Maíz procesado (t)</td><td>{f(P['maiz_noviembre_t'])}</td><td>{f(PL['maiz_dic'])}</td></tr>
<tr><td>Jarabe elaborado (t) = almidón transformado</td><td>{f(PL['Jn'])}</td><td>{f(PL['Jd'])}</td></tr>
<tr><td>Horas de planta usadas (de 60.000)</td><td>{f(PL['horas_nov'])}</td><td>{f(PL['horas_dic'])}</td></tr>
<tr><td>Ventas esperadas almidón interno / externo (t)</td><td>{f(g('nov','Almidón','Interno','ventas_medias_t'))} / {f(g('nov','Almidón','Externo','ventas_medias_t'))}</td><td>{f(g('dic','Almidón','Interno','ventas_medias_t'))} / {f(g('dic','Almidón','Externo','ventas_medias_t'))}</td></tr>
<tr><td>Ventas esperadas jarabe interno / externo (t)</td><td>{f(g('nov','Jarabe','Interno','ventas_medias_t'))} / {f(g('nov','Jarabe','Externo','ventas_medias_t'))}</td><td>{f(g('dic','Jarabe','Interno','ventas_medias_t'))} / {f(g('dic','Jarabe','Externo','ventas_medias_t'))}</td></tr>
<tr><td>Jarabe vencido esperado (t)</td><td>{f(st['jarabe_vencido_nov_medio'])}</td><td>{f(st['jarabe_vencido_dic_medio'])}</td></tr>
<tr><td>Stock de almidón al cierre: media (percentil 95) (t)</td><td>{f(st['almidon_cierre_nov_medio'])} ({f(st['almidon_cierre_nov_p95'])})</td><td>{f(st['almidon_cierre_dic_medio'])} ({f(st['almidon_cierre_dic_p95'])})</td></tr>
<tr><td>Stock de maíz al cierre (t)</td><td>0</td><td>0</td></tr>
</tbody></table>
<p>Resultado económico incremental esperado de noviembre-diciembre (ventas − procesamiento − maíz de diciembre − conservación − disposición + valor de continuidad;
excluye el maíz de noviembre y el stock inicial, que son costos hundidos): <b>{f(ev['media_MARS'])} M ARS</b>, con desvío {f(ev['desvio_MARS'])} M,
percentil 5 = {f(ev['p05_MARS'])} M y CVaR 5% = {f(ev['CVaR5_MARS'])} M. El depósito nunca se desborda en la simulación (máximo 30.000 t).</p>

<h3>Principales riesgos asumidos</h3>
<ul>
<li><b>Faltante en el mercado externo en noviembre</b> (casi seguro: la probabilidad de atender toda la demanda externa de almidón es {pct(g('nov','Almidón','Externo','P_satisfaccion_total'))}); es consecuencia del pedido heredado, no de la política.</li>
<li><b>Caída de la demanda</b>: con demanda externa −20% o interna −10% el plan fijo genera jarabe vencido (≈ 2.200–2.800 t) y almidón sobrante, que queda valuado a 180 USD/t; el resultado cae ≈ 6–8%, pero el mercado interno se sigue cubriendo al 100%.</li>
<li><b>Rendimiento del maíz</b>: si se necesitaran 1,60 t de maíz por t de almidón, el almidón obtenido cae ≈ 6% y el faltante externo crece (fracción cubierta {pct(rob.query("escenario=='Rendimiento 1,60 t maíz/t almidón' and plan=='Recomendado'").fill_externo.iloc[0])}); el interno se mantiene cubierto.</li>
<li><b>Tipo de cambio</b>: el anticipo pierde frente a pagar en diciembre sólo si el TC de diciembre resulta menor que 1.715 ARS/USD (apreciación nominal, nunca observada en los 22 meses). Con una apreciación del 10% el anticipo cuesta ≈ {f(rob.query("escenario=='Apreciación: TC -10%' and plan=='Sin anticipo'").media_MARS.iloc[0]-rob.query("escenario=='Apreciación: TC -10%' and plan=='Recomendado'").media_MARS.iloc[0])} M ARS; con una devaluación del 15% ahorra ≈ {f(rob.query("escenario=='Devaluación: TC dic +15%' and plan=='Recomendado'").media_MARS.iloc[0]-rob.query("escenario=='Devaluación: TC dic +15%' and plan=='Sin anticipo'").media_MARS.iloc[0])} M ARS.</li>
<li><b>Capacidad de planta en diciembre</b>: el plan usa {pct(PL['horas_dic']/60000)} de las horas; no queda margen para producir mucho más almidón sin resignar jarabe.</li>
</ul>

<h2>2. Datos de la cátedra y supuestos del alumno</h2>
<table class="izq"><thead><tr><th style="width:52%">Datos de la cátedra (padrón terminado en 5)</th><th>Supuestos y simplificaciones del alumno</th></tr></thead><tbody>
<tr><td>Histórico ene-2025 a oct-2026 (hoja Digito_5): demanda interna, externa y TC.</td><td>Horizonte mensual: producción, ventas y despachos se agregan por mes; sólo se controla el stock al cierre.</td></tr>
<tr><td>Composición: interno 45% A / 55% J; externo 55% A / 45% J (fija).</td><td>Relaciones de transformación constantes en el horizonte (1,50 t maíz/t almidón; 1 t almidón/t jarabe): dos meses, mismo proveedor y planta; el desvío se evalúa como riesgo (rendimiento 1,60).</td></tr>
<tr><td>Stock inicial almidón 15.000 t; maíz de noviembre 57.500 t pagado a 171.500 ARS/t.</td><td>Jarabe: no pasa de un mes a otro (vida útil 72 h); lo no vendido en el mes vence.</td></tr>
<tr><td>Precios: almidón 640.000 ARS/t (int.) y 300 USD/t (ext.); jarabe 750.000 ARS/t (int.) y 365 USD/t (ext.).</td><td>Errores de pronóstico normales; TC lognormal; demandas interna y externa independientes entre sí (correlación estimada {f(FC['rho_int_ext'],2)}, no significativa con 9 datos).</td></tr>
<tr><td>Costos: proceso 95 USD/t almidón; maíz 100 USD/t (150 USD por t de almidón); jarabe +35 USD/t; conservación 8 USD/t·mes; disposición jarabe 12 USD/t; continuidad 180 USD/t.</td><td>Piso de incertidumbre de 2% (CV) para la demanda interna (el error histórico fuera de muestra es ≈ 0,01%, pero 22 meses no permiten descartar un cambio).</td></tr>
<tr><td>Planta: 60.000 h/mes (1 h por t almidón, 0,25 h por t jarabe); jarabe ≤ 30.000 t/mes; mínimo 30.000 t/mes de almidón; depósito ≤ 30.000 t.</td><td>Cotización del maíz en diciembre = 100 USD/t (condiciones normales); 120 USD/t se analiza como escenario adverso.</td></tr>
<tr><td>Caja 20.000 M ARS antes del pedido de noviembre → {f(P['caja_para_anticipo_ARS']/1e6,2)} M ARS para anticipar ({f(P['maiz_max_anticipo_t'],2)} t).</td><td>Almidón que excediera el depósito se liquida sin valor con costo de 12 USD/t (nunca ocurre en el plan propuesto).</td></tr>
<tr><td>Prioridad del mercado interno por producto; pedidos no atendidos se pierden.</td><td>Objetivo: maximizar el resultado esperado en ARS nominales (sin intereses), con importes USD al TC del mes. Costos hundidos excluidos.</td></tr>
</tbody></table>

<h2 class="salto">3. Parte A — Pronóstico</h2>
<p><b>Método de selección.</b> Para cada serie se compararon varios métodos con <b>validación de origen móvil</b>: con la historia hasta el mes <i>t</i> se pronostican
<i>t+1</i> y <i>t+2</i>, y se repite avanzando el origen. Es exactamente el uso que tendrán (noviembre = 1 mes, diciembre = 2 meses adelante). Para las demandas se usaron
los orígenes de feb-2026 a oct-2026 (los métodos estacionales necesitan al menos un año de historia); para el TC, de sep-2025 en adelante. Se elige el menor MAPE promedio
y la incertidumbre se mide con los errores <i>fuera de muestra</i> del método elegido (no con los residuos de ajuste, que la subestiman).</p>
""")


def tabla_val(s, n=5):
    d = val[s].head(n)
    return tabla(d, ["metodo", "MAPE_h1_%", "MAPE_h2_%", "sesgo_h1_%", "RMSE_h1", "RMSE_h2"],
                 ["Método", "MAPE 1 mes", "MAPE 2 meses", "Sesgo 1 mes", "RMSE 1 mes", "RMSE 2 meses"],
                 [None, lambda x: f(x, 2) + "%", lambda x: f(x, 2) + "%", lambda x: f(x, 2) + "%", lambda x: f(x, 0), lambda x: f(x, 0)])


A(f"""<h3>Demanda interna</h3>
<p>La serie tiene una estacionalidad marcada (pico en mayo, mínimos en octubre-enero) y cada mes de 2026 es exactamente 1,78% mayor que el mismo mes de 2025.
El método <b>estacional × crecimiento interanual</b> (mismo mes del año anterior × media geométrica de los cocientes interanuales) tiene un error fuera de muestra
prácticamente nulo; los métodos sin estacionalidad (ingenuo, promedio móvil, Holt) fallan por 5–10%.</p>
{tabla_val('di')}
<h3>Demanda externa</h3>
<p>Estacionalidad opuesta (mínimos en abril-mayo, máximos en octubre-noviembre) con ruido importante: el cociente interanual oscila entre 0,90 y 1,08.
Con sólo 22 meses, un modelo parsimonioso que usa toda la historia — <b>regresión con tendencia lineal y un armónico anual</b> (4 parámetros) — supera al estacional
ingenuo, que copia el ruido del año anterior. Error fuera de muestra ≈ 4–5%.</p>
{tabla_val('de')}
<h3>Tipo de cambio</h3>
<p>Crece de forma sostenida (≈ 2,3–4,1% mensual, sin ninguna baja). El mejor método es una <b>caminata aleatoria con deriva logarítmica</b> estimada con los
últimos 6 meses (crecimiento ≈ 3,1% mensual), que captura la leve aceleración reciente.</p>
{tabla_val('tc', 4)}
{img('fig_pronosticos.png')}
<h3>Pronósticos e incertidumbre</h3>
<table><thead><tr><th>Variable</th><th>Noviembre</th><th>Intervalo 90%</th><th>Diciembre</th><th>Intervalo 90%</th><th>Desvío relativo (nov / dic)</th></tr></thead><tbody>
""")
for s, nom in (("di", "Demanda interna (t)"), ("de", "Demanda externa (t)"), ("tc", "Tipo de cambio (ARS/USD)")):
    p = FC[s]
    A(f"<tr><td>{nom}</td><td>{f(p['nov'])}</td><td>{f(p['nov_li90'])} – {f(p['nov_ls90'])}</td><td>{f(p['dic'])}</td>"
      f"<td>{f(p['dic_li90'])} – {f(p['dic_ls90'])}</td><td>{pct(p['sd_rel_nov'],2)} / {pct(p['sd_rel_dic'],2)}</td></tr>")
A("</tbody></table>")
comp_d = pd.DataFrame(R["demanda_por_producto"])
A(tabla(comp_d, ["mes", "Almidón interno", "Jarabe interno", "Almidón externo", "Jarabe externo", "Total (t almidón eq.)"],
        ["Demanda esperada por producto (t MS)", "Almidón int.", "Jarabe int.", "Almidón ext.", "Jarabe ext.", "Total"],
        [lambda x: x.capitalize()] + [lambda x: f(x)] * 5))
A(f"""<p><b>Análisis de la incertidumbre.</b> (i) La demanda interna es casi determinística en la historia (error {pct(FC['di']['sd_rel_estadistico'][0],3)});
como 22 meses no alcanzan para descartar un cambio de régimen se adoptó un CV del 2% (supuesto prudencial, con correlación nov-dic alta: un desvío de nivel
afecta a ambos meses). (ii) La demanda externa es la fuente principal de incertidumbre: desvío ≈ {pct(FC['de']['sd_rel_nov'])} en noviembre y
{pct(FC['de']['sd_rel_dic'])} en diciembre (≈ ±{f(1.645*FC['de']['sd_rel_nov']*FC['de']['nov'])} t con 90% de confianza); los errores de ambos meses
casi no están correlacionados ({f(FC['de']['rho_nov_dic'],2)}). (iii) El TC tiene un error muy bajo (&lt; 1%) porque la serie es muy regular; aun así se
estresa el plan con una devaluación del 15% y una apreciación del 10%. Con estos parámetros se generan escenarios conjuntos (nov, dic) de las tres variables.</p>

<h2 class="salto">4. Parte B — Modelo de producción y abastecimiento</h2>
<h3>Lógica económica</h3>
<p>Valor de una tonelada de almidón según su destino (ARS/t, con el TC pronosticado; el jarabe se neta del costo de transformación de 35 USD/t):</p>
<table><thead><tr><th>Destino de 1 t de almidón</th><th>Noviembre (TC {f(tc_n)})</th><th>Diciembre (TC {f(tc_d)})</th></tr></thead><tbody>
""")
for (n1, v1), (_, v2) in zip(margenes(tc_n), margenes(tc_d)):
    A(f"<tr><td>{n1}</td><td>{f(v1)}</td><td>{f(v2)}</td></tr>")
A(f"""<tr><td>Quedar en depósito al cierre de diciembre (180 − 8 USD)</td><td>—</td><td>{f(172*tc_d)}</td></tr>
<tr><td><i>Costo de obtener 1 t de almidón en diciembre — maíz anticipado</i></td><td>—</td><td><i>{f(costo_alm_anticipo)}</i></td></tr>
<tr><td><i>Costo de obtener 1 t de almidón en diciembre — maíz pagado al recibir</i></td><td>—</td><td><i>{f(costo_alm_spot)}</i></td></tr>
</tbody></table>
<p>Consecuencias: (1) todos los destinos de venta superan el costo de producir, así que conviene producir para toda la demanda esperada; (2) el orden de rentabilidad
(jarabe int. &gt; almidón int. &gt; jarabe ext. &gt; almidón ext.) es compatible con la prioridad comercial del mercado interno; (3) producir de más es caro (vale
{f(172*tc_d)} si sobra contra {f(costo_alm_anticipo)} de costo), por lo que la cantidad óptima es un cuantil de la demanda, no la demanda máxima;
(4) el jarabe sobrante pierde todo (almidón + 35 + 12 USD/t), por eso se planifica por debajo de su demanda media; (5) fijar el maíz a 171.500 ARS/t
ahorra ≈ {f(100*tc_d-171500)} ARS por t frente a pagarlo en diciembre, de modo que el anticipo óptimo es el máximo financiable.</p>

<h3>Formulación (programación lineal estocástica de dos etapas)</h3>
<p><b>Primera etapa</b> (se decide en noviembre y no se revisa): <span class="mono">Jn, Jd</span> = jarabe de noviembre y diciembre; <span class="mono">Pd</span> = almidón a obtener
en diciembre (maíz <span class="mono">C = 1,5·Pd</span>); <span class="mono">F</span> = maíz anticipado; <span class="mono">Q</span> = maíz pagado al recibir.<br>
<b>Segunda etapa</b> (por escenario): ventas <span class="mono">sAi, sAe, sJi, sJe</span>, jarabe vencido <span class="mono">W</span>, stock de almidón <span class="mono">I</span>.
Se usa un árbol de 100 nodos de noviembre × 50 de diciembre (5.000 trayectorias); las variables de noviembre dependen sólo del nodo de noviembre (no anticipatividad).</p>
<div class="caja mono" style="white-space:pre-line">max  −171.500·F + Σ<sub>s</sub> p<sub>s</sub> · Σ<sub>t∈{{nov,dic}}</sub> [ 640.000·sAi + 300·e·sAe + 750.000·sJi + 365·e·sJe − 95·e·P<sub>t</sub> − 35·e·J<sub>t</sub> − 12·e·W − 8·e·I ]  + 180·e<sub>dic</sub>·I<sub>dic</sub> − 100·e<sub>dic</sub>·Q
s.a.  F + Q = 1,5·Pd ;   F ≤ {f(P['maiz_max_anticipo_t'],2)} (caja) ;   Pd ≥ 30.000 (continuidad) ;   Pn = 57.500/1,5 = {f(Pn,2)} (fijo)
      P<sub>t</sub> + 0,25·J<sub>t</sub> ≤ 60.000 (horas) ;   J<sub>t</sub> ≤ 30.000 (etapa jarabe)
      sJi + sJe + W = J<sub>t</sub>   (el jarabe no se stockea)
      I<sub>t−1</sub> + P<sub>t</sub> − J<sub>t</sub> − sAi − sAe = I<sub>t</sub> ;   0 ≤ I<sub>t</sub> ≤ 30.000 (depósito) ;   I<sub>oct</sub> = 15.000
      sAi ≤ 0,45·DI ;  sJi ≤ 0,55·DI ;  sAe ≤ 0,55·DE ;  sJe ≤ 0,45·DE   (por escenario y mes)</div>
<p>La prioridad del mercado interno no requiere restricciones adicionales: mientras el precio interno en ARS supere al externo (TC &lt; 2.055), el modelo atiende
primero el interno por conveniencia. La evaluación posterior (simulación) aplica la regla comercial de forma explícita en todos los escenarios. Se resolvió con
<b>PuLP</b> (solver HiGHS o CBC).</p>

<h3>Estabilidad y validación del modelo</h3>
<p>El modelo se resolvió con 5 árboles independientes de 2.000 trayectorias y luego con uno de 5.000; cada plan se evaluó en 20.000 escenarios nuevos
(fuera de muestra) con la regla comercial exacta.</p>
""")
A(tabla(reps, ["replica", "Jn", "C_maiz", "Jd", "F", "obj_en_muestra_MARS", "obj_fuera_muestra_MARS"],
        ["Réplica", "Jn (t)", "Maíz dic (t)", "Jd (t)", "Anticipo (t)", "Resultado en muestra (M ARS)", "Fuera de muestra (M ARS)"],
        [lambda x: f(x), lambda x: f(x), lambda x: f(x), lambda x: f(x), lambda x: f(x, 2), lambda x: f(x), lambda x: f(x)]))
A(f"""<p>Las decisiones varían menos de ±1% entre réplicas y el resultado fuera de muestra varía menos de 0,02%: la superficie es plana cerca del óptimo y la
recomendación (árbol de 5.000 trayectorias, redondeada a toneladas) es estable.</p>
<h3>Comparación con planes alternativos</h3>
""")
A(tabla(comp, ["plan", "Jn", "maiz_dic", "Jd", "F", "media_MARS", "p05_MARS", "CVaR5_MARS", "fill_externo"],
        ["Plan", "Jn", "Maíz dic", "Jd", "Anticipo", "Media (M ARS)", "P5", "CVaR 5%", "% demanda ext. cubierta"],
        [None] + [lambda x: f(x)] * 4 + [lambda x: f(x)] * 3 + [lambda x: pct(x)], "comp"))
A(f"""<p>El plan determinístico (optimizar con la demanda esperada) produce todo el jarabe esperado y genera más vencimientos: el plan estocástico rinde
<b>{f(R['VSS_MARS'])} M ARS más en promedio</b> (valor de la solución estocástica) y tiene una cola inferior mucho mejor (P5 +{f(comp.p05_MARS.iloc[0]-comp.p05_MARS.iloc[1])} M).
No anticipar el maíz cuesta ≈ {f(comp.media_MARS.iloc[0]-comp.media_MARS.iloc[2])} M ARS; cada tonelada adicional de anticipo valdría ≈ {f(R['valor_marginal_anticipo_ARS_por_t'])} ARS
(la caja es la restricción activa). Operar en diciembre en el mínimo de continuidad (30.000 t) dejaría ≈ {f(comp.media_MARS.iloc[0]-comp.media_MARS.iloc[3])} M ARS de margen sin capturar.</p>
{img('fig_resultado.png')}

<h2 class="salto">5. Parte C — Análisis de la política propuesta</h2>
<h3>C.1 Nivel de servicio</h3>
<p>Dos medidas por producto, mercado y mes, con 20.000 escenarios: <b>probabilidad de satisfacer completamente la demanda</b> (nivel de servicio tipo 1) y
<b>fracción de la demanda cubierta</b> (ventas esperadas / demanda esperada, tipo 2).</p>
""")
A(tabla(ns, ["mes", "producto", "mercado", "demanda_media_t", "ventas_medias_t", "faltante_medio_t", "P_satisfaccion_total", "fill_rate"],
        ["Mes", "Producto", "Mercado", "Demanda media (t)", "Ventas medias (t)", "Faltante medio (t)", "P(satisfacción total)", "Fracción cubierta"],
        [lambda x: x.capitalize(), None, None, lambda x: f(x), lambda x: f(x), lambda x: f(x), lambda x: pct(x), lambda x: pct(x)]))
A(f"""{img('fig_servicio.png')}
<p>El mercado interno se atiende completamente en el 100% de los escenarios (compromiso comercial prioritario). En noviembre el externo queda corto casi siempre
porque falta almidón ({f(S0+Pn)} t disponibles); el faltante se reparte entre almidón y jarabe externos según sus márgenes. En diciembre, con producción
planificada, se cubre ≈ {pct(g('dic','Almidón','Externo','fill_rate'))} del almidón externo y {pct(g('dic','Jarabe','Externo','fill_rate'))} del jarabe externo;
la probabilidad de cubrirlo totalmente es baja porque el plan se fija en el cuantil económicamente óptimo, no en un cuantil alto.</p>

<h3>C.2 Stock de seguridad para un 95% de servicio en el mercado externo</h3>
<p><b>Criterio adoptado:</b> nivel de servicio tipo 1 (de ciclo) — probabilidad ≥ 95% de atender <i>toda</i> la demanda externa de almidón del mes, respetando la
prioridad del interno. Como el interno se atiende primero, el almidón disponible para la venta debe cubrir el percentil 95 de la demanda total de almidón:
{f(c2['q95_demanda_almidon_dic'])} t en diciembre (el plan dispone {f(c2['almidon_para_venta_dic_plan'])} t) y {f(c2['q95_demanda_almidon_nov'])} t en noviembre
(se dispone de {f(c2['almidon_para_venta_nov_plan'])} t). El stock de seguridad requerido en diciembre es por lo tanto
<b>{f(c2['q95_demanda_almidon_dic']-c2['almidon_para_venta_dic_plan'])} t de almidón</b>.</p>
<table class="izq"><thead><tr><th>Alternativa</th><th>Cambio en el plan</th><th>P(atender todo el almidón externo)</th><th>Costo esperado</th></tr></thead><tbody>
<tr><td>(a) Sólo producir más almidón en diciembre</td><td>Necesita Pd = {f(c2['a_Pd_requerido'])} t pero las horas permiten como máximo {f(c2['a_Pd_max_por_horas'])} t
→ <b>no alcanza</b>; con +{f(c2['a_almidon_adicional_t'])} t (+{f(c2['a_maiz_adicional_t'])} t de maíz)</td><td>dic: {pct(c2['a_P_ext_almidon_dic'])}</td><td>{f(c2['a_costo_MARS'],1)} M ARS</td></tr>
<tr><td>(b) Re-optimizar con la restricción de 95% en diciembre</td><td>+{f(c2['b_almidon_adicional_produccion_t'])} t de almidón obtenido (+{f(1.5*c2['b_almidon_adicional_produccion_t'])} t de maíz) y
−{f(PL['Jd']-c2['b_plan']['Jd'])} t de jarabe: +{f(c2['b_almidon_adicional_para_venta_t'])} t de almidón para la venta</td><td>dic: {pct(c2['b_P_ext_almidon_dic'])}</td><td><b>{f(c2['b_costo_MARS'],1)} M ARS</b></td></tr>
<tr><td>(c) 95% también en noviembre</td><td>Además, desviar {f(c2['c_almidon_liberado_nov_t'])} t de almidón del jarabe de noviembre (no se puede obtener más almidón: el maíz está fijo)</td>
<td>nov: {pct(c2['c_P_ext_almidon_nov'])}; dic: {pct(c2['c_P_ext_almidon_dic'])}</td><td>{f(c2['c_costo_MARS'],1)} M ARS</td></tr>
</tbody></table>
<p>La protección de diciembre cuesta ≈ {f(c2['b_costo_MARS'])} M ARS ({f(c2['b_costo_MARS']*1e6/max(c2['b_almidon_adicional_para_venta_t'],1)/tc_d)} USD por t protegida): cada tonelada extra
cuesta 245 USD y, si no se vende, sólo recupera 172 USD; además, por el límite de horas, una parte se consigue resignando jarabe. En noviembre el 95% sólo se alcanza quitando
almidón al jarabe externo (cuya probabilidad de atención total cae a {pct(c2['c_P_ext_jarabe_nov'])}): es trasladar el faltante de un producto a otro. Por eso no se
recomienda incorporarlo al plan base; si la gerencia valorara el servicio al exterior por encima de su margen, la opción (b) es la de menor costo.</p>

<h3>C.3 ¿Conviene usar existencias de almidón como amortiguador de la demanda de jarabe?</h3>
<p><b>Dentro del modelo propuesto, no.</b> El jarabe no se puede stockear (72 h) y su producción mensual queda fijada en el plan, que no se revisa al conocer la demanda.
Un stock de almidón no puede convertirse en jarabe “a pedido” si el plan ya fijó la cantidad de jarabe, por lo que sólo protegería la demanda de almidón. Mantener un colchón
tiene costo: liberar 1.000 t de almidón al cierre de noviembre (bajando el jarabe planificado) cuesta ≈ {f(c3['colchon_1000_costo_MARS'])} M ARS y 2.000 t
≈ {f(c3['colchon_2000_costo_MARS'])} M ARS; en diciembre, cada tonelada sobrante vale 172 USD frente a 245 USD de costo, y las horas de planta casi no dejan
margen (sólo {f(c3['colchon_dic_1000_efectivo_t'])} t extra). En noviembre, además, no hay almidón sobrante que guardar.</p>
<p><b>Alcance.</b> El almidón sí sería un buen amortiguador si la elaboración de jarabe pudiera ajustarse dentro del mes a la demanda real (producción contra pedido
a partir de almidón en stock, que es lo que la vida útil de 72 h sugiere operativamente). Se cuantificó resolviendo el modelo con el jarabe como decisión de segunda etapa:
el resultado esperado mejora ≈ <b>{f(c3['valor_flexibilidad_MARS'])} M ARS</b> ({pct(c3['valor_flexibilidad_MARS']/c3['obj_plan_fijo_MARS'],2)}), el jarabe medio
sube de {f(c3['Jn_fijo'])} a {f(c3['Jn_flexible_medio'])} t en noviembre porque ya no hay riesgo de que venza. Ese valor es el techo de lo que justificaría
pagar por flexibilidad operativa; en la política entregada (no revisable) el amortiguador efectivo es la reserva implícita al planificar el jarabe por debajo de su demanda media:
el almidón no usado se vende como almidón en lugar de vencer como jarabe.</p>

<h2 class="salto">6. Robustez frente a condiciones adversas</h2>
<p>El plan se mantiene fijo (no se re-optimiza) y se simula bajo cada condición; se compara con el plan determinístico y con el mismo plan sin anticipo.</p>
""")
rr = rob.pivot(index="escenario", columns="plan", values="media_MARS").reindex(rob.escenario.unique()).reset_index()
rr2 = rob[rob.plan == "Recomendado"].set_index("escenario")
rr["p05"] = rr.escenario.map(rr2.p05_MARS)
rr["int"] = rr.escenario.map(rr2.P_interno_total)
rr["ext"] = rr.escenario.map(rr2.fill_externo)
rr["venc"] = rr.escenario.map(rr2.jarabe_vencido_t)
rr["stk"] = rr.escenario.map(rr2.stock_dic_t)
A(tabla(rr, ["escenario", "Recomendado", "Determinístico", "Sin anticipo", "p05", "int", "ext", "venc", "stk"],
        ["Condición", "Recomendado (M ARS)", "Determinístico", "Sin anticipo", "P5 recom.", "P(interno 100%)", "% ext. cubierto", "Jarabe vencido (t)", "Stock dic (t)"],
        [None] + [lambda x: f(x)] * 4 + [lambda x: pct(x, 0), lambda x: pct(x), lambda x: f(x), lambda x: f(x)]))
A(f"""<p>El plan recomendado cubre el mercado interno al 100% en todas las condiciones, nunca desborda el depósito y respeta el mínimo de continuidad. Supera al plan
determinístico en todas las condiciones salvo cuando la demanda resulta claramente mayor a la pronosticada (allí producir todo el jarabe esperado convenía).
El anticipo sólo pierde frente a una apreciación nominal del peso, la única condición no observada en la historia; protege frente a devaluación y suba del maíz,
que son los riesgos más probables y de mayor impacto.</p>

<h2>7. Sensibilidad a los supuestos del alumno</h2>
""")
A(tabla(sens, ["variante", "Jn", "maiz_dic", "Jd", "F", "obj_MARS"],
        ["Variante (árbol 2.000 trayectorias)", "Jn (t)", "Maíz dic (t)", "Jd (t)", "Anticipo (t)", "Resultado esperado (M ARS)"],
        [None] + [lambda x: f(x)] * 3 + [lambda x: f(x, 2), lambda x: f(x)]))
A(f"""<p>Las decisiones se mueven menos de ±1,5% ante cambios razonables de los supuestos: más incertidumbre lleva a planificar algo menos de jarabe (para no vencer)
y algo menos de almidón; el anticipo siempre es el máximo financiable.</p>

<h2>8. Simplificaciones y limitaciones</h2>
<ul>
<li>Modelo mensual: no se representa la sincronización diaria entre producción y despachos dentro del mes (el enunciado indica que se distribuyen durante el mes).</li>
<li>La distribución de la demanda se estimó con 9 orígenes de validación; la del TC supone continuidad del régimen cambiario. Ambos riesgos se cubren con las pruebas de estrés.</li>
<li>El rendimiento maíz/almidón se toma constante (1,50); un rendimiento peor reduce el almidón disponible pero no compromete el mercado interno ni la continuidad.</li>
<li>El resultado está en pesos nominales sin intereses ni costo de oportunidad de la caja, como indica el enunciado.</li>
<li>No se incluyen penalidades por faltantes (el enunciado indica que los pedidos no atendidos se pierden sin penalidad).</li>
</ul>

<h2>9. Respuestas para el formulario</h2>
<div class="form">Noviembre — jarabe planificado (t MS):            {v['1_jarabe_noviembre_t']}
Diciembre — maíz total a comprar (t):              {v['2_maiz_diciembre_t']}
Diciembre — jarabe planificado (t MS):             {v['3_jarabe_diciembre_t']}
Anticipo — maíz con precio fijado en nov. (t):    {v['4_anticipo_maiz_t']}</div>
<p><b>C.1</b> Interno (almidón y jarabe, ambos meses): probabilidad 100%, fracción cubierta 100%. Externo noviembre: almidón {pct(g('nov','Almidón','Externo','P_satisfaccion_total'))} /
{pct(g('nov','Almidón','Externo','fill_rate'))} cubierto; jarabe {pct(g('nov','Jarabe','Externo','P_satisfaccion_total'))} / {pct(g('nov','Jarabe','Externo','fill_rate'))}.
Externo diciembre: almidón {pct(g('dic','Almidón','Externo','P_satisfaccion_total'))} / {pct(g('dic','Almidón','Externo','fill_rate'))}; jarabe
{pct(g('dic','Jarabe','Externo','P_satisfaccion_total'))} / {pct(g('dic','Jarabe','Externo','fill_rate'))}.<br>
<b>C.2</b> Criterio: P(atender toda la demanda externa de almidón del mes) ≥ 95%. Diciembre: {f(c2['q95_demanda_almidon_dic']-c2['almidon_para_venta_dic_plan'])} t de almidón adicional para la venta
(+{f(c2['b_almidon_adicional_produccion_t'])} t producidas y −{f(PL['Jd']-c2['b_plan']['Jd'])} t de jarabe, por el límite de horas), costo esperado ≈ {f(c2['b_costo_MARS'])} M ARS.
En noviembre no puede producirse más almidón; alcanzar 95% exige desviar {f(c2['c_almidon_liberado_nov_t'])} t del jarabe (costo total ≈ {f(c2['c_costo_MARS'])} M ARS).<br>
<b>C.3</b> No dentro del modelo propuesto: el jarabe no se stockea y su producción queda fijada, así que el stock de almidón no puede absorber la demanda de jarabe y
mantenerlo cuesta (8 USD/t·mes, y en diciembre vale 172 vs 245 USD de costo). Sólo convendría si el jarabe pudiera elaborarse contra pedido dentro del mes:
esa flexibilidad vale ≈ {f(c3['valor_flexibilidad_MARS'])} M ARS.</p>

<h2>Anexo — Archivos y ejecución</h2>
<p>El ZIP contiene <code>datos/</code> (planilla de la cátedra), <code>src/</code> (parámetros, pronóstico, modelo PuLP, simulación y gráficos),
<code>main.py</code> (ejecuta todo, ≈ 40 s), <code>resultados/</code> (CSV, JSON y figuras), <code>informe/</code> (este informe y su generador),
<code>TP3_Stocks.ipynb</code> (notebook para Colab) y <code>README.md</code> con instrucciones:
<code>pip install -r requirements.txt</code> → <code>python main.py</code> → <code>python informe/generar_informe.py</code>.
Semillas fijas: los resultados son reproducibles.</p>
</body></html>""")

out_html = AQUI / "informe_TP3.html"
out_html.write_text("".join(html), encoding="utf-8")
print("HTML:", out_html)
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto(out_html.as_uri())
        pg.pdf(path=str(AQUI / "informe_TP3.pdf"), format="A4", print_background=True,
               margin={"top": "16mm", "bottom": "16mm", "left": "15mm", "right": "15mm"},
               display_header_footer=True, header_template="<span></span>",
               footer_template='<div style="font-size:7pt;color:#777;width:100%;text-align:center">'
                               'TP3 Investigación Operativa · padrón terminado en 5 · pág. <span class="pageNumber"></span>/<span class="totalPages"></span></div>')
        b.close()
    print("PDF:", AQUI / "informe_TP3.pdf")
except Exception as e:  # pragma: no cover
    import subprocess
    try:
        subprocess.run(["node", str(AQUI / "a_pdf.js")], check=True)
    except Exception as e2:
        print("No se pudo generar el PDF automáticamente:", e, e2)
        print("Abrir el HTML en un navegador e imprimir a PDF.")
