#!/usr/bin/env python3
"""Pruebas de FichIN en una copia temporal; no modifica fichin.db real.
Ejecutar junto a servidor.py, cert.pem, clave.pem y ca.pem.
"""
import concurrent.futures
import getpass
import http.client
import json
import os
from pathlib import Path
import secrets
import runpy
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager

BASE = Path(__file__).resolve().parent


def comprobar(condicion, titulo):
    if not condicion:
        raise AssertionError(titulo)
    print("OK - " + titulo, flush=True)


def puerto_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def ejecutar():
    for nombre in ("servidor.py", "ca.pem", "cert.pem", "clave.pem"):
        if not (BASE / nombre).is_file():
            raise SystemExit("Falta " + nombre + " junto al script de pruebas.")
    clave = os.environ.get("FICHIN_TEST_PASSWORD") or getpass.getpass(
        "Contrasena de prueba compartida por ana y luis: "
    )
    contexto = ssl.create_default_context(cafile=str(BASE / "ca.pem"))
    # El script docente incluye 127.0.0.1 como SAN del certificado.
    host = "127.0.0.1"
    tokens = []

    with tempfile.TemporaryDirectory(prefix="fichin-pruebas-") as tmp:
        carpeta = Path(tmp)
        servidor = carpeta / "servidor.py"
        shutil.copy2(BASE / "servidor.py", servidor)
        env = os.environ.copy()
        for nombre in ("CERT", "CLAVE", "PUERTO", "HOST", "FICHIN_SESSION_TTL_SECONDS"):
            env.pop(nombre, None)
        sin_tls = subprocess.run([sys.executable, str(servidor)], env=env,
                                 capture_output=True, text=True, timeout=5)
        comprobar(sin_tls.returncode != 0 and "HTTPS obligatorio" in sin_tls.stderr,
                  "Arranque sin TLS rechazado")
        codigo = runpy.run_path(str(servidor))
        cuentas = codigo["USUARIOS"]
        comprobar(set(cuentas) == {"ana", "luis"}, "Solo existen las cuentas necesarias")
        comprobar(all("clave" not in u and len(bytes.fromhex(u["sal"])) == 16 for u in cuentas.values())
                  and len({u["sal"] for u in cuentas.values()}) == len(cuentas)
                  and cuentas["ana"]["hash"] != cuentas["luis"]["hash"],
                  "Verificadores con sales distintas, sin campos de contrasena en claro")
        comprobar(codigo["_caducada"](("ana", 28800, 0), 1800)
                  and not codigo["_caducada"](("ana", 28800, 0), 1799),
                  "Regla de caducidad por inactividad (prueba de funcion)")
        env_tls = dict(env, CERT=str(BASE / "cert.pem"), CLAVE=str(BASE / "clave.pem"), HOST=host)
        bad = subprocess.run([sys.executable, str(servidor)],
                             env=dict(env_tls, CERT=str(carpeta / "no-existe.pem")),
                             capture_output=True, text=True, timeout=5)
        comprobar(bad.returncode != 0 and "certificados TLS" in bad.stderr,
                  "Certificado inexistente rechazado")

        def peticion(puerto, metodo, ruta, datos=None, token=None, ctx=contexto):
            headers = {}
            if token is not None:
                headers["Authorization"] = "Bearer " + token
            cuerpo = None
            if datos is not None:
                headers["Content-Type"] = "application/json"
                cuerpo = json.dumps(datos).encode()
            conn = http.client.HTTPSConnection(host, puerto, context=ctx, timeout=5)
            try:
                conn.request(metodo, ruta, body=cuerpo, headers=headers)
                r = conn.getresponse()
                resultado = (r.status, json.loads(r.read()), dict(r.getheaders()))
                return resultado
            finally:
                conn.close()

        @contextmanager
        def arrancar(ttl=28800):
            puerto = puerto_libre()
            log = carpeta / ("servidor-%d.log" % puerto)
            with log.open("wb") as salida:
                p = subprocess.Popen([sys.executable, str(servidor)],
                                     env=dict(env_tls, PUERTO=str(puerto), FICHIN_SESSION_TTL_SECONDS=str(ttl)),
                                     stdout=salida, stderr=subprocess.STDOUT)
                try:
                    inicio = time.monotonic()
                    while True:
                        if p.poll() is not None:
                            raise RuntimeError("No arranca el servidor: " + log.read_text())
                        try:
                            if peticion(puerto, "GET", "/api/salud")[0] == 200:
                                break
                        except (OSError, http.client.HTTPException):
                            pass
                        if time.monotonic() - inicio > 8:
                            raise RuntimeError("Tiempo de arranque agotado: " + log.read_text())
                        time.sleep(0.05)
                    yield puerto
                finally:
                    p.terminate()
                    try:
                        p.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        p.kill()
                        p.wait()

        def login(puerto, usuario, contrasena):
            return peticion(puerto, "POST", "/api/login", {"usuario": usuario, "clave": contrasena})

        def entrar(puerto, usuario):
            codigo, datos, _ = login(puerto, usuario, clave)
            comprobar(codigo == 200 and datos["usuario"] == usuario and len(datos["token"]) == 43,
                      "Login correcto: " + usuario)
            tokens.append(datos["token"])
            return datos["token"]

        def ficha(tipo):
            return {"tipo": tipo, "latitud": 36.72, "longitud": -4.42}

        with arrancar() as puerto:
            r = peticion(puerto, "GET", "/api/salud")
            comprobar(r[0] == 200 and r[2].get("Cache-Control") == "no-store", "HTTPS y cabecera no-store")
            try:
                peticion(puerto, "GET", "/api/salud", ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT))
            except ssl.SSLCertVerificationError:
                print("OK - Certificado no confiable rechazado por el cliente")
            else:
                raise AssertionError("El cliente acepto un certificado no confiable")
            c = http.client.HTTPConnection(host, puerto, timeout=5)
            try:
                c.request("GET", "/api/salud")
                c.getresponse()
            except (OSError, http.client.HTTPException):
                print("OK - El puerto TLS no responde a HTTP en claro")
            else:
                raise AssertionError("El servidor respondio a HTTP en claro")
            finally:
                c.close()
            comprobar(peticion(puerto, "GET", "/api/elementos")[0] == 401, "Lectura sin token rechazada")
            comprobar(peticion(puerto, "POST", "/api/elementos", ficha("Entrada"))[0] == 401,
                      "Escritura sin token rechazada")
            incorrecta = secrets.token_urlsafe(18)
            a = login(puerto, "ana", incorrecta)
            b = login(puerto, "no-existe", incorrecta)
            comprobar(a[:2] == b[:2] and a[0] == 401, "Error generico de autenticacion")
            ana = entrar(puerto, "ana")
            luis = entrar(puerto, "luis")
            comprobar(ana != luis, "Tokens independientes y opacos")
            perfil = peticion(puerto, "GET", "/api/perfil", token=ana)
            comprobar(perfil[0] == 200 and set(perfil[1]) == {"usuario", "nombre", "rol"}, "Perfil con datos minimos")
            comprobar(peticion(puerto, "GET", "/api/admin/usuarios", token=ana)[0] == 404,
                      "Endpoint administrativo retirado")
            for etiqueta, invalida in (
                ("Propietario enviado por cliente", dict(ficha("Entrada"), usuario="luis")),
                ("Fecha enviada por cliente", dict(ficha("Entrada"), fecha="2020-01-01")),
                ("ID enviado por cliente", dict(ficha("Entrada"), id=999)),
                ("Tipo invalido", ficha("Otro")),
                ("Latitud invalida", dict(ficha("Entrada"), latitud=91)),
                ("Coordenada booleana", dict(ficha("Entrada"), latitud=True)),
            ):
                comprobar(peticion(puerto, "POST", "/api/elementos", invalida, ana)[0] == 400,
                          etiqueta + " rechazado")
            r = peticion(puerto, "POST", "/api/elementos", ficha("Entrada"), ana)
            comprobar(r[0] == 201 and r[1]["titulo"] == "Entrada" and r[1]["fecha"].endswith("Z"),
                      "Entrada creada con ID y hora UTC del servidor")
            id_ana = r[1]["id"]
            comprobar(peticion(puerto, "GET", "/api/elementos/%s" % id_ana, token=ana)[0] == 200,
                      "Ana puede leer su fichaje")
            comprobar(peticion(puerto, "GET", "/api/elementos/%s" % id_ana, token=luis)[0] == 404,
                      "Luis no puede leer el fichaje de Ana")
            comprobar(peticion(puerto, "GET", "/api/elementos", token=luis)[1]["elementos"] == [],
                      "Historial aislado por usuario")
            comprobar(peticion(puerto, "POST", "/api/elementos", ficha("Entrada"), ana)[0] == 409,
                      "Dos entradas seguidas rechazadas")
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                respuestas = list(pool.map(lambda _: peticion(puerto, "POST", "/api/elementos", ficha("Salida"), ana)[0], range(2)))
            comprobar(sorted(respuestas) == [201, 409], "Dos salidas simultaneas: solo se admite una")
            comprobar(peticion(puerto, "POST", "/api/logout", token=ana)[0] == 200, "Logout aceptado")
            comprobar(peticion(puerto, "GET", "/api/elementos", token=ana)[0] == 401, "Token revocado tras logout")
            comprobar(peticion(puerto, "POST", "/api/elementos", ficha("Entrada"), ana)[0] == 401,
                      "Token revocado tampoco puede escribir")
            comprobar(peticion(puerto, "GET", "/api/elementos", token=luis)[0] == 200, "Logout de Ana no cierra sesion de Luis")

        with arrancar() as puerto:
            comprobar(peticion(puerto, "GET", "/api/elementos", token=luis)[0] == 401, "Reinicio invalida sesiones anteriores")
            ana = entrar(puerto, "ana")
            r = peticion(puerto, "GET", "/api/elementos", token=ana)
            comprobar(r[0] == 200 and len(r[1]["elementos"]) == 2 and r[1]["elementos"][-1]["id"] == id_ana,
                      "Historial persiste tras reiniciar")

        with arrancar(ttl=2) as puerto:
            ana = entrar(puerto, "ana")
            comprobar(peticion(puerto, "GET", "/api/elementos", token=ana)[0] == 200, "Token valido antes de caducar")
            time.sleep(2.2)
            comprobar(peticion(puerto, "GET", "/api/elementos", token=ana)[0] == 401, "Caducidad absoluta aplicada por el servidor")

        with arrancar() as puerto:
            incorrecta = secrets.token_urlsafe(18)
            resultados = [login(puerto, "ana", incorrecta)[0] for _ in range(5)]
            comprobar(resultados == [401]*5, "Primeros cinco intentos incorrectos reciben 401")
            r = login(puerto, "ana", incorrecta)
            comprobar(r[0] == 429 and int(r[2].get("Retry-After", "0")) > 0,
                      "Sexto intento limitado por cuenta con Retry-After")
            for i in range(25):
                if login(puerto, "inexistente-%d" % i, incorrecta)[0] != 401:
                    raise AssertionError("Limite por IP prematuro")
            comprobar(login(puerto, "otro-usuario", incorrecta)[0] == 429, "Limite por IP tambien se aplica")

        logs = "\n".join(p.read_text(errors="replace") for p in carpeta.glob("servidor-*.log"))
        comprobar(clave not in logs and all(t not in logs for t in tokens), "Sin contrasenas ni tokens en logs")
    print("\nTODAS LAS PRUEBAS SUPERADAS. La base de datos real no se ha modificado.")


if __name__ == "__main__":
    ejecutar()
