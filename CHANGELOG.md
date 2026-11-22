# Historial de versiones

## 2.1.0 — 2026-09-25 · Importa
- Nueva marca: **Importa**, con el lema «Tu negocio importa». Pantalla de acceso, barra lateral, título de pestaña, PDF, política de privacidad y archivos descargados.
- El módulo del menú que se llamaba «Importa» pasa a llamarse **Abastece**, para no confundirse con la marca.
- Compatibilidad: la app sigue usando `importo.db` o `chileimport.db` si no existe `importa.db`, y acepta `IMPORTO_PEPPER` y `CHILEIMPORT_PEPPER` además de `IMPORTA_PEPPER`. Nadie pierde datos ni acceso.
- Redacción: se eliminaron todos los «(s)» de los textos visibles (por ejemplo, «sin embarques activos», «1 día libre», «3 cotizaciones actualizadas»).
- Redacción: la misión del día ya no dice «Completaste…» para algo pendiente.
- Redacción: el mensaje de Target 2.5x decía «retorno $2.5× el capital»; ahora dice «recuperas 2,5 veces tu capital», con decimales en formato chileno.
- Los gráficos sin título ya no muestran la palabra «undefined».

## 2.0.0 — 2026-09-19 · la app pasa a llamarse **Importo**
- Nueva identidad: isotipo propio (flecha que entra y se detiene sobre la línea de la bodega) en la pantalla de acceso, la barra lateral, el favicon y el ícono de aplicación; encabezado del PDF y títulos actualizados.
- Variables de entorno `IMPORTO_PEPPER` e `IMPORTO_DB`, con los nombres antiguos aceptados. Si existe `chileimport.db` y no hay `importo.db`, se sigue usando la base anterior: nadie pierde datos ni acceso.
- Seguridad: datos escritos por el usuario ahora se escapan antes de renderizarse (evita inyección de HTML hacia otro usuario o el administrador).
- Seguridad: la capa de datos exige rol de administrador y propiedad de la cuenta, no solo la interfaz.
- Seguridad: la sesión se revalida contra la base en cada interacción; una cuenta desactivada o eliminada pierde el acceso al instante.
- Seguridad: lista blanca de columnas al actualizar incidentes, contraseñas frecuentes rechazadas, contenedor sin root, cabeceras HSTS y anti-clickjacking en Caddy, límite de subida a 5 MB.
- Seguridad: el descuento de stock filtra por dueño también en la escritura, no solo en la lectura previa.
- Política de privacidad v2026-09-19: nombra el servicio y la ley que cumple (19.628 modificada por la 21.719) y cita a la Agencia. Al ser una versión nueva, la app pide aceptarla al entrar.

## 1.5.0 — 2026-09-14
- Menú lateral reorganizado en 5 módulos temáticos plegables (Aprende, Formaliza, Importa, Vende, Administra) más Tu cuenta; el módulo de la página actual se abre solo y ninguno se bloquea.
- Tarjeta del jugador en la barra lateral: anillo de progreso, nivel y racha de días con actividad.
- Misión del día: una sola acción recomendada, visible en Empieza aquí, Panel de hoy y Mi recorrido.
- "Mi recorrido" rediseñado como mapa de niveles: camino encadenado por módulo, meta final, muro de 14 medallas y detalle plegable por módulo.
- Contador de racha calculado desde ventas y gastos registrados.

## 1.4.1 — 2026-09-14
- Corregido un f-string con comillas anidadas que impedía abrir la app en Python 3.10 y 3.11 (solo funcionaba en 3.12+).
- Revisado todo el código con un escáner de tokens para asegurar compatibilidad desde Python 3.10.

## 1.4.0 — 2026-09-14
- Nueva sección "Cotiza tu flete": guarda cotizaciones de marítimo LCL, FCL 20' y 40', aéreo y courier; compara costo por unidad, días de tránsito, CIF, arancel e IVA de cada una; edición y eliminación en línea; copia los valores elegidos al costeo con un clic.
- Motor de comparación con la regla de cobro de cada medio (W/M en LCL, contenedores en FCL, peso volumétrico en aéreo y courier) y avisos: contenedor subutilizado, cobro por volumétrico, courier sin agente bajo US$3.000.
- Nueva sección "Mi recorrido": 14 hitos verificados contra datos reales, agrupados por etapa, con niveles de Novato a Experto, celebración al desbloquear y barra de progreso en la barra lateral.
- Corrección de CSS que pintaba de blanco las etiquetas e íconos de ayuda de la barra lateral.

## 1.3.0 — 2026-09-14
- Menú lateral reordenado como un camino: Empieza aquí y Etapas 0 a 5 (aprende, formaliza, costea, importa, vende, administra) más Tu cuenta.
- Nueva página "Empieza aquí": siguiente paso concreto, avance del plan y mapa de las seis etapas.
- Cada página muestra a qué etapa pertenece y un desplegable "¿Para qué sirve esta sección y cómo se usa?".
- Globos de ayuda en todos los campos de ingreso de datos (60 nuevos): qué significa el dato y de dónde sacarlo.

## 1.2.0 — 2026-09-13
- Guía del emprendedor: plan por etapas con avance guardado, comparación de sociedades (SpA recomendada), regímenes tributarios 2026 (Ley 21.755), canales de pago y plataformas de venta.
- Glosario con buscador (45 términos de importación, tributarios y e-commerce).
- Salud de tu empresa: puntaje 0–100 en seis dimensiones (liquidez, rentabilidad, ventas, tributario, operación, cumplimiento) con una acción por dimensión.
- Régimen tributario configurable; PPM por defecto corregido a 0,125 % (Pro Pyme General 2026) en vez de 1 %.
- Entrada de datos fluida: parámetros de la barra lateral y catálogo se guardan solos; ETA y días libres editables en línea; avisos toast al registrar ventas y gastos.

## 1.1.0 — 2026-09-13
- Guardado automático del costeo y del pricing por usuario (sobrevive recargas y cierres de sesión).
- Eliminación de cotizaciones/embarques con borrado en cascada (líneas, inventario, ventas, asientos F29) y auditoría.
- Publicidad en el pricing: % de la venta o CAC fijo por canal (IVA recuperable), ROAS mínimo, columna Publicidad.
- Gastos y compras nacionales con crédito fiscal; costos fijos recurrentes → punto de equilibrio mensual.
- F29 mensual con remanente arrastrado, PPM configurable y códigos de referencia; libros de ventas y compras en CSV.
- Ventas con documento (boleta/factura) y folio. Dólar aduanero de la DIN separado del observado.
- Checklist Ley del Consumidor (garantía legal 6 meses, retracto 10 días, precio con IVA, T&C).
- Política de privacidad v2026-09-13 y RAT actualizados (proveedores en libros).

## 1.0.0 — 2026-09-13 (versión definitiva)
- Autenticación por correo personal con PBKDF2-SHA256, bloqueo por intentos y expiración de sesión.
- Aislamiento de datos por usuario en todas las tablas; administrador y gestión de cuentas.
- Cumplimiento Ley 19.628 / 21.719: consentimiento versionado, seis derechos del titular, RAT, brechas con reloj de 72 h, retención, bitácora exportable.
- Cotización de embarques multiproducto con prorrateo de costos comunes (m³, peso o FOB) y catálogo de productos.
- Nuevo sistema de diseño: navegación lateral, tema claro/oscuro, modo celular, tipografía Manrope + IBM Plex Mono.
- Docker + Caddy (HTTPS automático), scripts de arranque y respaldo.

## 0.3 — seguridad y cuentas · 0.2 — rediseño y multiproducto · 0.1 — versión inicial
