"""
database.py — Capa de persistencia SQLite para Importa.

- Context manager transaccional (`get_connection`): commit al salir, rollback ante error.
- Creación automática de tablas (`init_db`).
- Dataclasses tipadas para cada entidad y métodos CRUD.
- Operaciones compuestas (`registrar_importacion`, `registrar_venta`) ejecutadas en UNA sola
  transacción para garantizar consistencia entre inventario, ventas y libro F29.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Iterator, Optional

def _ruta_db() -> str:
    """Ruta de la base. Respeta la variable de entorno y, si no la hay, reutiliza la base
    de versiones anteriores (importo.db o chileimport.db) para no perder datos al cambiar de marca."""
    for var in ("IMPORTA_DB", "IMPORTO_DB", "CHILEIMPORT_DB"):
        valor = os.environ.get(var)
        if valor:
            return valor
    if not os.path.exists("importa.db"):
        for anterior in ("importo.db", "chileimport.db"):
            if os.path.exists(anterior):
                return anterior
    return "importa.db"


DB_PATH = _ruta_db()  # en Docker: /data/importa.db

# Tablas cuyos registros pertenecen a un usuario (aislamiento multiusuario)
TABLAS_USUARIO = ("productos", "cotizaciones", "cotizacion_items", "embarques", "inventario", "ventas", "f29_registro", "gastos", "fletes")

_ctx = threading.local()  # Streamlit ejecuta cada sesión en su propio hilo


def set_usuario_actual(uid: Optional[int], rol: str = "usuario") -> None:
    """Fija el usuario y su rol para las consultas de este hilo/sesión."""
    _ctx.uid = uid
    _ctx.rol = rol if uid is not None else None


def _uid() -> int:
    uid = getattr(_ctx, "uid", None)
    if uid is None:
        raise PermissionError("No hay un usuario autenticado en esta sesión")
    return int(uid)


def _require_admin() -> int:
    """Segunda barrera: aunque la interfaz oculte la sección, la capa de datos vuelve a comprobar el rol."""
    uid = _uid()
    if getattr(_ctx, "rol", None) != "admin":
        raise PermissionError("Esta operación requiere rol de administrador")
    return uid

# ---------------------------------------------------------------------------
# Conexión
# ---------------------------------------------------------------------------


@contextmanager
def get_connection(db_path: str = DB_PATH) -> Iterator[sqlite3.Connection]:
    """Context manager transaccional. Hace commit si todo va bien y rollback si falla."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 10000")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _rows(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Esquema
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    rol TEXT NOT NULL DEFAULT 'usuario',
    activo INTEGER NOT NULL DEFAULT 1,
    intentos_fallidos INTEGER NOT NULL DEFAULT 0,
    bloqueado_hasta TEXT,
    creado TEXT NOT NULL,
    ultimo_login TEXT
);

CREATE TABLE IF NOT EXISTS config_usuario (
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    clave TEXT NOT NULL,
    valor TEXT NOT NULL,
    actualizado TEXT NOT NULL,
    PRIMARY KEY (usuario_id, clave)
);

CREATE TABLE IF NOT EXISTS consentimientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    tipo TEXT NOT NULL,
    version TEXT NOT NULL,
    aceptado INTEGER NOT NULL,
    fecha TEXT NOT NULL,
    detalle TEXT
);

CREATE TABLE IF NOT EXISTS auditoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    fecha TEXT NOT NULL,
    accion TEXT NOT NULL,
    detalle TEXT
);

CREATE TABLE IF NOT EXISTS solicitudes_derechos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    derecho TEXT NOT NULL,
    detalle TEXT,
    fecha TEXT NOT NULL,
    plazo TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'Pendiente',
    respuesta TEXT,
    fecha_respuesta TEXT
);

CREATE TABLE IF NOT EXISTS incidentes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_deteccion TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    datos_afectados TEXT,
    usuarios_afectados INTEGER NOT NULL DEFAULT 0,
    riesgo TEXT NOT NULL DEFAULT 'Medio',
    medidas TEXT,
    notificado_agencia INTEGER NOT NULL DEFAULT 0,
    fecha_notificacion_agencia TEXT,
    notificado_titulares INTEGER NOT NULL DEFAULT 0,
    fecha_notificacion_titulares TEXT,
    estado TEXT NOT NULL DEFAULT 'Abierto',
    creado_por INTEGER
);

CREATE TABLE IF NOT EXISTS config_general (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    actualizado TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cotizaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id),
    fecha TEXT NOT NULL,
    producto TEXT NOT NULL,
    incoterm TEXT NOT NULL DEFAULT 'FOB',
    tlc INTEGER NOT NULL DEFAULT 0,
    largo_cm REAL, ancho_cm REAL, alto_cm REAL, peso_kg REAL,
    unidades_por_caja INTEGER, cajas INTEGER, cbm_total REAL,
    unidades INTEGER NOT NULL,
    fob_unit_usd REAL NOT NULL, fob_total_usd REAL NOT NULL,
    flete_usd REAL NOT NULL, seguro_usd REAL NOT NULL,
    cif_usd REAL NOT NULL, cif_clp REAL NOT NULL,
    advalorem_usd REAL NOT NULL, iva_usd REAL NOT NULL,
    honorarios_usd REAL NOT NULL, gastos_locales_clp REAL NOT NULL,
    landed_clp REAL NOT NULL, landed_usd REAL NOT NULL,
    landed_unit_clp REAL NOT NULL, desembolso_total_clp REAL NOT NULL,
    factor_internacion REAL NOT NULL, tipo_cambio REAL NOT NULL,
    origen TEXT, destino TEXT, prorrateo TEXT NOT NULL DEFAULT 'cbm', n_items INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id),
    nombre TEXT NOT NULL,
    hs_code TEXT,
    categoria TEXT NOT NULL DEFAULT 'General',
    largo_cm REAL NOT NULL DEFAULT 50, ancho_cm REAL NOT NULL DEFAULT 40, alto_cm REAL NOT NULL DEFAULT 40,
    peso_kg REAL NOT NULL DEFAULT 10,
    unidades_por_caja INTEGER NOT NULL DEFAULT 50,
    fob_unit_usd REAL NOT NULL DEFAULT 1,
    tlc INTEGER NOT NULL DEFAULT 1,
    dg INTEGER NOT NULL DEFAULT 0,
    proveedor TEXT,
    notas TEXT
);

CREATE TABLE IF NOT EXISTS cotizacion_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id),
    cotizacion_id INTEGER NOT NULL REFERENCES cotizaciones(id),
    producto_id INTEGER REFERENCES productos(id),
    producto TEXT NOT NULL,
    cajas INTEGER NOT NULL, unidades_por_caja INTEGER NOT NULL, unidades INTEGER NOT NULL,
    fob_unit_usd REAL NOT NULL, fob_total_usd REAL NOT NULL,
    cbm REAL NOT NULL, peso_kg REAL NOT NULL,
    tlc INTEGER NOT NULL DEFAULT 1, dg INTEGER NOT NULL DEFAULT 0,
    participacion REAL NOT NULL,
    flete_usd REAL NOT NULL, seguro_usd REAL NOT NULL, cif_usd REAL NOT NULL,
    advalorem_usd REAL NOT NULL, iva_usd REAL NOT NULL, iva_clp REAL NOT NULL,
    comunes_clp REAL NOT NULL,
    landed_clp REAL NOT NULL, landed_unit_clp REAL NOT NULL,
    desembolso_unit_clp REAL NOT NULL, factor_internacion REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS embarques (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id),
    cotizacion_id INTEGER NOT NULL REFERENCES cotizaciones(id),
    estado TEXT NOT NULL DEFAULT 'En Tránsito',
    fecha_eta TEXT NOT NULL,
    dias_libres INTEGER NOT NULL DEFAULT 5,
    forwarder TEXT,
    notas TEXT
);

CREATE TABLE IF NOT EXISTS inventario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id),
    producto TEXT NOT NULL,
    cotizacion_id INTEGER REFERENCES cotizaciones(id),
    item_id INTEGER REFERENCES cotizacion_items(id),
    producto_id INTEGER REFERENCES productos(id),
    unidades_iniciales INTEGER NOT NULL,
    unidades_disponibles INTEGER NOT NULL,
    costo_unitario_clp REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id),
    fecha TEXT NOT NULL,
    producto_id INTEGER NOT NULL REFERENCES inventario(id),
    cantidad INTEGER NOT NULL,
    canal TEXT NOT NULL,
    precio_unitario REAL NOT NULL,
    comision REAL NOT NULL DEFAULT 0,
    medio_pago TEXT NOT NULL,
    estado_liquidacion TEXT NOT NULL DEFAULT 'Retenido',
    fecha_liberacion TEXT,
    documento TEXT NOT NULL DEFAULT 'Boleta',
    folio TEXT,
    publicidad REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS fletes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id),
    fecha TEXT NOT NULL,
    nombre TEXT NOT NULL,
    modo TEXT NOT NULL,
    proveedor TEXT,
    origen TEXT,
    destino TEXT,
    tarifa REAL NOT NULL DEFAULT 0,
    minimo_usd REAL NOT NULL DEFAULT 0,
    recargos_usd REAL NOT NULL DEFAULT 0,
    locales_clp REAL NOT NULL DEFAULT 0,
    dias_transito INTEGER NOT NULL DEFAULT 30,
    dg_pct REAL NOT NULL DEFAULT 0,
    seguro_pct REAL NOT NULL DEFAULT 0,
    validez TEXT,
    notas TEXT,
    favorito INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS hitos (
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    clave TEXT NOT NULL,
    fecha TEXT NOT NULL,
    PRIMARY KEY (usuario_id, clave)
);

CREATE TABLE IF NOT EXISTS gastos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id),
    fecha TEXT NOT NULL,
    categoria TEXT NOT NULL,
    descripcion TEXT,
    proveedor TEXT,
    documento TEXT NOT NULL DEFAULT 'Factura',
    folio TEXT,
    neto REAL NOT NULL,
    iva REAL NOT NULL,
    total REAL NOT NULL,
    recurrente INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS f29_registro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id),
    fecha TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('CREDITO','DEBITO')),
    monto_clp REAL NOT NULL,
    descripcion TEXT,
    referencia TEXT
);
"""

DEFAULT_CONFIG: dict[str, str] = {
    "tc_usd": "950",
    "tc_uf": "39500",
    "kit_empaque_clp": "650",
    "merma_pct": "4",
    "lead_time_dias": "58",
    "dias_libres_default": "5",
}


MIGRACIONES: dict[str, dict[str, str]] = {
    "cotizaciones": {"origen": "TEXT", "destino": "TEXT", "prorrateo": "TEXT NOT NULL DEFAULT 'cbm'", "n_items": "INTEGER NOT NULL DEFAULT 1", "usuario_id": "INTEGER"},
    "inventario": {"item_id": "INTEGER", "producto_id": "INTEGER", "usuario_id": "INTEGER"},
    "productos": {"usuario_id": "INTEGER"},
    "cotizacion_items": {"usuario_id": "INTEGER"},
    "embarques": {"usuario_id": "INTEGER"},
    "ventas": {"usuario_id": "INTEGER", "documento": "TEXT NOT NULL DEFAULT 'Boleta'", "folio": "TEXT", "publicidad": "REAL NOT NULL DEFAULT 0"},
    "f29_registro": {"usuario_id": "INTEGER"},
}
INDICES = """
CREATE INDEX IF NOT EXISTS ix_cot_user ON cotizaciones(usuario_id);
CREATE INDEX IF NOT EXISTS ix_inv_user ON inventario(usuario_id);
CREATE INDEX IF NOT EXISTS ix_ven_user ON ventas(usuario_id, fecha);
CREATE INDEX IF NOT EXISTS ix_f29_user ON f29_registro(usuario_id, fecha);
CREATE INDEX IF NOT EXISTS ix_emb_user ON embarques(usuario_id);
CREATE INDEX IF NOT EXISTS ix_prod_user ON productos(usuario_id);
CREATE INDEX IF NOT EXISTS ix_gas_user ON gastos(usuario_id, fecha);
CREATE INDEX IF NOT EXISTS ix_fle_user ON fletes(usuario_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_prod_user_nombre ON productos(usuario_id, nombre);
"""


def _migrar(conn: sqlite3.Connection) -> None:
    for tabla, cols in MIGRACIONES.items():
        existentes = {r["name"] for r in conn.execute(f"PRAGMA table_info({tabla})")}
        for col, tipo in cols.items():
            if col not in existentes:
                conn.execute(f"ALTER TABLE {tabla} ADD COLUMN {col} {tipo}")


def init_db(db_path: str = DB_PATH) -> None:
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)
        _migrar(conn)
        conn.executescript(INDICES)
        now = datetime.now().isoformat(timespec="seconds")
        for k, v in DEFAULT_CONFIG.items():
            conn.execute(
                "INSERT OR IGNORE INTO config_general (clave, valor, actualizado) VALUES (?,?,?)",
                (k, v, now),
            )


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Cotizacion:
    producto: str
    unidades: int
    fob_unit_usd: float
    fob_total_usd: float
    flete_usd: float
    seguro_usd: float
    cif_usd: float
    cif_clp: float
    advalorem_usd: float
    iva_usd: float
    honorarios_usd: float
    gastos_locales_clp: float
    landed_clp: float
    landed_usd: float
    landed_unit_clp: float
    desembolso_total_clp: float
    factor_internacion: float
    tipo_cambio: float
    incoterm: str = "FOB"
    tlc: int = 0
    largo_cm: float = 0.0
    ancho_cm: float = 0.0
    alto_cm: float = 0.0
    peso_kg: float = 0.0
    unidades_por_caja: int = 0
    cajas: int = 0
    cbm_total: float = 0.0
    fecha: str = field(default_factory=lambda: date.today().isoformat())
    origen: str = ""
    destino: str = ""
    prorrateo: str = "cbm"
    n_items: int = 1
    id: Optional[int] = None


@dataclass
class Producto:
    nombre: str
    hs_code: str = ""
    categoria: str = "General"
    largo_cm: float = 50.0
    ancho_cm: float = 40.0
    alto_cm: float = 40.0
    peso_kg: float = 10.0
    unidades_por_caja: int = 50
    fob_unit_usd: float = 1.0
    tlc: int = 1
    dg: int = 0
    proveedor: str = ""
    notas: str = ""
    id: Optional[int] = None


@dataclass
class CotizacionItem:
    producto: str
    cajas: int
    unidades_por_caja: int
    unidades: int
    fob_unit_usd: float
    fob_total_usd: float
    cbm: float
    peso_kg: float
    participacion: float
    flete_usd: float
    seguro_usd: float
    cif_usd: float
    advalorem_usd: float
    iva_usd: float
    iva_clp: float
    comunes_clp: float
    landed_clp: float
    landed_unit_clp: float
    desembolso_unit_clp: float
    factor_internacion: float
    tlc: int = 1
    dg: int = 0
    producto_id: Optional[int] = None
    cotizacion_id: int = 0
    id: Optional[int] = None


@dataclass
class Embarque:
    cotizacion_id: int
    fecha_eta: str
    dias_libres: int = 5
    estado: str = "En Tránsito"
    forwarder: str = ""
    notas: str = ""
    id: Optional[int] = None


@dataclass
class InventarioItem:
    producto: str
    unidades_iniciales: int
    unidades_disponibles: int
    costo_unitario_clp: float
    cotizacion_id: Optional[int] = None
    item_id: Optional[int] = None
    producto_id: Optional[int] = None
    id: Optional[int] = None


@dataclass
class Venta:
    producto_id: int
    cantidad: int
    canal: str
    precio_unitario: float
    medio_pago: str
    comision: float = 0.0
    estado_liquidacion: str = "Retenido"
    fecha_liberacion: Optional[str] = None
    documento: str = "Boleta"
    folio: str = ""
    publicidad: float = 0.0
    fecha: str = field(default_factory=lambda: date.today().isoformat())
    id: Optional[int] = None


@dataclass
class Flete:
    nombre: str
    modo: str  # Marítimo LCL, Marítimo FCL 20', Marítimo FCL 40', Aéreo, Courier
    tarifa: float  # USD por m³ (LCL), USD por contenedor (FCL), USD por kg cobrable (aéreo/courier)
    proveedor: str = ""
    origen: str = ""
    destino: str = ""
    minimo_usd: float = 0.0
    recargos_usd: float = 0.0  # THC, BL, handling, documentación
    locales_clp: float = 0.0  # desconsolidación, almacenaje, transporte a bodega
    dias_transito: int = 30
    dg_pct: float = 0.0
    seguro_pct: float = 0.0  # % sobre FOB; 0 = usar presunto 2 %
    validez: str = ""
    notas: str = ""
    favorito: int = 0
    fecha: str = field(default_factory=lambda: date.today().isoformat())
    id: Optional[int] = None


@dataclass
class Gasto:
    fecha: str
    categoria: str
    neto: float
    iva: float
    total: float
    descripcion: str = ""
    proveedor: str = ""
    documento: str = "Factura"
    folio: str = ""
    recurrente: int = 0
    id: Optional[int] = None


@dataclass
class RegistroF29:
    tipo: str  # 'CREDITO' | 'DEBITO'
    monto_clp: float
    descripcion: str = ""
    referencia: str = ""
    fecha: str = field(default_factory=lambda: date.today().isoformat())
    id: Optional[int] = None


def _insert(conn: sqlite3.Connection, table: str, obj: Any) -> int:
    data = {k: v for k, v in asdict(obj).items() if k != "id"}
    if table in TABLAS_USUARIO:
        data["usuario_id"] = _uid()
    cols = ", ".join(data.keys())
    marks = ", ".join("?" for _ in data)
    cur = conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(data.values()))
    return int(cur.lastrowid)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def get_config(clave: str, default: str = "") -> str:
    """Valor del usuario actual; si no existe, el global; si no, default."""
    uid = getattr(_ctx, "uid", None)
    with get_connection() as conn:
        if uid is not None:
            row = conn.execute("SELECT valor FROM config_usuario WHERE usuario_id=? AND clave=?", (uid, clave)).fetchone()
            if row:
                return row["valor"]
        row = conn.execute("SELECT valor FROM config_general WHERE clave=?", (clave,)).fetchone()
        return row["valor"] if row else default


def get_config_float(clave: str, default: float = 0.0) -> float:
    try:
        return float(get_config(clave, str(default)))
    except ValueError:
        return default


def set_config(clave: str, valor: Any, global_: bool = False) -> None:
    """Guarda en la config del usuario actual (o en la global si `global_` o no hay sesión)."""
    uid = getattr(_ctx, "uid", None)
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        if global_ or uid is None:
            conn.execute(
                "INSERT INTO config_general (clave, valor, actualizado) VALUES (?,?,?) "
                "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor, actualizado=excluded.actualizado",
                (clave, str(valor), now),
            )
        else:
            conn.execute(
                "INSERT INTO config_usuario (usuario_id, clave, valor, actualizado) VALUES (?,?,?,?) "
                "ON CONFLICT(usuario_id, clave) DO UPDATE SET valor=excluded.valor, actualizado=excluded.actualizado",
                (uid, clave, str(valor), now),
            )


def get_all_config() -> dict[str, str]:
    with get_connection() as conn:
        return {r["clave"]: r["valor"] for r in conn.execute("SELECT clave, valor FROM config_general")}


# ---------------------------------------------------------------------------
# Cotizaciones
# ---------------------------------------------------------------------------


def insert_cotizacion(c: Cotizacion) -> int:
    with get_connection() as conn:
        return _insert(conn, "cotizaciones", c)


def list_cotizaciones() -> list[dict[str, Any]]:
    with get_connection() as conn:
        return _rows(conn.execute("SELECT * FROM cotizaciones WHERE usuario_id=? ORDER BY id DESC", (_uid(),)))


def get_cotizacion(cid: int) -> Optional[dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM cotizaciones WHERE id=? AND usuario_id=?", (cid, _uid())).fetchone()
        return dict(row) if row else None


def list_items(cotizacion_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        return _rows(conn.execute("SELECT * FROM cotizacion_items WHERE cotizacion_id=? AND usuario_id=? ORDER BY id", (cotizacion_id, _uid())))


# ---------------------------------------------------------------------------
# Catálogo de productos
# ---------------------------------------------------------------------------


def upsert_producto(p: Producto) -> int:
    data = {k: v for k, v in asdict(p).items() if k != "id"}
    with get_connection() as conn:
        if p.id:
            sets = ", ".join(f"{k}=?" for k in data)
            conn.execute(f"UPDATE productos SET {sets} WHERE id=? AND usuario_id=?", (*data.values(), p.id, _uid()))
            return p.id
        row = conn.execute("SELECT id FROM productos WHERE nombre=? AND usuario_id=?", (p.nombre, _uid())).fetchone()
        if row:
            sets = ", ".join(f"{k}=?" for k in data)
            conn.execute(f"UPDATE productos SET {sets} WHERE id=? AND usuario_id=?", (*data.values(), row["id"], _uid()))
            return int(row["id"])
        return _insert(conn, "productos", p)


def list_productos() -> list[dict[str, Any]]:
    with get_connection() as conn:
        return _rows(conn.execute("SELECT * FROM productos WHERE usuario_id=? ORDER BY nombre", (_uid(),)))


def delete_producto(pid: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM productos WHERE id=? AND usuario_id=?", (pid, _uid()))


# ---------------------------------------------------------------------------
# Embarques
# ---------------------------------------------------------------------------


def insert_embarque(e: Embarque) -> int:
    with get_connection() as conn:
        return _insert(conn, "embarques", e)


def list_embarques() -> list[dict[str, Any]]:
    with get_connection() as conn:
        return _rows(
            conn.execute(
                """SELECT e.*, c.producto, c.unidades, c.cif_usd
                   FROM embarques e JOIN cotizaciones c ON c.id = e.cotizacion_id
                   WHERE e.usuario_id=? ORDER BY e.fecha_eta ASC""",
                (_uid(),),
            )
        )


def update_embarque(eid: int, fecha_eta: str, dias_libres: int) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE embarques SET fecha_eta=?, dias_libres=? WHERE id=? AND usuario_id=?", (fecha_eta, dias_libres, eid, _uid()))


def update_embarque_estado(eid: int, estado: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE embarques SET estado=? WHERE id=? AND usuario_id=?", (estado, eid, _uid()))


# ---------------------------------------------------------------------------
# Inventario
# ---------------------------------------------------------------------------


def insert_inventario(i: InventarioItem) -> int:
    with get_connection() as conn:
        return _insert(conn, "inventario", i)


def list_inventario() -> list[dict[str, Any]]:
    with get_connection() as conn:
        return _rows(conn.execute("SELECT * FROM inventario WHERE usuario_id=? ORDER BY id DESC", (_uid(),)))


def get_inventario(iid: int) -> Optional[dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM inventario WHERE id=? AND usuario_id=?", (iid, _uid())).fetchone()
        return dict(row) if row else None


def ajustar_stock(iid: int, delta: int) -> None:
    with get_connection() as conn:
        _ajustar_stock(conn, iid, delta)


def _ajustar_stock(conn: sqlite3.Connection, iid: int, delta: int) -> None:
    row = conn.execute("SELECT unidades_disponibles FROM inventario WHERE id=? AND usuario_id=?", (iid, _uid())).fetchone()
    if row is None:
        raise ValueError(f"Producto de inventario {iid} no existe")
    nuevo = row["unidades_disponibles"] + delta
    if nuevo < 0:
        raise ValueError("Stock insuficiente para esta operación")
    conn.execute("UPDATE inventario SET unidades_disponibles=? WHERE id=? AND usuario_id=?", (nuevo, iid, _uid()))


# ---------------------------------------------------------------------------
# Ventas
# ---------------------------------------------------------------------------


def insert_venta(v: Venta) -> int:
    with get_connection() as conn:
        return _insert(conn, "ventas", v)


def list_ventas() -> list[dict[str, Any]]:
    with get_connection() as conn:
        return _rows(
            conn.execute(
                """SELECT v.*, i.producto, i.costo_unitario_clp,
                          v.cantidad * v.precio_unitario AS total_bruto,
                          v.cantidad * v.precio_unitario - v.comision AS total_neto
                   FROM ventas v JOIN inventario i ON i.id = v.producto_id
                   WHERE v.usuario_id=? ORDER BY v.fecha DESC, v.id DESC""",
                (_uid(),),
            )
        )


def update_venta_estado(vid: int, estado: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE ventas SET estado_liquidacion=? WHERE id=? AND usuario_id=?", (estado, vid, _uid()))


def liberar_ventas_vencidas(hoy: Optional[date] = None) -> int:
    """Marca como 'En Cuenta' las ventas cuya fecha de liberación ya pasó. Devuelve cantidad."""
    hoy = hoy or date.today()
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE ventas SET estado_liquidacion='En Cuenta' "
            "WHERE estado_liquidacion='Retenido' AND fecha_liberacion IS NOT NULL AND fecha_liberacion <= ? AND usuario_id=?",
            (hoy.isoformat(), _uid()),
        )
        return cur.rowcount


def resumen_caja() -> dict[str, float]:
    """Caja líquida real (En Cuenta) vs plata por liberar (Retenido), netas de comisión."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT estado_liquidacion, COALESCE(SUM(cantidad*precio_unitario - comision),0) AS neto
               FROM ventas WHERE usuario_id=? GROUP BY estado_liquidacion""",
            (_uid(),),
        ).fetchall()
    out = {"en_cuenta": 0.0, "retenido": 0.0}
    for r in rows:
        if r["estado_liquidacion"] == "En Cuenta":
            out["en_cuenta"] = float(r["neto"])
        else:
            out["retenido"] = float(r["neto"])
    return out


# ---------------------------------------------------------------------------
# F29
# ---------------------------------------------------------------------------


def insert_f29(r: RegistroF29) -> int:
    with get_connection() as conn:
        return _insert(conn, "f29_registro", r)


def list_f29() -> list[dict[str, Any]]:
    with get_connection() as conn:
        return _rows(conn.execute("SELECT * FROM f29_registro WHERE usuario_id=? ORDER BY fecha DESC, id DESC", (_uid(),)))


def resumen_f29(mes: Optional[str] = None) -> dict[str, float]:
    """Suma crédito y débito. Si `mes` (YYYY-MM) se entrega, filtra por ese período."""
    with get_connection() as conn:
        if mes:
            rows = conn.execute(
                "SELECT tipo, COALESCE(SUM(monto_clp),0) AS m FROM f29_registro WHERE substr(fecha,1,7)=? AND usuario_id=? GROUP BY tipo",
                (mes, _uid()),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT tipo, COALESCE(SUM(monto_clp),0) AS m FROM f29_registro WHERE usuario_id=? GROUP BY tipo", (_uid(),)
            ).fetchall()
    out = {"credito": 0.0, "debito": 0.0}
    for r in rows:
        out["credito" if r["tipo"] == "CREDITO" else "debito"] = float(r["m"])
    return out


def ventas_netas_periodo(mes: Optional[str] = None) -> float:
    """Ventas netas (sin IVA) para base de PPM."""
    with get_connection() as conn:
        if mes:
            row = conn.execute(
                "SELECT COALESCE(SUM(cantidad*precio_unitario),0)/1.19 AS n FROM ventas WHERE substr(fecha,1,7)=? AND usuario_id=?",
                (mes, _uid()),
            ).fetchone()
        else:
            row = conn.execute("SELECT COALESCE(SUM(cantidad*precio_unitario),0)/1.19 AS n FROM ventas WHERE usuario_id=?", (_uid(),)).fetchone()
        return float(row["n"])


# ---------------------------------------------------------------------------
# Operaciones compuestas (una sola transacción)
# ---------------------------------------------------------------------------


def registrar_importacion(
    cot: Cotizacion,
    fecha_eta: date,
    dias_libres: int,
    forwarder: str,
    iva_clp: float,
    items: Optional[list[CotizacionItem]] = None,
) -> dict[str, Any]:
    """Cabecera + líneas + embarque + un ítem de inventario por línea + crédito fiscal. Todo o nada."""
    with get_connection() as conn:
        cot_id = _insert(conn, "cotizaciones", cot)
        emb_id = _insert(
            conn,
            "embarques",
            Embarque(cotizacion_id=cot_id, fecha_eta=fecha_eta.isoformat(), dias_libres=dias_libres, forwarder=forwarder),
        )
        inv_ids: list[int] = []
        if items:
            for it in items:
                it.cotizacion_id = cot_id
                item_id = _insert(conn, "cotizacion_items", it)
                inv_ids.append(
                    _insert(
                        conn,
                        "inventario",
                        InventarioItem(
                            producto=it.producto,
                            cotizacion_id=cot_id,
                            item_id=item_id,
                            producto_id=it.producto_id,
                            unidades_iniciales=it.unidades,
                            unidades_disponibles=it.unidades,
                            costo_unitario_clp=it.landed_unit_clp,
                        ),
                    )
                )
        else:
            inv_ids.append(
                _insert(
                    conn,
                    "inventario",
                    InventarioItem(
                        producto=cot.producto,
                        cotizacion_id=cot_id,
                        unidades_iniciales=cot.unidades,
                        unidades_disponibles=cot.unidades,
                        costo_unitario_clp=cot.landed_unit_clp,
                    ),
                )
            )
        f29_id = _insert(
            conn,
            "f29_registro",
            RegistroF29(
                tipo="CREDITO",
                monto_clp=round(iva_clp),
                descripcion=f"IVA importación {cot.producto}",
                referencia=f"COT-{cot_id}",
            ),
        )
    return {"cotizacion_id": cot_id, "embarque_id": emb_id, "inventario_id": inv_ids[0], "inventario_ids": inv_ids, "f29_id": f29_id}


def registrar_venta(v: Venta, dias_retencion: int) -> dict[str, int]:
    """Venta + descuento de stock + débito fiscal en una transacción."""
    if dias_retencion <= 0:
        v.estado_liquidacion = "En Cuenta"
        v.fecha_liberacion = v.fecha
    else:
        v.estado_liquidacion = "Retenido"
        v.fecha_liberacion = (date.fromisoformat(v.fecha) + timedelta(days=dias_retencion)).isoformat()
    total_bruto = v.cantidad * v.precio_unitario
    iva_debito = total_bruto - total_bruto / 1.19
    with get_connection() as conn:
        _ajustar_stock(conn, v.producto_id, -v.cantidad)
        vid = _insert(conn, "ventas", v)
        f29_id = _insert(
            conn,
            "f29_registro",
            RegistroF29(
                tipo="DEBITO",
                monto_clp=round(iva_debito),
                descripcion=f"IVA venta {v.canal} x{v.cantidad}",
                referencia=f"VTA-{vid}",
                fecha=v.fecha,
            ),
        )
    return {"venta_id": vid, "f29_id": f29_id}


# ---------------------------------------------------------------------------
# Usuarios (autenticación) — no dependen del contexto de usuario
# ---------------------------------------------------------------------------


def crear_usuario(email: str, nombre: str, password_hash: str, salt: str, rol: str = "usuario") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (email, nombre, password_hash, salt, rol, creado) VALUES (?,?,?,?,?,?)",
            (email, nombre, password_hash, salt, rol, datetime.now().isoformat(timespec="seconds")),
        )
        return int(cur.lastrowid)


def get_usuario_por_email(email: str) -> Optional[dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM usuarios WHERE email=?", (email,)).fetchone()
        return dict(row) if row else None


def get_usuario(uid: int) -> Optional[dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM usuarios WHERE id=?", (uid,)).fetchone()
        return dict(row) if row else None


def contar_usuarios() -> int:
    with get_connection() as conn:
        return int(conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0])


def listar_usuarios() -> list[dict[str, Any]]:
    _require_admin()
    with get_connection() as conn:
        return _rows(conn.execute("SELECT id, email, nombre, rol, activo, creado, ultimo_login FROM usuarios ORDER BY id"))


def actualizar_intentos(uid: int, intentos: int, bloqueado_hasta: Optional[str]) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE usuarios SET intentos_fallidos=?, bloqueado_hasta=? WHERE id=?", (intentos, bloqueado_hasta, uid))


def marcar_login(uid: int) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE usuarios SET ultimo_login=? WHERE id=?", (datetime.now().isoformat(timespec="seconds"), uid))


def actualizar_password(uid: int, password_hash: str, salt: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE usuarios SET password_hash=?, salt=? WHERE id=?", (password_hash, salt, uid))


def actualizar_perfil(uid: int, nombre: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE usuarios SET nombre=? WHERE id=?", (nombre, uid))


def set_usuario_activo(uid: int, activo: bool) -> None:
    _require_admin()
    with get_connection() as conn:
        conn.execute("UPDATE usuarios SET activo=? WHERE id=?", (int(activo), uid))


def reclamar_datos_sin_dueno(uid: int) -> None:
    """Asigna al usuario los registros creados antes de existir cuentas (migración desde v1/v2)."""
    with get_connection() as conn:
        for t in TABLAS_USUARIO:
            conn.execute(f"UPDATE {t} SET usuario_id=? WHERE usuario_id IS NULL", (uid,))


def _propio_o_admin(uid: int) -> None:
    if uid != _uid() and getattr(_ctx, "rol", None) != "admin":
        raise PermissionError("Solo puedes operar sobre tu propia cuenta")


def resumen_usuario(uid: int) -> dict[str, int]:
    _propio_o_admin(uid)
    with get_connection() as conn:
        out = {}
        for t in ("productos", "cotizaciones", "ventas"):
            out[t] = int(conn.execute(f"SELECT COUNT(*) FROM {t} WHERE usuario_id=?", (uid,)).fetchone()[0])
        return out


# ---------------------------------------------------------------------------
# Protección de datos personales (Ley 19.628 / 21.719)
# ---------------------------------------------------------------------------


def registrar_consentimiento(uid: int, tipo: str, version: str, aceptado: bool, detalle: str = "") -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO consentimientos (usuario_id, tipo, version, aceptado, fecha, detalle) VALUES (?,?,?,?,?,?)",
            (uid, tipo, version, int(aceptado), datetime.now().isoformat(timespec="seconds"), detalle),
        )


def consentimientos_usuario(uid: int) -> list[dict[str, Any]]:
    _propio_o_admin(uid)
    with get_connection() as conn:
        return _rows(conn.execute("SELECT * FROM consentimientos WHERE usuario_id=? ORDER BY fecha DESC", (uid,)))


def ultimo_consentimiento(uid: int, tipo: str) -> Optional[dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM consentimientos WHERE usuario_id=? AND tipo=? ORDER BY id DESC LIMIT 1", (uid, tipo)).fetchone()
        return dict(row) if row else None


def auditar(accion: str, detalle: str = "", uid: Optional[int] = None) -> None:
    """Bitácora de accesos y operaciones sobre datos personales (evidencia de cumplimiento)."""
    if uid is None:
        uid = getattr(_ctx, "uid", None)
    with get_connection() as conn:
        conn.execute("INSERT INTO auditoria (usuario_id, fecha, accion, detalle) VALUES (?,?,?,?)", (uid, datetime.now().isoformat(timespec="seconds"), accion, detalle[:500]))


def auditoria_usuario(uid: int, limite: int = 200) -> list[dict[str, Any]]:
    _propio_o_admin(uid)
    with get_connection() as conn:
        return _rows(conn.execute("SELECT * FROM auditoria WHERE usuario_id=? ORDER BY id DESC LIMIT ?", (uid, limite)))


def auditoria_global(limite: int = 500) -> list[dict[str, Any]]:
    _require_admin()
    with get_connection() as conn:
        return _rows(conn.execute("SELECT a.*, u.email FROM auditoria a LEFT JOIN usuarios u ON u.id=a.usuario_id ORDER BY a.id DESC LIMIT ?", (limite,)))


def crear_solicitud(uid: int, derecho: str, detalle: str, plazo_dias: int) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO solicitudes_derechos (usuario_id, derecho, detalle, fecha, plazo) VALUES (?,?,?,?,?)",
            (uid, derecho, detalle, date.today().isoformat(), (date.today() + timedelta(days=plazo_dias)).isoformat()),
        )
        return int(cur.lastrowid)


def solicitudes(uid: Optional[int] = None) -> list[dict[str, Any]]:
    if uid is None:
        _require_admin()
    elif uid != _uid():
        raise PermissionError("No puedes ver las solicitudes de otra persona")
    with get_connection() as conn:
        if uid is None:
            return _rows(conn.execute("SELECT s.*, u.email FROM solicitudes_derechos s JOIN usuarios u ON u.id=s.usuario_id ORDER BY s.estado='Pendiente' DESC, s.plazo"))
        return _rows(conn.execute("SELECT * FROM solicitudes_derechos WHERE usuario_id=? ORDER BY id DESC", (uid,)))


def responder_solicitud(sid: int, estado: str, respuesta: str) -> None:
    _require_admin()
    with get_connection() as conn:
        conn.execute("UPDATE solicitudes_derechos SET estado=?, respuesta=?, fecha_respuesta=? WHERE id=?", (estado, respuesta, date.today().isoformat(), sid))


def crear_incidente(d: dict[str, Any]) -> int:
    _require_admin()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO incidentes (fecha_deteccion, descripcion, datos_afectados, usuarios_afectados, riesgo, medidas, creado_por) VALUES (?,?,?,?,?,?,?)",
            (d["fecha_deteccion"], d["descripcion"], d.get("datos_afectados", ""), int(d.get("usuarios_afectados", 0)), d.get("riesgo", "Medio"), d.get("medidas", ""), d.get("creado_por")),
        )
        return int(cur.lastrowid)


def listar_incidentes() -> list[dict[str, Any]]:
    _require_admin()
    with get_connection() as conn:
        return _rows(conn.execute("SELECT * FROM incidentes ORDER BY estado='Abierto' DESC, fecha_deteccion DESC"))


COLUMNAS_INCIDENTE = {"descripcion", "datos_afectados", "usuarios_afectados", "riesgo", "medidas",
                      "notificado_agencia", "fecha_notificacion_agencia", "notificado_titulares",
                      "fecha_notificacion_titulares", "estado"}


def actualizar_incidente(iid: int, campos: dict[str, Any]) -> None:
    _require_admin()
    campos = {k: v for k, v in campos.items() if k in COLUMNAS_INCIDENTE}
    if not campos:
        return
    sets = ", ".join(f"{k}=?" for k in campos)
    with get_connection() as conn:
        conn.execute(f"UPDATE incidentes SET {sets} WHERE id=?", (*campos.values(), iid))


def exportar_datos_usuario(uid: int) -> dict[str, Any]:
    """Derecho de acceso y portabilidad: todo lo que la app guarda sobre la persona, en formato abierto."""
    _propio_o_admin(uid)
    with get_connection() as conn:
        u = dict(conn.execute("SELECT id, email, nombre, rol, creado, ultimo_login FROM usuarios WHERE id=?", (uid,)).fetchone())
        out: dict[str, Any] = {"usuario": u, "exportado": datetime.now().isoformat(timespec="seconds")}
        for t in TABLAS_USUARIO:
            out[t] = _rows(conn.execute(f"SELECT * FROM {t} WHERE usuario_id=?", (uid,)))
        out["config"] = _rows(conn.execute("SELECT clave, valor, actualizado FROM config_usuario WHERE usuario_id=?", (uid,)))
        out["consentimientos"] = _rows(conn.execute("SELECT * FROM consentimientos WHERE usuario_id=?", (uid,)))
        out["solicitudes_derechos"] = _rows(conn.execute("SELECT * FROM solicitudes_derechos WHERE usuario_id=?", (uid,)))
        out["auditoria"] = _rows(conn.execute("SELECT fecha, accion, detalle FROM auditoria WHERE usuario_id=? ORDER BY id DESC LIMIT 1000", (uid,)))
        return out


def eliminar_cuenta(uid: int, hash_email: str) -> dict[str, int]:
    """Derecho de supresión: borra todos los datos del usuario. En la bitácora queda solo un hash del correo."""
    _propio_o_admin(uid)
    borrados: dict[str, int] = {}
    with get_connection() as conn:
        # Orden respeta las claves foráneas
        for t in ("ventas", "inventario", "cotizacion_items", "embarques", "cotizaciones", "productos", "f29_registro"):
            borrados[t] = conn.execute(f"DELETE FROM {t} WHERE usuario_id=?", (uid,)).rowcount
        for t in ("config_usuario", "consentimientos", "solicitudes_derechos"):
            borrados[t] = conn.execute(f"DELETE FROM {t} WHERE usuario_id=?", (uid,)).rowcount
        conn.execute("UPDATE auditoria SET usuario_id=NULL, detalle=? WHERE usuario_id=?", (f"titular suprimido {hash_email}", uid))
        conn.execute("DELETE FROM usuarios WHERE id=?", (uid,))
        conn.execute("INSERT INTO auditoria (usuario_id, fecha, accion, detalle) VALUES (NULL,?,?,?)", (datetime.now().isoformat(timespec="seconds"), "supresion_cuenta", f"titular {hash_email}: " + ", ".join(f"{k}={v}" for k, v in borrados.items())))
    return borrados


def cuentas_inactivas(meses: int) -> list[dict[str, Any]]:
    _require_admin()
    limite = (datetime.now() - timedelta(days=30 * meses)).isoformat()
    with get_connection() as conn:
        return _rows(conn.execute("SELECT id, email, nombre, creado, ultimo_login FROM usuarios WHERE COALESCE(ultimo_login, creado) < ? AND rol != 'admin'", (limite,)))


def estadisticas_tratamiento() -> dict[str, int]:
    _require_admin()
    with get_connection() as conn:
        return {
            "usuarios": int(conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]),
            "consentimientos": int(conn.execute("SELECT COUNT(*) FROM consentimientos WHERE aceptado=1").fetchone()[0]),
            "solicitudes_pendientes": int(conn.execute("SELECT COUNT(*) FROM solicitudes_derechos WHERE estado='Pendiente'").fetchone()[0]),
            "incidentes_abiertos": int(conn.execute("SELECT COUNT(*) FROM incidentes WHERE estado='Abierto'").fetchone()[0]),
            "eventos_auditoria": int(conn.execute("SELECT COUNT(*) FROM auditoria").fetchone()[0]),
        }


# ---------------------------------------------------------------------------
# Borradores / guardado automático (por usuario)
# ---------------------------------------------------------------------------


def guardar_borrador(clave: str, datos: Any) -> None:
    import json
    set_config(f"borrador_{clave}", json.dumps(datos, ensure_ascii=False, default=str))


def cargar_borrador(clave: str) -> Any:
    import json
    raw = get_config(f"borrador_{clave}", "")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Gastos y compras nacionales (generan crédito fiscal si hay factura)
# ---------------------------------------------------------------------------


def registrar_gasto(g: Gasto) -> dict[str, int]:
    with get_connection() as conn:
        gid = _insert(conn, "gastos", g)
        f29_id = 0
        if g.documento == "Factura" and g.iva > 0:
            f29_id = _insert(conn, "f29_registro", RegistroF29(tipo="CREDITO", monto_clp=round(g.iva), descripcion=f"IVA compra {g.categoria}: {g.descripcion or g.proveedor}", referencia=f"GAS-{gid}", fecha=g.fecha))
    return {"gasto_id": gid, "f29_id": f29_id}


def list_gastos(mes: Optional[str] = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if mes:
            return _rows(conn.execute("SELECT * FROM gastos WHERE usuario_id=? AND substr(fecha,1,7)=? ORDER BY fecha DESC, id DESC", (_uid(), mes)))
        return _rows(conn.execute("SELECT * FROM gastos WHERE usuario_id=? ORDER BY fecha DESC, id DESC", (_uid(),)))


def eliminar_gasto(gid: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM f29_registro WHERE referencia=? AND usuario_id=?", (f"GAS-{gid}", _uid()))
        conn.execute("DELETE FROM gastos WHERE id=? AND usuario_id=?", (gid, _uid()))


def costos_fijos_mensuales() -> float:
    """Suma neta de los gastos marcados como recurrentes (base para el punto de equilibrio mensual)."""
    with get_connection() as conn:
        row = conn.execute("SELECT COALESCE(SUM(neto),0) FROM gastos WHERE usuario_id=? AND recurrente=1", (_uid(),)).fetchone()
        return float(row[0])


# ---------------------------------------------------------------------------
# Eliminar cotización / embarque
# ---------------------------------------------------------------------------


def ventas_de_cotizacion(cid: int) -> int:
    with get_connection() as conn:
        return int(conn.execute("SELECT COUNT(*) FROM ventas v JOIN inventario i ON i.id=v.producto_id WHERE i.cotizacion_id=? AND v.usuario_id=?", (cid, _uid())).fetchone()[0])


def eliminar_cotizacion(cid: int, forzar: bool = False) -> dict[str, int]:
    """Borra cotización, líneas, embarque, inventario y el crédito fiscal asociado.
    Si hay ventas registradas se rechaza salvo `forzar` (entonces también se borran las ventas y sus débitos)."""
    uid = _uid()
    n_ventas = ventas_de_cotizacion(cid)
    if n_ventas and not forzar:
        raise ValueError(f"La cotización tiene {n_ventas} {'venta registrada' if n_ventas == 1 else 'ventas registradas'}. Elimínalas primero o confirma el borrado completo.")
    out: dict[str, int] = {}
    with get_connection() as conn:
        if n_ventas:
            vids = [r["id"] for r in conn.execute("SELECT v.id FROM ventas v JOIN inventario i ON i.id=v.producto_id WHERE i.cotizacion_id=? AND v.usuario_id=?", (cid, uid))]
            for vid in vids:
                conn.execute("DELETE FROM f29_registro WHERE referencia=? AND usuario_id=?", (f"VTA-{vid}", uid))
            out["ventas"] = conn.execute(f"DELETE FROM ventas WHERE id IN ({','.join('?'*len(vids))}) AND usuario_id=?", (*vids, uid)).rowcount if vids else 0
        out["inventario"] = conn.execute("DELETE FROM inventario WHERE cotizacion_id=? AND usuario_id=?", (cid, uid)).rowcount
        out["items"] = conn.execute("DELETE FROM cotizacion_items WHERE cotizacion_id=? AND usuario_id=?", (cid, uid)).rowcount
        out["embarques"] = conn.execute("DELETE FROM embarques WHERE cotizacion_id=? AND usuario_id=?", (cid, uid)).rowcount
        out["f29"] = conn.execute("DELETE FROM f29_registro WHERE referencia=? AND usuario_id=?", (f"COT-{cid}", uid)).rowcount
        out["cotizacion"] = conn.execute("DELETE FROM cotizaciones WHERE id=? AND usuario_id=?", (cid, uid)).rowcount
    return out


# ---------------------------------------------------------------------------
# Libro de ventas / compras y F29 mensual
# ---------------------------------------------------------------------------


def meses_con_movimiento() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT substr(fecha,1,7) AS m FROM (SELECT fecha, usuario_id FROM ventas UNION ALL SELECT fecha, usuario_id FROM gastos UNION ALL SELECT fecha, usuario_id FROM f29_registro) WHERE usuario_id=? ORDER BY m DESC",
            (_uid(),),
        ).fetchall()
        return [r["m"] for r in rows]


def libro_ventas(mes: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        return _rows(conn.execute(
            """SELECT v.fecha, v.documento, v.folio, i.producto, v.cantidad, v.canal,
                      ROUND(v.cantidad*v.precio_unitario/1.19) AS neto,
                      ROUND(v.cantidad*v.precio_unitario - v.cantidad*v.precio_unitario/1.19) AS iva,
                      ROUND(v.cantidad*v.precio_unitario) AS total
               FROM ventas v JOIN inventario i ON i.id=v.producto_id
               WHERE v.usuario_id=? AND substr(v.fecha,1,7)=? ORDER BY v.fecha, v.id""", (_uid(), mes)))


def libro_compras(mes: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        compras = _rows(conn.execute("SELECT fecha, documento, folio, proveedor, categoria AS detalle, neto, iva, total FROM gastos WHERE usuario_id=? AND substr(fecha,1,7)=? ORDER BY fecha, id", (_uid(), mes)))
        imports = _rows(conn.execute(
            """SELECT c.fecha, 'DIN' AS documento, 'COT-'||c.id AS folio, 'Aduana de Chile' AS proveedor, c.producto AS detalle,
                      ROUND((c.cif_usd + c.advalorem_usd)*c.tipo_cambio) AS neto, ROUND(c.iva_usd*c.tipo_cambio) AS iva,
                      ROUND((c.cif_usd + c.advalorem_usd + c.iva_usd)*c.tipo_cambio) AS total
               FROM cotizaciones c WHERE c.usuario_id=? AND substr(c.fecha,1,7)=? ORDER BY c.fecha""", (_uid(), mes)))
        return compras + imports


def resumen_f29_mensual(mes: str) -> dict[str, float]:
    """Débito y crédito del mes, y remanente acumulado de meses anteriores."""
    with get_connection() as conn:
        deb = float(conn.execute("SELECT COALESCE(SUM(monto_clp),0) FROM f29_registro WHERE usuario_id=? AND tipo='DEBITO' AND substr(fecha,1,7)=?", (_uid(), mes)).fetchone()[0])
        cre = float(conn.execute("SELECT COALESCE(SUM(monto_clp),0) FROM f29_registro WHERE usuario_id=? AND tipo='CREDITO' AND substr(fecha,1,7)=?", (_uid(), mes)).fetchone()[0])
        deb_ant = float(conn.execute("SELECT COALESCE(SUM(monto_clp),0) FROM f29_registro WHERE usuario_id=? AND tipo='DEBITO' AND substr(fecha,1,7)<?", (_uid(), mes)).fetchone()[0])
        cre_ant = float(conn.execute("SELECT COALESCE(SUM(monto_clp),0) FROM f29_registro WHERE usuario_id=? AND tipo='CREDITO' AND substr(fecha,1,7)<?", (_uid(), mes)).fetchone()[0])
        ventas_netas = float(conn.execute("SELECT COALESCE(SUM(cantidad*precio_unitario),0)/1.19 FROM ventas WHERE usuario_id=? AND substr(fecha,1,7)=?", (_uid(), mes)).fetchone()[0])
    remanente = max(0.0, cre_ant - deb_ant)
    return {"debito": deb, "credito": cre, "remanente_anterior": remanente, "ventas_netas": ventas_netas}


# ---------------------------------------------------------------------------
# Cotizaciones de flete
# ---------------------------------------------------------------------------


def upsert_flete(f: Flete) -> int:
    data = {k: v for k, v in asdict(f).items() if k != "id"}
    with get_connection() as conn:
        if f.id:
            sets = ", ".join(f"{k}=?" for k in data)
            conn.execute(f"UPDATE fletes SET {sets} WHERE id=? AND usuario_id=?", (*data.values(), f.id, _uid()))
            return f.id
        return _insert(conn, "fletes", f)


def list_fletes() -> list[dict[str, Any]]:
    with get_connection() as conn:
        return _rows(conn.execute("SELECT * FROM fletes WHERE usuario_id=? ORDER BY favorito DESC, id", (_uid(),)))


def eliminar_flete(fid: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM fletes WHERE id=? AND usuario_id=?", (fid, _uid()))


def marcar_favorito_flete(fid: int) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE fletes SET favorito=0 WHERE usuario_id=?", (_uid(),))
        conn.execute("UPDATE fletes SET favorito=1 WHERE id=? AND usuario_id=?", (fid, _uid()))


# ---------------------------------------------------------------------------
# Hitos (recorrido del emprendedor)
# ---------------------------------------------------------------------------


def marcar_hito(clave: str) -> bool:
    """Devuelve True si el hito se logró por primera vez ahora."""
    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM hitos WHERE usuario_id=? AND clave=?", (_uid(), clave)).fetchone()
        if row:
            return False
        conn.execute("INSERT INTO hitos (usuario_id, clave, fecha) VALUES (?,?,?)", (_uid(), clave, datetime.now().isoformat(timespec="seconds")))
        return True


def hitos_logrados() -> dict[str, str]:
    with get_connection() as conn:
        return {r["clave"]: r["fecha"] for r in conn.execute("SELECT clave, fecha FROM hitos WHERE usuario_id=?", (_uid(),))}
