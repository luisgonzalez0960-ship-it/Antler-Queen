import random
import select
import socket
import sys
import threading
import time

PUERTO = 5556
MAX_INVITADOS = 3
MAX_SALAS = 300
ESPERA_ACEPTAR = 20.0
LETRAS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

SALAS = {}
CERROJO = threading.Lock()


def registrar(texto):
    print(time.strftime("%H:%M:%S"), texto, flush=True)


def leer_linea(sock, limite=80, espera=10.0):
    sock.settimeout(espera)
    datos = b""
    try:
        while len(datos) < limite:
            byte = sock.recv(1)
            if not byte:
                return None
            if byte == b"\n":
                return datos.decode("utf-8", "replace").strip()
            datos += byte
    except (socket.timeout, OSError):
        return None
    return None


def enviar_linea(sock, texto):
    try:
        sock.sendall((texto + "\n").encode("utf-8"))
        return True
    except OSError:
        return False


def cerrar(sock):
    try:
        sock.close()
    except OSError:
        pass


def configurar(sock):
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    except OSError:
        pass


def codigo_nuevo():
    for _ in range(50):
        codigo = "".join(random.choice(LETRAS) for _ in range(5))
        if codigo not in SALAS:
            return codigo
    return None


def puente(a, b):
    configurar(a)
    configurar(b)
    a.settimeout(None)
    b.settimeout(None)
    try:
        while True:
            listos, _, _ = select.select([a, b], [], [], 120)
            if not listos:
                continue
            for origen in listos:
                datos = origen.recv(4096)
                if not datos:
                    return
                destino = b if origen is a else a
                destino.sendall(datos)
    except OSError:
        pass
    finally:
        cerrar(a)
        cerrar(b)


def atender_anfitrion(sock, direccion):
    with CERROJO:
        if len(SALAS) >= MAX_SALAS:
            codigo = None
        else:
            codigo = codigo_nuevo()
        if codigo is not None:
            sala = {"control": sock, "pendientes": {}, "siguiente": 1, "activos": 0}
            SALAS[codigo] = sala
    if codigo is None:
        enviar_linea(sock, "ERROR servidor_lleno")
        cerrar(sock)
        return
    configurar(sock)
    enviar_linea(sock, "CODIGO " + codigo)
    registrar(f"sala {codigo} creada por {direccion[0]}")
    try:
        sock.settimeout(None)
        while True:
            datos = sock.recv(256)
            if not datos:
                break
    except OSError:
        pass
    with CERROJO:
        SALAS.pop(codigo, None)
        pendientes = list(sala["pendientes"].values())
        sala["pendientes"].clear()
    for registro in pendientes:
        enviar_linea(registro["sock"], "ERROR sala_cerrada")
        cerrar(registro["sock"])
        registro["evento"].set()
    cerrar(sock)
    registrar(f"sala {codigo} cerrada")


def atender_invitado(sock, direccion, codigo):
    codigo = codigo.upper()
    with CERROJO:
        sala = SALAS.get(codigo)
        if sala is None:
            motivo = "sala_no_existe"
        elif sala["activos"] + len(sala["pendientes"]) >= MAX_INVITADOS:
            motivo = "sala_llena"
        else:
            motivo = None
            identificador = sala["siguiente"]
            sala["siguiente"] += 1
            registro = {"sock": sock, "evento": threading.Event(), "aceptado": False}
            sala["pendientes"][identificador] = registro
            control = sala["control"]
    if motivo is not None:
        enviar_linea(sock, "ERROR " + motivo)
        cerrar(sock)
        return
    if not enviar_linea(control, f"NUEVO {identificador}"):
        with CERROJO:
            sala["pendientes"].pop(identificador, None)
        enviar_linea(sock, "ERROR sin_respuesta")
        cerrar(sock)
        return
    registrar(f"invitado {direccion[0]} entra a la sala {codigo}")
    if not registro["evento"].wait(ESPERA_ACEPTAR):
        with CERROJO:
            sala["pendientes"].pop(identificador, None)
        if not registro["aceptado"]:
            enviar_linea(sock, "ERROR sin_respuesta")
            cerrar(sock)


def atender_aceptar(sock, codigo, identificador):
    codigo = codigo.upper()
    with CERROJO:
        sala = SALAS.get(codigo)
        registro = None
        if sala is not None:
            registro = sala["pendientes"].pop(identificador, None)
        if registro is not None:
            registro["aceptado"] = True
            sala["activos"] += 1
    if registro is None:
        enviar_linea(sock, "ERROR no_hay_invitado")
        cerrar(sock)
        return
    invitado = registro["sock"]
    enviar_linea(sock, "OK")
    enviar_linea(invitado, "OK")
    registro["evento"].set()
    puente(sock, invitado)
    with CERROJO:
        if codigo in SALAS:
            SALAS[codigo]["activos"] = max(0, SALAS[codigo]["activos"] - 1)


def atender(sock, direccion):
    linea = leer_linea(sock)
    if not linea:
        cerrar(sock)
        return
    partes = linea.split()
    try:
        if partes[0] == "HOST":
            atender_anfitrion(sock, direccion)
        elif partes[0] == "UNIRSE" and len(partes) == 2:
            atender_invitado(sock, direccion, partes[1][:8])
        elif partes[0] == "ACEPTAR" and len(partes) == 3:
            atender_aceptar(sock, partes[1][:8], int(partes[2]))
        else:
            enviar_linea(sock, "ERROR peticion_invalida")
            cerrar(sock)
    except (ValueError, OSError):
        cerrar(sock)


def main():
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else PUERTO
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(("", puerto))
    servidor.listen(64)
    registrar(f"Relay de YELLOWJACKETS escuchando en el puerto {puerto}")
    while True:
        conexion, direccion = servidor.accept()
        threading.Thread(target=atender, args=(conexion, direccion), daemon=True).start()


if __name__ == "__main__":
    main()
