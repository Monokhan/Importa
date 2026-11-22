"""
guide.py — Guía del emprendedor: de cero a vender con éxito en e-commerce (Chile).

Contenido estático, verificado a septiembre de 2026. Tasas y comisiones cambian: la app las marca como
referenciales. No sustituye la asesoría de un contador o abogado.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Regímenes tributarios (vigentes 2026)
# ---------------------------------------------------------------------------

REGIMENES = {
    "Pro Pyme Transparente (14 D N°8)": {"idpc": 0.0, "ppm": 0.002, "ppm_alto": 0.005, "resumen": "La empresa no paga impuesto de Primera Categoría; los dueños tributan por la utilidad en su Global Complementario (tramo exento hasta 13,5 UTA). Contabilidad simplificada. Ideal si retiras casi toda la utilidad y tus ingresos personales son bajos o medios."},
    "Pro Pyme General (14 D N°3)": {"idpc": 0.125, "ppm": 0.00125, "ppm_alto": 0.0025, "resumen": "Impuesto de Primera Categoría 12,5 % por 2025–2027 (Ley 21.755; 15 % en 2028, 25 % después). PPM rebajado a 0,125 %. Los dueños tributan solo por lo que retiran, con el impuesto de la empresa como crédito. Ideal si reinviertes las utilidades para crecer."},
    "Semi Integrado (14 A)": {"idpc": 0.27, "ppm": 0.01, "ppm_alto": 0.01, "resumen": "27 % de Primera Categoría, contabilidad completa, PPM 1 % el primer año. Obligatorio sobre 75.000 UF de ingresos promedio. No conviene a una pyme que puede acogerse a 14 D."},
}
REGIMEN_DEFAULT = "Pro Pyme General (14 D N°3)"

# ---------------------------------------------------------------------------
# Tipo de sociedad
# ---------------------------------------------------------------------------

SOCIEDADES = [
    {"tipo": "SpA (Sociedad por Acciones)", "socios": "1 o más", "responsabilidad": "Limitada al capital aportado", "constitucion": "Gratis y en el día en tuempresaenundia.cl (con firma electrónica avanzada) o ante notario", "cuando": "**Recomendada** para importar y vender online: protege tu patrimonio personal, permite sumar socios o inversionistas emitiendo acciones, y los bancos y marketplaces la aceptan sin trabas.", "contras": "Debes llevar contabilidad (simplificada en Pro Pyme) y presentar F22 anual aunque no tengas utilidad."},
    {"tipo": "EIRL", "socios": "Solo 1 (persona natural)", "responsabilidad": "Limitada", "constitucion": "Gratis en tuempresaenundia.cl", "cuando": "Si tienes claro que nunca tendrás socios. Giro único declarado.", "contras": "No puedes incorporar socios ni vender participación; para crecer tendrías que transformarla en SpA."},
    {"tipo": "Sociedad Ltda.", "socios": "2 a 50", "responsabilidad": "Limitada", "constitucion": "Gratis en tuempresaenundia.cl", "cuando": "Dos socios que se conocen bien y no planean traer inversionistas.", "contras": "Cualquier cambio de socios o capital exige modificar la escritura con acuerdo unánime."},
    {"tipo": "Persona natural con giro", "socios": "Solo tú", "responsabilidad": "**Ilimitada**: responde todo tu patrimonio (auto, casa, ahorros)", "constitucion": "Inicio de actividades en sii.cl en minutos", "cuando": "Para probar un producto con menos de ~$2 millones antes de formalizar.", "contras": "Mezcla tus finanzas personales con las del negocio; una deuda o un reclamo del SII te alcanza a ti. Mercado Libre y bancos te tratan como persona, con menos herramientas."},
]

# ---------------------------------------------------------------------------
# Plan por etapas
# ---------------------------------------------------------------------------

ETAPAS: list[dict] = [
    {"n": 0, "titulo": "Validar la idea antes de gastar", "dias": "Semana 1–2", "tareas": [
        "Elegir 1–3 productos con margen: landed cost × 2,5 debe caber bajo el precio de mercado (usa Costeo y el benchmark de Mercado Libre).",
        "Revisar en Requisitos Chile si el producto exige SEC, SUBTEL, ISP o certificaciones: eso define costo y tiempo.",
        "Pedir cotizaciones FOB a 3 proveedores (Alibaba, 1688 con agente, ferias) y una muestra pagada por courier.",
        "Definir el capital inicial y correr la calculadora Target 2.5x: cuántas unidades y a qué precio.",
    ]},
    {"n": 1, "titulo": "Constituir la empresa y activarla en el SII", "dias": "Semana 2–3", "tareas": [
        "Crear una SpA en tuempresaenundia.cl (gratis; necesitas ClaveÚnica y, para no ir al notario, firma electrónica avanzada).",
        "Obtener el RUT de la empresa y hacer Inicio de Actividades en sii.cl con giros: 479100 (venta al por menor por internet) y 469000 (venta al por mayor).",
        "Elegir el régimen tributario al iniciar actividades (Pro Pyme General o Transparente; puedes cambiarlo cada año antes del 30 de abril).",
        "Solicitar patente comercial en la municipalidad donde estará la bodega u oficina (puede ser tu casa si el municipio lo permite).",
        "Abrir cuenta corriente o cuenta empresa (Banco Estado, Santander, BCI, Mercado Pago o Tenpo Empresas) y una cuenta de comercio exterior para pagar en dólares.",
        "Activar boleta y factura electrónica gratis en el sistema de facturación del SII (o Nubox, Bsale, Defontana si quieres integración con tienda).",
    ]},
    {"n": 2, "titulo": "Preparar la importación", "dias": "Semana 3–5", "tareas": [
        "Negociar precio FOB, MOQ, tiempo de producción y forma de pago 30/70 (anticipo y saldo contra B/L o inspección aprobada).",
        "Pedir Certificado de Origen (Form F para China) para pagar 0 % de arancel en vez de 6 %.",
        "Cotizar flete con 2–3 forwarders (LCL marítimo suele ser lo más barato sobre 1 m³; aéreo bajo 100 kg urgentes). Declarar baterías de litio como DG.",
        "Sobre US$1.000 FOB necesitas agente de aduana: contrátalo antes del embarque y entrégale el mandato. Bajo ese monto puedes despachar tú mismo (DIPS). Los courier tramitan envíos simplificados hasta US$3.000 FOB.",
        "Registrar el embarque en la app con la ETA y los días libres del extraportuario.",
    ]},
    {"n": 3, "titulo": "Fabricación, inspección y embarque", "dias": "Semana 5–9", "tareas": [
        "Pagar el anticipo (30 %) y registrar el dólar de ese día en el modo profesional.",
        "Contratar inspección pre-embarque (PSI, US$150–250) y aprobar el checklist AQL antes de liberar el saldo.",
        "Exigir Commercial Invoice, Packing List, B/L o AWB y Certificado de Origen con los datos exactos de tu SpA.",
        "Pagar el saldo (70 %) y enviar los documentos al agente de aduana.",
    ]},
    {"n": 4, "titulo": "Internación en Chile", "dias": "Semana 9–12", "tareas": [
        "El agente presenta la DIN; revisa con la auditoría DIN de la app que FOB, flete, seguro y CIF coincidan.",
        "Pagar derechos e IVA (el IVA es crédito fiscal: vuelve en tu F29).",
        "Retirar del extraportuario antes de que venzan los días libres: la sobrestadía se cobra en dólares por día.",
        "Marcar el embarque como retirado; el inventario queda listo para vender.",
    ]},
    {"n": 5, "titulo": "Vender", "dias": "Desde la semana 12", "tareas": [
        "Publicar en Mercado Libre (el canal que más vende en Chile) con fotos propias, título con palabras clave y precio bajo o sobre $19.990 según tu estrategia de envío.",
        "Abrir tienda propia (Jumpseller o Shopify) con Webpay Plus y Mercado Pago; sumar Instagram Shopping y WhatsApp Business.",
        "Cumplir la Ley del Consumidor: precio con IVA, garantía legal de 6 meses, retracto de 10 días, términos y condiciones y datos de la empresa visibles.",
        "Emitir boleta o factura electrónica por cada venta y registrarla en la app (alimenta caja, stock y F29).",
        "Invertir en publicidad con ROAS objetivo (la app te muestra el mínimo para no perder) y medir CAC por canal.",
    ]},
    {"n": 6, "titulo": "Operar en régimen", "dias": "Cada mes", "tareas": [
        "Declarar y pagar el F29 hasta el día 20 (día 12 si no declaras por internet). La app te arma débito, crédito, remanente y PPM.",
        "Registrar todos los gastos con factura para recuperar su IVA y controlar el punto de equilibrio.",
        "Vigilar la cobertura de stock: emitir la orden #2 cuando la app lo indique, financiada con los cobros liberados (cash-to-cash).",
        "Presentar la Declaración de Renta (F22) en abril y revisar si conviene cambiar de régimen antes del 30 de abril.",
        "Cumplir la Ley de Protección de Datos (vigente desde el 1 de diciembre de 2026): política publicada, responsable definido, derechos atendidos.",
    ]},
]

# ---------------------------------------------------------------------------
# Canales de pago y plataformas de venta
# ---------------------------------------------------------------------------

PAGOS = [
    {"canal": "Transbank Webpay Plus", "tipo": "Tarjetas débito/crédito", "comision": "~1,5 % + IVA débito · ~2,95 % + IVA crédito (varía por rubro)", "liquidacion": "1–3 días hábiles", "para": "Tienda propia. El más conocido y confiable para el cliente chileno. Requiere empresa con RUT."},
    {"canal": "Mercado Pago Checkout", "tipo": "Tarjetas, saldo MP, cuotas", "comision": "~3,5 % + IVA (menos si liquidas a 14 días)", "liquidacion": "Inmediata a 14 días según tarifa", "para": "Tienda propia e Instagram; obligatorio dentro de Mercado Libre. Fácil de activar, cuotas sin interés promocionales."},
    {"canal": "Flow", "tipo": "Agregador (Webpay, MACH, Onepay, transferencia)", "comision": "~3,2 % + IVA", "liquidacion": "2–3 días hábiles", "para": "Cuando quieres varios medios de pago con una sola integración y links de pago por WhatsApp."},
    {"canal": "Khipu / Fintoc", "tipo": "Transferencia bancaria simplificada", "comision": "~1 % + IVA o tarifa fija baja", "liquidacion": "Inmediata", "para": "Ventas B2B y tickets altos: la comisión más baja del mercado. El cliente paga desde su banco sin tarjeta."},
    {"canal": "Getnet (Santander) / Kushki", "tipo": "Tarjetas", "comision": "~2,5–3 % + IVA", "liquidacion": "1–2 días hábiles", "para": "Alternativas a Transbank con mejor tarifa para volúmenes medios; Getnet también da POS físico."},
    {"canal": "Transferencia directa", "tipo": "Banco a banco", "comision": "0 %", "liquidacion": "Inmediata", "para": "Mayoristas y clientes recurrentes. Emite igual la boleta/factura; registra la venta con 0 días de retención."},
]

PLATAFORMAS = [
    {"plataforma": "Mercado Libre", "tipo": "Marketplace", "costo": "13–19 % por venta según categoría y exposición; envío gratis obligatorio desde $19.990", "para": "Primer canal para partir: tráfico ya existe. Usa Full (bodega ML) cuando tengas rotación probada."},
    {"plataforma": "Falabella / Paris / Ripley Marketplace", "tipo": "Marketplace", "costo": "12–20 % por venta + logística", "para": "Segundo escalón: marca respaldada por retail. Exigen boleta electrónica, ficha completa y SLA de despacho."},
    {"plataforma": "Jumpseller", "tipo": "Tienda propia (chilena)", "costo": "Plan mensual en CLP + comisión de la pasarela", "para": "Tienda propia integrada con Webpay, boleta electrónica y Chilexpress/Starken sin programar."},
    {"plataforma": "Shopify", "tipo": "Tienda propia", "costo": "Plan mensual en USD + pasarela", "para": "Mayor ecosistema de apps y diseño; conviene si vendes también fuera de Chile."},
    {"plataforma": "WooCommerce (WordPress)", "tipo": "Tienda propia", "costo": "Gratis + hosting (~$5.000–15.000/mes)", "para": "Máximo control y costo bajo si tú o alguien maneja WordPress."},
    {"plataforma": "Instagram Shopping + WhatsApp Business", "tipo": "Social commerce", "costo": "Gratis; publicidad Meta Ads opcional", "para": "Catálogo y cierre por mensaje. Ideal para productos visuales y ventas asistidas."},
    {"plataforma": "Google Merchant Center", "tipo": "Listado gratuito en Google Shopping", "costo": "Gratis (Shopping Ads opcional)", "para": "Aparecer cuando buscan tu producto. Conecta el catálogo de tu tienda propia."},
    {"plataforma": "Ventas B2B directas", "tipo": "Mayorista", "costo": "0 % comisión", "para": "Ferreterías, tiendas de barrio, retail regional: márgenes menores pero volumen y cobro por transferencia."},
]

# ---------------------------------------------------------------------------
# Glosario
# ---------------------------------------------------------------------------

GLOSARIO = {
    "Ad-valorem": "Arancel aduanero general de Chile: 6 % sobre el valor CIF. Baja a 0 % con Certificado de Origen de un país con TLC (China, EE. UU., UE, Corea, etc.).",
    "Agente de aduana": "Profesional autorizado que presenta la DIN ante Aduanas. Obligatorio para importaciones sobre US$1.000 FOB.",
    "AQL": "Acceptable Quality Level: estándar de muestreo para inspeccionar un lote. AQL 2.5 para defectos mayores y 4.0 para menores es lo habitual en productos de consumo.",
    "AWB": "Air Waybill, guía aérea. Documento de transporte para carga aérea; equivale al B/L marítimo.",
    "B/L": "Bill of Lading, conocimiento de embarque. Documento que acredita la carga marítima y su propiedad; sin él no puedes retirar.",
    "Boleta / Factura electrónica": "Documentos tributarios electrónicos obligatorios en Chile. Boleta para consumidores finales; factura para empresas (permite al comprador usar el IVA como crédito).",
    "CAC": "Costo de Adquisición de Cliente: cuánto gastas en publicidad para lograr una venta. CAC = inversión publicitaria ÷ ventas conseguidas.",
    "Cash-to-cash": "Días que pasan desde que pagas al proveedor hasta que recuperas ese dinero en cobros liberados. Define cuándo puedes financiar la siguiente orden sin capital nuevo.",
    "CBM": "Metro cúbico (m³). Unidad de cobro del flete marítimo LCL. Largo × ancho × alto (en metros) × cantidad de cajas.",
    "Certificado de Origen": "Documento emitido en el país exportador (Form F en China) que acredita el origen y permite el arancel preferencial del TLC.",
    "CIF": "Cost, Insurance and Freight: valor FOB + flete + seguro. Es la base sobre la que Aduanas calcula el arancel y el IVA.",
    "Crédito fiscal": "IVA que pagaste en compras con factura y en la importación (DIN). Se descuenta del IVA que cobras en tus ventas en el F29.",
    "Débito fiscal": "IVA contenido en las boletas y facturas que emites. Es el 19 % que le cobras al cliente y debes enterar al SII.",
    "Demurrage / sobrestadía": "Cobro diario (en dólares) por mantener la carga o el contenedor más allá de los días libres en puerto o extraportuario.",
    "DG / IMO Clase 9": "Carga peligrosa. Las baterías de litio viajan como IMO 9 con MSDS y prueba UN38.3; el flete lleva recargo.",
    "DIN": "Declaración de Ingreso: el formulario aduanero con el que se liquidan arancel e IVA de la importación. Su copia sirve para acreditar el crédito fiscal.",
    "DIPS": "Declaración de Importación de Pago Simultáneo: trámite simplificado para importaciones de bajo valor sin agente de aduana.",
    "EXW": "Ex Works: el precio incluye solo la mercadería en la fábrica; tú pagas transporte interno, despacho de exportación, flete y seguro.",
    "F22": "Declaración anual de impuesto a la renta (abril). Ahí se calcula el impuesto de Primera Categoría y se descuentan los PPM pagados.",
    "F29": "Formulario mensual del SII: IVA débito menos crédito, PPM y retenciones. Vence el día 12, o el 20 si declaras y pagas por internet.",
    "Factor de internación": "Landed cost ÷ FOB. Cuántas veces el precio de fábrica termina costando el producto en tu bodega. Sobre 2 conviene revisar flete, cubicaje o arancel.",
    "FOB": "Free On Board: precio del producto puesto a bordo del barco o avión en origen. Es el valor que negocias con el proveedor.",
    "Forwarder": "Agente de carga que contrata el flete internacional, consolida contenedores y coordina con la naviera o aerolínea.",
    "Global Complementario": "Impuesto personal progresivo de los dueños sobre las rentas que retiran (o toda la utilidad en Pro Pyme Transparente). Tramo exento hasta 13,5 UTA anuales.",
    "Incoterms": "Reglas de la Cámara de Comercio Internacional que fijan qué costos y riesgos asume cada parte: EXW, FOB, CIF, DDP, etc.",
    "IVA de importación": "19 % sobre CIF + ad-valorem, pagado al internar. Es crédito fiscal recuperable en el F29 del mismo mes.",
    "Landed cost": "Costo total del producto puesto en tu bodega: FOB + flete + seguro + arancel + agente + gastos locales. Sin IVA, porque el IVA vuelve como crédito.",
    "LCL / FCL": "Less/Full Container Load: carga consolidada con otros importadores (pagas por m³) o contenedor completo.",
    "Lead time": "Días desde que emites la orden hasta que el producto está en tu bodega: producción + tránsito + aduana. Marítimo desde China: 50–70 días.",
    "Margen limpio": "Lo que te queda por unidad después de IVA, comisión del canal, pasarela, flete, publicidad, empaque, merma y costo en bodega.",
    "Mercado Envíos Flex": "Modalidad de Mercado Libre en que tú despachas el mismo día en tu ciudad; ML bonifica parte del envío.",
    "MSDS": "Hoja de datos de seguridad del producto (obligatoria para baterías y químicos). La exige el forwarder para carga DG.",
    "PPM": "Pago Provisional Mensual: anticipo del impuesto a la renta que pagas en el F29 como % de las ventas netas (0,125 % Pro Pyme General en 2026; 0,2 % Transparente).",
    "Pro Pyme": "Regímenes tributarios del artículo 14 D de la Ley de la Renta para empresas con ingresos bajo 75.000 UF: General (N°3) y Transparente (N°8).",
    "PSI": "Pre-Shipment Inspection: inspección de calidad en la fábrica antes de embarcar. Se paga antes de liberar el saldo al proveedor.",
    "Punto de equilibrio": "Unidades que debes vender en un mes para cubrir los costos fijos con el margen limpio. Sobre esa cifra empiezas a ganar.",
    "RAT": "Registro de Actividades de Tratamiento: inventario de qué datos personales tratas, para qué y por cuánto tiempo. Lo exige la Ley 21.719.",
    "Remanente de crédito fiscal": "Crédito de IVA que no alcanzaste a usar en un mes y arrastras al siguiente, reajustado por UTM.",
    "ROAS": "Return On Ad Spend: ventas generadas por cada peso invertido en publicidad. La app calcula el ROAS mínimo para no perder dinero.",
    "Seguro presunto": "Si no acreditas una póliza, Aduanas presume un seguro del 2 % del FOB para calcular el CIF.",
    "SEC": "Superintendencia de Electricidad y Combustibles: exige sello de certificación a productos eléctricos que se conectan a 220 V.",
    "SUBTEL": "Subsecretaría de Telecomunicaciones: homologa equipos que emiten radiofrecuencia (WiFi, Bluetooth, celular).",
    "TLC": "Tratado de Libre Comercio. Chile tiene acuerdos con China, EE. UU., la UE, Corea y otros que rebajan el arancel a 0 % con Certificado de Origen.",
    "UF / UTM / UTA": "Unidades reajustables usadas por la ley: UF (diaria, ~$39.500), UTM (mensual, ~$68.000) y UTA (anual = 12 UTM). Los tramos y umbrales tributarios se fijan en ellas.",
    "W/M": "Weight or Measure: el flete marítimo LCL cobra por lo que sea mayor entre toneladas y metros cúbicos (1 m³ = 1 ton).",
}
