"""
auth.py — Autenticación y seguridad de cuentas para Importa.

- Registro e inicio de sesión con correo electrónico personal + contraseña.
- Contraseñas con PBKDF2-HMAC-SHA256 (600.000 iteraciones), sal aleatoria por usuario y
  "pepper" opcional desde la variable de entorno IMPORTA_PEPPER (acepta también IMPORTO_PEPPER y CHILEIMPORT_PEPPER).
- Comparación en tiempo constante, bloqueo temporal tras intentos fallidos y expiración
  de sesión por inactividad.
- Cada sesión de Streamlit guarda el usuario en `st.session_state`; los datos se aíslan
  en la base por `usuario_id` (ver database.py).
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import streamlit as st

import database as db

PBKDF2_ITER = 600_000
MAX_INTENTOS = 5
BLOQUEO_MIN = 15
SESION_HORAS = 8
MIN_PASSWORD = 8
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


@dataclass
class Usuario:
    id: int
    email: str
    nombre: str
    rol: str


def _pepper() -> bytes:
    # Se acepta el nombre antiguo para que las cuentas creadas antes del cambio de marca sigan entrando.
    return (os.environ.get("IMPORTA_PEPPER") or os.environ.get("IMPORTO_PEPPER") or os.environ.get("CHILEIMPORT_PEPPER", "")).encode()


def hash_password(password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode() + _pepper(), salt, PBKDF2_ITER)
    return dk.hex(), salt.hex()


def verificar_password(password: str, hash_hex: str, salt_hex: str) -> bool:
    calc, _ = hash_password(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(calc, hash_hex)


def email_valido(email: str) -> bool:
    return bool(EMAIL_RE.match(email.strip().lower()))


# Contraseñas que aparecen primero en cualquier ataque de diccionario.
PASSWORDS_DEBILES = {
    "12345678", "123456789", "1234567890", "contrasena1", "contraseña1", "password1", "password123",
    "qwerty123", "abc12345", "importa123", "importo123", "minegocio1", "chile1234", "santiago1", "admin1234", "usuario123",
    "iloveyou1", "11111111", "00000000", "asdf1234", "zxcv1234", "1q2w3e4r",
}


def password_fuerte(pw: str) -> tuple[bool, str]:
    if len(pw) < MIN_PASSWORD:
        return False, f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres."
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        return False, "Combina letras y números."
    if pw.lower() in PASSWORDS_DEBILES:
        return False, "Esa contraseña es de las más usadas del mundo: elige otra."
    if len(set(pw)) < 4:
        return False, "Usa más variedad de caracteres."
    return True, ""


# ---------------------------------------------------------------------------
# Registro / login
# ---------------------------------------------------------------------------


def registrar(email: str, nombre: str, password: str, acepta_politica: bool = False, acepta_comunicaciones: bool = False, version_politica: str = "") -> tuple[bool, str]:
    email = email.strip().lower()
    if not acepta_politica:
        return False, "Debes leer y aceptar la Política de Privacidad para crear la cuenta."
    if not email_valido(email):
        return False, "Ingresa un correo electrónico válido."
    ok, msg = password_fuerte(password)
    if not ok:
        return False, msg
    if db.get_usuario_por_email(email):
        return False, "Ese correo ya tiene una cuenta. Inicia sesión."
    h, s = hash_password(password)
    primer_usuario = db.contar_usuarios() == 0
    uid = db.crear_usuario(email=email, nombre=nombre.strip() or email.split("@")[0], password_hash=h, salt=s, rol="admin" if primer_usuario else "usuario")
    if primer_usuario:
        db.reclamar_datos_sin_dueno(uid)  # datos de versiones anteriores pasan al primer usuario
    db.registrar_consentimiento(uid, "politica_privacidad", version_politica, True, "Aceptada al crear la cuenta")
    db.registrar_consentimiento(uid, "comunicaciones", version_politica, acepta_comunicaciones, "Finalidad secundaria: avisos y novedades por correo")
    db.auditar("registro", f"cuenta creada para {email}", uid)
    return True, "Cuenta creada. Ya puedes iniciar sesión."


def login(email: str, password: str) -> tuple[Optional[Usuario], str]:
    email = email.strip().lower()
    u = db.get_usuario_por_email(email)
    # Mismo mensaje exista o no la cuenta: evita enumerar correos
    generico = "Correo o contraseña incorrectos."
    if not u or not u["activo"]:
        # Consumir tiempo similar al de una verificación real
        hash_password(password, b"0" * 16)
        return None, generico
    if u["bloqueado_hasta"] and datetime.fromisoformat(u["bloqueado_hasta"]) > datetime.now():
        restante = int((datetime.fromisoformat(u["bloqueado_hasta"]) - datetime.now()).total_seconds() // 60) + 1
        return None, f"Cuenta bloqueada por intentos fallidos. Intenta en {restante} min."
    if not verificar_password(password, u["password_hash"], u["salt"]):
        intentos = u["intentos_fallidos"] + 1
        bloqueo = (datetime.now() + timedelta(minutes=BLOQUEO_MIN)).isoformat() if intentos >= MAX_INTENTOS else None
        db.actualizar_intentos(u["id"], 0 if bloqueo else intentos, bloqueo)
        db.auditar("login_fallido", "contraseña incorrecta" + (" · cuenta bloqueada" if bloqueo else ""), u["id"])
        if bloqueo:
            return None, f"Demasiados intentos. Cuenta bloqueada {BLOQUEO_MIN} minutos."
        return None, generico
    db.actualizar_intentos(u["id"], 0, None)
    db.marcar_login(u["id"])
    db.auditar("login", "inicio de sesión", u["id"])
    return Usuario(u["id"], u["email"], u["nombre"], u["rol"]), ""


def cambiar_password(uid: int, actual: str, nueva: str) -> tuple[bool, str]:
    u = db.get_usuario(uid)
    if not u or not verificar_password(actual, u["password_hash"], u["salt"]):
        return False, "La contraseña actual no es correcta."
    ok, msg = password_fuerte(nueva)
    if not ok:
        return False, msg
    h, s = hash_password(nueva)
    db.actualizar_password(uid, h, s)
    db.auditar("cambio_password", "contraseña actualizada por el titular", uid)
    return True, "Contraseña actualizada."


# ---------------------------------------------------------------------------
# Sesión de Streamlit
# ---------------------------------------------------------------------------


def usuario_actual() -> Optional[Usuario]:
    u = st.session_state.get("auth_user")
    if not u:
        return None
    ultimo = st.session_state.get("auth_ultimo_uso")
    if ultimo and datetime.now() - ultimo > timedelta(hours=SESION_HORAS):
        cerrar_sesion()
        return None
    # La sesión vale solo mientras la cuenta siga existiendo y activa: si el administrador
    # la desactiva o el titular la elimina, la sesión abierta deja de funcionar en el acto.
    fila = db.get_usuario(u.id)
    if not fila or not fila["activo"]:
        cerrar_sesion()
        return None
    if fila["rol"] != u.rol or fila["nombre"] != u.nombre:
        u = Usuario(u.id, fila["email"], fila["nombre"], fila["rol"])
        st.session_state["auth_user"] = u
    st.session_state["auth_ultimo_uso"] = datetime.now()
    return u


def iniciar_sesion(u: Usuario) -> None:
    """Sesión limpia: se descarta todo el estado anterior para que nada quede de otra cuenta."""
    # Limpia cualquier estado de otra sesión y fija el usuario
    for k in list(st.session_state.keys()):
        if not k.startswith("tc_"):
            del st.session_state[k]
    st.session_state["auth_user"] = u
    st.session_state["auth_ultimo_uso"] = datetime.now()


def cerrar_sesion() -> None:
    u = st.session_state.get("auth_user")
    if u:
        db.auditar("logout", "cierre de sesión", u.id)
    for k in list(st.session_state.keys()):
        del st.session_state[k]
