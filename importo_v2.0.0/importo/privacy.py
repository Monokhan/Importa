"""
privacy.py — Cumplimiento de la Ley 19.628 sobre protección de la vida privada, según fue
reformada por la Ley 21.719 (vigencia plena: 1 de diciembre de 2026; fiscaliza la Agencia de
Protección de Datos Personales, APDP).

Este módulo reúne lo que la app puede resolver por software:
- Política de privacidad versionada, generada con los datos del responsable.
- Catálogo de derechos del titular (acceso, rectificación, supresión, oposición, portabilidad, bloqueo).
- Registro de actividades de tratamiento (RAT) generado desde la propia estructura de la app.
- Reloj de 72 horas para notificar brechas de seguridad a la Agencia.
- Lista de verificación de las obligaciones organizacionales que NO se resuelven con código.

Nada de esto sustituye asesoría legal: los plazos y textos deben validarse con un abogado y
con los reglamentos que dicte la Agencia.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any

import database as db

VERSION_POLITICA = "2026-09-19"
PLAZO_RESPUESTA_DIAS = 30  # plazo de referencia para responder solicitudes de derechos (validar con asesoría)
HORAS_NOTIFICACION_BRECHA = 72
RETENCION_INACTIVIDAD_MESES_DEFAULT = 24

DERECHOS = {
    "Acceso": "Saber qué datos personales tuyos se tratan, con qué finalidad y por cuánto tiempo.",
    "Rectificación": "Corregir datos inexactos, incompletos o desactualizados.",
    "Supresión": "Que se eliminen tus datos cuando ya no sean necesarios o retires tu consentimiento.",
    "Oposición": "Oponerte a un tratamiento concreto (por ejemplo, a recibir comunicaciones).",
    "Portabilidad": "Recibir tus datos en un formato estructurado y de uso común para llevarlos a otro servicio.",
    "Bloqueo": "Suspender temporalmente el tratamiento mientras se resuelve una solicitud de rectificación, supresión u oposición.",
}

CAMPOS_RESPONSABLE = {
    "resp_nombre": ("Nombre o razón social del responsable", "Mi Empresa Importadora SpA"),
    "resp_rut": ("RUT", "76.123.456-7"),
    "resp_direccion": ("Domicilio", "Av. Ejemplo 123, Santiago"),
    "resp_email": ("Correo para ejercer derechos", "privacidad@miempresa.cl"),
    "resp_dpo": ("Delegado de protección de datos (si lo hay)", ""),
    "resp_retencion_meses": ("Meses de inactividad antes de eliminar cuentas", str(RETENCION_INACTIVIDAD_MESES_DEFAULT)),
}


def datos_responsable() -> dict[str, str]:
    return {k: db.get_config(k, v[1]) for k, v in CAMPOS_RESPONSABLE.items()}


def hash_email(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Política de privacidad
# ---------------------------------------------------------------------------


def politica_privacidad(r: dict[str, str] | None = None) -> str:
    r = r or datos_responsable()
    dpo = f"\n- Delegado de protección de datos: {r['resp_dpo']}" if r.get("resp_dpo") else ""
    return f"""### Política de Privacidad de Importo · versión {VERSION_POLITICA}

Esta política explica cómo **Importo** trata tus datos personales, conforme a la Ley 19.628 sobre protección de la vida privada, modificada por la Ley 21.719, que rige plenamente desde el 1 de diciembre de 2026 y es fiscalizada por la Agencia de Protección de Datos Personales.

**1. Responsable del tratamiento**
- {r['resp_nombre']} · RUT {r['resp_rut']}
- {r['resp_direccion']}
- Contacto para ejercer derechos: {r['resp_email']}{dpo}

**2. Qué datos tratamos y por qué**
| Dato | Finalidad | Base de licitud |
|---|---|---|
| Correo electrónico y nombre | Crear tu cuenta, identificarte y comunicarnos contigo sobre el servicio | Ejecución del contrato de uso (art. 13) |
| Contraseña (solo su hash) | Autenticación segura | Ejecución del contrato |
| Fecha y hora de accesos, cambios de contraseña, exportaciones y eliminaciones | Seguridad de la cuenta y evidencia de cumplimiento | Interés legítimo y obligación legal |
| Datos comerciales que registras (productos, embarques, ventas, gastos, IVA) | Prestar el servicio de costeo y gestión | Ejecución del contrato |
| Nombre de proveedores y folios de documentos que tú ingresas en gastos y ventas | Libro de compras/ventas y F29 | Obligación legal tributaria (SII); si un proveedor es persona natural, tú eres responsable de ese dato |
| Aceptación de esta política y de comunicaciones | Acreditar tu consentimiento | Obligación legal |

No tratamos datos personales sensibles ni datos de menores. No hacemos perfilamiento ni decisiones automatizadas con efectos jurídicos sobre ti.

**3. Con quién se comparten**
Con nadie. Las consultas a mindicador.cl (tipo de cambio) y a la API de Mercado Libre (precios de referencia) no incluyen tus datos personales. No hay transferencias internacionales de datos personales. Si el servicio se aloja en un proveedor de nube, ese proveedor actúa como encargado del tratamiento bajo contrato.

**4. Cuánto tiempo los conservamos**
Mientras tu cuenta esté activa. Las cuentas sin actividad durante {r['resp_retencion_meses']} meses se eliminan, previo aviso al correo registrado. La bitácora de seguridad conserva solo un identificador irreversible (hash) del correo tras una supresión.

**5. Tus derechos**
Puedes ejercer en cualquier momento, desde la sección **Privacidad y mis datos** o escribiendo a {r['resp_email']}:
""" + "\n".join(f"- **{k}**: {v}" for k, v in DERECHOS.items()) + f"""

Responderemos dentro del plazo legal (referencia: {PLAZO_RESPUESTA_DIAS} días). Si no quedas conforme, puedes reclamar ante la Agencia de Protección de Datos Personales.

**6. Seguridad**
Contraseñas cifradas con PBKDF2-SHA256, aislamiento de datos por cuenta, bloqueo por intentos fallidos, sesión con expiración, bitácora de accesos y respaldo periódico. Ante una vulneración que afecte tus datos, notificaremos a la Agencia dentro de 72 horas y a ti sin dilación si el riesgo es alto.

**7. Cambios**
Si esta política cambia de forma relevante, te pediremos aceptar la nueva versión al iniciar sesión. Conservamos el historial de versiones aceptadas.
"""


# ---------------------------------------------------------------------------
# Registro de actividades de tratamiento (RAT)
# ---------------------------------------------------------------------------


def registro_actividades(r: dict[str, str] | None = None) -> list[dict[str, str]]:
    r = r or datos_responsable()
    return [
        {"actividad": "Gestión de cuentas de usuario", "titulares": "Usuarios registrados", "categorias": "Correo, nombre, hash de contraseña, fechas de acceso", "finalidad": "Autenticación y prestación del servicio", "base": "Ejecución de contrato", "conservacion": f"Vigencia de la cuenta + {r['resp_retencion_meses']} meses de inactividad", "encargados": "Proveedor de hosting (si aplica)", "transferencias": "Ninguna", "medidas": "PBKDF2-SHA256, bloqueo por intentos, expiración de sesión, HTTPS"},
        {"actividad": "Bitácora de seguridad y cumplimiento", "titulares": "Usuarios registrados", "categorias": "Fecha, acción, identificador de usuario", "finalidad": "Seguridad, evidencia ante la Agencia", "base": "Interés legítimo / obligación legal", "conservacion": "24 meses; tras supresión solo hash del correo", "encargados": "Ninguno", "transferencias": "Ninguna", "medidas": "Acceso restringido a administrador"},
        {"actividad": "Gestión de consentimientos", "titulares": "Usuarios registrados", "categorias": "Versión de política aceptada, fecha, opción de comunicaciones", "finalidad": "Acreditar consentimiento", "base": "Obligación legal", "conservacion": "Vigencia de la cuenta", "encargados": "Ninguno", "transferencias": "Ninguna", "medidas": "Registro inmutable con fecha"},
        {"actividad": "Datos comerciales del usuario (costeo, inventario, ventas)", "titulares": "Usuarios registrados (datos de su negocio)", "categorias": "Productos, embarques, ventas, IVA; no incluyen datos de terceros identificables", "finalidad": "Prestar el servicio de costeo y gestión", "base": "Ejecución de contrato", "conservacion": "Vigencia de la cuenta", "encargados": "Proveedor de hosting (si aplica)", "transferencias": "Ninguna", "medidas": "Aislamiento por usuario, respaldos"},
        {"actividad": "Libro de compras y ventas (gastos, folios, proveedores)", "titulares": "Proveedores y clientes ingresados por el usuario (pueden ser personas naturales)", "categorias": "Nombre o razón social, folio de documento, montos", "finalidad": "Registro tributario y F29", "base": "Obligación legal (SII)", "conservacion": "6 años (plazo de prescripción tributaria)", "encargados": "Ninguno", "transferencias": "Ninguna", "medidas": "Aislamiento por usuario, minimización (sin RUT ni contacto)"},
        {"actividad": "Solicitudes de derechos", "titulares": "Usuarios registrados", "categorias": "Derecho solicitado, fecha, respuesta", "finalidad": "Atender derechos ARCO-P-B en plazo", "base": "Obligación legal", "conservacion": "36 meses", "encargados": "Ninguno", "transferencias": "Ninguna", "medidas": "Acceso restringido a administrador"},
        {"actividad": "Registro de brechas de seguridad", "titulares": "Usuarios afectados", "categorias": "Descripción, datos afectados, notificaciones", "finalidad": "Notificar a la Agencia en 72 h y a los titulares", "base": "Obligación legal", "conservacion": "60 meses", "encargados": "Ninguno", "transferencias": "Ninguna", "medidas": "Acceso restringido a administrador"},
    ]


def rat_markdown() -> str:
    r = datos_responsable()
    filas = registro_actividades(r)
    cab = "| " + " | ".join(["Actividad", "Titulares", "Categorías de datos", "Finalidad", "Base de licitud", "Conservación", "Encargados", "Transferencias", "Medidas"]) + " |\n|" + "---|" * 9 + "\n"
    cuerpo = "\n".join("| " + " | ".join(f[k] for k in ("actividad", "titulares", "categorias", "finalidad", "base", "conservacion", "encargados", "transferencias", "medidas")) + " |" for f in filas)
    return f"# Registro de actividades de tratamiento\n\n**Responsable:** {r['resp_nombre']} · RUT {r['resp_rut']} · {r['resp_direccion']}\n**Contacto:** {r['resp_email']}\n**Generado:** {datetime.now().strftime('%d-%m-%Y %H:%M')} · Política v{VERSION_POLITICA}\n\n" + cab + cuerpo + "\n"


# ---------------------------------------------------------------------------
# Brechas de seguridad
# ---------------------------------------------------------------------------


def estado_brecha(inc: dict[str, Any]) -> dict[str, Any]:
    deteccion = datetime.fromisoformat(inc["fecha_deteccion"])
    limite = deteccion + timedelta(hours=HORAS_NOTIFICACION_BRECHA)
    restante = limite - datetime.now()
    horas = restante.total_seconds() / 3600
    if inc["notificado_agencia"]:
        color, msg = "verde", f"Notificado a la Agencia el {inc['fecha_notificacion_agencia']}."
    elif horas < 0:
        color, msg = "rojo", f"PLAZO VENCIDO hace {abs(horas):.0f} h. Notifica a la Agencia de inmediato y documenta el motivo del retraso."
    elif horas < 24:
        color, msg = "rojo", f"Quedan {horas:.0f} h para notificar a la Agencia (límite {limite.strftime('%d-%m %H:%M')})."
    else:
        color, msg = "ambar", f"Quedan {horas:.0f} h para notificar a la Agencia (límite {limite.strftime('%d-%m %H:%M')})."
    return {"color": color, "mensaje": msg, "limite": limite, "horas_restantes": horas}


def plantilla_notificacion_agencia(inc: dict[str, Any], r: dict[str, str] | None = None) -> str:
    r = r or datos_responsable()
    return f"""NOTIFICACIÓN DE VULNERACIÓN DE SEGURIDAD — Agencia de Protección de Datos Personales

Responsable: {r['resp_nombre']} · RUT {r['resp_rut']} · {r['resp_direccion']}
Contacto: {r['resp_email']}{(' · DPO: ' + r['resp_dpo']) if r.get('resp_dpo') else ''}

1. Fecha y hora de detección: {inc['fecha_deteccion']}
2. Naturaleza de la vulneración: {inc['descripcion']}
3. Categorías y volumen de datos afectados: {inc.get('datos_afectados') or 'por determinar'}
4. Número aproximado de titulares afectados: {inc.get('usuarios_afectados', 0)}
5. Nivel de riesgo para los titulares: {inc.get('riesgo', 'Medio')}
6. Medidas adoptadas y propuestas: {inc.get('medidas') or 'por determinar'}
7. Comunicación a los titulares: {'realizada el ' + str(inc.get('fecha_notificacion_titulares')) if inc.get('notificado_titulares') else 'pendiente / no requerida según evaluación de riesgo'}

Fecha de esta notificación: {datetime.now().strftime('%d-%m-%Y %H:%M')}
"""


# ---------------------------------------------------------------------------
# Checklist organizacional (lo que no se resuelve con código)
# ---------------------------------------------------------------------------

CHECKLIST_ORGANIZACIONAL = [
    ("Datos del responsable completos en la política (nombre, RUT, domicilio, correo)", "config"),
    ("Designar un encargado interno o Delegado de Protección de Datos si el volumen lo amerita", "manual"),
    ("Contrato de encargo con el proveedor de hosting / nube (cláusulas de confidencialidad, seguridad y devolución de datos)", "manual"),
    ("Evaluar si corresponde una evaluación de impacto (solo si se agregan tratamientos de alto riesgo: datos sensibles, perfilamiento masivo)", "manual"),
    ("Procedimiento escrito de respuesta a brechas y responsable de notificar a la Agencia en 72 h", "manual"),
    ("Respaldo diario de la base de datos y prueba de restauración cada trimestre", "manual"),
    ("HTTPS obligatorio y `server.allowedHosts` fijado al dominio", "manual"),
    ("Revisar solicitudes de derechos pendientes al menos una vez por semana", "app"),
    ("Ejecutar la limpieza de cuentas inactivas según el plazo de retención declarado", "app"),
    ("Revisar esta política y el RAT cuando cambie un tratamiento o un proveedor", "manual"),
]


def exportar_json(uid: int) -> bytes:
    return json.dumps(db.exportar_datos_usuario(uid), ensure_ascii=False, indent=2, default=str).encode("utf-8")
