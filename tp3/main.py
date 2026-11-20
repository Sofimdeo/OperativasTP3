"""
TP3 - Gestión integrada de stocks (padrón terminado en 5).

Ejecuta todo el trabajo y deja los resultados en ./resultados:
    python main.py
"""
import copy
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from parametros import Caso, DIR_RESULTADOS  # noqa: E402
from pronostico import cargar_datos, pronosticar, generar_escenarios, fourier_1, combinacion_sn_fourier  # noqa: E402
from modelo import generar_arbol, construir_y_resolver, resolver_valor_esperado  # noqa: E402
from simulacion import simular, nivel_servicio, resumen_resultado  # noqa: E402
import graficos  # noqa: E402

N1, N2 = 100, 50          # árbol de la optimización final (5.000 trayectorias)
N1_REP, N2_REP = 50, 40   # réplicas SAA para medir estabilidad
N_REPLICAS = 5
N_SIM = 20_000            # escenarios de evaluación fuera de muestra
SEMILLA_ARBOL = 2026
SEMILLA_SIM = 12345

DIR_RESULTADOS.mkdir(exist_ok=True)
caso = Caso()
R = {"parametros": caso.resumen()}


def plan_de(res):
    return {k: float(res[k]) for k in ("Jn", "Pd", "Jd", "F")}


def evaluar(plan, esc, **kw):
    plan = {**plan, "F": min(plan["F"], caso.maiz_por_almidon * plan["Pd"])}
    sim = simular(caso, plan, esc, **kw)
    return sim, resumen_resultado(sim)


# =============================================================================
# PARTE A - Pronóstico
# =============================================================================
print("Parte A: pronóstico...")
df = cargar_datos()
fc = pronosticar(df, cv_min_int=caso.cv_min_demanda_interna)
for s in ("di", "de", "tc"):
    fc[s]["tabla"].to_csv(DIR_RESULTADOS / f"validacion_{s}.csv", index=False)
R["pronostico"] = {s: {"metodo": fc[s]["metodo"], "nov": float(fc[s]["pron"][0]),
                       "dic": float(fc[s]["pron"][1]), "sd_rel_nov": fc[s]["sd_rel"][0],
                       "sd_rel_dic": fc[s]["sd_rel"][1], "rho_nov_dic": fc[s]["rho_h1_h2"]}
                   for s in ("di", "de", "tc")}
R["pronostico"]["di"]["sd_rel_estadistico"] = fc["di"]["sd_rel_estadistico"]
R["pronostico"]["rho_int_ext"] = fc["rho_int_ext"]
# intervalos de 90% y composición por producto
for s in ("di", "de", "tc"):
    p = R["pronostico"][s]
    for mes in ("nov", "dic"):
        sd = p[f"sd_rel_{mes}"] * p[mes]
        p[f"{mes}_li90"], p[f"{mes}_ls90"] = p[mes] - 1.645 * sd, p[mes] + 1.645 * sd
comp = []
for mes, k in (("nov", 0), ("dic", 1)):
    di, de = fc["di"]["pron"][k], fc["de"]["pron"][k]
    comp.append({"mes": mes, "Almidón interno": caso.share_int["A"] * di,
                 "Jarabe interno": caso.share_int["J"] * di,
                 "Almidón externo": caso.share_ext["A"] * de,
                 "Jarabe externo": caso.share_ext["J"] * de,
                 "Total (t almidón eq.)": di + de})
R["demanda_por_producto"] = comp
graficos.pronosticos(df, fc, DIR_RESULTADOS)

# escenarios de evaluación (independientes de los usados para optimizar)
esc = generar_escenarios(fc, N_SIM, np.random.default_rng(SEMILLA_SIM))

# =============================================================================
# PARTE B - Modelo estocástico
# =============================================================================
print("Parte B: réplicas SAA...")
reps = []
for k in range(N_REPLICAS):
    a = generar_arbol(fc, N1_REP, N2_REP, np.random.default_rng(100 + k))
    r = construir_y_resolver(caso, a)
    _, ev = evaluar(plan_de(r), esc)
    reps.append({"replica": k + 1, "Jn": r["Jn"], "Pd": r["Pd"], "C_maiz": r["C"], "Jd": r["Jd"],
                 "F": r["F"], "obj_en_muestra_MARS": r["objetivo"] / 1e6,
                 "obj_fuera_muestra_MARS": ev["media_MARS"]})
reps = pd.DataFrame(reps)
reps.to_csv(DIR_RESULTADOS / "replicas_saa.csv", index=False)
R["replicas"] = reps.to_dict("records")

print("Parte B: modelo final...")
arbol = generar_arbol(fc, N1, N2, np.random.default_rng(SEMILLA_ARBOL))
opt = construir_y_resolver(caso, arbol)
R["optimo_lp"] = {k: (float(v) if isinstance(v, (float, int, np.floating)) else v)
                  for k, v in opt.items() if k != "modelo"}

# Plan recomendado: se redondea a toneladas enteras; el anticipo se trunca para
# no exceder la caja disponible.
Jn = round(opt["Jn"])
Jd = round(opt["Jd"])
C = round(opt["C"])
F = min(np.floor(opt["F"] * 100) / 100, C)
F = min(F, np.floor(caso.maiz_max_anticipo * 100) / 100)
plan = {"Jn": float(Jn), "Pd": C / caso.maiz_por_almidon, "Jd": float(Jd), "F": float(F)}
R["plan"] = {"Jn": Jn, "maiz_dic": C, "Pd": plan["Pd"], "Jd": Jd, "F": F,
             "Q_spot": C - F, "anticipo_ARS": F * caso.precio_maiz_ars_anticipo,
             "pago_dic_esperado_ARS": (C - F) * caso.precio_maiz_usd * fc["tc"]["pron"][1],
             "horas_nov": caso.produccion_almidon_noviembre + caso.horas_jarabe * Jn,
             "horas_dic": plan["Pd"] + caso.horas_jarabe * Jd}
sim, ev = evaluar(plan, esc)
R["evaluacion_plan"] = ev
ns = nivel_servicio(sim)
ns.to_csv(DIR_RESULTADOS / "nivel_servicio.csv", index=False)
R["nivel_servicio"] = ns.to_dict("records")
R["stocks_esperados"] = {
    "almidon_cierre_nov_medio": float(sim.I_nov.mean()),
    "almidon_cierre_nov_p95": float(np.percentile(sim.I_nov, 95)),
    "almidon_cierre_dic_medio": float(sim.I_dic.mean()),
    "almidon_cierre_dic_p95": float(np.percentile(sim.I_dic, 95)),
    "P_stock_dic_mayor_0": float((sim.I_dic > 1e-6).mean()),
    "jarabe_vencido_nov_medio": float(sim.W_nov.mean()),
    "jarabe_vencido_dic_medio": float(sim.W_dic.mean()),
    "desborde_deposito_P": float(((sim.O_nov + sim.O_dic) > 1e-6).mean()),
}
R["resultado_por_mes_MARS"] = {"nov": float(sim.res_nov.mean() / 1e6),
                               "dic": float(sim.res_dic.mean() / 1e6),
                               "anticipo": float(-F * caso.precio_maiz_ars_anticipo / 1e6)}
graficos.distribucion_resultado(sim, DIR_RESULTADOS)
graficos.ventas_vs_demanda(ns, DIR_RESULTADOS)

# Comparación con planes alternativos
print("Parte B: comparación con alternativas...")
det = resolver_valor_esperado(caso, fc)
alternativas = {
    "Plan recomendado (estocástico)": plan,
    "Plan determinístico (valores esperados)": plan_de(det),
    "Recomendado sin anticipo (F = 0)": {**plan, "F": 0.0},
    "Recomendado con mínimo de continuidad en dic.": {**plan, "Pd": caso.min_almidon_mes,
                                                       "Jd": min(plan["Jd"], caso.min_almidon_mes)},
}
comp_alt = []
for nombre, p in alternativas.items():
    s_, e_ = evaluar(p, esc)
    n_ = nivel_servicio(s_)
    comp_alt.append({"plan": nombre, "Jn": p["Jn"], "maiz_dic": caso.maiz_por_almidon * p["Pd"],
                     "Jd": p["Jd"], "F": p["F"], **e_,
                     "fill_externo": float(n_[n_.mercado == "Externo"].ventas_medias_t.sum()
                                           / n_[n_.mercado == "Externo"].demanda_media_t.sum())})
comp_alt = pd.DataFrame(comp_alt)
comp_alt.to_csv(DIR_RESULTADOS / "comparacion_planes.csv", index=False)
R["comparacion_planes"] = comp_alt.to_dict("records")
R["VSS_MARS"] = float(comp_alt.media_MARS.iloc[0] - comp_alt.media_MARS.iloc[1])

# Precio sombra de la caja para el anticipo (valor de 1 t más de anticipo)
p_ = {**plan, "F": plan["F"] - 1000}
_, e_ = evaluar(p_, esc)
R["valor_marginal_anticipo_ARS_por_t"] = float((ev["media_MARS"] - e_["media_MARS"]) * 1e6 / 1000)

# =============================================================================
# PARTE C
# =============================================================================
print("Parte C: stock de seguridad...")
# C2. Criterio: nivel de servicio tipo 1 (ciclo) = P(atender toda la demanda
# externa de almidón del mes) >= 95%. Con prioridad del mercado interno, eso
# exige que el almidón disponible para vender cubra el percentil 95 de la
# demanda total de almidón (interna + externa) del mes.
dA_nov = caso.share_int["A"] * esc["di"][:, 0] + caso.share_ext["A"] * esc["de"][:, 0]
dA_dic = caso.share_int["A"] * esc["di"][:, 1] + caso.share_ext["A"] * esc["de"][:, 1]
q95_nov, q95_dic = float(np.percentile(dA_nov, 95)), float(np.percentile(dA_dic, 95))
S0, Pn = caso.stock_inicial_almidon, caso.produccion_almidon_noviembre
base_disp_dic = plan["Pd"] - plan["Jd"]
c2 = {"criterio": "Nivel de servicio tipo 1 (probabilidad de no tener faltante en el mes) >= 95% "
                  "en el mercado externo de almidón, respetando la prioridad del interno",
      "q95_demanda_almidon_nov": q95_nov, "q95_demanda_almidon_dic": q95_dic,
      "almidon_para_venta_dic_plan": base_disp_dic,
      "almidon_para_venta_nov_plan": S0 + Pn - plan["Jn"]}
# (a) sólo producir más almidón en diciembre, sin tocar el jarabe
Pd_req = q95_dic + plan["Jd"]
Pd_max_horas = caso.horas_mes - caso.horas_jarabe * plan["Jd"]
c2["a_Pd_requerido"] = Pd_req
c2["a_Pd_max_por_horas"] = Pd_max_horas
c2["a_factible"] = bool(Pd_req <= Pd_max_horas)
pa = {**plan, "Pd": min(Pd_req, Pd_max_horas)}
pa["F"] = min(plan["F"], caso.maiz_max_anticipo)
sa, ea = evaluar(pa, esc)
na = nivel_servicio(sa)
c2["a_almidon_adicional_t"] = pa["Pd"] - plan["Pd"]
c2["a_maiz_adicional_t"] = caso.maiz_por_almidon * (pa["Pd"] - plan["Pd"])
c2["a_costo_MARS"] = ev["media_MARS"] - ea["media_MARS"]
c2["a_P_ext_almidon_dic"] = float(na.query("mes=='dic' and producto=='Almidón' and mercado=='Externo'").P_satisfaccion_total.iloc[0])


# (b) re-optimizar con la restricción de servicio en diciembre (puede reasignar jarabe)
def r_dic(m, v):
    jd = [x for x in m.variables() if x.name == "Jd"][0]
    m += v["Pd"] - jd >= q95_dic, "servicio95_dic"


ob = construir_y_resolver(caso, arbol, restricciones_extra=r_dic)
pb = {**plan_de(ob)}
pb["F"] = min(pb["F"], plan["F"])
sb, eb = evaluar(pb, esc)
nb = nivel_servicio(sb)
c2["b_plan"] = pb
c2["b_almidon_adicional_produccion_t"] = pb["Pd"] - plan["Pd"]
c2["b_almidon_adicional_para_venta_t"] = (pb["Pd"] - pb["Jd"]) - base_disp_dic
c2["b_costo_MARS"] = ev["media_MARS"] - eb["media_MARS"]
c2["b_P_ext_almidon_dic"] = float(nb.query("mes=='dic' and producto=='Almidón' and mercado=='Externo'").P_satisfaccion_total.iloc[0])
c2["b_P_ext_jarabe_dic"] = float(nb.query("mes=='dic' and producto=='Jarabe' and mercado=='Externo'").P_satisfaccion_total.iloc[0])


# (c) noviembre: el almidón no puede aumentarse (maíz fijo), sólo liberarse
# desviándolo del jarabe; se re-optimiza con ambas restricciones.
def r_ambos(m, v):
    r_dic(m, v)
    jn = [x for x in m.variables() if x.name == "Jn"][0]
    m += S0 + Pn - jn >= q95_nov, "servicio95_nov"


oc = construir_y_resolver(caso, arbol, restricciones_extra=r_ambos)
pc = plan_de(oc)
pc["F"] = min(pc["F"], plan["F"])
sc_, ec = evaluar(pc, esc)
nc = nivel_servicio(sc_)
c2["c_plan"] = pc
c2["c_almidon_liberado_nov_t"] = plan["Jn"] - pc["Jn"]
c2["c_costo_MARS"] = ev["media_MARS"] - ec["media_MARS"]
c2["c_P_ext_almidon_nov"] = float(nc.query("mes=='nov' and producto=='Almidón' and mercado=='Externo'").P_satisfaccion_total.iloc[0])
c2["c_P_ext_almidon_dic"] = float(nc.query("mes=='dic' and producto=='Almidón' and mercado=='Externo'").P_satisfaccion_total.iloc[0])
c2["c_P_ext_jarabe_nov"] = float(nc.query("mes=='nov' and producto=='Jarabe' and mercado=='Externo'").P_satisfaccion_total.iloc[0])
# costo unitario directo de la protección (USD/t)
c2["costo_directo_por_t_extra_USD"] = {
    "produccion_almidon": caso.costo_ref_almidon_usd,
    "valor_si_se_vende_ext": caso.precio_almidon_ext_usd,
    "valor_si_sobra_al_cierre": caso.valor_continuidad_usd - caso.costo_conservacion_usd}
R["C2"] = c2

print("Parte C: almidón como amortiguador...")
# C3. Variante en la que el jarabe se decide DESPUÉS de conocer la demanda del
# mes (elaboración contra pedido a partir del almidón en stock). La diferencia
# de resultado con el plan fijo mide cuánto valdría usar el almidón como
# amortiguador de la demanda de jarabe.
a_c3 = generar_arbol(fc, N1_REP, N2_REP, np.random.default_rng(100))
fijo = construir_y_resolver(caso, a_c3)
flex = construir_y_resolver(caso, a_c3, jarabe_recurso=True)
# variante: stock de almidón adicional mantenido como colchón en diciembre
c3 = {"obj_plan_fijo_MARS": fijo["objetivo"] / 1e6, "obj_jarabe_flexible_MARS": flex["objetivo"] / 1e6,
      "valor_flexibilidad_MARS": (flex["objetivo"] - fijo["objetivo"]) / 1e6,
      "Pd_fijo": fijo["Pd"], "Pd_flexible": flex["Pd"],
      "Jn_fijo": fijo["Jn"], "Jn_flexible_medio": flex["Jn_medio"],
      "Jd_fijo": fijo["Jd"], "Jd_flexible_medio": flex["Jd_medio"],
      "stock_nov_fijo": fijo["stock_nov_medio"], "stock_nov_flexible": flex["stock_nov_medio"]}
# costo de mantener un colchón de almidón de X t al cierre de noviembre en el plan fijo
for colchon in (1000, 2000):
    pcol = {**plan, "Jn": plan["Jn"] - colchon}  # libera almidón que queda en stock si no se vende
    s_, e_ = evaluar(pcol, esc)
    c3[f"colchon_{colchon}_costo_MARS"] = ev["media_MARS"] - e_["media_MARS"]
# costo de colchón en diciembre (producir X t extra que, si no se usa, queda a valor de continuidad)
for colchon in (1000, 2000):
    pcol = {**plan, "Pd": min(plan["Pd"] + colchon, caso.horas_mes - caso.horas_jarabe * plan["Jd"])}
    s_, e_ = evaluar(pcol, esc)
    c3[f"colchon_dic_{colchon}_costo_MARS"] = ev["media_MARS"] - e_["media_MARS"]
    c3[f"colchon_dic_{colchon}_efectivo_t"] = pcol["Pd"] - plan["Pd"]
R["C3"] = c3

# =============================================================================
# Robustez: condiciones adversas (plan fijo, sin re-optimizar)
# =============================================================================
print("Robustez...")


def escalar(e, di=(1, 1), de=(1, 1), tc=(1, 1)):
    x = copy.deepcopy(e)
    x["di"] = x["di"] * np.array(di)
    x["de"] = x["de"] * np.array(de)
    x["tc"] = x["tc"] * np.array(tc)
    return x


estres = {
    "Base": (esc, {}),
    "Demanda externa -20%": (escalar(esc, de=(0.8, 0.8)), {}),
    "Demanda externa +20%": (escalar(esc, de=(1.2, 1.2)), {}),
    "Demanda interna -10%": (escalar(esc, di=(0.9, 0.9)), {}),
    "Demanda interna +10%": (escalar(esc, di=(1.1, 1.1)), {}),
    "Devaluación: TC dic +15%": (escalar(esc, tc=(1.05, 1.15)), {}),
    "Apreciación: TC -10%": (escalar(esc, tc=(0.95, 0.9)), {}),
    "Maíz 120 USD/t": (esc, {"precio_maiz_usd": 120.0}),
    "Rendimiento 1,60 t maíz/t almidón": (esc, {"rendimiento": 1.60}),
    "Combinado: ext -20%, TC -10%, rend. 1,60": (escalar(esc, de=(0.8, 0.8), tc=(0.95, 0.9)),
                                                 {"rendimiento": 1.60}),
}
rob = []
for nombre, (e_, kw) in estres.items():
    for pn, p in (("Recomendado", plan), ("Determinístico", plan_de(det)), ("Sin anticipo", {**plan, "F": 0.0})):
        s_, r_ = evaluar(p, e_, **kw)
        n_ = nivel_servicio(s_)
        rob.append({"escenario": nombre, "plan": pn, "media_MARS": r_["media_MARS"],
                    "p05_MARS": r_["p05_MARS"],
                    "P_interno_total": float(np.mean((s_.sAi_nov >= s_.dAi_nov - 1e-6) & (s_.sJi_nov >= s_.dJi_nov - 1e-6)
                                                     & (s_.sAi_dic >= s_.dAi_dic - 1e-6) & (s_.sJi_dic >= s_.dJi_dic - 1e-6))),
                    "fill_externo": float(n_[n_.mercado == "Externo"].ventas_medias_t.sum()
                                          / n_[n_.mercado == "Externo"].demanda_media_t.sum()),
                    "jarabe_vencido_t": float((s_.W_nov + s_.W_dic).mean()),
                    "stock_dic_t": float(s_.I_dic.mean()),
                    "desborde_t": float((s_.O_nov + s_.O_dic).mean())})
rob = pd.DataFrame(rob)
rob.to_csv(DIR_RESULTADOS / "robustez.csv", index=False)
R["robustez"] = rob.to_dict("records")

# =============================================================================
# Sensibilidad del plan a supuestos del alumno
# =============================================================================
print("Sensibilidad...")
sens = []


def correr_variante(nombre, fc_v):
    a = generar_arbol(fc_v, N1_REP, N2_REP, np.random.default_rng(100))
    r = construir_y_resolver(caso, a)
    sens.append({"variante": nombre, "Jn": r["Jn"], "maiz_dic": r["C"], "Jd": r["Jd"], "F": r["F"],
                 "obj_MARS": r["objetivo"] / 1e6})


correr_variante("Base (CV interno 2%)", fc)
for cv in (0.0, 0.04):
    f2 = pronosticar(df, cv_min_int=cv)
    correr_variante(f"CV mínimo demanda interna {int(cv*100)}%", f2)
f2 = copy.deepcopy(fc)
f2["de"]["pron"] = combinacion_sn_fourier(df.de.values.astype(float), 2)
correr_variante("Demanda externa: método combinado", f2)
f2 = copy.deepcopy(fc)
f2["de"]["sd_rel"] = [2 * v for v in fc["de"]["sd_rel"]]
correr_variante("Desvío demanda externa x2", f2)
f2 = copy.deepcopy(fc)
f2["tc"]["sd_rel"] = [0.03, 0.06]
correr_variante("TC con desvío 3% / 6%", f2)
sens = pd.DataFrame(sens)
sens.to_csv(DIR_RESULTADOS / "sensibilidad.csv", index=False)
R["sensibilidad"] = sens.to_dict("records")

# =============================================================================
# Valores para el formulario
# =============================================================================
R["formulario"] = {
    "1_jarabe_noviembre_t": f"{Jn:.2f}",
    "2_maiz_diciembre_t": f"{C:.2f}",
    "3_jarabe_diciembre_t": f"{Jd:.2f}",
    "4_anticipo_maiz_t": f"{F:.2f}",
}


def _conv(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.bool_):
        return bool(o)
    raise TypeError(type(o))


(DIR_RESULTADOS / "resultados.json").write_text(json.dumps(R, indent=2, ensure_ascii=False, default=_conv))
print("\nVALORES PARA EL FORMULARIO")
for k, v in R["formulario"].items():
    print(f"  {k}: {v}")
print(f"\nResultado esperado: {ev['media_MARS']:,.0f} M ARS (p05 {ev['p05_MARS']:,.0f})")
print("Resultados en", DIR_RESULTADOS)
