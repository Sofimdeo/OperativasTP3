"""
Parte B - Modelo de producción y abastecimiento (programación lineal estocástica
de dos etapas, resuelta con PuLP).

Primera etapa (se decide al comienzo de noviembre y no se revisa):
    Jn  : jarabe a elaborar en noviembre (t MS)
    Pd  : almidón a obtener en diciembre (t MS)  -> maíz de diciembre = 1,5 * Pd
    Jd  : jarabe a elaborar en diciembre (t MS)
    F   : maíz de diciembre cuyo precio se fija y paga en noviembre (t)
    Q   : maíz de diciembre que se paga al recibirlo (t)   (F + Q = 1,5 * Pd)

Segunda etapa (recurso, por escenario): ventas por producto y mercado, jarabe
vencido, stock de almidón al cierre de cada mes. El árbol respeta la
no anticipatividad: las ventas y el stock de noviembre dependen sólo de lo
ocurrido en noviembre (nodo i); las de diciembre, de la trayectoria (i, j).

Función objetivo: maximizar el resultado esperado en ARS de nov-dic
(ventas - procesamiento - maíz de diciembre - conservación - disposición
+ valor de continuidad del almidón al cierre de diciembre). El maíz de
noviembre y el stock inicial son costos hundidos y no se incluyen.
"""
import numpy as np
import pulp

from parametros import Caso


def solver():
    disponibles = pulp.listSolvers(onlyAvailable=True)
    if "HiGHS" in disponibles:
        return pulp.HiGHS(msg=False)
    if "HiGHS_CMD" in disponibles:
        return pulp.HiGHS_CMD(msg=False)
    return pulp.PULP_CBC_CMD(msg=False)


def generar_arbol(fc, N1, N2, rng):
    """Árbol de escenarios: N1 nodos de noviembre y N2 hijos de diciembre por nodo.
    Diciembre se muestrea condicionado a noviembre (normal bivariada) para que
    las correlaciones entre meses sean las estimadas en la Parte A."""
    arbol = {}
    for s in ("di", "de", "tc"):
        m1, m2 = fc[s]["pron"]
        s1, s2 = fc[s]["sd_rel"]
        r = float(np.clip(fc[s]["rho_h1_h2"], -0.95, 0.95))
        z1 = rng.standard_normal(N1) * s1
        z2 = (r * s2 / s1) * z1[:, None] + s2 * np.sqrt(1 - r ** 2) * rng.standard_normal((N1, N2))
        if s == "tc":
            nov = m1 * np.exp(z1 - s1 ** 2 / 2)
            dic = m2 * np.exp(z2 - s2 ** 2 / 2)
        else:
            nov = np.maximum(m1 * (1 + z1), 0)
            dic = np.maximum(m2 * (1 + z2), 0)
        arbol[s] = (nov, dic)
    arbol["N1"], arbol["N2"] = N1, N2
    return arbol


def construir_y_resolver(caso: Caso, arbol, fijar=None, jarabe_recurso=False,
                         restricciones_extra=None, nombre="TP3"):
    """Construye y resuelve el programa estocástico.

    fijar: dict opcional con valores fijos de primera etapa {"Jn","Pd","Jd","F"}.
    jarabe_recurso: si True, el jarabe se decide en cada escenario luego de conocer
        la demanda del mes (política de 'almidón como amortiguador', Parte C3).
    restricciones_extra: función f(modelo, vars) para agregar restricciones.
    """
    c = caso
    N1, N2 = arbol["N1"], arbol["N2"]
    DIn, DId = arbol["di"]
    DEn, DEd = arbol["de"]
    En, Ed = arbol["tc"]
    p1, p2 = 1.0 / N1, 1.0 / (N1 * N2)
    sA_i, sJ_i = c.share_int["A"], c.share_int["J"]
    sA_e, sJ_e = c.share_ext["A"], c.share_ext["J"]
    S0 = c.stock_inicial_almidon
    Pn = c.produccion_almidon_noviembre

    m = pulp.LpProblem(nombre, pulp.LpMaximize)
    V = lambda n, ub=None: pulp.LpVariable(n, lowBound=0, upBound=ub)

    # ---------------- primera etapa ----------------
    Pd = V("Pd")
    F = V("F", ub=c.maiz_max_anticipo)
    Q = V("Q")
    if jarabe_recurso:
        Jn = {i: V(f"Jn_{i}", c.cap_jarabe) for i in range(N1)}
        Jd = {(i, j): V(f"Jd_{i}_{j}", c.cap_jarabe) for i in range(N1) for j in range(N2)}
        Jn_ = lambda i: Jn[i]
        Jd_ = lambda i, j: Jd[i, j]
    else:
        Jn0 = V("Jn", c.cap_jarabe)
        Jd0 = V("Jd", c.cap_jarabe)
        Jn_ = lambda i: Jn0
        Jd_ = lambda i, j: Jd0

    m += F + Q == c.maiz_por_almidon * Pd, "maiz_diciembre"
    m += Pd >= c.min_almidon_mes, "continuidad_dic"
    m += Pn >= c.min_almidon_mes, "continuidad_nov"  # dato: se verifica
    if fijar:
        for k, v in fijar.items():
            var = {"Pd": Pd, "F": F}.get(k)
            if k == "Jn" and not jarabe_recurso:
                var = Jn0
            if k == "Jd" and not jarabe_recurso:
                var = Jd0
            if var is not None:
                m += var == v, f"fijar_{k}"

    # ---------------- segunda etapa ----------------
    obj = []
    # costos determinísticos de primera etapa
    obj.append(-c.precio_maiz_ars_anticipo * F)
    nov = {}
    for i in range(N1):
        e = En[i]
        v = {k: V(f"{k}_n{i}") for k in ("sAi", "sAe", "sJi", "sJe", "W", "I", "O")}
        nov[i] = v
        Jn_i = Jn_(i)
        m += v["sAi"] <= sA_i * DIn[i]
        m += v["sAe"] <= sA_e * DEn[i]
        m += v["sJi"] <= sJ_i * DIn[i]
        m += v["sJe"] <= sJ_e * DEn[i]
        m += v["sJi"] + v["sJe"] + v["W"] == Jn_i                       # jarabe no se stockea
        m += S0 + Pn - Jn_i - v["sAi"] - v["sAe"] - v["O"] == v["I"]    # balance almidón
        m += v["I"] <= c.cap_deposito
        m += Pn + c.horas_jarabe * Jn_i <= c.horas_mes                    # horas de planta
        obj.append(p1 * (c.precio_almidon_int_ars * v["sAi"] + c.precio_almidon_ext_usd * e * v["sAe"]
                         + c.precio_jarabe_int_ars * v["sJi"] + c.precio_jarabe_ext_usd * e * v["sJe"]
                         - c.costo_proceso_almidon_usd * e * Pn
                         - c.costo_jarabe_usd * e * Jn_i
                         - c.costo_disposicion_usd * e * v["W"]
                         - c.costo_conservacion_usd * e * v["I"]
                         - c.costo_desborde_usd * e * v["O"]))
        for j in range(N2):
            e2 = Ed[i, j]
            w = {k: pulp.LpVariable(f"{k}_d{i}_{j}", lowBound=0)
                 for k in ("sAi", "sAe", "sJi", "sJe", "W", "I", "O")}
            Jd_ij = Jd_(i, j)
            m += w["sAi"] <= sA_i * DId[i, j]
            m += w["sAe"] <= sA_e * DEd[i, j]
            m += w["sJi"] <= sJ_i * DId[i, j]
            m += w["sJe"] <= sJ_e * DEd[i, j]
            m += w["sJi"] + w["sJe"] + w["W"] == Jd_ij
            m += v["I"] + Pd - Jd_ij - w["sAi"] - w["sAe"] - w["O"] == w["I"]
            m += w["I"] <= c.cap_deposito
            m += Pd + c.horas_jarabe * Jd_ij <= c.horas_mes
            obj.append(p2 * (c.precio_almidon_int_ars * w["sAi"] + c.precio_almidon_ext_usd * e2 * w["sAe"]
                             + c.precio_jarabe_int_ars * w["sJi"] + c.precio_jarabe_ext_usd * e2 * w["sJe"]
                             - c.costo_proceso_almidon_usd * e2 * Pd
                             - c.costo_jarabe_usd * e2 * Jd_ij
                             - c.costo_disposicion_usd * e2 * w["W"]
                             - c.costo_conservacion_usd * e2 * w["I"]
                             - c.costo_desborde_usd * e2 * w["O"]
                             + c.valor_continuidad_usd * e2 * w["I"]
                             - c.precio_maiz_usd * e2 * Q))
    m += pulp.lpSum(obj)
    if restricciones_extra:
        restricciones_extra(m, {"Pd": Pd, "F": F, "Q": Q})
    m.solve(solver())
    estado = pulp.LpStatus[m.status]
    res = {"estado": estado, "objetivo": pulp.value(m.objective),
           "Pd": Pd.value(), "F": F.value(), "Q": Q.value(),
           "C": c.maiz_por_almidon * Pd.value()}
    if not jarabe_recurso:
        res["Jn"], res["Jd"] = Jn0.value(), Jd0.value()
    else:
        res["Jn_medio"] = float(np.mean([Jn[i].value() for i in range(N1)]))
        res["Jd_medio"] = float(np.mean([Jd[k].value() for k in Jd]))
    res["stock_nov_medio"] = float(np.mean([nov[i]["I"].value() for i in range(N1)]))
    res["modelo"] = m
    return res


def resolver_valor_esperado(caso: Caso, fc):
    """Problema determinístico con los valores esperados (para medir el VSS)."""
    arbol = {"N1": 1, "N2": 1,
             "di": (np.array([fc["di"]["pron"][0]]), np.array([[fc["di"]["pron"][1]]])),
             "de": (np.array([fc["de"]["pron"][0]]), np.array([[fc["de"]["pron"][1]]])),
             "tc": (np.array([fc["tc"]["pron"][0]]), np.array([[fc["tc"]["pron"][1]]]))}
    return construir_y_resolver(caso, arbol, nombre="Determinístico")
