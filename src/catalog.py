"""Catálogo de series INE usadas en el proyecto.

Cada entrada describe cómo localizar una (o varias) series dentro de una tabla
Tempus3 a partir de su nombre oficial:

- ``exact``: nombre exacto de la serie (se normalizan espacios y mayúsculas).
- ``regex``: expresión regular sobre el nombre normalizado (minúsculas). En las
  series múltiples, el grupo con nombre ``dim`` define la dimensión (sector,
  grupo de gasto, CCAA...).
- ``multi``: ``None`` (serie única), ``"dim"`` (dimensión del grupo ``dim``)
  o ``"ccaa"`` (la dimensión se normaliza a nombre de comunidad autónoma).
- ``better``: dirección deseable del indicador (``"up"``, ``"down"`` o ``None``)
  para colorear mejoras/empeoramientos sin juicios ad hoc.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SeriesSpec:
    key: str
    table: int
    block: str
    label: str
    unit: str
    freq: str  # M, Q, S (semestral), A
    exact: str | None = None
    regex: str | None = None
    multi: str | None = None
    better: str | None = None
    desc: str = ""
    source: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)


BLOCKS = {
    "empleo": "Mercado laboral",
    "precios": "Precios",
    "salarios": "Salarios y poder adquisitivo",
    "actividad": "Crecimiento y actividad",
    "vivienda": "Vivienda",
    "bienestar": "Bienestar y desigualdad",
    "demografia": "Demografía",
    "genero": "Brecha de género",
    "justicia": "Justicia penal y nacionalidad",
}

_PIB = r"^total nacional\. datos ajustados de estacionalidad y calendario\. producto interior bruto a precios de mercado\. "
_ETCL = r"^industria, construcción y servicios \(excepto [^)]*\)\. "
_AGE = r"(?P<dim>todas las edades|de \d+ a \d+ años|\d+ y más años)"
_BAND = r"(de \d+ a \d+ años|\d+ y más años)"

SERIES: list[SeriesSpec] = [
    # ── Mercado laboral ──────────────────────────────────────────────────────
    SeriesSpec("paro", 14506, "empleo", "Tasa de paro", "%", "Q",
               exact="Tasa de paro de la población. Ambos sexos. Total Nacional. Total.",
               better="down", source="EPA",
               desc="Parados sobre población activa. Indicador laboral de referencia."),
    SeriesSpec("paro_hombres", 14506, "empleo", "Tasa de paro · hombres", "%", "Q",
               exact="Tasa de paro de la población. Hombres. Total Nacional. Total.", better="down", source="EPA"),
    SeriesSpec("paro_mujeres", 14506, "empleo", "Tasa de paro · mujeres", "%", "Q",
               exact="Tasa de paro de la población. Mujeres. Total Nacional. Total.", better="down", source="EPA"),
    SeriesSpec("paro_juvenil", 14506, "empleo", "Tasa de paro < 25 años", "%", "Q",
               exact="Tasa de paro de la población. Ambos sexos. Total Nacional. Menores de 25 años.",
               better="down", source="EPA", desc="Paro de menores de 25 años, crónicamente alto en España."),
    SeriesSpec("paro_ccaa", 14506, "empleo", "Tasa de paro por CCAA", "%", "Q",
               regex=r"^tasa de paro de la población\. ambos sexos\. (?P<dim>.+)\. total\.$",
               multi="ccaa", better="down", source="EPA"),
    SeriesSpec("paro_ld_edad", 67577, "empleo", "Paro de larga duración por edad", "%", "Q",
               regex=r"^total nacional\. ambos sexos\. (?P<dim>de .+? años)\. tasa de desempleo de larga duración",
               multi="dim", better="down", source="EPA",
               desc="Parados que llevan más de un año buscando empleo, sobre población activa."),
    SeriesSpec("empleo", 67555, "empleo", "Tasa de empleo 20-64", "%", "A",
               exact="Total Nacional. Ambos sexos. De 20 a 64 años. Tasa de empleo de la población. HVD.",
               better="up", source="EPA", desc="Ocupados de 20 a 64 años sobre población de esa edad (objetivo UE 2030)."),
    SeriesSpec("empleo_hombres", 67555, "empleo", "Tasa de empleo 20-64 · hombres", "%", "A",
               exact="Total Nacional. Hombres. De 20 a 64 años. Tasa de empleo de la población. HVD.", better="up", source="EPA"),
    SeriesSpec("empleo_mujeres", 67555, "empleo", "Tasa de empleo 20-64 · mujeres", "%", "A",
               exact="Total Nacional. Mujeres. De 20 a 64 años. Tasa de empleo de la población. HVD.", better="up", source="EPA"),
    SeriesSpec("empleo_ccaa", 67555, "empleo", "Tasa de empleo 20-64 por CCAA", "%", "A",
               regex=r"^(?P<dim>.+)\. ambos sexos\. de 20 a 64 años\. tasa de empleo",
               multi="ccaa", better="up", source="EPA"),
    SeriesSpec("ocupados", 65109, "empleo", "Ocupados (EPA)", "miles", "Q",
               exact="Total Nacional. Ambos sexos. Total. Ocupados. Valor absoluto.",
               better="up", source="EPA", desc="Personas con empleo según la Encuesta de Población Activa."),
    SeriesSpec("ocupados_sector", 67827, "empleo", "Ocupados por rama (CNTR, ajustado)", "miles", "Q",
               regex=r"^ocupado/a\. total nacional\. personas\. datos ajustados de estacionalidad y calendario\. (?P<dim>.+)\. dato base\.$",
               multi="dim", better="up", source="CNTR"),
    SeriesSpec("temporalidad", 65977, "empleo", "Asalariados con contrato temporal", "%", "A",
               regex=r"^asalariados\. total nacional\. ambos sexos\. temporal: total\. porcentaje",
               better="down", source="EPA", desc="Peso del empleo temporal; la reforma laboral de 2022 lo redujo con fuerza."),
    SeriesSpec("vacantes", 6047, "empleo", "Puestos de trabajo vacantes", "puestos", "Q",
               regex=r"^total nacional\. industria, construcción y servicios.*vacantes",
               source="ETCL", desc="Vacantes declaradas por las empresas: termómetro de tensión del mercado laboral."),
    SeriesSpec("productividad", 67828, "empleo", "Productividad y costes (var. anual)", "%", "Q",
               regex=r"^(?P<dim>.+?)\. datos ajustados de estacionalidad y calendario\. variación anual",
               multi="dim", source="CNTR"),

    # ── Precios ──────────────────────────────────────────────────────────────
    SeriesSpec("ipc", 76130, "precios", "IPC general (var. anual)", "%", "M",
               exact="Nacional. Índice general. Variación anual.", better="down", source="IPC",
               desc="Inflación general interanual."),
    SeriesSpec("ipc_subyacente", 76130, "precios", "IPC subyacente (var. anual)", "%", "M",
               exact="Nacional. Subyacente: General sin alimentos no elaborados ni productos energéticos. Variación anual.",
               better="down", source="IPC", desc="Excluye energía y alimentos frescos: mide la inflación de fondo."),
    SeriesSpec("ipc_energia", 76130, "precios", "IPC productos energéticos (var. anual)", "%", "M",
               exact="Nacional. Productos energéticos. Variación anual.", better="down", source="IPC"),
    SeriesSpec("ipc_alimentos", 76130, "precios", "IPC alimentos, bebidas y tabaco (var. anual)", "%", "M",
               exact="Nacional. Alimentos, bebidas y tabaco. Variación anual.", better="down", source="IPC"),
    SeriesSpec("ipc_servicios", 76130, "precios", "IPC servicios (var. anual)", "%", "M",
               exact="Nacional. Servicios. Variación anual.", better="down", source="IPC"),
    SeriesSpec("ipc_indice", 76130, "precios", "IPC índice general", "índice", "M",
               exact="Nacional. Índice general. Índice.", source="IPC",
               desc="Nivel de precios; se usa como deflactor para salarios reales."),
    SeriesSpec("ipc_grupos", 76135, "precios", "IPC por grupos ECOICOP (var. anual)", "%", "M",
               regex=r"^nacional\. (?P<dim>.+)\. variación anual\.$", multi="dim", better="down", source="IPC"),
    SeriesSpec("ipc_ccaa", 79182, "precios", "IPC por CCAA (var. anual)", "%", "M",
               regex=r"^(?P<dim>.+)\. índice general\. variación anual\.$", multi="ccaa", better="down", source="IPC"),

    # ── Salarios ─────────────────────────────────────────────────────────────
    SeriesSpec("coste_salarial", 6030, "salarios", "Coste salarial por trabajador y mes", "€", "Q",
               regex=_ETCL + r"coste salarial total\. total", better="up", source="ETCL",
               desc="Salario bruto medio mensual pagado por las empresas (incluye pagas extra prorrateadas por trimestre)."),
    SeriesSpec("coste_laboral", 6030, "salarios", "Coste laboral por trabajador y mes", "€", "Q",
               regex=_ETCL + r"coste laboral total\. total", source="ETCL",
               desc="Salario + cotizaciones sociales y otros costes: lo que cuesta un trabajador a la empresa."),
    SeriesSpec("coste_hora", 79658, "salarios", "Coste laboral por hora efectiva", "€", "Q",
               regex=r"^coste laboral total por hora\. total nacional\. industria, construcción y servicios", source="ETCL"),
    SeriesSpec("salario_medio", 28191, "salarios", "Ganancia media anual por trabajador", "€", "A",
               exact="Ambos sexos. Total Nacional. Dato base. Media.", better="up", source="EAES"),
    SeriesSpec("salario_mediana", 28191, "salarios", "Ganancia mediana anual", "€", "A",
               exact="Ambos sexos. Total Nacional. Dato base. Mediana.", better="up", source="EAES",
               desc="El salario del trabajador 'del medio': menos sensible a sueldos muy altos que la media."),
    SeriesSpec("salario_p10", 28191, "salarios", "Ganancia anual · percentil 10", "€", "A",
               exact="Ambos sexos. Total Nacional. Dato base. Percentil 10.", better="up", source="EAES"),
    SeriesSpec("salario_p90", 28191, "salarios", "Ganancia anual · percentil 90", "€", "A",
               exact="Ambos sexos. Total Nacional. Dato base. Percentil 90.", source="EAES"),
    SeriesSpec("salario_mujeres", 28191, "salarios", "Ganancia media anual · mujeres", "€", "A",
               exact="Mujeres. Total Nacional. Dato base. Media.", better="up", source="EAES"),
    SeriesSpec("salario_hombres", 28191, "salarios", "Ganancia media anual · hombres", "€", "A",
               exact="Hombres. Total Nacional. Dato base. Media.", source="EAES"),
    SeriesSpec("salario_ccaa", 28191, "salarios", "Ganancia media anual por CCAA", "€", "A",
               regex=r"^ambos sexos\. (?P<dim>.+)\. dato base\. media\.$", multi="ccaa", better="up", source="EAES"),

    # ── Brecha salarial de género ────────────────────────────────────────────
    SeriesSpec("salario_mediana_mujeres", 28191, "genero", "Ganancia mediana anual · mujeres", "€", "A",
               exact="Mujeres. Total Nacional. Dato base. Mediana.", source="EAES"),
    SeriesSpec("salario_mediana_hombres", 28191, "genero", "Ganancia mediana anual · hombres", "€", "A",
               exact="Hombres. Total Nacional. Dato base. Mediana.", source="EAES"),
    SeriesSpec("salario_ccaa_mujeres", 28191, "genero", "Ganancia media anual por CCAA · mujeres", "€", "A",
               regex=r"^mujeres\. (?P<dim>.+)\. dato base\. media\.$", multi="ccaa", source="EAES"),
    SeriesSpec("salario_ccaa_hombres", 28191, "genero", "Ganancia media anual por CCAA · hombres", "€", "A",
               regex=r"^hombres\. (?P<dim>.+)\. dato base\. media\.$", multi="ccaa", source="EAES"),
    SeriesSpec("salario_hora", 30046, "genero", "Salario medio por hora", "€/h", "A",
               exact="Salario medio por hora", source="EAES"),
    SeriesSpec("salario_hora_mujeres", 30046, "genero", "Salario medio por hora · mujeres", "€/h", "A",
               exact="Salario medio por hora de mujeres", source="EAES",
               desc="Base del indicador europeo de brecha salarial no ajustada (Gender Pay Gap)."),
    SeriesSpec("salario_hora_hombres", 30046, "genero", "Salario medio por hora · hombres", "€/h", "A",
               exact="Salario medio por hora de hombres", source="EAES"),
    SeriesSpec("salario_hora_sector_mujeres", 30046, "genero", "Salario por hora por sector · mujeres", "€/h", "A",
               regex=r"^mujeres\. total nacional\. dato base\. (?P<dim>.+)\. salario por hora\.$", multi="dim", source="EAES"),
    SeriesSpec("salario_hora_sector_hombres", 30046, "genero", "Salario por hora por sector · hombres", "€/h", "A",
               regex=r"^hombres\. total nacional\. dato base\. (?P<dim>.+)\. salario por hora\.$", multi="dim", source="EAES"),
    SeriesSpec("salario_ocupacion_mujeres", 28186, "genero", "Salario medio por ocupación · mujeres", "€", "A",
               regex=r"^(?P<dim>.+)\. mujeres\. salario medio bruto\. total nacional\. dato base\.$", multi="dim", source="EAES"),
    SeriesSpec("salario_ocupacion_hombres", 28186, "genero", "Salario medio por ocupación · hombres", "€", "A",
               regex=r"^(?P<dim>.+)\. hombres\. salario medio bruto\. total nacional\. dato base\.$", multi="dim", source="EAES"),
    SeriesSpec("salario_actividad_mujeres", 28185, "genero", "Salario medio por actividad · mujeres", "€", "A",
               regex=r"^mujeres\. (?P<dim>.+)\. dato base\. total nacional\. salario medio bruto\.$", multi="dim", source="EAES"),
    SeriesSpec("salario_actividad_hombres", 28185, "genero", "Salario medio por actividad · hombres", "€", "A",
               regex=r"^hombres\. (?P<dim>.+)\. dato base\. total nacional\. salario medio bruto\.$", multi="dim", source="EAES"),

    # ── Crecimiento y actividad ──────────────────────────────────────────────
    SeriesSpec("pib", 67822, "actividad", "PIB (var. anual, volumen)", "%", "Q",
               regex=_PIB + r"variación anual\.", better="up", source="CNTR",
               desc="Crecimiento real del PIB respecto al mismo trimestre del año anterior."),
    SeriesSpec("pib_trimestral", 67822, "actividad", "PIB (var. trimestral, volumen)", "%", "Q",
               regex=_PIB + r"variación trimestral\.", better="up", source="CNTR"),
    SeriesSpec("pib_indice", 67822, "actividad", "PIB índice de volumen encadenado", "índice", "Q",
               regex=_PIB + r"dato base\.", better="up", source="CNTR"),
    SeriesSpec("ipi", 70177, "actividad", "Producción industrial (var. anual)", "%", "M",
               exact="Total Nacional. Total industria. Variación anual.", better="up", source="IPI"),
    SeriesSpec("sociedades", 13917, "actividad", "Sociedades mercantiles constituidas", "sociedades", "M",
               exact="Sociedades Constituídas. Número de Sociedades. Total Nacional. Mercantiles.",
               better="up", source="SM", desc="Creación de empresas: proxy del dinamismo emprendedor."),
    SeriesSpec("turistas", 75720, "actividad", "Turistas internacionales", "personas", "M",
               exact="Turista. Total Nacional. Dato base.", better="up", source="FRONTUR"),
    SeriesSpec("turistas_ccaa", 75720, "actividad", "Turistas internacionales por CCAA", "personas", "M",
               regex=r"^(?P<dim>.+)\. turista\. dato base\.$", multi="ccaa", better="up", source="FRONTUR"),
    SeriesSpec("gasto_turistas", 75714, "actividad", "Gasto de turistas internacionales", "M€", "M",
               exact="Gasto total. Total Nacional. Turista. Dato base.", better="up", source="EGATUR"),

    # ── Vivienda ─────────────────────────────────────────────────────────────
    SeriesSpec("ipv", 80270, "vivienda", "Precio de la vivienda (IPV, var. anual)", "%", "Q",
               exact="Nacional. General. Variación anual.", better="down", source="IPV",
               desc="Precio de compraventa de vivienda libre. Desde el punto de vista del acceso, subir es peor."),
    SeriesSpec("ipv_nueva", 80270, "vivienda", "IPV vivienda nueva (var. anual)", "%", "Q",
               exact="Nacional. Vivienda nueva. Variación anual.", better="down", source="IPV"),
    SeriesSpec("ipv_segunda", 80270, "vivienda", "IPV segunda mano (var. anual)", "%", "Q",
               exact="Nacional. Vivienda segunda mano. Variación anual.", better="down", source="IPV"),
    SeriesSpec("ipv_indice", 80270, "vivienda", "IPV índice general", "índice", "Q",
               exact="Nacional. General. Índice.", source="IPV"),
    SeriesSpec("ipv_ccaa", 80270, "vivienda", "IPV por CCAA (var. anual)", "%", "Q",
               regex=r"^(?P<dim>.+)\. general\. variación anual\.$", multi="ccaa", better="down", source="IPV"),
    SeriesSpec("alquiler_indice", 59056, "vivienda", "Índice de precios del alquiler (IPVA)", "índice", "A",
               exact="Total Nacional. Total. Índice.", source="IPVA"),
    SeriesSpec("alquiler", 59056, "vivienda", "Alquiler (IPVA, var. anual)", "%", "A",
               exact="Total Nacional. Total. Variación anual.", better="down", source="IPVA"),
    SeriesSpec("alquiler_ccaa", 59056, "vivienda", "Alquiler por CCAA (var. anual)", "%", "A",
               regex=r"^(?P<dim>.+)\. total\. variación anual\.$", multi="ccaa", better="down", source="IPVA"),
    SeriesSpec("hipotecas", 13896, "vivienda", "Hipotecas constituidas (todas las fincas)", "hipotecas", "M",
               exact="Total fincas. Número de hipotecas. Total Nacional. Base nueva. Mensual.", source="HPT"),
    SeriesSpec("tipo_hipoteca", 24457, "vivienda", "Tipo de interés medio hipotecas sobre vivienda", "%", "M",
               exact="Viviendas. Tipo de interés medio. Total Nacional. Base nueva. Mensual. Total.",
               better="down", source="HPT"),

    # ── Bienestar ────────────────────────────────────────────────────────────
    SeriesSpec("arope", 67240, "bienestar", "Riesgo de pobreza o exclusión (AROPE)", "%", "A",
               regex=r"^ambos sexos\. total\. total nacional\. tasa de riesgo de pobreza o exclusión social",
               better="down", source="ECV",
               desc="Indicador europeo que combina pobreza de renta, carencia material y baja intensidad laboral."),
    SeriesSpec("arope_infantil", 67240, "bienestar", "AROPE menores de 16", "%", "A",
               regex=r"^ambos sexos\. menores de 16 años\. total nacional\. tasa de riesgo de pobreza o exclusión social",
               better="down", source="ECV"),
    SeriesSpec("pobreza", 67240, "bienestar", "Tasa de riesgo de pobreza", "%", "A",
               regex=r"^ambos sexos\. total\. total nacional\. en riesgo de pobreza", better="down", source="ECV",
               desc="Personas con renta inferior al 60% de la mediana nacional (renta del año anterior)."),
    SeriesSpec("carencia_severa", 68027, "bienestar", "Carencia material y social severa", "%", "A",
               exact="Ambos sexos. Total. Total Nacional. Con carencia material y social severa. Base 2013.",
               better="down", source="ECV"),
    SeriesSpec("gini", 67245, "bienestar", "Coeficiente de Gini", "índice", "A",
               exact="Total Nacional. Ambos sexos. Total. Gini. Base 2013.", better="down", source="ECV",
               desc="Desigualdad de la renta: 0 = igualdad total, 100 = un solo hogar lo tiene todo."),
    SeriesSpec("s80s20", 67245, "bienestar", "Ratio S80/S20", "ratio", "A",
               exact="Total Nacional. Ambos sexos. Total. Desigualdad (S80/S20). Base 2013.", better="down", source="ECV",
               desc="Renta del 20% más rico dividida entre la del 20% más pobre."),
    SeriesSpec("arope_ccaa", 67989, "bienestar", "AROPE por CCAA", "%", "A",
               regex=r"^(?P<dim>[^.]+)\..*tasa de riesgo de pobreza o exclusión social \(indicador arope\)",
               multi="ccaa", better="down", source="ECV"),

    # ── Demografía ───────────────────────────────────────────────────────────
    SeriesSpec("saldo_migratorio", 69758, "demografia", "Saldo migratorio total", "personas", "A",
               exact="Total. Total. Saldo total. Dato base.", source="EMCR"),
    SeriesSpec("saldo_exterior", 69758, "demografia", "Saldo migratorio con el extranjero", "personas", "A",
               exact="Total. Total. Saldo exterior. Dato base.", source="EMCR"),
    SeriesSpec("nacimientos", 46682, "demografia", "Nacimientos mensuales (estimación)", "nacimientos", "M",
               exact="Total Nacional. Total. Todas las edades. Dato base.", source="EMN"),
    # Población por nacionalidad y edad: serie histórica (2010-2025, semestral) + serie actual (2025-, trimestral)
    SeriesSpec("pob_hist_total", 56942, "demografia", "Población residente por edad · total (histórica)", "personas", "S",
               regex=r"^total nacional\. total\. " + _AGE + r"\. total\. población\. número\.$",
               multi="dim", source="ECP", desc="Estadística Continua de Población (1 de enero y 1 de julio)."),
    SeriesSpec("pob_hist_espanola", 56942, "demografia", "Población residente por edad · española (histórica)", "personas", "S",
               regex=r"^total nacional\. española\. " + _AGE + r"\. total\. población\. número\.$", multi="dim", source="ECP"),
    SeriesSpec("pob_hist_sexo", 56942, "demografia", "Población residente por sexo y nacionalidad (histórica)", "personas", "S",
               regex=r"^total nacional\. (?P<dim>(total|española)\. todas las edades\. (hombres|mujeres))\. población\. número\.$",
               multi="dim", source="ECP"),
    SeriesSpec("pob_total", 82104, "demografia", "Población residente por edad · total", "personas", "S",
               regex=r"^total nacional\. total\. " + _AGE + r"\. total\. población\. número\.$", multi="dim", source="ECP"),
    SeriesSpec("pob_espanola", 82104, "demografia", "Población residente por edad · española", "personas", "S",
               regex=r"^total nacional\. española\. " + _AGE + r"\. total\. población\. número\.$", multi="dim", source="ECP"),
    SeriesSpec("pob_sexo", 82104, "demografia", "Población residente por sexo y nacionalidad", "personas", "S",
               regex=r"^total nacional\. (?P<dim>(total|española)\. todas las edades\. (hombres|mujeres))\. población\. número\.$",
               multi="dim", source="ECP"),

    # ── Justicia penal y nacionalidad ────────────────────────────────────────
    SeriesSpec("condenados_nac", 25704, "justicia", "Personas condenadas (adultos) por nacionalidad", "personas", "A",
               regex=r"^total\. total nacional\. dato base\. (?P<dim>total|española|extranjera)\.$",
               multi="dim", source="CONA",
               desc="Adultos con sentencia condenatoria firme inscrita en el Registro Central de Penados en el año."),
    SeriesSpec("condenados_hombres_nac", 25704, "justicia", "Hombres condenados por nacionalidad", "personas", "A",
               regex=r"^hombres\. total nacional\. dato base\. (?P<dim>total|española|extranjera)\.$", multi="dim", source="CONA"),
    SeriesSpec("condenados_mujeres_nac", 25704, "justicia", "Mujeres condenadas por nacionalidad", "personas", "A",
               regex=r"^mujeres\. total nacional\. dato base\. (?P<dim>total|española|extranjera)\.$", multi="dim", source="CONA"),
    SeriesSpec("condenados_edad_espanola", 25645, "justicia", "Condenados españoles por edad", "personas", "A",
               regex=r"^total\. española\. (?P<dim>de \d+ a \d+ años|\d+ y más años)\. dato base\. total nacional\.$",
               multi="dim", source="CONA"),
    SeriesSpec("condenados_edad_total", 25645, "justicia", "Condenados por edad · total", "personas", "A",
               regex=r"^total\. total\. (?P<dim>de \d+ a \d+ años|\d+ y más años)\. dato base\. total nacional\.$",
               multi="dim", source="CONA"),
    # Desagregación sexo × edad para la estandarización conjunta por edad y sexo
    SeriesSpec("condenados_sexo_edad_total", 25645, "justicia", "Condenados por sexo y edad · total", "personas", "A",
               regex=r"^(?P<dim>(hombres|mujeres)\. total\. " + _BAND + r")\. dato base\. total nacional\.$",
               multi="dim", source="CONA"),
    SeriesSpec("condenados_sexo_edad_espanola", 25645, "justicia", "Condenados por sexo y edad · españoles", "personas", "A",
               regex=r"^(?P<dim>(hombres|mujeres)\. española\. " + _BAND + r")\. dato base\. total nacional\.$",
               multi="dim", source="CONA"),
    SeriesSpec("pob_hist_sexo_edad_total", 56942, "demografia", "Población por sexo y edad · total (histórica)", "personas", "S",
               regex=r"^total nacional\. total\. (?P<dim>" + _BAND + r"\. (hombres|mujeres))\. población\. número\.$",
               multi="dim", source="ECP"),
    SeriesSpec("pob_hist_sexo_edad_espanola", 56942, "demografia", "Población por sexo y edad · española (histórica)", "personas", "S",
               regex=r"^total nacional\. española\. (?P<dim>" + _BAND + r"\. (hombres|mujeres))\. población\. número\.$",
               multi="dim", source="ECP"),
    SeriesSpec("pob_sexo_edad_total", 82104, "demografia", "Población por sexo y edad · total", "personas", "S",
               regex=r"^total nacional\. total\. (?P<dim>" + _BAND + r"\. (hombres|mujeres))\. población\. número\.$",
               multi="dim", source="ECP"),
    SeriesSpec("pob_sexo_edad_espanola", 82104, "demografia", "Población por sexo y edad · española", "personas", "S",
               regex=r"^total nacional\. española\. (?P<dim>" + _BAND + r"\. (hombres|mujeres))\. población\. número\.$",
               multi="dim", source="ECP"),
    SeriesSpec("delitos_tipo_total", 49050, "justicia", "Delitos en sentencias condenatorias por tipo · total", "delitos", "A",
               regex=r"^total nacional\. dato base\. (?P<dim>.+)\. total\.$", multi="dim", source="CONA"),
    SeriesSpec("delitos_tipo_espanola", 49050, "justicia", "Delitos en sentencias condenatorias por tipo · españoles", "delitos", "A",
               regex=r"^total nacional\. dato base\. (?P<dim>.+)\. española\.$", multi="dim", source="CONA"),
]

CCAA = [
    ("andalucía", "Andalucía"),
    ("aragón", "Aragón"),
    ("asturias", "Asturias"),
    ("balears", "Baleares"),
    ("canarias", "Canarias"),
    ("cantabria", "Cantabria"),
    ("castilla y león", "Castilla y León"),
    ("castilla - la mancha", "Castilla-La Mancha"),
    ("castilla-la mancha", "Castilla-La Mancha"),
    ("cataluña", "Cataluña"),
    ("comunitat valenciana", "C. Valenciana"),
    ("extremadura", "Extremadura"),
    ("galicia", "Galicia"),
    ("madrid", "Madrid"),
    ("murcia", "Murcia"),
    ("navarra", "Navarra"),
    ("país vasco", "País Vasco"),
    ("rioja", "La Rioja"),
    ("ceuta", "Ceuta"),
    ("melilla", "Melilla"),
    ("total nacional", "España"),
    ("nacional", "España"),
]

# Fechas de investidura (inicio efectivo de cada Gobierno)
LEGISLATURES = [
    {"id": "XII", "name": "XII Legislatura (Rajoy II)", "start": "2016-10-29", "end": "2018-06-01"},
    {"id": "XII-S", "name": "XII Legislatura (Sánchez I, moción de censura)", "start": "2018-06-02", "end": "2020-01-07"},
    {"id": "XIV", "name": "XIV Legislatura (Sánchez II, coalición)", "start": "2020-01-08", "end": "2023-11-16"},
    {"id": "XV", "name": "XV Legislatura (Sánchez III)", "start": "2023-11-17", "end": None},
]
XV_START = "2023-11-17"
XIV_START = "2020-01-08"

SPEC_BY_KEY = {s.key: s for s in SERIES}
