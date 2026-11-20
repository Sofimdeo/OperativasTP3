# TP3 — Gestión integrada de stocks (Investigación Operativa)

Padrón terminado en **5** (hoja `Digito_5`).

## Valores de decisión (formulario)

| # | Decisión | Valor |
|---|---|---|
| 1 | Noviembre: jarabe planificado (t MS) | 27707.00 |
| 2 | Diciembre: maíz total a comprar (t) | 79091.00 |
| 3 | Diciembre: jarabe planificado (t MS) | 27061.00 |
| 4 | Anticipo: maíz con precio fijado y pagado en noviembre (t) | 59118.07 |

## Contenido

```
datos/TP_Stocks_Alumnos.xlsx   planilla de la cátedra (se usa la hoja Digito_5)
src/parametros.py              datos del caso (cátedra) y supuestos del alumno, separados
src/pronostico.py              Parte A: métodos, validación de origen móvil, incertidumbre, escenarios
src/modelo.py                  Parte B: programa lineal estocástico de dos etapas en PuLP
src/simulacion.py              simulación Monte Carlo del plan con las reglas comerciales; niveles de servicio
src/graficos.py                figuras del informe
main.py                        ejecuta todo (A, B, C, robustez y sensibilidad) -> resultados/
informe/generar_informe.py     arma informe_TP3.html y informe_TP3.pdf desde resultados/
informe/a_pdf.js               alternativa para imprimir el PDF con Playwright (Node)
TP3_Stocks.ipynb               notebook equivalente para Colab/Jupyter
resultados/                    CSV, JSON y figuras generadas
```

## Ejecución

Requiere Python 3.10+.

```bash
pip install -r requirements.txt
python main.py                     # ~40 s; imprime los 4 valores del formulario
python informe/generar_informe.py  # genera informe/informe_TP3.html (+ PDF si hay Playwright)
```

Solver: PuLP usa HiGHS si está instalado (`pip install highspy`), si no el CBC que trae PuLP.
Las semillas aleatorias están fijas, por lo que los resultados son reproducibles
(con otro solver pueden variar decimales). Si no se genera el PDF, abrir el HTML
en el navegador e imprimir a PDF.
