"""Gráficos del informe (PNG estáticos)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

AZUL, NARANJA, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
TINTA, TINTA2, GRILLA = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": GRILLA,
    "axes.labelcolor": TINTA2, "xtick.color": TINTA2, "ytick.color": TINTA2,
    "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlecolor": TINTA,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRILLA, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "legend.frameon": False, "savefig.dpi": 200, "figure.facecolor": "white",
})


def _miles(ax):
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", ".")))


def pronosticos(df, fc, carpeta):
    fechas_f = pd.date_range("2026-11-01", periods=2, freq="MS")
    titulos = {"di": "Demanda interna total (t MS)", "de": "Demanda externa total (t MS)",
               "tc": "Tipo de cambio (ARS/USD)"}
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 8.2))
    for ax, s in zip(axes, ("di", "de", "tc")):
        ax.plot(df.mes, df[s], color=AZUL, lw=2, marker="o", ms=3.5, label="Histórico")
        f = np.asarray(fc[s]["pron"])
        sd = np.asarray(fc[s]["sd_rel"]) * f
        x = [df.mes.iloc[-1]] + list(fechas_f)
        ax.plot(x, [df[s].iloc[-1]] + list(f), color=NARANJA, lw=2, marker="o", ms=4.5,
                label=f"Pronóstico: {fc[s]['metodo']}")
        ax.fill_between(fechas_f, f - 1.645 * sd, f + 1.645 * sd, color=NARANJA, alpha=0.18, lw=0,
                        label="Intervalo 90%")
        for k, (xi, yi) in enumerate(zip(fechas_f, f)):
            ax.annotate(f"{yi:,.0f}".replace(",", "."), (xi, yi), textcoords="offset points",
                        xytext=(-34, 6) if k == 0 else (6, -3), fontsize=8, color=TINTA)
        ax.set_xlim(df.mes.iloc[0] - pd.Timedelta(days=15), fechas_f[-1] + pd.Timedelta(days=40))
        ax.set_title(titulos[s], loc="left")
        _miles(ax)
        ax.legend(loc="upper left", fontsize=7.5)
    fig.tight_layout()
    fig.savefig(carpeta / "fig_pronosticos.png")
    plt.close(fig)


def distribucion_resultado(sim, carpeta):
    x = sim["resultado"] / 1e6
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    ax.hist(x, bins=60, color=AZUL, edgecolor="white", linewidth=0.4)
    ax.set_xlim(np.percentile(x, 0.2), x.max() + 50)
    ytop = ax.get_ylim()[1]
    for q, lab, fy, ha in ((np.percentile(x, 5), "P5", 0.92, "right"), (x.mean(), "Media", 0.92, "right"),
                           (np.percentile(x, 95), "P95", 0.75, "left")):
        ax.axvline(q, color=TINTA2, lw=1, ls="--")
        ax.annotate(f"{lab}: {q:,.0f}".replace(",", "."), (q, ytop * fy), ha=ha,
                    xytext=(-4 if ha == "right" else 4, 0), textcoords="offset points", fontsize=8, color=TINTA)
    ax.set_title("Resultado nov-dic del plan recomendado (M ARS, 20.000 escenarios)", loc="left")
    ax.set_xlabel("M ARS")
    ax.set_ylabel("Escenarios")
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", ".")))
    fig.tight_layout()
    fig.savefig(carpeta / "fig_resultado.png")
    plt.close(fig)


def ventas_vs_demanda(ns, carpeta):
    ns = ns.copy()
    ns["etq"] = ns.producto.str[:3] + ". " + ns.mercado.str[:3].str.lower() + ".\n" + ns.mes
    fig, ax = plt.subplots(figsize=(7.2, 2.9))
    x = np.arange(len(ns))
    w = 0.38
    ax.bar(x - w / 2 - 0.01, ns.demanda_media_t, w, color=AZUL, label="Demanda media")
    ax.bar(x + w / 2 + 0.01, ns.ventas_medias_t, w, color=AQUA, label="Ventas medias")
    for xi, fr, d in zip(x, ns.fill_rate, ns.demanda_media_t):
        ax.annotate(f"{100*fr:.1f}%", (xi, d), xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=7.5, color=TINTA)
    ax.set_xticks(x, ns.etq, fontsize=7.5)
    ax.set_ylim(0, ns.demanda_media_t.max() * 1.28)
    _miles(ax)
    ax.set_title("Demanda y ventas medias (t); % = fracción de la demanda cubierta", loc="left")
    ax.legend(loc="upper right", fontsize=7.5, ncol=2)
    fig.tight_layout()
    fig.savefig(carpeta / "fig_servicio.png")
    plt.close(fig)
