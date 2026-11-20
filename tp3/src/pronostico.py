"""
Parte A - Pronóstico de demanda interna, demanda externa y tipo de cambio.

Procedimiento:
  1. Se definen varios métodos candidatos por serie.
  2. Se evalúan con validación de origen móvil (rolling origin) a 1 y 2 meses,
     que es exactamente el uso que se les dará (noviembre = h1, diciembre = h2).
  3. Se elige el método de menor error fuera de muestra.
  4. La incertidumbre se estima con los errores fuera de muestra del método elegido
     (desvío relativo por horizonte y correlaciones), y se usa para generar escenarios.
"""
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from parametros import ARCHIVO_DATOS, DIGITO


def cargar_datos(digito: int = DIGITO) -> pd.DataFrame:
    df = pd.read_excel(ARCHIVO_DATOS, sheet_name=f"Digito_{digito}", header=3).dropna()
    df.columns = ["mes", "di", "de", "tc"]
    df["mes"] = pd.to_datetime(df["mes"])
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Métodos de pronóstico: cada uno recibe la historia y el horizonte H
# y devuelve un array con los pronósticos h = 1..H
# ---------------------------------------------------------------------------
def naive(y, H):
    return np.repeat(y[-1], H)


def promedio_movil_3(y, H):
    return np.repeat(np.mean(y[-3:]), H)


def estacional_naive(y, H):
    n = len(y)
    return np.array([y[n + h - 1 - 12] for h in range(1, H + 1)])


def estacional_crecimiento(y, H):
    """Estacional ingenuo x crecimiento interanual (media geométrica de los
    cocientes y_t / y_{t-12} disponibles, como máximo los últimos 12)."""
    n = len(y)
    r = y[12:] / y[:-12]
    r = r[-12:]
    g = np.exp(np.mean(np.log(r))) if len(r) else 1.0
    return np.array([y[n + h - 1 - 12] * g for h in range(1, H + 1)])


def _fourier_X(t, K=1, tendencia=True):
    cols = [np.ones_like(t, dtype=float)]
    if tendencia:
        cols.append(t.astype(float))
    for k in range(1, K + 1):
        cols += [np.sin(2 * np.pi * k * t / 12), np.cos(2 * np.pi * k * t / 12)]
    return np.column_stack(cols)


def fourier_1(y, H):
    """Regresión: tendencia lineal + 1 armónico anual (4 parámetros)."""
    t = np.arange(len(y))
    tf = np.arange(len(y), len(y) + H)
    b, *_ = np.linalg.lstsq(_fourier_X(t, 1), y, rcond=None)
    return _fourier_X(tf, 1) @ b


def fourier_2(y, H):
    t = np.arange(len(y))
    tf = np.arange(len(y), len(y) + H)
    b, *_ = np.linalg.lstsq(_fourier_X(t, 2), y, rcond=None)
    return _fourier_X(tf, 2) @ b


def combinacion_sn_fourier(y, H):
    """Promedio simple de estacional con crecimiento y Fourier(1)."""
    return 0.5 * estacional_crecimiento(y, H) + 0.5 * fourier_1(y, H)


def holt_lineal(y, H):
    m = ExponentialSmoothing(y, trend="add", initialization_method="estimated").fit()
    return m.forecast(H)


# --- tipo de cambio (se trabaja en logaritmos: crecimiento porcentual) ---
def rw_deriva_total(y, H):
    g = np.mean(np.diff(np.log(y)))
    return y[-1] * np.exp(g * np.arange(1, H + 1))


def rw_deriva_6(y, H):
    g = np.mean(np.diff(np.log(y[-7:])))
    return y[-1] * np.exp(g * np.arange(1, H + 1))


def rw_deriva_3(y, H):
    g = np.mean(np.diff(np.log(y[-4:])))
    return y[-1] * np.exp(g * np.arange(1, H + 1))


def tendencia_loglineal(y, H):
    t = np.arange(len(y))
    b = np.polyfit(t, np.log(y), 1)
    return np.exp(np.polyval(b, np.arange(len(y), len(y) + H)))


def holt_log(y, H):
    m = ExponentialSmoothing(np.log(y), trend="add", initialization_method="estimated").fit()
    return np.exp(m.forecast(H))


METODOS_DEMANDA = {
    "Ingenuo (último valor)": naive,
    "Promedio móvil 3": promedio_movil_3,
    "Holt lineal": holt_lineal,
    "Estacional ingenuo": estacional_naive,
    "Estacional x crecimiento interanual": estacional_crecimiento,
    "Regresión tendencia + 1 armónico": fourier_1,
    "Regresión tendencia + 2 armónicos": fourier_2,
    "Combinación (est. x crec. + 1 armónico)": combinacion_sn_fourier,
}

METODOS_TC = {
    "Ingenuo (último valor)": naive,
    "Deriva log 21 meses": rw_deriva_total,
    "Deriva log últimos 6 meses": rw_deriva_6,
    "Deriva log últimos 3 meses": rw_deriva_3,
    "Tendencia log-lineal": tendencia_loglineal,
    "Holt sobre log": holt_log,
}


def backtest(y, metodo, origen_min, H=2):
    """Validación de origen móvil. Devuelve DataFrame con errores relativos
    (real/pronóstico - 1) por origen y horizonte."""
    filas = []
    for n in range(origen_min, len(y)):
        f = metodo(y[:n], H)
        for h in range(1, H + 1):
            if n + h - 1 < len(y):
                real = y[n + h - 1]
                filas.append({"origen": n, "h": h, "pron": f[h - 1], "real": real,
                              "err_rel": real / f[h - 1] - 1})
    return pd.DataFrame(filas)


def evaluar_metodos(y, metodos, origen_min):
    res, detalle = [], {}
    for nombre, m in metodos.items():
        bt = backtest(y, m, origen_min)
        detalle[nombre] = bt
        fila = {"metodo": nombre}
        for h in (1, 2):
            e = bt[bt.h == h]
            fila[f"MAPE_h{h}_%"] = 100 * np.mean(np.abs(e.err_rel))
            fila[f"RMSE_h{h}"] = np.sqrt(np.mean((e.real - e.pron) ** 2))
            fila[f"sesgo_h{h}_%"] = 100 * np.mean(e.err_rel)
        fila["MAPE_prom_%"] = (fila["MAPE_h1_%"] + fila["MAPE_h2_%"]) / 2
        res.append(fila)
    tabla = pd.DataFrame(res).sort_values("MAPE_prom_%").reset_index(drop=True)
    return tabla, detalle


# Origen mínimo de la validación: los métodos estacionales necesitan 12 meses
# (y el de crecimiento al menos 13). Se usan los mismos orígenes para todos.
ORIGEN_MIN_DEMANDA = 13
ORIGEN_MIN_TC = 8


def pronosticar(df: pd.DataFrame, cv_min_int: float = 0.02):
    """Ejecuta la selección de métodos y devuelve un diccionario con pronósticos
    puntuales, tablas de validación y parámetros de incertidumbre."""
    out = {}
    series = {"di": (METODOS_DEMANDA, ORIGEN_MIN_DEMANDA),
              "de": (METODOS_DEMANDA, ORIGEN_MIN_DEMANDA),
              "tc": (METODOS_TC, ORIGEN_MIN_TC)}
    for s, (metodos, omin) in series.items():
        y = df[s].values.astype(float)
        tabla, detalle = evaluar_metodos(y, metodos, omin)
        mejor = tabla.metodo.iloc[0]
        f = metodos[mejor](y, 2)
        bt = detalle[mejor]
        e1 = bt[bt.h == 1].set_index("origen").err_rel
        e2 = bt[bt.h == 2].set_index("origen").err_rel
        comunes = e1.index.intersection(e2.index)
        # desvío relativo fuera de muestra (RMS de errores relativos, incluye sesgo)
        sd1 = float(np.sqrt(np.mean(e1 ** 2)))
        sd2 = float(np.sqrt(np.mean(e2 ** 2)))
        rho12 = float(np.corrcoef(e1[comunes], e2[comunes])[0, 1]) if len(comunes) > 2 else 0.0
        out[s] = {"tabla": tabla, "metodo": mejor, "pron": f, "sd_rel": [sd1, sd2],
                  "rho_h1_h2": rho12, "errores": bt}
    # piso de incertidumbre para la demanda interna (supuesto del alumno)
    out["di"]["sd_rel_estadistico"] = list(out["di"]["sd_rel"])
    out["di"]["sd_rel"] = [max(v, cv_min_int) for v in out["di"]["sd_rel"]]
    # correlación interna/externa de errores h1 (con errores ~0 no es informativa)
    e_i = out["di"]["errores"].query("h==1").set_index("origen").err_rel
    e_e = out["de"]["errores"].query("h==1").set_index("origen").err_rel
    c = e_i.index.intersection(e_e.index)
    out["rho_int_ext"] = float(np.corrcoef(e_i[c], e_e[c])[0, 1])
    return out


def generar_escenarios(fc, n, rng, rho_int_ext=0.0):
    """Genera n trayectorias conjuntas (nov, dic) de DI, DE y TC.

    Demandas: normales con media = pronóstico y desvío relativo por horizonte,
    correlación nov-dic según los errores fuera de muestra.
    TC: lognormal; log TC_dic = log TC_nov + crecimiento + shock, de modo que la
    varianza a 2 meses coincide con la estimada para h=2.
    """
    out = {}
    for s in ("di", "de"):
        m1, m2 = fc[s]["pron"]
        s1, s2 = fc[s]["sd_rel"]
        r = np.clip(fc[s]["rho_h1_h2"], -0.95, 0.95)
        cov = np.array([[s1 ** 2, r * s1 * s2], [r * s1 * s2, s2 ** 2]])
        z = rng.multivariate_normal([0, 0], cov, size=n)
        out[s] = np.column_stack([m1 * (1 + z[:, 0]), m2 * (1 + z[:, 1])]).clip(min=0)
    m1, m2 = fc["tc"]["pron"]
    s1, s2 = fc["tc"]["sd_rel"]
    r = np.clip(fc["tc"]["rho_h1_h2"], -0.95, 0.95)
    cov = np.array([[s1 ** 2, r * s1 * s2], [r * s1 * s2, s2 ** 2]])
    z = rng.multivariate_normal([0, 0], cov, size=n)
    # media lognormal = pronóstico
    out["tc"] = np.column_stack([m1 * np.exp(z[:, 0] - s1 ** 2 / 2),
                                 m2 * np.exp(z[:, 1] - s2 ** 2 / 2)])
    return out


if __name__ == "__main__":
    df = cargar_datos()
    fc = pronosticar(df)
    for s in ("di", "de", "tc"):
        print(f"\n=== {s} ===")
        print(fc[s]["tabla"].round(3).to_string())
        print("Elegido:", fc[s]["metodo"], "->", np.round(fc[s]["pron"], 1),
              "sd_rel:", np.round(fc[s]["sd_rel"], 4), "rho12:", round(fc[s]["rho_h1_h2"], 3))
    print("rho int-ext", fc["rho_int_ext"])
