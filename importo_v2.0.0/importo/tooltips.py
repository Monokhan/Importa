"""
tooltips.py — Globos de ayuda para todos los campos de la app.

`instalar()` envuelve los widgets de entrada de Streamlit para que, si un campo no trae `help=`,
se le agregue el texto definido aquí según su etiqueta. Así cada dato que el usuario ingresa
tiene explicación sin repetirla en cada llamada.
"""
from __future__ import annotations

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

try:
    from streamlit.delta_generator import main_dg as _MAIN
except ImportError:  # versiones antiguas
    _MAIN = getattr(st, "_main")

HELP: dict[str, str] = {
    # Acceso
    "Correo electrónico": "El correo con el que creaste tu cuenta.",
    "Contraseña": "Mínimo 8 caracteres con letras y números.",
    "Correo electrónico personal": "Será tu usuario. Tus datos quedan asociados solo a este correo.",
    "Tu nombre": "Cómo quieres que te salude la app.",
    "Contraseña (mín. 8, letras y números)": "Usa una frase fácil de recordar para ti y difícil de adivinar.",
    "Repite la contraseña": "Debe coincidir exactamente con la anterior.",
    # Sidebar
    "Dólar manual": "Actívalo si mindicador.cl no responde o quieres simular con otro tipo de cambio.",
    "USD observado (CLP)": "Dólar observado del Banco Central. Se usa para convertir FOB, flete y seguro a pesos.",
    "UF (CLP)": "Unidad de Fomento del día. Referencia para umbrales tributarios.",
    "Kit de empaque por despacho (CLP)": "Caja o bolsa, cinta y etiqueta por cada pedido enviado. Se descuenta del margen de cada venta.",
    "Merma y garantía (%)": "Provisión para productos fallados, devoluciones y garantía legal de 6 meses. Entre 3 % y 5 % es lo habitual.",
    "Lead time fabricación + tránsito (días)": "Días desde que emites la orden al proveedor hasta tener el producto en bodega. Marítimo desde China: 50 a 70.",
    "Tema oscuro": "Cambia los colores de toda la app.",
    "Modo celular": "Una sola columna y letra más grande para usar desde el teléfono.",
    # Costeo
    "Agregar desde el catálogo": "Trae un producto ya guardado con sus medidas y precio FOB.",
    "Origen": "Ciudad o puerto donde el proveedor entrega la carga (Shenzhen, Ningbo, Guangzhou).",
    "Destino": "Puerto o aeropuerto de llegada en Chile (San Antonio, Valparaíso, Santiago aéreo).",
    "Flete internacional total (USD)": "Lo que cobra el forwarder por mover todo el lote. Pide 2 o 3 cotizaciones.",
    "Recargo DG si hay baterías (%)": "Sobreprecio del flete por carga peligrosa (baterías de litio, IMO clase 9). Suele ser 25 % a 40 %.",
    "Seguro contratado (USD, 0 = presunto 2 %)": "Si no contratas seguro, Aduanas presume un 2 % del FOB para calcular el CIF.",
    "Forwarder / naviera": "Empresa que transporta la carga. Sirve para identificar el embarque.",
    "Inspección pre-embarque PSI (USD)": "Inspección de calidad en la fábrica antes de embarcar. Recomendada: US$150 a 250. Evita pagar el saldo por un lote defectuoso.",
    "Incoterm 2020": "Qué incluye el precio del proveedor: EXW solo fábrica, FOB puesto a bordo, CIF con flete y seguro, DDP con impuestos pagados.",
    "Costos en origen EXW (USD)": "Transporte interno en China y despacho de exportación cuando compras EXW.",
    "Dólar aduanero de la DIN (0 = usar observado)": "Aduanas liquida con su propio tipo de cambio para la fecha de la DIN. Déjalo en 0 para usar el dólar observado.",
    "Desconsolidación / puerto (CLP)": "Cobro del almacén extraportuario por desarmar el contenedor y entregar tu carga. Pide la tarifa al forwarder.",
    "Almacenaje extraportuario (CLP)": "Costo de bodega en puerto durante los días libres o los que excedas.",
    "Transporte a bodega (CLP)": "Camión desde el puerto hasta tu bodega o casa.",
    "Otros gastos (CLP)": "Cualquier otro cobro local: gastos de agente, sellos, revisiones.",
    "Tarifa base agente de aduana (USD)": "Mínimo que cobra el agente por tramitar la DIN. Sobre US$3.000 CIF suele ser un porcentaje.",
    "Usar agente aunque CIF ≤ US$3.000": "Márcalo si prefieres que un agente haga el trámite aunque el monto no lo obligue.",
    "Prorrateo de costos comunes": "Cómo repartir flete, agente y gastos locales entre los productos del embarque. Por m³ es lo más justo en marítimo; por peso en aéreo; por FOB es lo que suelen usar los contadores.",
    "Fecha estimada de arribo (ETA)": "Cuándo llega la carga a Chile. Desde ese día corren los días libres del almacén.",
    "Días libres de almacenaje": "Días sin cobro en el extraportuario después del arribo, según tu naviera o forwarder. Normalmente 5 o 7.",
    "Guardar productos nuevos en el catálogo": "Los productos que no venían del catálogo se guardan para reutilizarlos.",
    "% anticipo": "Porcentaje del FOB que pagas al confirmar la orden. Lo habitual es 30 %.",
    "Dólar al pagar el anticipo": "Tipo de cambio del día en que hiciste la transferencia del anticipo.",
    "Dólar al pagar el saldo": "Tipo de cambio del día en que pagaste el 70 % restante.",
    "FOB declarado (USD)": "Copia el valor FOB que aparece en la DIN de tu agente.",
    "Flete declarado (USD)": "Copia el flete que aparece en la DIN.",
    "Seguro declarado (USD)": "Copia el seguro que aparece en la DIN.",
    "CIF declarado (USD)": "Copia el valor CIF de la DIN.",
    "Ad-valorem declarado (USD)": "Copia el arancel de la DIN.",
    "IVA declarado (USD)": "Copia el IVA de la DIN.",
    # Catálogo
    "Producto": "Nombre comercial con el que reconocerás el producto.",
    "Nombre": "Nombre comercial del producto.",
    "Partida arancelaria (HS)": "Código de 6 a 8 dígitos que clasifica el producto en Aduanas (ej. 8507.60 baterías). Pídelo a tu agente o al proveedor.",
    "Categoría normativa": "Define qué certificaciones exige Chile (SEC, SUBTEL, ISP).",
    "Proveedor": "Fábrica o vendedor. Solo el nombre comercial.",
    "FOB unitario (USD)": "Precio por unidad puesto a bordo en origen, según la cotización del proveedor.",
    "Unidades por caja máster": "Cuántas unidades vienen en cada caja grande de embarque.",
    "Peso por caja (kg)": "Peso bruto de la caja máster con producto.",
    "Certificado de origen TLC (0 %)": "Con Certificado de Origen (Form F en China) el arancel es 0 %. Sin él, 6 %.",
    "Largo caja (cm)": "Medida exterior de la caja máster.",
    "Ancho caja (cm)": "Medida exterior de la caja máster.",
    "Alto caja (cm)": "Medida exterior de la caja máster.",
    "Carga peligrosa (baterías de litio)": "Productos con baterías de litio viajan como carga peligrosa: flete con recargo y documentos extra.",
    "Notas (requisitos, certificaciones, contacto)": "Cualquier dato útil: contacto del proveedor, certificados que ya tienes, MOQ.",
    "Eliminar del catálogo": "Borra la ficha del producto. No afecta a embarques ya registrados.",
    # Precios
    "Producto a costear": "Elige de qué producto calcular precios: de la cotización actual, del inventario o un costo manual.",
    "Landed cost unitario (CLP, sin IVA)": "Costo total por unidad puesta en bodega, sin IVA.",
    "Comisión de categoría (%)": "Lo que cobra Mercado Libre por venta según categoría y tipo de publicación. Revísalo en tu cuenta de vendedor.",
    "Bonificación Mercado Envíos Flex": "Si despachas tú mismo el mismo día, Mercado Libre bonifica parte del envío.",
    "Mix ML (%)": "Qué porcentaje de tus ventas esperas por Mercado Libre. Los tres canales deben sumar 100 %.",
    "Precio ML (CLP c/IVA)": "Precio final que ve el cliente en Mercado Libre. Desde $19.990 el envío gratis es obligatorio y lo pagas tú.",
    "Product Ads ML (% de la venta)": "Inversión en publicidad dentro de Mercado Libre como porcentaje de la venta (ACOS). Típico: 5 % a 15 %.",
    "Flete plano que asumes (CLP, 0 = paga el cliente)": "Si ofreces envío gratis en tu tienda, cuánto te cuesta cada despacho.",
    "Mix web (%)": "Porcentaje de ventas esperado por tu tienda propia o Instagram.",
    "Precio web (CLP c/IVA)": "Precio final en tu tienda. Suele ser algo menor que en Mercado Libre porque no pagas comisión.",
    "Meta / Google Ads (% de la venta)": "Publicidad en Instagram, Facebook o Google como porcentaje de la venta. 15 % equivale a un ROAS de 6,7.",
    "Costo fijo por venta web (CLP)": "Alternativa al porcentaje: cuánto te cuesta en publicidad conseguir un pedido (CAC).",
    "Mix B2B (%)": "Porcentaje de ventas a mayoristas o tiendas.",
    "Precio B2B (CLP c/IVA)": "Precio a mayoristas. Menor margen por unidad, pero volumen y sin comisión.",
    "Prospección B2B (% de la venta)": "Costo de conseguir clientes mayoristas (muestras, visitas, comisiones de vendedor).",
    "Costos fijos mensuales netos (CLP)": "Arriendo, sueldos, software, contador: lo que pagas aunque no vendas. Viene de los gastos recurrentes.",
    "Capital disponible (CLP)": "Plata que puedes invertir en la primera orden sin comprometer tu vida personal.",
    "Múltiplo objetivo sobre el capital": "2,5 significa recuperar el capital y ganar 1,5 veces más. Es una meta razonable para importación.",
    "Venta diaria estimada (unidades)": "Cuántas unidades crees que venderás por día en promedio.",
    "Días de retención de la pasarela": "Mercado Pago retiene el dinero hasta 14 días; Transbank 1 a 3 días hábiles.",
    "Buscar producto similar": "Palabras con las que un cliente buscaría tu producto en Mercado Libre.",
    "Access token de Mercado Libre (opcional)": "Si la búsqueda pública falla, crea una app gratis en developers.mercadolibre.cl y pega el token.",
    "Precios separados por coma": "Escribe los precios de la competencia que veas en Mercado Libre para calcular mínimo, mediana y máximo.",
    # Operación
    "Tarifa de sobrestadía estimada (USD por día)": "Lo que cobra el almacén o naviera por cada día después de los días libres. Pregunta al forwarder.",
    "Estado": "En Tránsito: viajando · En Aduana: llegó y está en el extraportuario · En Bodega: ya lo retiraste.",
    "ETA": "Fecha estimada de arribo. Corrígela si la naviera la cambia.",
    "Días libres": "Días sin cobro de almacenaje después del arribo.",
    "Confirmo": "Marca para habilitar el borrado. Es definitivo.",
    "Venta diaria (u)": "Unidades vendidas por día en promedio.",
    "Cobro neto por unidad (CLP)": "Lo que llega a tu cuenta por unidad tras comisiones y flete.",
    "Costo de la orden #2 (CLP con IVA)": "Cuánto necesitas juntar para la siguiente compra al proveedor.",
    "Retención pasarela (días)": "Días que la pasarela retiene tus cobros antes de depositarlos.",
    # Ventas
    "Cantidad": "Unidades vendidas en esta operación.",
    "Fecha": "Fecha de la venta o del gasto (la de la boleta o factura).",
    "Canal": "Por dónde se vendió: Mercado Libre, tu tienda web o venta directa a empresas.",
    "Precio unitario (CLP c/IVA)": "Precio final cobrado por unidad, con IVA incluido.",
    "Medio de pago": "Define cuántos días tarda el dinero en llegar a tu cuenta.",
    "Documento tributario": "Boleta para personas; factura para empresas que quieran usar el IVA. Ambas se emiten en sii.cl y generan débito fiscal.",
    "Folio del documento (opcional)": "Número de la boleta o factura electrónica, para el libro de ventas.",
    "Venta retenida": "Ventas cuyo dinero aún no ha sido depositado por la pasarela.",
    # Gastos
    "Categoría": "Agrupa el gasto para tu punto de equilibrio y para el contador.",
    "Descripción": "Qué compraste o pagaste.",
    "Documento": "Solo la factura da derecho a crédito fiscal de IVA. Boletas y gastos sin documento no.",
    "Folio": "Número de la factura o boleta.",
    "Total pagado (CLP, con IVA si aplica)": "Monto total que salió de tu cuenta.",
    "Incluye IVA 19 %": "Desmárcalo para gastos exentos (honorarios, arriendo de persona natural, seguros).",
    "Es un costo fijo mensual (recurrente)": "Arriendo, sueldos, software: se repite cada mes y alimenta el punto de equilibrio.",
    "Gasto": "Elige el gasto que quieres eliminar.",
    "Período": "Mes del F29 que quieres revisar.",
    "Régimen tributario": "Régimen elegido en el SII. Define la tasa de PPM. Puedes cambiarlo cada año antes del 30 de abril.",
    # Cuenta y privacidad
    "Contraseña actual": "Necesaria para confirmar que eres tú.",
    "Nueva contraseña": "Mínimo 8 caracteres con letras y números.",
    "Repite la nueva": "Debe coincidir con la nueva contraseña.",
    "Usuario": "Cuenta sobre la que quieres actuar.",
    "Derecho": "Acceso: saber qué datos hay · Rectificación: corregir · Supresión: borrar · Oposición: que no se use · Portabilidad: llevártelos · Bloqueo: suspender mientras se resuelve.",
    "Describe tu solicitud": "Explica qué necesitas; el responsable debe responder en el plazo legal.",
    "Escribe tu correo para confirmar": "Escríbelo exactamente igual para evitar borrados por error.",
    "Tu contraseña": "Confirma tu identidad antes de eliminar la cuenta.",
    "Buscar término": "Escribe una palabra; se filtran los términos y sus definiciones.",
    # Cumplimiento
    "Nombre o razón social del responsable": "Nombre legal de tu empresa tal como aparece en el SII.",
    "RUT": "RUT de la empresa.",
    "Domicilio": "Dirección comercial registrada.",
    "Correo para ejercer derechos": "Correo donde los titulares pueden pedir acceso, rectificación o supresión.",
    "Delegado de protección de datos (si lo hay)": "Persona encargada de datos personales. No es obligatorio para una pyme pequeña.",
    "Meses de inactividad antes de eliminar cuentas": "Plazo de conservación declarado en la política. 24 meses es un valor razonable.",
    "Fecha y hora de detección (AAAA-MM-DD HH:MM)": "Desde este momento corren las 72 horas para notificar a la Agencia.",
    "Qué ocurrió": "Descripción de la vulneración: acceso no autorizado, pérdida de respaldo, filtración, etc.",
    "Datos afectados (categorías)": "Correos, nombres, historial de compras, etc.",
    "Titulares afectados (aprox.)": "Cuántas personas podrían verse afectadas.",
    "Riesgo para los titulares": "Alto si podrían sufrir fraude, suplantación o daño; entonces también hay que avisarles a ellos.",
    "Medidas adoptadas": "Qué hiciste para contener la brecha: cambio de claves, bloqueo, restauración.",
    "Cuenta a eliminar": "Cuenta inactiva más allá del plazo de retención.",
    "Respuesta": "Texto que verá el titular como respuesta a su solicitud.",
    "Resolver": "Atendida si cumpliste lo pedido; Rechazada si no procede (explica por qué en la respuesta).",
}

_WIDGETS = ("number_input", "text_input", "text_area", "selectbox", "multiselect", "checkbox", "toggle", "slider", "date_input", "radio")


def instalar() -> None:
    """Envuelve los widgets para inyectar `help` desde HELP cuando la llamada no lo trae."""
    if getattr(DeltaGenerator, "_tooltips_instalados", False):
        return
    for nombre in _WIDGETS:
        original = getattr(DeltaGenerator, nombre)

        def envoltura(self, label, *args, _orig=original, **kwargs):
            if kwargs.get("help") is None and isinstance(label, str):
                texto = HELP.get(label.strip())
                if texto:
                    kwargs["help"] = texto
            return _orig(self, label, *args, **kwargs)

        setattr(DeltaGenerator, nombre, envoltura)
        # `st.number_input` es un método ya ligado al contenedor principal: se re-liga a la envoltura
        setattr(st, nombre, (lambda _n: (lambda *a, **k: getattr(DeltaGenerator, _n)(_MAIN, *a, **k)))(nombre))
    DeltaGenerator._tooltips_instalados = True
