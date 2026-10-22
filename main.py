import pygame
import random
import os
import socket
import select
import json
import threading

pygame.init()

ANCHO = 1000
ALTO = 600
SUELO = 500
ALTO_PERSONAJE = 180

PUERTO = 5555

VELOCIDAD = 4
VELOCIDAD_CORRER = 7
IMPULSO_SALTO = 12
GRAVEDAD = 0.6
DURACION_SALTO = 2 * IMPULSO_SALTO / GRAVEDAD
LANZAMIENTO = 0.7
VELOCIDAD_PROYECTIL = 9

VIDA_MAXIMA = 100
DANO_DEFENSA = 0.2

ATAQUES = {
    "ataque": {"dano": 10, "ventana": (0.33, 0.78), "alcance": 0.6, "duracion": 450, "derriba": False},
    "fuerte": {"dano": 16, "ventana": (0.5, 0.95), "alcance": 0.8, "duracion": 520, "derriba": False},
    "patada": {"dano": 8, "ventana": (0.2, 0.8), "alcance": 0.7, "duracion": 450, "derriba": False},
    "patada_fuerte": {"dano": 14, "ventana": (0.3, 0.95), "alcance": 0.85, "duracion": 600, "derriba": True},
    "especial": {"dano": 20, "ventana": (0, 0), "alcance": 0, "duracion": 700, "derriba": True},
}

DURACION_FASE = {"golpe": 300, "caida": 500, "levantarse": 500}

CONTROLES_J1 = {
    "izq": [pygame.K_a],
    "der": [pygame.K_d],
    "salto": [pygame.K_w, pygame.K_SPACE],
    "correr": [pygame.K_LSHIFT],
    "ataque": pygame.K_f,
    "fuerte": pygame.K_g,
    "patada": pygame.K_v,
    "patada_fuerte": pygame.K_b,
    "especial": pygame.K_r,
    "defensa": [pygame.K_c],
    "transformar": pygame.K_t,
}

CONTROLES_J2 = {
    "izq": [pygame.K_LEFT],
    "der": [pygame.K_RIGHT],
    "salto": [pygame.K_UP],
    "correr": [pygame.K_RSHIFT],
    "ataque": pygame.K_COMMA,
    "fuerte": pygame.K_PERIOD,
    "patada": pygame.K_m,
    "patada_fuerte": pygame.K_n,
    "especial": pygame.K_MINUS,
    "defensa": [pygame.K_RCTRL],
    "transformar": pygame.K_RETURN,
}

ventana = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Reina de Corazones")

fuente = pygame.font.SysFont(None, 32)
fuente_grande = pygame.font.SysFont(None, 72)
fuente_chica = pygame.font.SysFont(None, 22)
fuente_mini = pygame.font.SysFont(None, 19)
reloj = pygame.time.Clock()

escenarios = {
    "Avion en el bosque": "assets/Bosque.png",
    "Cabaña abandonada": "assets/Cabaña.png",
    "Lago congelado": "assets/Lago.png"
}

for nombre, ruta in escenarios.items():
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"No se encontró la imagen: {ruta}")
    escenarios[nombre] = pygame.image.load(ruta).convert()

tarjetas = {
    "Avion en el bosque": pygame.Rect(40, 150, 280, 300),
    "Cabaña abandonada": pygame.Rect(360, 150, 280, 300),
    "Lago congelado": pygame.Rect(680, 150, 280, 300)
}

imagenes_tarjetas = {}
for nombre, imagen in escenarios.items():
    imagenes_tarjetas[nombre] = pygame.transform.scale(
        imagen,
        (tarjetas[nombre].width - 10, 210)
    )

mapas = {}
for nombre, imagen in escenarios.items():
    mapas[nombre] = pygame.transform.scale(imagen, (ANCHO, ALTO))

def cargar_animacion(ruta, columnas, filas=1, margen_x=0, margen_y=0, espacio_x=0, espacio_y=0):
    hoja = pygame.image.load(ruta).convert_alpha()
    ancho_hoja = hoja.get_width()
    alto_hoja = hoja.get_height()

    frame_w = (ancho_hoja - (2 * margen_x) - (espacio_x * (columnas - 1))) // columnas
    frame_h = (alto_hoja - (2 * margen_y) - (espacio_y * (filas - 1))) // filas

    if frame_w <= 0 or frame_h <= 0:
        raise ValueError(f"Dimensiones inválidas para la hoja de sprites: {ruta}")

    cuadros = []

    for fila in range(filas):
        for columna in range(columnas):
            x = margen_x + columna * (frame_w + espacio_x)
            y = margen_y + fila * (frame_h + espacio_y)

            cuadro = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
            cuadro.blit(hoja, (0, 0), (x, y, frame_w, frame_h))
            cuadros.append(cuadro)

    return cuadros


def segmentos_hoja(hoja, hueco_min=1):
    mascara = pygame.mask.from_surface(hoja, 10)
    w, h = hoja.get_size()
    ocupadas = [any(mascara.get_at((px, py)) for py in range(h)) for px in range(w)]

    segmentos = []
    inicio = None
    for px, ocupada in enumerate(ocupadas + [False]):
        if ocupada and inicio is None:
            inicio = px
        elif not ocupada and inicio is not None:
            segmentos.append([inicio, px - 1])
            inicio = None

    unidos = []
    for s in segmentos:
        if unidos and s[0] - unidos[-1][1] - 1 < hueco_min:
            unidos[-1][1] = s[1]
        else:
            unidos.append(s)

    return [tuple(s) for s in unidos if s[1] - s[0] >= 4]


def unir_hasta(segmentos, cantidad):
    segs = [list(s) for s in segmentos]
    while len(segs) > cantidad:
        i = min(range(len(segs) - 1), key=lambda k: segs[k + 1][0] - segs[k][1])
        segs[i][1] = segs[i + 1][1]
        del segs[i + 1]
    return [tuple(s) for s in segs]


def recortar_segmento(hoja, segmento):
    x0, x1 = segmento
    franja = hoja.subsurface((x0, 0, x1 - x0 + 1, hoja.get_height()))
    caja = franja.get_bounding_rect(min_alpha=10)
    return franja.subsurface(caja).copy()


def cargar_animacion_auto(ruta, columnas, anclar_pies=False):
    hoja = pygame.image.load(ruta).convert_alpha()
    segmentos = segmentos_hoja(hoja)

    if len(segmentos) > columnas:
        segmentos = unir_hasta(segmentos, columnas)

    if len(segmentos) != columnas:
        print(f"AVISO {ruta}: detecté {len(segmentos)} sprites y esperaba {columnas}. "
              f"Uso corte por cuadrícula.")
        return cargar_animacion(ruta, columnas)

    franjas = []
    centros = []
    cajas = []
    for x0, x1 in segmentos:
        franja = hoja.subsurface((x0, 0, x1 - x0 + 1, hoja.get_height()))
        mascara = pygame.mask.from_surface(franja, 10)
        franjas.append(franja)
        centros.append(mascara.centroid()[0])
        cajas.append(franja.get_bounding_rect(min_alpha=10))

    if anclar_pies:
        alto = max(c.height for c in cajas)
    else:
        arriba_comun = min(c.top for c in cajas)
        alto = max(c.bottom for c in cajas) - arriba_comun

    mitad = max(
        max(cx, f.get_width() - cx) for f, cx in zip(franjas, centros)
    )
    ancho = int(mitad * 2) + 2

    cuadros = []
    for franja, cx, caja in zip(franjas, centros, cajas):
        lienzo = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        destino_x = ancho // 2 - int(round(cx))
        if anclar_pies:
            lienzo.blit(
                franja,
                (destino_x, alto - caja.height),
                (0, caja.top, franja.get_width(), caja.height)
            )
        else:
            lienzo.blit(
                franja,
                (destino_x, 0),
                (0, arriba_comun, franja.get_width(), alto)
            )
        cuadros.append(lienzo)
    return cuadros


def distancia_rects(a, b):
    dx = max(0, a.left - b.right, b.left - a.right)
    dy = max(0, a.top - b.bottom, b.top - a.bottom)
    return dx * dx + dy * dy


def datos_sprite(sup):
    caja = sup.get_bounding_rect(min_alpha=10)
    alto_pies = max(4, caja.height // 8)
    franja = sup.subsurface((0, caja.bottom - alto_pies, sup.get_width(), alto_pies))
    cx = pygame.mask.from_surface(franja, 10).centroid()[0]
    return (sup, caja, cx)


def separar_sprites(hoja, cantidad):
    segmentos = segmentos_hoja(hoja, hueco_min=16)
    if len(segmentos) == cantidad:
        sprites = []
        for x0, x1 in segmentos:
            sup = pygame.Surface(hoja.get_size(), pygame.SRCALPHA)
            sup.blit(hoja, (x0, 0), (x0, 0, x1 - x0 + 1, hoja.get_height()))
            sprites.append(datos_sprite(sup))
        return sprites

    mascara = pygame.mask.from_surface(hoja, 10)
    componentes = mascara.connected_components()

    if len(componentes) < cantidad:
        return None

    componentes.sort(key=lambda m: m.count(), reverse=True)
    principales = componentes[:cantidad]
    sobrantes = componentes[cantidad:]

    rects_principales = [m.get_bounding_rects()[0] for m in principales]
    orden = sorted(range(cantidad), key=lambda i: rects_principales[i].centerx)
    principales = [principales[i] for i in orden]
    rects_principales = [rects_principales[i] for i in orden]

    for sobrante in sobrantes:
        rect_sobrante = sobrante.get_bounding_rects()[0]
        j = min(
            range(cantidad),
            key=lambda i: distancia_rects(rect_sobrante, rects_principales[i])
        )
        principales[j].draw(sobrante, (0, 0))

    sprites = []
    for grupo in principales:
        sup = pygame.Surface(hoja.get_size(), pygame.SRCALPHA)
        grupo.to_surface(sup, setsurface=hoja, unsetcolor=None)
        sprites.append(datos_sprite(sup))

    return sprites


def lienzos_pies(sprites, arriba, alto):
    mitad = max(max(cx - caja.left, caja.right - cx) for _, caja, cx in sprites)
    ancho = int(mitad) * 2 + 4

    cuadros = []
    for sup, caja, cx in sprites:
        lienzo = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        destino_x = ancho // 2 - int(round(cx))
        lienzo.blit(sup, (destino_x, 0), (0, arriba, sup.get_width(), alto))
        cuadros.append(lienzo)
    return cuadros


def cargar_ataque(ruta, columnas):
    hoja = pygame.image.load(ruta).convert_alpha()
    sprites = separar_sprites(hoja, columnas)

    if sprites is None:
        print(f"AVISO {ruta}: no encontré {columnas} piezas. Uso detección por columnas.")
        return cargar_animacion_auto(ruta, columnas)

    arriba = min(caja.top for _, caja, _ in sprites)
    abajo = max(caja.bottom for _, caja, _ in sprites)
    return lienzos_pies(sprites, arriba, abajo - arriba)


def cargar_especial(ruta, n_personaje, n_proyectil, respaldo):
    if not os.path.exists(ruta):
        print(f"AVISO {ruta}: no existe. Uso el ataque normal.")
        return respaldo, []

    hoja = pygame.image.load(ruta).convert_alpha()
    sprites = separar_sprites(hoja, n_personaje + n_proyectil)

    if sprites is None:
        print(f"AVISO {ruta}: no encontré {n_personaje + n_proyectil} piezas. Uso el ataque normal.")
        return respaldo, []

    arriba = min(caja.top for _, caja, _ in sprites)
    abajo = max(caja.bottom for _, caja, _ in sprites)
    alto = abajo - arriba

    personaje = lienzos_pies(sprites[:n_personaje], arriba, alto)

    sprites_proyectil = sprites[n_personaje:]
    ancho_proyectil = max((caja.width for _, caja, _ in sprites_proyectil), default=0)
    proyectil = []
    for sup, caja, _ in sprites_proyectil:
        lienzo = pygame.Surface((ancho_proyectil, alto), pygame.SRCALPHA)
        lienzo.blit(sup, (ancho_proyectil - caja.width, 0), (caja.left, arriba, caja.width, alto))
        proyectil.append(lienzo)

    return personaje, proyectil


def cargar_quieta(ruta):
    img = pygame.image.load(ruta).convert_alpha()
    segmentos = segmentos_hoja(img, hueco_min=3)
    if not segmentos:
        return [img]
    principal = max(segmentos, key=lambda s: s[1] - s[0])
    return [recortar_segmento(img, principal)]


def escalar_animaciones(anims, alto_objetivo):
    referencia = anims["quieta"][0].get_height()
    k = alto_objetivo / referencia
    return {
        nombre: [
            pygame.transform.smoothscale(
                f, (max(1, int(f.get_width() * k)), max(1, int(f.get_height() * k)))
            )
            for f in cuadros
        ]
        for nombre, cuadros in anims.items()
    }


ataque_antler = cargar_ataque("Personajes/AntlerQueenA.png", 9)
especial_antler, proyectil_antler = cargar_especial(
    "Personajes/AntlerQueenSA.png", 4, 2, ataque_antler
)

animaciones_antler = escalar_animaciones({
    "quieta": cargar_quieta("Personajes/AntlerQueen.png"),
    "caminar": cargar_animacion_auto("Personajes/AntlerQueenW.png", 7),
    "correr": cargar_animacion_auto("Personajes/AntlerQueenR.png", 6),
    "ataque": ataque_antler,
    "especial": especial_antler,
    "proyectil": proyectil_antler,
    "salto": cargar_animacion_auto("Personajes/AntlerQueenJ.png", 7, True),
}, ALTO_PERSONAJE)

avisos_personajes = []

CUENTAS_BASE = {
    "I": 5, "W": 6, "R": 5, "J": 5, "B": 5, "A1": 5, "A2": 5,
    "K1": 5, "K2": 5, "H": 5, "F": 4, "U": 4, "V": 3, "L": 3,
}

DEFINICIONES = [
    {
        "clave": "cazadora",
        "nombre": "NATALIE",
        "prefijos": ("Natalie", "Cazadora"),
        "cuentas": dict(CUENTAS_BASE),
        "especial": (7, 1),
        "escala_proyectil": 1.0,
        "descripcion": "Defensa, golpes y alce de hielo",
    },
    {
        "clave": "misty",
        "nombre": "MISTY",
        "prefijos": ("Misty",),
        "cuentas": dict(CUENTAS_BASE, B=6),
        "especial": (6, 1),
        "escala_proyectil": 0.55,
        "descripcion": "Hacha, ave y hongos mágicos",
    },
    {
        "clave": "van",
        "nombre": "VAN",
        "prefijos": ("Van",),
        "cuentas": dict(CUENTAS_BASE, B=6),
        "especial": (4, 3),
        "escala_proyectil": 0.6,
        "descripcion": "Fuego, cintas y lobo espectral",
    },
    {
        "clave": "jackie",
        "nombre": "JACKIE",
        "prefijos": ("Jackie",),
        "cuentas": dict(CUENTAS_BASE, B=6),
        "especial": (4, 1),
        "escala_proyectil": 0.5,
        "descripcion": "Hielo, conejos y avispa reina",
    },
]


def cargar_plantilla(definicion):
    nombre = definicion["nombre"]
    cuentas = definicion["cuentas"]
    sufijos = list(cuentas.keys()) + ["SA"]
    candidatos = ["Personajes/", "Personajes/Personajes/", "./"]
    try:
        carpeta_script = os.path.dirname(os.path.abspath(__file__))
        candidatos.append(os.path.join(carpeta_script, "Personajes") + os.sep)
        candidatos.append(carpeta_script + os.sep)
    except NameError:
        pass

    base = None
    prefijo = None
    for pref in definicion["prefijos"]:
        for candidato in candidatos:
            if all(os.path.exists(f"{candidato}{pref}{s}.png") for s in sufijos):
                base = candidato
                prefijo = pref
                break
        if base is not None:
            break

    if base is None:
        pref = definicion["prefijos"][0]
        faltan = [f"{pref}{s}" for s in sufijos if not os.path.exists(f"Personajes/{pref}{s}.png")]
        if not definicion.get("silencioso"):
            avisos_personajes.append(
                f"{nombre} no disponible: faltan {', '.join(faltan[:3])} en la carpeta Personajes"
            )
            print(f"AVISO: faltan {', '.join(faltan)} en Personajes. {nombre} no estará disponible.")
        return None

    def ruta(sufijo):
        return f"{base}{prefijo}{sufijo}.png"

    try:
        ataque = cargar_ataque(ruta("A1"), cuentas["A1"])
        n_personaje, n_proyectil = definicion["especial"]
        especial, proyectil = cargar_especial(ruta("SA"), n_personaje, n_proyectil, ataque)
        animaciones = {
            "quieta": cargar_animacion_auto(ruta("I"), cuentas["I"]),
            "caminar": cargar_animacion_auto(ruta("W"), cuentas["W"]),
            "correr": cargar_animacion_auto(ruta("R"), cuentas["R"]),
            "salto": cargar_animacion_auto(ruta("J"), cuentas["J"], True),
            "defensa": cargar_ataque(ruta("B"), cuentas["B"]),
            "ataque": ataque,
            "fuerte": cargar_ataque(ruta("A2"), cuentas["A2"]),
            "patada": cargar_ataque(ruta("K1"), cuentas["K1"]),
            "patada_fuerte": cargar_ataque(ruta("K2"), cuentas["K2"]),
            "especial": especial,
            "proyectil": proyectil,
            "golpe": cargar_ataque(ruta("H"), cuentas["H"]),
            "caida": cargar_ataque(ruta("F"), cuentas["F"]),
            "levantarse": cargar_ataque(ruta("U"), cuentas["U"]),
            "victoria": cargar_ataque(ruta("V"), cuentas["V"]),
            "derrota": cargar_ataque(ruta("L"), cuentas["L"]),
        }
        animaciones = escalar_animaciones(animaciones, ALTO_PERSONAJE)
        factor = definicion["escala_proyectil"]
        if factor != 1.0:
            animaciones["proyectil"] = [
                pygame.transform.smoothscale(
                    f,
                    (max(1, int(f.get_width() * factor)), max(1, int(f.get_height() * factor)))
                )
                for f in animaciones["proyectil"]
            ]
        return animaciones
    except Exception as error:
        avisos_personajes.append(f"{nombre} no se pudo cargar: {error}"[:110])
        print(f"AVISO: no se pudo cargar a {nombre}: {error!r}")
        return None


boton_confirmar = pygame.Rect(375, 500, 250, 55)

BOTONES_MENU = [
    ("uno", "UN JUGADOR", pygame.Rect(300, 210, 400, 70)),
    ("local", "2 JUGADORES (MISMO PC)", pygame.Rect(300, 305, 400, 70)),
    ("online", "ONLINE", pygame.Rect(300, 400, 400, 70)),
]

BOTONES_ONLINE = [
    ("host", "CREAR PARTIDA", pygame.Rect(300, 210, 400, 70)),
    ("unirse", "UNIRSE A UNA PARTIDA", pygame.Rect(300, 305, 400, 70)),
    ("volver", "VOLVER", pygame.Rect(300, 400, 400, 70)),
]

DEFINICION_SHAUNA = {
    "clave": "humana",
    "nombre": "SHAUNA",
    "prefijos": ("Shauna",),
    "cuentas": dict(CUENTAS_BASE, B=6),
    "especial": (4, 4),
    "escala_proyectil": 0.6,
}

animaciones_shauna = cargar_plantilla(DEFINICION_SHAUNA)
if animaciones_shauna is None:
    detalle = avisos_personajes[-1] if avisos_personajes else "revisa la consola"
    raise FileNotFoundError(f"No se pudo cargar a Shauna: {detalle}")
avisos_personajes.clear()

ANIMACIONES = {"humana": animaciones_shauna, "criatura": animaciones_antler}

PERSONAJES = {
    "shauna": {
        "nombre": "SHAUNA",
        "formas": ["humana", "criatura"],
        "forma_inicial": "humana",
        "descripcion": "Se transforma en Antler Queen",
    },
}

for definicion in DEFINICIONES:
    animaciones_nuevas = cargar_plantilla(definicion)
    if animaciones_nuevas is not None:
        clave_nueva = definicion["clave"]
        ANIMACIONES[clave_nueva] = animaciones_nuevas
        PERSONAJES[clave_nueva] = {
            "nombre": definicion["nombre"],
            "formas": [clave_nueva],
            "forma_inicial": clave_nueva,
            "descripcion": definicion["descripcion"],
        }


def alguna(teclas, lista):
    return any(teclas[k] for k in lista)


def dibujar_texto(texto, tipo, color, pos, alineacion="izq"):
    sombra = tipo.render(texto, True, (0, 0, 0))
    imagen = tipo.render(texto, True, color)
    rect = imagen.get_rect()
    if alineacion == "centro":
        rect.midtop = pos
    elif alineacion == "der":
        rect.topright = pos
    else:
        rect.topleft = pos
    ventana.blit(sombra, rect.move(2, 2))
    ventana.blit(imagen, rect)


def lineas_ajustadas(texto, tipo, ancho_max):
    lineas = []
    actual = ""
    for palabra in texto.split():
        prueba = (actual + " " + palabra).strip()
        if tipo.size(prueba)[0] <= ancho_max:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def dibujar_boton(rect, texto):
    encima = rect.collidepoint(pygame.mouse.get_pos())
    color = (230, 60, 85) if encima else (200, 40, 60)
    pygame.draw.rect(ventana, color, rect, border_radius=8)
    etiqueta = fuente.render(texto, True, (255, 255, 255))
    ventana.blit(etiqueta, etiqueta.get_rect(center=rect.center))


def ip_local():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


class Red:
    def __init__(self):
        self.servidor = None
        self.sock = None
        self.buffer = b""
        self.conectado = False
        self.estado_conexion = None

    def crear_servidor(self):
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            servidor.bind(("", PUERTO))
            servidor.listen(1)
        except OSError:
            servidor.close()
            raise
        self.servidor = servidor

    def aceptar(self):
        if self.servidor is None:
            return False
        listos, _, _ = select.select([self.servidor], [], [], 0)
        if not listos:
            return False
        conexion, _ = self.servidor.accept()
        conexion.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock = conexion
        self.conectado = True
        self.servidor.close()
        self.servidor = None
        return True

    def conectar(self, ip):
        self.estado_conexion = "conectando"

        def tarea():
            try:
                s = socket.create_connection((ip, PUERTO), timeout=5)
                s.settimeout(None)
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self.sock = s
                self.conectado = True
                self.estado_conexion = "ok"
            except (OSError, UnicodeError):
                self.estado_conexion = "error"

        threading.Thread(target=tarea, daemon=True).start()

    def enviar(self, datos):
        if not self.conectado or self.sock is None:
            return
        try:
            linea = json.dumps(datos, separators=(",", ":")) + "\n"
            self.sock.sendall(linea.encode("utf-8"))
        except OSError:
            self.conectado = False

    def recibir(self):
        mensajes = []
        if not self.conectado or self.sock is None:
            return mensajes
        try:
            while True:
                listos, _, _ = select.select([self.sock], [], [], 0)
                if not listos:
                    break
                datos = self.sock.recv(65536)
                if not datos:
                    self.conectado = False
                    break
                self.buffer += datos
        except OSError:
            self.conectado = False
        while b"\n" in self.buffer:
            linea, self.buffer = self.buffer.split(b"\n", 1)
            if linea:
                try:
                    mensajes.append(json.loads(linea.decode("utf-8")))
                except ValueError:
                    pass
        return mensajes

    def cerrar(self):
        self.conectado = False
        for s in (self.sock, self.servidor):
            if s is not None:
                try:
                    s.close()
                except OSError:
                    pass
        self.sock = None
        self.servidor = None


class Jugador:
    def __init__(self, nombre, inicio_x, mira_derecha, controles, personaje):
        self.nombre = nombre
        self.inicio_x = inicio_x
        self.mira_derecha_inicial = mira_derecha
        self.controles = controles
        self.personaje = personaje
        self.forma = PERSONAJES[personaje]["forma_inicial"]
        self.reiniciar()

    def reiniciar(self):
        self.x = self.inicio_x
        self.mirando_derecha = self.mira_derecha_inicial
        self.altura = 0
        self.vel_y = 0
        self.en_salto = False
        self.tiempo_salto = 0
        self.atacando = False
        self.tipo_ataque = "ataque"
        self.inicio_ataque = 0
        self.proyectil_lanzado = False
        self.id_ataque = 0
        self.id_proyectil = 0
        self.proyectiles = []
        self.accion = "quieta"
        self.accion_anterior = "quieta"
        self.indice_cuadro = 0
        self.ultima_actualizacion = 0
        self.vida = VIDA_MAXIMA
        self.golpes_recibidos = set()
        self.golpeado_hasta = 0
        self.defendiendo = False
        self.inicio_defensa = 0
        self.estado_golpe = None
        self.inicio_golpe = 0
        self.estado_final = None
        self.inicio_final = 0

    def rect_cuerpo(self):
        return pygame.Rect(int(self.x) + 20, SUELO - int(self.altura) - 170, 60, 170)

    def rect_golpe(self, alcance):
        centro = int(self.x) + 50
        ancho = int(ALTO_PERSONAJE * alcance)
        izquierda = centro + 10 if self.mirando_derecha else centro - 10 - ancho
        return pygame.Rect(izquierda, SUELO - int(self.altura) - 150, ancho, 140)

    def invulnerable(self):
        return self.estado_golpe in ("caida", "levantarse")

    def recibir_dano(self, dano, direccion, ahora, derriba=False):
        animaciones = ANIMACIONES.get(self.forma, animaciones_shauna)

        if self.defendiendo:
            self.vida = max(0, self.vida - max(1, int(dano * DANO_DEFENSA)))
            self.x = max(0, min(self.x + direccion * 6, ANCHO - 100))
            return

        self.vida = max(0, self.vida - dano)
        self.x = max(0, min(self.x + direccion * 20, ANCHO - 100))

        fase = None
        if self.vida > 0 and not self.en_salto:
            if derriba and animaciones.get("caida") and animaciones.get("levantarse"):
                fase = "caida"
            elif animaciones.get("golpe"):
                fase = "golpe"

        if fase is not None:
            self.estado_golpe = fase
            self.inicio_golpe = ahora
            self.atacando = False
        else:
            self.golpeado_hasta = ahora + 250

    def tecla_presionada(self, tecla, ahora):
        c = self.controles
        if c is None or self.vida <= 0 or self.estado_golpe is not None:
            return
        if self.atacando or self.en_salto:
            return

        if tecla == c["transformar"]:
            formas = PERSONAJES[self.personaje]["formas"]
            if len(formas) > 1:
                self.forma = formas[(formas.index(self.forma) + 1) % len(formas)]
                self.indice_cuadro = 0
                self.accion_anterior = "quieta"
            return

        for tipo in ("ataque", "fuerte", "patada", "patada_fuerte", "especial"):
            if tecla == c[tipo] and ANIMACIONES[self.forma].get(tipo):
                self.atacando = True
                self.tipo_ataque = tipo
                self.inicio_ataque = ahora
                self.proyectil_lanzado = False
                self.defendiendo = False
                self.id_ataque += 1
                break

    def lanzar_proyectil(self, ahora, cuadros_proyectil):
        direccion = 1 if self.mirando_derecha else -1
        separacion = int(ALTO_PERSONAJE * 0.45) + cuadros_proyectil[0].get_width() // 4
        self.id_proyectil += 1
        self.proyectiles.append({
            "id": self.id_proyectil,
            "x": self.x + 50 + direccion * separacion,
            "direccion": direccion,
            "inicio": ahora,
            "f": 0,
            "golpeo": False,
            "resto": 999,
        })
        self.proyectil_lanzado = True

    def mover_proyectiles(self, ahora, animaciones):
        cuadros_proyectil = animaciones.get("proyectil") or []
        for p in self.proyectiles:
            p["x"] += p["direccion"] * VELOCIDAD_PROYECTIL
            if cuadros_proyectil:
                p["f"] = ((ahora - p["inicio"]) // 100) % len(cuadros_proyectil)
            if p["golpeo"]:
                p["resto"] -= 1
        self.proyectiles = [
            p for p in self.proyectiles
            if -400 < p["x"] < ANCHO + 400 and p["resto"] > 0
        ]

    def avanzar_golpe(self, ahora):
        if self.estado_golpe is None:
            return
        if ahora - self.inicio_golpe >= DURACION_FASE[self.estado_golpe]:
            if self.estado_golpe == "caida":
                self.estado_golpe = "levantarse"
                self.inicio_golpe = ahora
            else:
                self.estado_golpe = None

    def actualizar(self, teclas, ahora, x_rival):
        c = self.controles
        animaciones = ANIMACIONES[self.forma]

        self.avanzar_golpe(ahora)
        if self.estado_golpe is not None:
            cuadros = animaciones[self.estado_golpe]
            fase = DURACION_FASE[self.estado_golpe]
            self.accion = self.estado_golpe
            self.indice_cuadro = min(
                len(cuadros) - 1, int((ahora - self.inicio_golpe) / fase * len(cuadros))
            )
            self.accion_anterior = "golpe"
            self.defendiendo = False
            self.mover_proyectiles(ahora, animaciones)
            return

        quiere_defender = bool(
            animaciones.get("defensa")
            and alguna(teclas, c["defensa"])
            and not self.atacando
            and not self.en_salto
        )
        if quiere_defender and not self.defendiendo:
            self.inicio_defensa = ahora
        self.defendiendo = quiere_defender

        se_mueve = False
        corriendo = alguna(teclas, c["correr"])
        velocidad_actual = VELOCIDAD_CORRER if corriendo else VELOCIDAD

        if not self.atacando and not self.defendiendo:
            if alguna(teclas, c["izq"]):
                self.x -= velocidad_actual
                self.mirando_derecha = False
                se_mueve = True
            if alguna(teclas, c["der"]):
                self.x += velocidad_actual
                self.mirando_derecha = True
                se_mueve = True

        self.x = max(0, min(self.x, ANCHO - 100))

        if alguna(teclas, c["salto"]) and not self.en_salto and not self.atacando and not self.defendiendo:
            self.en_salto = True
            self.vel_y = IMPULSO_SALTO
            self.altura = 0
            self.tiempo_salto = 0

        if self.en_salto:
            self.altura += self.vel_y
            self.vel_y -= GRAVEDAD
            self.tiempo_salto += 1
            if self.altura <= 0:
                self.altura = 0
                self.vel_y = 0
                self.en_salto = False

        if x_rival is not None and not se_mueve and not self.atacando and not self.en_salto:
            self.mirando_derecha = x_rival >= self.x

        indice_ataque = 0
        n_ataque = 1
        if self.atacando:
            n_ataque = len(animaciones[self.tipo_ataque])
            por_cuadro = ATAQUES[self.tipo_ataque]["duracion"] / n_ataque
            indice_ataque = int((ahora - self.inicio_ataque) / por_cuadro)
            if indice_ataque >= n_ataque:
                self.atacando = False

        if self.atacando and self.tipo_ataque == "especial" and not self.proyectil_lanzado:
            cuadros_proyectil = animaciones.get("proyectil") or []
            if cuadros_proyectil and indice_ataque / n_ataque >= LANZAMIENTO:
                self.lanzar_proyectil(ahora, cuadros_proyectil)

        if self.atacando:
            self.accion = self.tipo_ataque
            self.indice_cuadro = indice_ataque
            self.accion_anterior = "ataque"
        elif self.en_salto:
            self.accion = "salto"
            progreso = min(self.tiempo_salto / DURACION_SALTO, 0.999)
            self.indice_cuadro = int(progreso * len(animaciones["salto"]))
            self.accion_anterior = "salto"
        elif self.defendiendo:
            cuadros = animaciones["defensa"]
            self.accion = "defensa"
            self.indice_cuadro = min(1, int((ahora - self.inicio_defensa) / 80), len(cuadros) - 1)
            self.accion_anterior = "defensa"
        else:
            if se_mueve:
                nueva = "correr" if corriendo else "caminar"
            else:
                nueva = "quieta"

            if nueva != self.accion_anterior:
                self.indice_cuadro = 0
                self.accion_anterior = nueva

            self.accion = nueva
            cuadros = animaciones[nueva]

            if ahora - self.ultima_actualizacion >= 100:
                self.indice_cuadro += 1
                self.ultima_actualizacion = ahora

            self.indice_cuadro %= len(cuadros)

        self.mover_proyectiles(ahora, animaciones)

    def actualizar_final(self, ahora):
        animaciones = ANIMACIONES.get(self.forma, animaciones_shauna)
        self.altura = 0
        self.en_salto = False
        self.atacando = False
        self.defendiendo = False
        transcurrido = ahora - self.inicio_final

        if self.estado_final == "ganador" and animaciones.get("victoria"):
            cuadros = animaciones["victoria"]
            self.accion = "victoria"
            self.indice_cuadro = int(transcurrido // 300) % len(cuadros)
        elif self.estado_final == "perdedor" and animaciones.get("caida"):
            if transcurrido < DURACION_FASE["caida"] or not animaciones.get("derrota"):
                cuadros = animaciones["caida"]
                self.accion = "caida"
                self.indice_cuadro = min(
                    len(cuadros) - 1,
                    int(transcurrido / DURACION_FASE["caida"] * len(cuadros))
                )
            else:
                cuadros = animaciones["derrota"]
                self.accion = "derrota"
                espera = transcurrido - DURACION_FASE["caida"]
                self.indice_cuadro = int(espera // 400) % len(cuadros)
        else:
            self.accion = "quieta"
            self.indice_cuadro = 0

    def estado(self):
        return {
            "x": self.x,
            "altura": self.altura,
            "mirando": self.mirando_derecha,
            "forma": self.forma,
            "accion": self.accion,
            "indice": self.indice_cuadro,
            "vida": self.vida,
            "atacando": self.atacando,
            "tipo": self.tipo_ataque,
            "id_ataque": self.id_ataque,
            "proyectiles": [
                {
                    "id": p["id"],
                    "x": p["x"],
                    "d": p["direccion"],
                    "f": p["f"],
                    "g": 1 if p["golpeo"] else 0,
                }
                for p in self.proyectiles
            ],
        }

    def aplicar_estado(self, e):
        proyectiles = [
            {
                "id": p["id"],
                "x": p["x"],
                "direccion": p["d"],
                "f": p["f"],
                "golpeo": bool(p["g"]),
            }
            for p in e["proyectiles"]
        ]
        self.x = e["x"]
        self.altura = e["altura"]
        self.mirando_derecha = e["mirando"]
        self.forma = e["forma"]
        self.accion = e["accion"]
        self.indice_cuadro = e["indice"]
        self.vida = e["vida"]
        self.atacando = e["atacando"]
        self.tipo_ataque = e["tipo"]
        self.id_ataque = e["id_ataque"]
        self.proyectiles = proyectiles

    def dibujar(self, ahora):
        animaciones = ANIMACIONES.get(self.forma, animaciones_shauna)
        cuadros = animaciones.get(self.accion) or animaciones["quieta"]
        imagen = cuadros[max(0, min(int(self.indice_cuadro), len(cuadros) - 1))]
        if not self.mirando_derecha:
            imagen = pygame.transform.flip(imagen, True, False)

        parpadeo = ahora < self.golpeado_hasta and (ahora // 60) % 2 == 0
        if not parpadeo:
            ventana.blit(
                imagen,
                (int(self.x) + 50 - imagen.get_width() // 2,
                 SUELO - imagen.get_height() - int(self.altura))
            )

        cuadros_proyectil = animaciones.get("proyectil") or []
        if cuadros_proyectil:
            for p in self.proyectiles:
                if p["golpeo"]:
                    continue
                img_p = cuadros_proyectil[max(0, min(int(p["f"]), len(cuadros_proyectil) - 1))]
                if p["direccion"] < 0:
                    img_p = pygame.transform.flip(img_p, True, False)
                ventana.blit(
                    img_p,
                    (int(p["x"]) - img_p.get_width() // 2, SUELO - img_p.get_height())
                )


def nombre_tecla(tecla):
    return pygame.key.name(tecla).upper()


def texto_ayuda(jugador):
    c = jugador.controles
    animaciones = ANIMACIONES.get(jugador.forma, animaciones_shauna)
    partes = [
        f"{nombre_tecla(c['izq'][0])}/{nombre_tecla(c['der'][0])} mover",
        f"{nombre_tecla(c['salto'][0])} saltar",
        f"{nombre_tecla(c['correr'][0])} correr",
    ]
    etiquetas = (
        ("ataque", "golpe"), ("fuerte", "golpe fuerte"), ("patada", "patada"),
        ("patada_fuerte", "patada fuerte"), ("especial", "especial"),
    )
    for tipo, etiqueta in etiquetas:
        if animaciones.get(tipo):
            partes.append(f"{nombre_tecla(c[tipo])} {etiqueta}")
    if animaciones.get("defensa"):
        partes.append(f"{nombre_tecla(c['defensa'][0])} defensa")
    if len(PERSONAJES[jugador.personaje]["formas"]) > 1:
        partes.append(f"{nombre_tecla(c['transformar'])} transformar")
    return " | ".join(partes)


def rect_proyectil(p, cuadros):
    if cuadros:
        img = cuadros[max(0, min(int(p["f"]), len(cuadros) - 1))]
        ancho = int(img.get_width() * 0.5)
        alto = int(img.get_height() * 0.45)
    else:
        ancho = 60
        alto = 60
    return pygame.Rect(int(p["x"]) - ancho // 2, SUELO - alto, ancho, alto)


def marcar_proyectiles(duenio, rival):
    cuerpo = rival.rect_cuerpo()
    animaciones = ANIMACIONES.get(duenio.forma, animaciones_shauna)
    cuadros = animaciones.get("proyectil") or []
    for p in duenio.proyectiles:
        if not p["golpeo"] and rect_proyectil(p, cuadros).colliderect(cuerpo):
            p["golpeo"] = True
            p["resto"] = 6


def aplicar_golpes(atacante, defensor, ahora):
    if defensor.vida <= 0 or defensor.invulnerable():
        return
    cuerpo = defensor.rect_cuerpo()
    animaciones = ANIMACIONES.get(atacante.forma, animaciones_shauna)

    tipo = atacante.tipo_ataque
    if atacante.atacando and tipo in ATAQUES and tipo != "especial":
        cfg = ATAQUES[tipo]
        n = max(1, len(animaciones.get(tipo) or [None]))
        progreso = (atacante.indice_cuadro + 0.5) / n
        clave = ("a", atacante.id_ataque)
        en_ventana = cfg["ventana"][0] <= progreso <= cfg["ventana"][1]
        if clave not in defensor.golpes_recibidos and en_ventana:
            if atacante.rect_golpe(cfg["alcance"]).colliderect(cuerpo):
                defensor.golpes_recibidos.add(clave)
                direccion = 1 if atacante.mirando_derecha else -1
                defensor.recibir_dano(cfg["dano"], direccion, ahora, cfg["derriba"])
                if defensor.invulnerable() or defensor.vida <= 0:
                    return

    cuadros = animaciones.get("proyectil") or []
    for p in atacante.proyectiles:
        clave = ("p", p["id"])
        if clave in defensor.golpes_recibidos:
            continue
        if rect_proyectil(p, cuadros).colliderect(cuerpo):
            defensor.golpes_recibidos.add(clave)
            cfg = ATAQUES["especial"]
            defensor.recibir_dano(cfg["dano"], p["direccion"], ahora, cfg["derriba"])
            break


class Aplicacion:
    def __init__(self):
        self.red = Red()
        self.ip_propia = ""
        self.reiniciar_todo("")

    def reiniciar_todo(self, mensaje):
        self.red.cerrar()
        self.red = Red()
        self.estado = "menu"
        self.modo = None
        self.mensaje = mensaje
        self.texto_ip = ""
        self.votos = {nombre: 0 for nombre in escenarios}
        self.voto_actual = None
        self.escenario = None
        self.jugadores = []
        self.local = None
        self.remoto = None
        self.terminada = False
        self.desconectado = False
        self.ganador = ""
        self.eleccion = []
        self.mi_personaje = None
        self.personaje_rival = None

    def iniciar_partida(self):
        self.terminada = False
        self.desconectado = False
        self.ganador = ""
        self.local = None
        self.remoto = None

        if self.modo == "uno":
            self.jugadores = [Jugador("JUGADOR 1", 150, True, CONTROLES_J1, self.eleccion[0])]
        elif self.modo == "local":
            self.jugadores = [
                Jugador("JUGADOR 1", 150, True, CONTROLES_J1, self.eleccion[0]),
                Jugador("JUGADOR 2", 750, False, CONTROLES_J2, self.eleccion[1]),
            ]
        elif self.modo == "online_host":
            j1 = Jugador("JUGADOR 1", 150, True, CONTROLES_J1, self.mi_personaje)
            j2 = Jugador("JUGADOR 2", 750, False, None, self.personaje_rival)
            self.jugadores = [j1, j2]
            self.local = j1
            self.remoto = j2
        elif self.modo == "online_cliente":
            j1 = Jugador("JUGADOR 1", 150, True, None, self.personaje_rival)
            j2 = Jugador("JUGADOR 2", 750, False, CONTROLES_J1, self.mi_personaje)
            self.jugadores = [j1, j2]
            self.local = j2
            self.remoto = j1

        self.estado = "juego"

    def tarjetas_personaje(self):
        claves = list(PERSONAJES.keys())
        n = len(claves)
        separacion = 30
        ancho = min(280, (ANCHO - 40 - (n - 1) * separacion) // n)
        total = n * ancho + (n - 1) * separacion
        inicio = (ANCHO - total) // 2
        return {
            clave: pygame.Rect(inicio + i * (ancho + separacion), 150, ancho, 300)
            for i, clave in enumerate(claves)
        }

    def elegir_personaje(self, clave):
        if self.modo == "uno":
            self.eleccion = [clave]
            self.iniciar_partida()
        elif self.modo == "local":
            self.eleccion.append(clave)
            if len(self.eleccion) == 2:
                self.iniciar_partida()
        else:
            self.mi_personaje = clave
            self.red.enviar({"tipo": "listo", "personaje": clave})
            self.revisar_listos()

    def revisar_listos(self):
        if self.estado != "personaje":
            return
        if self.mi_personaje is not None and self.personaje_rival is not None:
            self.iniciar_partida()

    def evento_personaje(self, evento):
        if evento.type != pygame.MOUSEBUTTONDOWN or evento.button != 1:
            return
        if self.modo in ("online_host", "online_cliente") and self.mi_personaje is not None:
            return
        for clave, rect in self.tarjetas_personaje().items():
            if rect.collidepoint(evento.pos):
                self.elegir_personaje(clave)
                break

    def al_presionar_escape(self):
        if self.estado == "menu":
            return
        if self.estado == "online":
            self.estado = "menu"
            self.mensaje = ""
        elif self.estado in ("esperando_jugador", "ingresar_ip"):
            self.red.cerrar()
            self.red = Red()
            self.estado = "online"
            self.mensaje = ""
        else:
            self.reiniciar_todo("")

    def manejar_evento(self, evento, ahora):
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            self.al_presionar_escape()
            return

        if self.estado == "menu":
            self.evento_menu(evento)
        elif self.estado == "online":
            self.evento_online(evento)
        elif self.estado == "ingresar_ip":
            self.evento_ip(evento)
        elif self.estado == "votacion":
            self.evento_votacion(evento)
        elif self.estado == "personaje":
            self.evento_personaje(evento)
        elif self.estado == "juego":
            self.evento_juego(evento, ahora)

    def evento_menu(self, evento):
        accion = None
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            for clave, _, rect in BOTONES_MENU:
                if rect.collidepoint(evento.pos):
                    accion = clave
        elif evento.type == pygame.KEYDOWN:
            accion = {pygame.K_1: "uno", pygame.K_2: "local", pygame.K_3: "online"}.get(evento.key)

        if accion in ("uno", "local"):
            self.modo = accion
            self.estado = "votacion"
            self.mensaje = ""
        elif accion == "online":
            self.estado = "online"
            self.mensaje = ""

    def evento_online(self, evento):
        accion = None
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            for clave, _, rect in BOTONES_ONLINE:
                if rect.collidepoint(evento.pos):
                    accion = clave
        elif evento.type == pygame.KEYDOWN:
            accion = {pygame.K_1: "host", pygame.K_2: "unirse", pygame.K_3: "volver"}.get(evento.key)

        if accion == "host":
            try:
                self.red.crear_servidor()
                self.ip_propia = ip_local()
                self.estado = "esperando_jugador"
                self.mensaje = ""
            except OSError:
                self.red = Red()
                self.mensaje = "No se pudo abrir el puerto. Puede que ya haya otra partida abierta."
        elif accion == "unirse":
            self.estado = "ingresar_ip"
            self.texto_ip = ""
            self.mensaje = ""
        elif accion == "volver":
            self.estado = "menu"
            self.mensaje = ""

    def evento_ip(self, evento):
        if evento.type != pygame.KEYDOWN:
            return
        if evento.key == pygame.K_BACKSPACE:
            self.texto_ip = self.texto_ip[:-1]
        elif evento.key == pygame.K_RETURN:
            ip = self.texto_ip.strip()
            if ip and self.red.estado_conexion != "conectando":
                self.red = Red()
                self.red.conectar(ip)
                self.mensaje = "Conectando..."
        elif evento.unicode and evento.unicode.isprintable() and len(self.texto_ip) < 40:
            self.texto_ip += evento.unicode

    def evento_votacion(self, evento):
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            for nombre, rectangulo in tarjetas.items():
                if rectangulo.collidepoint(evento.pos):
                    if self.voto_actual is not None:
                        self.votos[self.voto_actual] -= 1
                    self.voto_actual = nombre
                    self.votos[nombre] += 1

            if boton_confirmar.collidepoint(evento.pos) and self.voto_actual is not None:
                maximo_votos = max(self.votos.values())
                empatados = [
                    nombre for nombre, cantidad in self.votos.items()
                    if cantidad == maximo_votos
                ]
                self.escenario = random.choice(empatados)
                if self.modo == "online_host":
                    self.red.enviar({"tipo": "inicio", "escenario": self.escenario})
                self.eleccion = []
                self.estado = "personaje"

    def evento_juego(self, evento, ahora):
        if evento.type != pygame.KEYDOWN:
            return
        if self.terminada or self.desconectado:
            if evento.key == pygame.K_RETURN and self.modo == "local" and self.terminada:
                self.iniciar_partida()
            return
        if self.modo in ("uno", "local"):
            for j in self.jugadores:
                j.tecla_presionada(evento.key, ahora)
        else:
            self.local.tecla_presionada(evento.key, ahora)

    def procesar_mensaje(self, msg):
        if not isinstance(msg, dict):
            return
        tipo = msg.get("tipo")
        if tipo == "inicio":
            if self.modo == "online_cliente" and self.estado == "esperando_inicio":
                escenario = msg.get("escenario")
                if escenario in mapas:
                    self.escenario = escenario
                    self.eleccion = []
                    self.estado = "personaje"
        elif tipo == "listo":
            personaje = msg.get("personaje")
            if personaje in PERSONAJES:
                self.personaje_rival = personaje
                self.revisar_listos()
        elif tipo == "estado" and self.remoto is not None:
            try:
                self.remoto.aplicar_estado(msg)
            except (KeyError, TypeError):
                pass

    def revisar_fin(self, ahora):
        if len(self.jugadores) < 2:
            return
        j1, j2 = self.jugadores
        if j1.vida <= 0 or j2.vida <= 0:
            self.terminada = True
            if j1.vida <= 0 and j2.vida <= 0:
                self.ganador = "EMPATE"
                j1.estado_final = "perdedor"
                j2.estado_final = "perdedor"
            elif j1.vida <= 0:
                self.ganador = "GANA " + j2.nombre
                j1.estado_final = "perdedor"
                j2.estado_final = "ganador"
            else:
                self.ganador = "GANA " + j1.nombre
                j1.estado_final = "ganador"
                j2.estado_final = "perdedor"
            j1.inicio_final = ahora
            j2.inicio_final = ahora

    def actualizar(self, ahora):
        if self.estado == "esperando_jugador":
            if self.red.aceptar():
                self.modo = "online_host"
                self.estado = "votacion"
        elif self.estado == "ingresar_ip":
            if self.red.estado_conexion == "ok":
                self.modo = "online_cliente"
                self.estado = "esperando_inicio"
                self.mensaje = ""
            elif self.red.estado_conexion == "error":
                self.red.estado_conexion = None
                self.mensaje = "No se pudo conectar. Revisa la IP y que el anfitrión esté esperando."
        elif self.estado == "esperando_inicio":
            for msg in self.red.recibir():
                self.procesar_mensaje(msg)
            if self.estado == "esperando_inicio" and not self.red.conectado:
                self.reiniciar_todo("El anfitrión cerró la partida.")
        elif self.estado == "votacion" and self.modo == "online_host":
            if not self.red.conectado:
                self.reiniciar_todo("El otro jugador se desconectó.")
        elif self.estado == "personaje" and self.modo in ("online_host", "online_cliente"):
            for msg in self.red.recibir():
                self.procesar_mensaje(msg)
            if self.estado == "personaje" and not self.red.conectado:
                self.reiniciar_todo("El otro jugador se desconectó.")
        elif self.estado == "juego":
            self.actualizar_juego(ahora)

    def actualizar_juego(self, ahora):
        teclas = pygame.key.get_pressed()
        online = self.modo in ("online_host", "online_cliente")

        if online:
            for msg in self.red.recibir():
                self.procesar_mensaje(msg)
            if not self.red.conectado and not self.terminada:
                self.desconectado = True

        if not self.terminada and not self.desconectado:
            if self.modo == "uno":
                self.jugadores[0].actualizar(teclas, ahora, None)
            elif self.modo == "local":
                j1, j2 = self.jugadores
                j1.actualizar(teclas, ahora, j2.x)
                j2.actualizar(teclas, ahora, j1.x)
                for atacante, defensor in ((j1, j2), (j2, j1)):
                    marcar_proyectiles(atacante, defensor)
                    aplicar_golpes(atacante, defensor, ahora)
                self.revisar_fin(ahora)
            else:
                self.local.actualizar(teclas, ahora, self.remoto.x)
                marcar_proyectiles(self.local, self.remoto)
                aplicar_golpes(self.remoto, self.local, ahora)
                self.revisar_fin(ahora)

        if self.terminada:
            if self.modo == "local":
                finales = self.jugadores
            elif self.local is not None:
                finales = [self.local]
            else:
                finales = []
            for j in finales:
                j.actualizar_final(ahora)

        if online and self.red.conectado:
            datos = self.local.estado()
            datos["tipo"] = "estado"
            self.red.enviar(datos)

    def dibujar(self, ahora):
        ventana.fill((20, 20, 30))
        if self.estado == "menu":
            self.dibujar_menu()
        elif self.estado == "online":
            self.dibujar_online()
        elif self.estado == "esperando_jugador":
            self.dibujar_espera_host()
        elif self.estado == "ingresar_ip":
            self.dibujar_ingresar_ip()
        elif self.estado == "votacion":
            self.dibujar_votacion()
        elif self.estado == "personaje":
            self.dibujar_personaje()
        elif self.estado == "esperando_inicio":
            dibujar_texto("CONECTADO", fuente_grande, (255, 255, 255), (ANCHO // 2, 190), "centro")
            dibujar_texto(
                "Esperando a que el anfitrión elija el escenario...",
                fuente, (255, 215, 0), (ANCHO // 2, 290), "centro"
            )
            dibujar_texto("ESC: salir", fuente_chica, (200, 200, 200), (ANCHO // 2, 540), "centro")
        elif self.estado == "juego":
            self.dibujar_juego(ahora)

    def dibujar_aviso(self):
        if self.mensaje:
            dibujar_texto(self.mensaje, fuente_chica, (255, 120, 120), (ANCHO // 2, 520), "centro")

    def dibujar_menu(self):
        dibujar_texto("REINA DE CORAZONES", fuente_grande, (255, 255, 255), (ANCHO // 2, 70), "centro")
        dibujar_texto("ELIGE EL MODO DE JUEGO", fuente, (255, 215, 0), (ANCHO // 2, 150), "centro")
        for _, texto, rect in BOTONES_MENU:
            dibujar_boton(rect, texto)
        dibujar_texto(
            "Tambien puedes presionar 1, 2 o 3",
            fuente_chica, (200, 200, 200), (ANCHO // 2, 500), "centro"
        )
        self.dibujar_aviso()

    def dibujar_online(self):
        dibujar_texto("ONLINE", fuente_grande, (255, 255, 255), (ANCHO // 2, 70), "centro")
        dibujar_texto("UNO CREA LA PARTIDA Y EL OTRO SE UNE", fuente, (255, 215, 0), (ANCHO // 2, 150), "centro")
        for _, texto, rect in BOTONES_ONLINE:
            dibujar_boton(rect, texto)
        dibujar_texto(
            "Conexion directa: misma red WiFi o puerto abierto en el router",
            fuente_chica, (200, 200, 200), (ANCHO // 2, 490), "centro"
        )
        self.dibujar_aviso()

    def dibujar_espera_host(self):
        dibujar_texto("ESPERANDO JUGADOR...", fuente_grande, (255, 255, 255), (ANCHO // 2, 120), "centro")
        dibujar_texto(f"Tu IP: {self.ip_propia}", fuente_grande, (255, 215, 0), (ANCHO // 2, 230), "centro")
        dibujar_texto(f"Puerto: {PUERTO}", fuente, (255, 255, 255), (ANCHO // 2, 310), "centro")
        dibujar_texto(
            "Dile al otro jugador que elija UNIRSE y escriba esa IP",
            fuente, (200, 200, 200), (ANCHO // 2, 380), "centro"
        )
        dibujar_texto(
            "Por internet hay que abrir el puerto en el router o usar una VPN como Tailscale",
            fuente_chica, (200, 200, 200), (ANCHO // 2, 430), "centro"
        )
        dibujar_texto("ESC: cancelar", fuente_chica, (200, 200, 200), (ANCHO // 2, 540), "centro")

    def dibujar_ingresar_ip(self):
        dibujar_texto("IP DEL ANFITRION", fuente_grande, (255, 255, 255), (ANCHO // 2, 110), "centro")
        caja = pygame.Rect(300, 240, 400, 60)
        pygame.draw.rect(ventana, (70, 70, 85), caja, border_radius=8)
        pygame.draw.rect(ventana, (255, 255, 255), caja, 2, border_radius=8)
        cursor = "|" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        etiqueta = fuente.render(self.texto_ip + cursor, True, (255, 255, 255))
        ventana.blit(etiqueta, etiqueta.get_rect(midleft=(caja.x + 15, caja.centery)))
        dibujar_texto("ENTER: conectar | ESC: volver", fuente, (200, 200, 200), (ANCHO // 2, 340), "centro")
        self.dibujar_aviso()

    def dibujar_votacion(self):
        titulo = fuente.render("ELIGE EL ESCENARIO", True, (255, 255, 255))
        ventana.blit(titulo, (350, 60))

        for nombre, rectangulo in tarjetas.items():
            pygame.draw.rect(ventana, (70, 70, 85), rectangulo)
            ventana.blit(imagenes_tarjetas[nombre], (rectangulo.x + 5, rectangulo.y + 5))

            texto = fuente.render(nombre, True, (255, 255, 255))
            ventana.blit(texto, (rectangulo.x + 10, rectangulo.y + 230))

            texto_votos = fuente.render(f"Votos: {self.votos[nombre]}", True, (255, 215, 0))
            ventana.blit(texto_votos, (rectangulo.x + 10, rectangulo.y + 265))

            if self.voto_actual == nombre:
                pygame.draw.rect(ventana, (255, 50, 70), rectangulo, 4)

        pygame.draw.rect(ventana, (200, 40, 60), boton_confirmar, border_radius=8)
        texto_boton = fuente.render("CONFIRMAR VOTO", True, (255, 255, 255))
        ventana.blit(texto_boton, texto_boton.get_rect(center=boton_confirmar.center))

    def dibujar_personaje(self):
        if self.modo == "local":
            titulo = f"JUGADOR {min(len(self.eleccion) + 1, 2)}: ELIGE TU PERSONAJE"
        else:
            titulo = "ELIGE TU PERSONAJE"
        dibujar_texto(titulo, fuente, (255, 255, 255), (ANCHO // 2, 60), "centro")

        for clave, rect in self.tarjetas_personaje().items():
            datos = PERSONAJES[clave]
            pygame.draw.rect(ventana, (70, 70, 85), rect)
            quieta = ANIMACIONES[datos["forma_inicial"]]["quieta"][0]
            ventana.blit(quieta, (rect.centerx - quieta.get_width() // 2, rect.y + 15))
            dibujar_texto(datos["nombre"], fuente, (255, 255, 255), (rect.centerx, rect.y + 215), "centro")
            lineas = lineas_ajustadas(datos["descripcion"], fuente_mini, rect.width - 16)
            for numero, linea in enumerate(lineas):
                dibujar_texto(
                    linea, fuente_mini, (200, 200, 200),
                    (rect.centerx, rect.y + 255 + numero * 17), "centro"
                )
            if self.mi_personaje == clave:
                pygame.draw.rect(ventana, (255, 50, 70), rect, 4)

        for i, aviso in enumerate(avisos_personajes[:3]):
            dibujar_texto(aviso, fuente_mini, (255, 120, 120), (ANCHO // 2, 465 + i * 18), "centro")

        if self.mi_personaje is not None:
            dibujar_texto(
                "Esperando al otro jugador...", fuente, (255, 215, 0), (ANCHO // 2, 500), "centro"
            )
        dibujar_texto("ESC: salir", fuente_chica, (200, 200, 200), (ANCHO // 2, 550), "centro")

    def dibujar_barras(self):
        j1, j2 = self.jugadores
        barras = (
            (j1, pygame.Rect(20, 20, 380, 24), False),
            (j2, pygame.Rect(ANCHO - 400, 20, 380, 24), True),
        )
        for j, barra, derecha in barras:
            pygame.draw.rect(ventana, (40, 40, 50), barra)
            proporcion = max(0, j.vida) / VIDA_MAXIMA
            relleno = pygame.Rect(barra.x, barra.y, int(barra.width * proporcion), barra.height)
            if derecha:
                relleno.right = barra.right
            if proporcion > 0.5:
                color = (60, 200, 90)
            elif proporcion > 0.25:
                color = (230, 200, 50)
            else:
                color = (220, 50, 60)
            pygame.draw.rect(ventana, color, relleno)
            pygame.draw.rect(ventana, (255, 255, 255), barra, 2)

            nombre = j.nombre
            if self.local is not None and j is self.local:
                nombre += " (TU)"
            if derecha:
                dibujar_texto(nombre, fuente_chica, (255, 255, 255), (barra.right, 48), "der")
            else:
                dibujar_texto(nombre, fuente_chica, (255, 255, 255), (barra.x, 48), "izq")

    def dibujar_juego(self, ahora):
        ventana.blit(mapas[self.escenario], (0, 0))

        for j in self.jugadores:
            j.dibujar(ahora)

        if len(self.jugadores) == 2:
            self.dibujar_barras()

        dibujar_texto(
            f"ESCENARIO: {self.escenario}", fuente_chica, (255, 255, 255),
            (ANCHO // 2, 50), "centro"
        )

        blanco = (255, 255, 255)
        if self.modo == "local":
            dibujar_texto("J1: " + texto_ayuda(self.jugadores[0]), fuente_mini, blanco, (20, ALTO - 55))
            dibujar_texto("J2: " + texto_ayuda(self.jugadores[1]), fuente_mini, blanco, (20, ALTO - 30))
        else:
            propio = self.local if self.local is not None else self.jugadores[0]
            dibujar_texto(texto_ayuda(propio) + " | ESC menu", fuente_mini, blanco, (20, ALTO - 30))

        if self.terminada or self.desconectado:
            velo = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
            velo.fill((0, 0, 0, 150))
            ventana.blit(velo, (0, 0))
            titulo = "SE PERDIO LA CONEXION" if self.desconectado else self.ganador
            dibujar_texto(titulo, fuente_grande, (255, 215, 0), (ANCHO // 2, 220), "centro")
            if self.modo == "local" and self.terminada:
                ayuda = "ENTER: revancha | ESC: menu"
            else:
                ayuda = "ESC: menu"
            dibujar_texto(ayuda, fuente, blanco, (ANCHO // 2, 320), "centro")

    def ejecutar(self):
        ejecutando = True
        while ejecutando:
            ahora = pygame.time.get_ticks()
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    ejecutando = False
                else:
                    self.manejar_evento(evento, ahora)
            self.actualizar(ahora)
            self.dibujar(ahora)
            pygame.display.flip()
            reloj.tick(60)
        self.red.cerrar()


Aplicacion().ejecutar()
pygame.quit()