"""
Parámetros del caso (TP3 - Gestión integrada de stocks).

Se separan explícitamente:
  * DATOS DE LA CÁTEDRA: surgen del enunciado y dependen del último dígito del padrón (d).
  * SUPUESTOS DEL ALUMNO: decisiones de modelado propias (marcadas como tales).
"""
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVO_DATOS = RAIZ / "datos" / "TP_Stocks_Alumnos.xlsx"
DIR_RESULTADOS = RAIZ / "resultados"

DIGITO = 5  # último dígito del padrón


@dataclass
class Caso:
    d: int = DIGITO

    # ---------------- DATOS DE LA CÁTEDRA ----------------
    maiz_por_almidon: float = 1.50          # t maíz / t almidón (rendimiento normal)
    almidon_por_jarabe: float = 1.00        # t almidón / t jarabe
    horas_almidon: float = 1.00             # h-eq / t almidón obtenido
    horas_jarabe: float = 0.25              # h-eq / t almidón transformado en jarabe
    horas_mes: float = 60_000.0             # h-eq disponibles por mes
    cap_jarabe: float = 30_000.0            # t/mes máximo de la etapa jarabe
    min_almidon_mes: float = 30_000.0       # t/mes de almidón obtenido (continuidad operativa)
    cap_deposito: float = 30_000.0          # t de almidón al cierre de cada mes
    costo_disposicion_usd: float = 12.0     # USD/t jarabe vencido
    costo_conservacion_usd: float = 8.0     # USD/t almidón al cierre de cada mes
    valor_continuidad_usd: float = 180.0    # USD/t almidón al cierre de diciembre
    costo_jarabe_usd: float = 35.0          # USD/t transformación almidón -> jarabe
    precio_maiz_usd: float = 100.0          # USD/t (cotización de referencia)
    tc_octubre: float = 1_715.0             # ARS/USD cierre de octubre
    precio_maiz_ars_anticipo: float = 171_500.0  # ARS/t (100 USD x 1715)
    caja_inicial_ars: float = 20_000e6      # ARS antes de pagar el pedido de noviembre

    # ---------------- Valores que dependen del dígito ----------------
    @property
    def stock_inicial_almidon(self) -> float:
        return 10_000 + 1_000 * self.d

    @property
    def maiz_noviembre(self) -> float:
        return 55_000 + 500 * self.d

    @property
    def precio_almidon_int_ars(self) -> float:
        return 600_000 + 8_000 * self.d

    @property
    def precio_almidon_ext_usd(self) -> float:
        return 290 + 2 * self.d

    @property
    def precio_jarabe_int_ars(self) -> float:
        return 720_000 + 6_000 * self.d

    @property
    def precio_jarabe_ext_usd(self) -> float:
        return 350 + 3 * self.d

    @property
    def costo_proceso_almidon_usd(self) -> float:
        """Procesamiento sin maíz, USD por t de almidón (70 + 5d)."""
        return 70 + 5 * self.d

    @property
    def costo_ref_almidon_usd(self) -> float:
        """Costo de referencia hasta almidón (maíz a 100 USD/t + proceso) = 220 + 5d."""
        return self.maiz_por_almidon * self.precio_maiz_usd + self.costo_proceso_almidon_usd

    @property
    def share_int(self) -> dict:
        """Composición de la demanda interna (%A / %J)."""
        a = (40 + self.d) / 100
        return {"A": a, "J": 1 - a}

    @property
    def share_ext(self) -> dict:
        """Composición de la demanda externa (%A / %J)."""
        a = (60 - self.d) / 100
        return {"A": a, "J": 1 - a}

    @property
    def produccion_almidon_noviembre(self) -> float:
        """Todo el maíz recibido se procesa en el mes: almidón de noviembre fijo."""
        return self.maiz_noviembre / self.maiz_por_almidon

    @property
    def caja_para_anticipo_ars(self) -> float:
        return self.caja_inicial_ars - self.maiz_noviembre * self.precio_maiz_ars_anticipo

    @property
    def maiz_max_anticipo(self) -> float:
        """t de maíz de diciembre que pueden fijarse y pagarse con la caja disponible."""
        return self.caja_para_anticipo_ars / self.precio_maiz_ars_anticipo

    # ---------------- SUPUESTOS DEL ALUMNO ----------------
    # Piso de incertidumbre para la demanda interna (riesgo de modelo): el histórico
    # muestra un crecimiento interanual prácticamente constante y residuos casi nulos,
    # pero 22 meses no alcanzan para descartar desvíos. Se adopta un CV mínimo.
    cv_min_demanda_interna: float = 0.02
    # Almidón que excede la capacidad del depósito al cierre: se asume liquidado sin
    # valor con un costo de disposición igual al del jarabe (12 USD/t). Sólo actúa
    # en escenarios extremos y desalienta planes que puedan desbordar el depósito.
    costo_desborde_usd: float = 12.0

    def resumen(self) -> dict:
        return {
            "digito": self.d,
            "stock_inicial_almidon_t": self.stock_inicial_almidon,
            "maiz_noviembre_t": self.maiz_noviembre,
            "almidon_noviembre_t": self.produccion_almidon_noviembre,
            "precio_almidon_int_ARS": self.precio_almidon_int_ars,
            "precio_almidon_ext_USD": self.precio_almidon_ext_usd,
            "precio_jarabe_int_ARS": self.precio_jarabe_int_ars,
            "precio_jarabe_ext_USD": self.precio_jarabe_ext_usd,
            "costo_ref_almidon_USD": self.costo_ref_almidon_usd,
            "costo_proceso_almidon_USD": self.costo_proceso_almidon_usd,
            "composicion_interna_A_J": (self.share_int["A"], self.share_int["J"]),
            "composicion_externa_A_J": (self.share_ext["A"], self.share_ext["J"]),
            "caja_para_anticipo_ARS": self.caja_para_anticipo_ars,
            "maiz_max_anticipo_t": self.maiz_max_anticipo,
        }


if __name__ == "__main__":
    import pprint
    pprint.pprint(Caso().resumen())
