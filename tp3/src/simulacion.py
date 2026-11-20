"""
Simulación (Monte Carlo) de un plan fijo aplicando exactamente las reglas
comerciales del enunciado. Se usa para evaluar el plan fuera de la muestra
con la que se optimizó, para la Parte C y para las pruebas de robustez.

Reglas operativas en cada mes:
  1. El jarabe planificado se elabora (si hay almidón suficiente).
  2. Jarabe: se atiende primero el mercado interno, el remanente al externo
     hasta su demanda; lo que sobra vence (12 USD/t de disposición).
  3. Almidón disponible = stock inicial + obtenido - usado en jarabe.
     Se atiende primero el interno y luego el externo hasta su demanda; en
     noviembre se reserva sólo lo necesario para el jarabe de diciembre si
     el almidón de diciembre no alcanzara.
  4. Lo que excede la capacidad del depósito se liquida sin valor.
"""
import numpy as np
import pandas as pd

from parametros import Caso


def simular(caso: Caso, plan: dict, esc: dict, rendimiento=None, precio_maiz_usd=None):
    """plan: {"Jn","Pd","Jd","F"} (Pd = almidón planificado para diciembre, el maíz
    comprado es 1,5*Pd). esc: dict con arrays (n,2) para di, de, tc.
    rendimiento: t maíz / t almidón efectivo (por defecto el normal)."""
    c = caso
    y = rendimiento or c.maiz_por_almidon
    pm = c.precio_maiz_usd if precio_maiz_usd is None else precio_maiz_usd
    di, de, tc = esc["di"], esc["de"], esc["tc"]
    n = len(di)
    maiz_dic = c.maiz_por_almidon * plan["Pd"]
    F = plan["F"]
    Q = maiz_dic - F
    P = np.array([c.maiz_noviembre / y, maiz_dic / y])
    Jplan = np.array([plan["Jn"], plan["Jd"]])

    r = {}
    stock = np.full(n, float(c.stock_inicial_almidon))
    resultado = np.full(n, -c.precio_maiz_ars_anticipo * F)
    for t, mes in enumerate(("nov", "dic")):
        e = tc[:, t]
        dAi, dJi = c.share_int["A"] * di[:, t], c.share_int["J"] * di[:, t]
        dAe, dJe = c.share_ext["A"] * de[:, t], c.share_ext["J"] * de[:, t]
        disponible = stock + P[t]
        J = np.minimum(Jplan[t], disponible)
        sJi = np.minimum(J, dJi)
        sJe = np.minimum(J - sJi, dJe)
        W = J - sJi - sJe
        A = disponible - J
        reserva = 0.0
        if t == 0:
            reserva = max(0.0, plan["Jd"] - P[1])
        sAi = np.minimum(A, dAi)
        sAe = np.minimum(np.maximum(A - sAi - reserva, 0), dAe)
        I = A - sAi - sAe
        O = np.maximum(I - c.cap_deposito, 0)
        I = I - O
        res_mes = (c.precio_almidon_int_ars * sAi + c.precio_almidon_ext_usd * e * sAe
                   + c.precio_jarabe_int_ars * sJi + c.precio_jarabe_ext_usd * e * sJe
                   - c.costo_proceso_almidon_usd * e * P[t]
                   - c.costo_jarabe_usd * e * J
                   - c.costo_disposicion_usd * e * W
                   - c.costo_conservacion_usd * e * I
                   - c.costo_desborde_usd * e * O)
        if t == 1:
            res_mes += c.valor_continuidad_usd * e * I - pm * e * Q
        resultado += res_mes
        stock = I
        for k, v in dict(dAi=dAi, dAe=dAe, dJi=dJi, dJe=dJe, sAi=sAi, sAe=sAe, sJi=sJi,
                         sJe=sJe, W=W, I=I, O=O, J=J, res=res_mes, tc=e).items():
            r[f"{k}_{mes}"] = v
    r["resultado"] = resultado
    return pd.DataFrame(r)


def nivel_servicio(sim: pd.DataFrame, tol=1e-6):
    """Probabilidad de satisfacer completamente la demanda (nivel de servicio
    tipo 1) y fracción de la demanda cubierta (fill rate, tipo 2)."""
    filas = []
    for mes in ("nov", "dic"):
        for prod, nom in (("A", "Almidón"), ("J", "Jarabe")):
            for mk, nm in (("i", "Interno"), ("e", "Externo")):
                d = sim[f"d{prod}{mk}_{mes}"]
                s = sim[f"s{prod}{mk}_{mes}"]
                filas.append({"mes": mes, "producto": nom, "mercado": nm,
                              "demanda_media_t": d.mean(), "ventas_medias_t": s.mean(),
                              "P_satisfaccion_total": float(np.mean(s >= d - tol)),
                              "fill_rate": float(s.sum() / d.sum()),
                              "faltante_medio_t": float((d - s).mean())})
    return pd.DataFrame(filas)


def resumen_resultado(sim: pd.DataFrame):
    x = sim["resultado"] / 1e6
    q = np.percentile(x, [5, 50, 95])
    cola = x[x <= q[0]].mean()
    return {"media_MARS": float(x.mean()), "desvio_MARS": float(x.std()),
            "p05_MARS": float(q[0]), "p50_MARS": float(q[1]), "p95_MARS": float(q[2]),
            "CVaR5_MARS": float(cola)}
