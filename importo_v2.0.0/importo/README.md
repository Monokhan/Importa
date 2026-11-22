# Importo · v2.0.0

**Tu costo real, puesto en bodega.**

Costeo de importaciones, inteligencia tributaria (F29/SII), logística y caja para comerciantes chilenos.
Python + Streamlit + SQLite + Plotly + fpdf2. Sin servicios de pago. Multiusuario, con cuentas por correo y cumplimiento de la Ley 19.628 / 21.719.

---

## Índice
1. [Qué hace](#1-qué-hace)
2. [Requisitos](#2-requisitos)
3. [Correr en tu computador (paso a paso)](#3-correr-en-tu-computador-paso-a-paso)
4. [Subir a GitHub (paso a paso)](#4-subir-a-github-paso-a-paso)
5. [Publicar en internet](#5-publicar-en-internet)
6. [Primer uso](#6-primer-uso)
7. [Seguridad y cuentas](#7-seguridad-y-cuentas)
8. [Protección de datos personales](#8-protección-de-datos-personales-ley-19628--21719)
9. [Capacidad](#9-capacidad)
10. [Estructura del proyecto](#10-estructura-del-proyecto)
11. [Supuestos editables](#11-supuestos-editables)

---

## 1. Qué hace

El menú lateral se agrupa en cinco módulos plegables — **📚 Aprende · 🏛️ Formaliza · 📦 Importa · 🛒 Vende · 📊 Administra** — cada uno con su progreso. Ninguno se bloquea: si ya sabes importar, puedes saltarte pasos. Cada página indica a qué etapa pertenece, trae un desplegable que explica para qué sirve, y cada campo tiene su globo de ayuda.

| Sección | Funcionalidad |
|---|---|
| **Salud de tu empresa** | Puntaje 0–100 en seis dimensiones (liquidez, rentabilidad, ventas, tributario, operación, cumplimiento) con la acción prioritaria del día |
| **Guía del emprendedor** | Plan por etapas de cero a la primera importación con avance guardado · qué sociedad crear (SpA) · regímenes tributarios 2026 y cómo aprovecharlos · canales de pago · dónde vender |
| **Glosario** | 45 términos de importación, tributarios y e-commerce con buscador |
| **Panel de hoy** | Caja disponible vs retenida en pasarelas · semáforo F29 (crédito vs débito fiscal + PPM) · acciones urgentes (días libres, quiebre de stock) · curva de recuperación de la inversión con punto de equilibrio · línea de tiempo del embarque |
| **Costeo e internación** | Embarques con **varios productos**: tabla editable, arancel por producto (TLC 0 % / 6 %), carga peligrosa por línea, **prorrateo** de flete, seguro, agente, PSI y gastos locales por m³ (W/M), peso o FOB · cubicaje y optimizador de espacio · liquidación FOB → CIF → ad-valorem → IVA → agente → landed cost · modo **Guiado** (4 pasos con semáforo de viabilidad) o **Profesional** (Incoterms 2020, pagos 30/70 con doble dólar, auditoría DIN, checklist PSI/AQL) |
| **Mi recorrido** | 14 hitos que se desbloquean con hechos reales (no casillas), agrupados por etapa, con niveles de Novato a Experto |
| **Cotiza tu flete** | Cotizaciones de marítimo LCL/FCL, aéreo y courier guardadas, editables y eliminables; comparación de costo por unidad y días de tránsito; copia al costeo |
| **Catálogo de productos** | Ficha por producto (HS, categoría normativa, caja máster, FOB, proveedor); se reutiliza en cada embarque |
| **Precios y márgenes** | Mercado Libre (comisión, umbral $19.990, flete vendedor, Flex, Product Ads) · web con Webpay 2,9 % + IVA y Meta/Google Ads (% o CAC) · B2B · kit de empaque y merma · ROAS mínimo · **punto de equilibrio mensual** con costos fijos · margen limpio ponderado · **calculadora inversa Target 2.5x** · proyección de caja · benchmark API Mercado Libre |
| **Operación y stock** | Días libres extraportuarios con alerta de sobrestadía · cobertura de stock y fecha máxima de reorden · ciclo cash-to-cash · eliminación de embarques en cascada |
| **Requisitos Chile** | Ley del Consumidor (garantía legal, retracto, precios) · baterías de litio (MSDS, UN38.3, IMO 9, sello SEC), telecom (SUBTEL), cosméticos/alimentos (CDA, Uso y Disposición), documentación base |
| **Ventas y dossier** | Registro de ventas con boleta/factura y folio, retención de pasarela · libro F29 · **dossier ejecutivo PDF** |
| **Gastos y F29** | Gastos y compras con crédito fiscal (facturas), costos fijos recurrentes, **F29 mensual** con remanente y PPM, libros de ventas y compras en CSV para el contador |
| **Mi cuenta / Privacidad** | Perfil, contraseña, descarga de datos, supresión de cuenta, solicitudes de derechos |
| **Cumplimiento (admin)** | Responsable del tratamiento, solicitudes, brechas (72 h), RAT, retención, bitácora, checklist |

---

## 2. Requisitos

- **Python 3.10, 3.11 o 3.12** → [python.org/downloads](https://www.python.org/downloads/) (en Windows marca *Add Python to PATH*).
- **Git** → [git-scm.com](https://git-scm.com/downloads).
- Una cuenta en [github.com](https://github.com).
- Internet la primera vez (instalar dependencias, fuentes y tipo de cambio). Después funciona sin conexión salvo el dólar y el benchmark.

---

## 3. Correr en tu computador (paso a paso)

### Opción A · un solo comando
Descomprime la carpeta y ejecuta:

- **Windows**: doble clic en `run.bat`
- **macOS / Linux**: `./run.sh`

El script crea el entorno virtual, instala dependencias y abre `http://localhost:8501`.

### Opción B · manual

```bash
# 1. Entrar a la carpeta
cd importo

# 2. Crear y activar el entorno virtual
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. (Recomendado) definir el pepper de contraseñas
cp .env.example .env               # edita IMPORTO_PEPPER con una frase larga
export IMPORTO_PEPPER="tu-frase"   # Windows: set IMPORTO_PEPPER=tu-frase

# 5. Ejecutar
streamlit run app.py
```

Se abre el navegador en `http://localhost:8501`. La base `importo.db` se crea sola en la primera ejecución.

**Desde el celular en tu misma red WiFi:** `streamlit run app.py --server.address 0.0.0.0` y entra a `http://IP_DE_TU_PC:8501` (la IP la ves con `ipconfig` / `ifconfig`).

**Detener:** `Ctrl + C` en la terminal.

---

## 4. Subir a GitHub (paso a paso)

### 4.1 Crear el repositorio en GitHub
1. Entra a [github.com/new](https://github.com/new).
2. *Repository name*: `importo`.
3. Elige **Private** (recomendado: la app maneja datos de tu negocio). Puedes hacerlo público después.
4. **No** marques "Add a README" ni ".gitignore" (ya vienen en la carpeta).
5. Clic en **Create repository**. Copia la URL que aparece, por ejemplo `https://github.com/TU_USUARIO/importo.git`.

### 4.2 Subir el código desde tu computador
Abre una terminal dentro de la carpeta `importo` y ejecuta línea por línea:

```bash
# Identifícate ante Git (solo la primera vez en este computador)
git config --global user.name "Tu Nombre"
git config --global user.email "tu@correo.cl"

# Inicializar el repositorio local
git init
git branch -M main

# Agregar todos los archivos (el .gitignore excluye la base de datos, .env y respaldos)
git add .
git commit -m "Importo v2.0.0"

# Conectar con GitHub y subir
git remote add origin https://github.com/TU_USUARIO/importo.git
git push -u origin main
```

GitHub te pedirá autenticarte. Si pide contraseña, usa un **Personal Access Token**: GitHub → *Settings → Developer settings → Personal access tokens → Generate new token (classic)* con permiso `repo`. Pégalo como contraseña.

### 4.3 Verificar
Recarga la página del repositorio: deben verse `app.py`, `README.md`, etc. **No** deben aparecer `importo.db` ni `.env` (si aparecen, bórralos del repo y revisa `.gitignore`).

### 4.4 Guardar cambios futuros
Cada vez que modifiques algo:

```bash
git add .
git commit -m "Describe el cambio"
git push
```

### 4.5 Clonar en otro computador
```bash
git clone https://github.com/TU_USUARIO/importo.git
cd importo
./run.sh          # o run.bat en Windows
```

---

## 5. Publicar en internet

### Opción 1 · Streamlit Community Cloud (gratis, ideal para partir)
1. Ve a [share.streamlit.io](https://share.streamlit.io) e inicia sesión con GitHub.
2. **New app** → elige el repositorio `importo`, rama `main`, archivo `app.py`.
3. En **Advanced settings → Secrets** agrega:
   ```toml
   IMPORTO_PEPPER = "una-frase-larga-y-secreta"
   ```
4. **Deploy**. En 2–3 minutos tendrás una URL `https://…streamlit.app` con HTTPS incluido.

Limitaciones: ~1 GB de RAM (15–25 usuarios activos a la vez) y **la base SQLite se reinicia cuando la app se redepliega o duerme**. Sirve para probar y para uso personal; para datos que no puedes perder usa la opción 2 o descarga respaldos con frecuencia.

### Opción 2 · Servidor propio con Docker y HTTPS automático (producción)
Funciona en cualquier VPS (DigitalOcean, Vultr, Hetzner, AWS Lightsail; desde ~US$6/mes) con Ubuntu y un dominio apuntando a la IP.

```bash
# En el servidor (Ubuntu 22.04+)
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
git clone https://github.com/TU_USUARIO/importo.git
cd importo
cp .env.example .env
nano .env        # completa IMPORTO_PEPPER y DOMINIO=app.tudominio.cl
docker compose up -d --build
```

Caddy obtiene el certificado HTTPS solo. La base queda en el volumen `datos` (persistente entre reinicios).

- Ver logs: `docker compose logs -f app`
- Actualizar: `git pull && docker compose up -d --build`
- Respaldo: `docker compose exec app python -c "import sqlite3;s=sqlite3.connect('/data/importo.db');d=sqlite3.connect('/data/respaldo.db');s.backup(d)"` y luego `docker compose cp app:/data/respaldo.db ./respaldo.db`

Además, en `.streamlit/config.toml` descomenta `allowedHosts = ["app.tudominio.cl"]`.

### Opción 3 · Servidor propio sin Docker
```bash
git clone … && cd importo && ./run.sh
```
y coloca delante nginx o Caddy con HTTPS. Para que sobreviva reinicios, crea un servicio `systemd` que ejecute `.venv/bin/streamlit run app.py --server.port 8501`.

---

## 6. Primer uso

1. Abre la app y ve a **Crear cuenta**. Lee y acepta la Política de Privacidad. **La primera cuenta es la administradora** y hereda los datos de versiones anteriores si los hubiera.
2. Entra a **Cumplimiento (admin)** y reemplaza los datos de ejemplo del responsable (razón social, RUT, domicilio, correo). Aparecen en la política y en el RAT.
3. En la barra lateral revisa el dólar (viene de mindicador.cl) y en **Parámetros** el kit de empaque, merma y lead time.
4. **Costeo e internación** → agrega tus productos → flete y seguro → gastos en Chile → **Registrar embarque**.
5. **Precios y márgenes** para fijar precios por canal; **Ventas y dossier** para registrar ventas y descargar el PDF.
6. Programa el respaldo: `./respaldo.sh` (o el comando Docker) al menos una vez por semana.

---

## 7. Seguridad y cuentas

- Registro con correo personal y contraseña (mín. 8 caracteres, letras y números).
- PBKDF2-HMAC-SHA256 con 600.000 iteraciones, sal por usuario, comparación en tiempo constante, *pepper* opcional `IMPORTO_PEPPER` (si lo defines, guárdalo: sin él nadie podrá entrar).
- Bloqueo de 15 min tras 5 intentos fallidos; mismo mensaje exista o no el correo; sesión expira a las 8 h sin uso.
- Todos los datos llevan `usuario_id`; ninguna consulta cruza cuentas. SQLite en modo WAL con índices.
- El administrador puede desactivar/reactivar cuentas.
- La sesión vive en la pestaña: al recargar la página se vuelve a iniciar sesión.
- **Revalidación continua:** cada interacción comprueba que la cuenta siga existiendo y activa. Si el administrador la desactiva, la sesión abierta se cierra de inmediato.
- **Doble barrera de permisos:** además de ocultar la sección en el menú, la capa de datos vuelve a exigir rol de administrador y propiedad de la cuenta. Un usuario no puede listar cuentas, ver solicitudes ajenas, exportar datos de otro ni eliminar su cuenta aunque manipule el estado de la sesión.
- **Contenido escapado:** todo lo que escribe una persona (productos, proveedores, descripciones, solicitudes) se escapa antes de mostrarse, para que no pueda inyectar HTML en la pantalla de otro usuario o del administrador.
- **Contraseñas débiles rechazadas:** además del largo mínimo, se bloquean las más usadas del mundo y las de poca variedad.
- **Contenedor sin root** y cabeceras HSTS, nosniff, anti-clickjacking y Referrer-Policy en el proxy.

### Al actualizar desde ChileImport ERP Pro
No tienes que hacer nada: si existe `chileimport.db` y aún no hay `importo.db`, la app sigue usando la base antigua y todas las cuentas entran igual. La variable `CHILEIMPORT_PEPPER` se sigue aceptando junto con la nueva `IMPORTO_PEPPER`.

---

## 8. Protección de datos personales (Ley 19.628 / 21.719)

La Ley 21.719 entra en vigencia plena el **1 de diciembre de 2026** y crea la Agencia de Protección de Datos Personales. La app implementa lo que la ley exige de un sistema:

| Exigencia | Implementación |
|---|---|
| Información y consentimiento | Política versionada antes del registro; casilla obligatoria; consentimiento de comunicaciones separado y no premarcado; re-aceptación al cambiar la versión; historial con fecha |
| Acceso y portabilidad | Descarga JSON de todos los datos del titular |
| Rectificación | Edición de perfil y de todos los datos comerciales |
| Supresión | Eliminación total de la cuenta confirmada con correo y contraseña; en la bitácora queda solo un hash |
| Oposición | Retiro del consentimiento a comunicaciones |
| Bloqueo | Solicitud que el admin resuelve suspendiendo la cuenta |
| Plazos | Cada solicitud nace con fecha límite (referencia 30 días) y semáforo |
| RAT | Registro de actividades de tratamiento generado y descargable |
| Brechas | Registro con cuenta regresiva de 72 h, plantilla para la Agencia y aviso a titulares |
| Minimización y retención | Solo correo y nombre; eliminación de cuentas inactivas según la política |
| Responsabilidad demostrable | Bitácora de auditoría exportable en CSV |

**Lo que no resuelve el software**: responsable interno o DPO, contrato de encargo con el hosting, procedimiento escrito de brechas, HTTPS y respaldos. Valida los textos y plazos con un abogado y con los reglamentos de la Agencia. Esta implementación no sustituye asesoría legal.

---

## 9. Capacidad

Medido con datos realistas: ~150 ms de CPU por interacción y ~20 MB de RAM por sesión, más ~200 MB fijos.

| Infraestructura | Usuarios activos simultáneos |
|---|---|
| Streamlit Community Cloud (1 GB) | 15–25 |
| VPS 1 vCPU / 2 GB | 30–50 |
| VPS 2 vCPU / 4 GB | 80–120 |
| VPS 4 vCPU / 8 GB | 150–250 |

Sobre ~200 usuarios activos: varias réplicas con *sticky sessions* y PostgreSQL (todo el SQL está en `database.py`).

---

## 10. Estructura del proyecto

```
app.py                    Interfaz Streamlit: login, 10 secciones, diseño propio
auth.py                   Registro, login, PBKDF2, bloqueo, sesión, auditoría
privacy.py                Política de privacidad, RAT, derechos, brechas 72 h, checklist
guide.py                  Guía del emprendedor, sociedades, regímenes 2026, canales de pago, glosario
health.py                 Puntaje de salud de la empresa
journey.py                Módulos, logros, niveles, racha y misión del día
database.py               SQLite multiusuario: esquema, migraciones, CRUD, transacciones
currency.py               Dólar / UF desde mindicador.cl con caché y fallback
customs_engine.py         Cubicaje W/M, liquidación aduanera, lote multiproducto, Incoterms, DIN
tax_engine.py             IVA crédito/débito, PPM, semáforo F29
operations_engine.py      Demurrage, cobertura de stock, cash-to-cash, flujo de caja
pricing_multichannel.py   ML / Web / B2B, mix, Target 2.5x, viabilidad
market_intel.py           Benchmark Mercado Libre Chile
pdf_report.py             Dossier ejecutivo PDF
assets/                   Isotipo en PNG: favicon, ícono de app (navy) y versiones 256/512
requirements.txt · run.sh · run.bat · respaldo.sh
Dockerfile · docker-compose.yml · Caddyfile · .env.example
.streamlit/config.toml · .gitignore · LICENSE · CHANGELOG.md
```

Todo lo que escribes en Costeo y Precios se **guarda automáticamente** por usuario y reaparece al volver a entrar.

Tablas: `usuarios` · `consentimientos` · `auditoria` · `solicitudes_derechos` · `incidentes` · `config_usuario` · `config_general` · `productos` · `cotizaciones` · `cotizacion_items` · `embarques` · `inventario` · `ventas` · `gastos` · `f29_registro`. Las bases de versiones anteriores se migran solas.

---

## 11. Supuestos editables

| Parámetro | Default | Dónde |
|---|---|---|
| Ad-valorem | 6 % (0 % con certificado TLC) | `customs_engine.py` |
| IVA importación | 19 % sobre CIF + ad-valorem | `customs_engine.py` |
| Seguro presunto | 2 % del FOB | `customs_engine.py` |
| Agente de aduana | Obligatorio si CIF > US$3.000; max(base, % escalonado) | UI |
| Comisión Mercado Libre | 15 % | UI |
| Umbral envío gratis ML / flete vendedor | $19.990 / $3.900 | `pricing_multichannel.py` |
| Webpay Plus | 2,9 % + IVA | `pricing_multichannel.py` |
| Kit de empaque / merma / lead time | $650 / 4 % / 58 días | Barra lateral |
| Régimen tributario / PPM | Pro Pyme General · 0,125 % (2026) | Gastos y F29 |
| Retención Mercado Pago / Transbank | 14 / 2 días | UI |
| Plazo respuesta a derechos / notificación de brechas | 30 días / 72 h | `privacy.py` |

> Tasas, umbrales y comisiones cambian. Verifica con tu agente de aduanas y contador. Herramienta de gestión interna, no sustituye asesoría profesional.

## Licencia
MIT.
