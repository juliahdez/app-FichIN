#!/usr/bin/env python3
"""FichIN: API de fichaje del proyecto docente. Solo HTTPS.

Arranque: PUERTO=8443 CERT=cert.pem CLAVE=clave.pem python3 servidor.py
Los fichajes persisten en fichin.db. Las sesiones se mantienen en memoria.
Se conserva el contrato JSON de Android para /api/elementos.
Las cuentas son de prueba; no utilizar este servidor con datos reales.
"""

import hashlib
import hmac
import json
import math
import os
import re
import secrets
import sqlite3
import ssl
import threading
import time
from collections import deque
from contextlib import closing
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PUERTO = int(os.environ.get("PUERTO", "8443"))
HOST = os.environ.get("HOST", "0.0.0.0")
CERT = os.environ.get("CERT")
CLAVE = os.environ.get("CLAVE")
RUTA_BD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fichin.db")

# PBKDF2-HMAC-SHA256, con una sal aleatoria distinta por cuenta.
# Solo se almacenan sales y verificadores, nunca contrasenas en claro.
ITERACIONES = 600_000
USUARIOS = {
    "ana": {
        "nombre": "Ana Ruiz", "rol": "usuario",
        "sal": "98f014755d735cd4fe613dff33e380b7",
        "hash": "d80a824c12a48a52eeeafebd7e6340cdd60c9f5e9244a89c8dc871d766fd4d6c",
    },
    "luis": {
        "nombre": "Luis Moreno", "rol": "usuario",
        "sal": "c3ef71b80aa2aced6515abd27b848ad8",
        "hash": "6dfc82e0fe268ff2acbbb8d80c7fa52211ea9fa506c80632730ce01d129f1e6c",
    },
}
# Mismo coste criptografico para cuentas que no existen.
VERIFICADOR_FICTICIO = {
    "sal": "32a09c549aaa8d2e6eaf301bb94db1f9",
    "hash": "66a96cc7d8e3544efb9a4ca16b9b7d86cae2809b646d363b011b6b29ee3476e3",
}

# Caducidad absoluta de 8 h y por inactividad de 30 min, en el servidor.
# El parametro de entorno permite acortar la duracion en pruebas aisladas.
DURACION_SESION = int(os.environ.get("FICHIN_SESSION_TTL_SECONDS", "28800"))
if not 1 <= DURACION_SESION <= 28800:
    raise SystemExit("Duracion de sesion no valida (1 a 28800 segundos).")
INACTIVIDAD_SESION = 1800
MAX_SESIONES = 4096
SESIONES = {}  # SHA-256(token) -> (usuario, caducidad absoluta, ultimo acceso)
LOCK_SESIONES = threading.Lock()

# Limite de intentos de login (incluye exitos): por cuenta y por IP.
# Se usa la IP de la conexion, nunca una cabecera enviada por el cliente.
VENTANA_LOGIN = 60
MAX_POR_CUENTA = 5
MAX_POR_IP = 30
MAX_CONTADORES = 4096
INTENTOS = {}  # (tipo, identificador) -> deque de tiempos monotonic
LOCK_INTENTOS = threading.Lock()


def verificar_clave(usuario, clave):
    cuenta = USUARIOS.get(usuario)
    datos = cuenta if cuenta is not None else VERIFICADOR_FICTICIO
    calculado = hashlib.pbkdf2_hmac(
        "sha256", clave.encode("utf-8"), bytes.fromhex(datos["sal"]), ITERACIONES
    )
    coincide = hmac.compare_digest(calculado, bytes.fromhex(datos["hash"]))
    return cuenta is not None and coincide


def reservar_intento(usuario, ip):
    """Devuelve 0 si admite el intento, o los segundos hasta poder reintentar."""
    ahora = time.monotonic()
    with LOCK_INTENTOS:
        # Retirar entradas antiguas para limitar el consumo de memoria.
        for k in list(INTENTOS):
            cola = INTENTOS[k]
            while cola and ahora - cola[0] >= VENTANA_LOGIN:
                cola.popleft()
            if not cola:
                del INTENTOS[k]
        claves = (("cuenta", usuario), ("ip", ip))
        espera = 0
        for k, limite in zip(claves, (MAX_POR_CUENTA, MAX_POR_IP)):
            cola = INTENTOS.get(k)
            if cola and len(cola) >= limite:
                espera = max(espera, math.ceil(VENTANA_LOGIN - (ahora - cola[0])))
        if espera:
            return espera
        if len(INTENTOS) + sum(k not in INTENTOS for k in claves) > MAX_CONTADORES:
            return VENTANA_LOGIN
        # Reservar antes de calcular el hash evita saltarse el limite en paralelo.
        for k in claves:
            INTENTOS.setdefault(k, deque()).append(ahora)
        return 0


def _hash_token(token):
    return hashlib.sha256(token.encode("ascii")).digest()


def _caducada(sesion, ahora):
    _, fin, ultimo = sesion
    return ahora >= fin or ahora - ultimo >= INACTIVIDAD_SESION


def crear_sesion(usuario):
    ahora = time.monotonic()
    with LOCK_SESIONES:
        for k, sesion in list(SESIONES.items()):
            if _caducada(sesion, ahora):
                del SESIONES[k]
        if len(SESIONES) >= MAX_SESIONES:
            return None
        token = secrets.token_urlsafe(32)
        SESIONES[_hash_token(token)] = (usuario, ahora + DURACION_SESION, ahora)
        return token


def resolver_sesion(token, revocar=False):
    if token is None:
        return None
    clave = _hash_token(token)
    ahora = time.monotonic()
    with LOCK_SESIONES:
        sesion = SESIONES.get(clave)
        if sesion is None:
            return None
        if _caducada(sesion, ahora):
            del SESIONES[clave]
            return None
        usuario, fin, _ = sesion
        if revocar:
            del SESIONES[clave]
        else:
            SESIONES[clave] = (usuario, fin, ahora)
        return usuario


def conectar_bd():
    db = sqlite3.connect(RUTA_BD, timeout=10)
    db.row_factory = sqlite3.Row
    return db


def inicializar_bd():
    # Conserva el esquema anterior; no borra ni reinicia los fichajes.
    with closing(conectar_bd()) as db, db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS fichajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                propietario TEXT NOT NULL,
                tipo TEXT NOT NULL CHECK (tipo IN ('Entrada', 'Salida')),
                latitud REAL NOT NULL CHECK (latitud BETWEEN -90 AND 90),
                longitud REAL NOT NULL CHECK (longitud BETWEEN -180 AND 180),
                fecha TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_fichajes_propietario
            ON fichajes(propietario, id)
        """)
    if os.name == "posix":
        os.chmod(RUTA_BD, 0o600)


def ficha_json(fila):
    return {
        "id": fila["id"],
        "titulo": fila["tipo"],
        "contenido": "Latitud: %.6f, longitud: %.6f" % (fila["latitud"], fila["longitud"]),
        "fecha": fila["fecha"],
    }


def _sin_duplicados(pares):
    obj = {}
    for k, v in pares:
        if k in obj:
            raise ValueError("Campo duplicado")
        obj[k] = v
    return obj


def _constante_invalida(_):
    raise ValueError("Numero no valido")


class Manejador(BaseHTTPRequestHandler):
    server_version = "FichIN"
    sys_version = ""

    def version_string(self):
        return self.server_version

    def _responder(self, codigo, cuerpo, espera=None):
        datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Connection", "close")
        if espera is not None:
            self.send_header("Retry-After", str(espera))
        self.end_headers()
        self.close_connection = True
        self.wfile.write(datos)

    def send_error(self, code, message=None, explain=None):
        # No reflejar la peticion ni los detalles internos en errores HTTP.
        self._responder(code, {"error": "Peticion no valida"})

    def _cuerpo(self):
        # Solo objetos JSON pequenos, sin campos duplicados ni NaN/Infinity.
        try:
            if self.headers.get("Transfer-Encoding") is not None:
                return None
            if len(self.headers.get_all("Content-Length", [])) != 1:
                return None
            largo = int(self.headers.get("Content-Length", "0"))
            if not 0 < largo <= 8192:
                return None
            if self.headers.get_content_type() != "application/json":
                return None
            bruto = self.rfile.read(largo)
            if len(bruto) != largo:
                return None
            cuerpo = json.loads(bruto.decode("utf-8"),
                                object_pairs_hook=_sin_duplicados,
                                parse_constant=_constante_invalida)
            return cuerpo if isinstance(cuerpo, dict) else None
        except (ValueError, UnicodeError, RecursionError, OSError):
            return None

    def _token(self):
        valores = self.headers.get_all("Authorization", [])
        if len(valores) != 1:
            return None
        m = re.fullmatch(r"Bearer ([A-Za-z0-9_-]{43})", valores[0], re.IGNORECASE)
        return m.group(1) if m else None

    def _usuario_autenticado(self):
        return resolver_sesion(self._token())

    def log_request(self, code="-", size="-"):
        # Solo rutas conocidas y estado, nunca la URL cruda, cabeceras ni cuerpos.
        ruta = getattr(self, "path", "").split("?")[0]
        conocidas = {"/api/salud", "/api/login", "/api/logout", "/api/elementos", "/api/perfil"}
        if re.fullmatch(r"/api/elementos/[0-9]{1,10}", ruta):
            ruta = "/api/elementos/{id}"
        elif ruta not in conocidas:
            ruta = "ruta desconocida"
        metodo = getattr(self, "command", "")
        if metodo not in ("GET", "POST"):
            metodo = "OTRO"
        print("[%s] %s %s %s" % (self.log_date_time_string(), metodo, ruta, code), flush=True)

    def log_error(self, formato, *args):
        print("Error en una peticion HTTP", flush=True)

    def do_GET(self):
        try:
            self._get()
        except sqlite3.Error:
            self._responder(503, {"error": "Servicio no disponible"})

    def _get(self):
        ruta = self.path.split("?")[0]
        if ruta == "/api/salud":
            return self._responder(200, {"estado": "ok", "servicio": "FichIN"})

        if ruta == "/api/elementos":
            usuario = self._usuario_autenticado()
            if usuario is None:
                return self._responder(401, {"error": "Sesion no valida"})
            with closing(conectar_bd()) as db:
                filas = db.execute(
                    "SELECT * FROM fichajes WHERE propietario = ? ORDER BY id DESC",
                    (usuario,),
                ).fetchall()
            return self._responder(200, {"elementos": [ficha_json(f) for f in filas]})

        if ruta == "/api/perfil":
            usuario = self._usuario_autenticado()
            if usuario is None:
                return self._responder(401, {"error": "Sesion no valida"})
            u = USUARIOS[usuario]
            # Solo los campos que utiliza la aplicacion. No se guardan DNI ni correo.
            return self._responder(200, {"usuario": usuario, "nombre": u["nombre"], "rol": u["rol"]})

        m = re.fullmatch(r"/api/elementos/([0-9]{1,10})", ruta)
        if m:
            usuario = self._usuario_autenticado()
            if usuario is None:
                return self._responder(401, {"error": "Sesion no valida"})
            idn = int(m.group(1))
            with closing(conectar_bd()) as db:
                fila = db.execute(
                    "SELECT * FROM fichajes WHERE id = ? AND propietario = ?",
                    (idn, usuario),
                ).fetchone()
            if fila is None:
                return self._responder(404, {"error": "No encontrado"})
            return self._responder(200, ficha_json(fila))

        # Se ha retirado /api/admin/usuarios: no existe funcion administrativa.
        return self._responder(404, {"error": "Ruta no encontrada"})

    def do_POST(self):
        try:
            self._post()
        except sqlite3.Error:
            self._responder(503, {"error": "Servicio no disponible"})

    def _post(self):
        ruta = self.path.split("?")[0]

        if ruta == "/api/logout":
            if resolver_sesion(self._token(), revocar=True) is None:
                return self._responder(401, {"error": "Sesion no valida"})
            return self._responder(200, {"estado": "ok"})

        if ruta == "/api/login":
            cuerpo = self._cuerpo()
            if cuerpo is None or set(cuerpo) != {"usuario", "clave"}:
                return self._responder(400, {"error": "Peticion no valida"})
            usuario, clave = cuerpo["usuario"], cuerpo["clave"]
            if not isinstance(usuario, str) or not isinstance(clave, str):
                return self._responder(400, {"error": "Peticion no valida"})
            usuario = usuario.strip().lower()
            try:
                if not 1 <= len(usuario) <= 64 or not 1 <= len(clave.encode("utf-8")) <= 1024:
                    return self._responder(400, {"error": "Peticion no valida"})
                usuario.encode("utf-8")
            except UnicodeError:
                return self._responder(400, {"error": "Peticion no valida"})
            espera = reservar_intento(usuario, self.client_address[0])
            if espera:
                return self._responder(429, {"error": "Demasiados intentos. Intentalo mas tarde"}, espera)
            if not verificar_clave(usuario, clave):
                return self._responder(401, {"error": "Credenciales no validas"})
            token = crear_sesion(usuario)
            if token is None:
                return self._responder(503, {"error": "Servicio no disponible"})
            return self._responder(200, {
                "token": token, "usuario": usuario,
                "nombre": USUARIOS[usuario]["nombre"], "rol": USUARIOS[usuario]["rol"],
            })

        if ruta == "/api/elementos":
            usuario = self._usuario_autenticado()
            if usuario is None:
                return self._responder(401, {"error": "Sesion no valida"})
            cuerpo = self._cuerpo()
            # El propietario se obtiene exclusivamente de la sesion autenticada.
            # El cliente no puede escoger propietario, ID ni fecha.
            if cuerpo is None or set(cuerpo) != {"tipo", "latitud", "longitud"}:
                return self._responder(400, {"error": "Campos de fichaje no validos"})
            tipo, latitud, longitud = cuerpo["tipo"], cuerpo["latitud"], cuerpo["longitud"]
            if tipo not in ("Entrada", "Salida"):
                return self._responder(400, {"error": "Tipo de fichaje no valido"})
            if (type(latitud) not in (int, float) or type(longitud) not in (int, float)
                    or not -90 <= latitud <= 90 or not -180 <= longitud <= 180):
                return self._responder(400, {"error": "Ubicacion no valida"})

            # Serializa la comprobacion y la escritura para evitar carreras.
            with closing(conectar_bd()) as db, db:
                db.execute("BEGIN IMMEDIATE")
                ultimo = db.execute(
                    "SELECT tipo FROM fichajes WHERE propietario = ? ORDER BY id DESC LIMIT 1",
                    (usuario,),
                ).fetchone()
                esperado = "Salida" if ultimo and ultimo["tipo"] == "Entrada" else "Entrada"
                if tipo != esperado:
                    nuevo = None
                else:
                    fecha = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
                    cursor = db.execute(
                        "INSERT INTO fichajes (propietario, tipo, latitud, longitud, fecha) VALUES (?, ?, ?, ?, ?)",
                        (usuario, tipo, latitud, longitud, fecha),
                    )
                    fila = db.execute("SELECT * FROM fichajes WHERE id = ?", (cursor.lastrowid,)).fetchone()
                    nuevo = ficha_json(fila)
            if nuevo is None:
                return self._responder(409, {"error": "La operacion no corresponde al estado de la jornada"})
            return self._responder(201, nuevo)

        return self._responder(404, {"error": "Ruta no encontrada"})


class ServidorTLS(ThreadingHTTPServer):
    # Limites modestos de recursos para el laboratorio. No es un servidor de produccion.
    daemon_threads = True
    request_queue_size = 32

    def __init__(self, direccion, contexto):
        self.contexto = contexto
        self.plazas = threading.BoundedSemaphore(32)
        super().__init__(direccion, Manejador)

    def get_request(self):
        conexion, direccion = super().get_request()
        try:
            conexion.settimeout(10)
            # El handshake ocurre en el hilo de la peticion, no en el hilo de aceptacion.
            tls = self.contexto.wrap_socket(conexion, server_side=True,
                                            do_handshake_on_connect=False)
            return tls, direccion
        except BaseException:
            conexion.close()
            raise

    def process_request(self, request, client_address):
        if not self.plazas.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.plazas.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.plazas.release()

    def handle_error(self, request, client_address):
        print("Conexion interrumpida o peticion no valida", flush=True)


def main():
    if not CERT or not CLAVE:
        raise SystemExit("HTTPS obligatorio. Define CERT y CLAVE antes de arrancar.")
    contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    contexto.minimum_version = ssl.TLSVersion.TLSv1_2
    try:
        contexto.load_cert_chain(certfile=CERT, keyfile=CLAVE)
    except (OSError, ssl.SSLError):
        raise SystemExit("No se han podido cargar los certificados TLS.") from None
    # Restringe los nuevos archivos de datos al usuario del proceso en Unix.
    if os.name == "posix":
        os.umask(0o077)
    inicializar_bd()
    with ServidorTLS((HOST, PUERTO), contexto) as servidor:
        print("FichIN escuchando en https://%s:%d" % (HOST, PUERTO), flush=True)
        print("Usuarios de prueba: ana / luis", flush=True)
        try:
            servidor.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
