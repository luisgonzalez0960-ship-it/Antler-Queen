import pygame
import random
import os
import socket
import select
import json
import math
import threading
import queue
import urllib.request

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

VIDA_MAXIMA = 300
VIDA_REINA = 600
DANO_DEFENSA = 0.15
MAX_JUGADORES = 4
DURACION_FASE1 = 60

ESCALADO_COMBO = 0.12
MINIMO_ESCALADO = 0.45
GOLPES_PARA_DERRIBO = 5
ENFRIAMIENTO_ESPECIAL = 4500
VELOCIDAD_DEFENSA = 70
RETENCION_DEFENSA = {"cazadora": 1}

ATAQUES = {
    "ataque": {"dano": 9, "ventana": (0.33, 0.78), "alcance": 0.6, "duracion": 450, "derriba": False},
    "fuerte": {"dano": 17, "ventana": (0.5, 0.95), "alcance": 0.8, "duracion": 520, "derriba": False},
    "patada": {"dano": 11, "ventana": (0.2, 0.8), "alcance": 0.7, "duracion": 450, "derriba": False},
    "patada_fuerte": {"dano": 22, "ventana": (0.3, 0.95), "alcance": 0.85, "duracion": 600, "derriba": True},
    "especial": {"dano": 36, "ventana": (0, 0), "alcance": 0, "duracion": 700, "derriba": True},
}

DURACION_FASE = {"golpe": 240, "caida": 500, "levantarse": 500}

ACCIONES = [
    "izq", "der", "salto", "correr", "defensa",
    "ataque", "fuerte", "patada", "patada_fuerte", "especial", "transformar",
]

ETIQUETAS_ACCION = {
    "izq": "IZQUIERDA", "der": "DERECHA", "salto": "SALTAR", "correr": "CORRER",
    "defensa": "DEFENSA", "ataque": "PUÑO", "fuerte": "PUÑO FUERTE", "patada": "PATADA",
    "patada_fuerte": "PATADA FUERTE", "especial": "ESPECIAL", "transformar": "TRANSFORMAR",
}


def controles_por_defecto():
    return {
        "J1": {
            "izq": [pygame.K_a],
            "der": [pygame.K_d],
            "salto": [pygame.K_w, pygame.K_SPACE],
            "correr": [pygame.K_LSHIFT],
            "defensa": [pygame.K_c],
            "ataque": [pygame.K_f],
            "fuerte": [pygame.K_g],
            "patada": [pygame.K_v],
            "patada_fuerte": [pygame.K_b],
            "especial": [pygame.K_r],
            "transformar": [pygame.K_t],
        },
        "J2": {
            "izq": [pygame.K_LEFT],
            "der": [pygame.K_RIGHT],
            "salto": [pygame.K_UP],
            "correr": [pygame.K_RSHIFT],
            "defensa": [pygame.K_DOWN],
            "ataque": [pygame.K_j],
            "fuerte": [pygame.K_k],
            "patada": [pygame.K_n],
            "patada_fuerte": [pygame.K_m],
            "especial": [pygame.K_u],
            "transformar": [pygame.K_i],
        },
    }


CONTROLES_J1 = controles_por_defecto()["J1"]
CONTROLES_J2 = controles_por_defecto()["J2"]


def carpeta_juego():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.getcwd()


def guardar_controles():
    datos = {}
    for nombre, c in (("J1", CONTROLES_J1), ("J2", CONTROLES_J2)):
        datos[nombre] = {accion: [pygame.key.name(k) for k in c[accion]] for accion in ACCIONES}
    try:
        with open(os.path.join(carpeta_juego(), "controles.json"), "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


def cargar_controles():
    ruta = os.path.join(carpeta_juego(), "controles.json")
    if not os.path.exists(ruta):
        return
    try:
        with open(ruta, encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except (OSError, ValueError):
        return
    if not isinstance(datos, dict):
        return
    for nombre, c in (("J1", CONTROLES_J1), ("J2", CONTROLES_J2)):
        guardados = datos.get(nombre)
        if not isinstance(guardados, dict):
            continue
        for accion in ACCIONES:
            nombres = guardados.get(accion)
            if not isinstance(nombres, list):
                continue
            teclas = []
            for n in nombres:
                try:
                    teclas.append(pygame.key.key_code(n))
                except (ValueError, TypeError, AttributeError):
                    pass
            if teclas:
                c[accion] = teclas


def restablecer_controles():
    base = controles_por_defecto()
    CONTROLES_J1.update(base["J1"])
    CONTROLES_J2.update(base["J2"])
    guardar_controles()


cargar_controles()

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
    {
        "clave": "taissa",
        "nombre": "TAISSA",
        "prefijos": ("Taissa",),
        "cuentas": dict(CUENTAS_BASE, W=5, B=4, A2=4, H=4),
        "especial": (4, 4),
        "escala_proyectil": 0.5,
        "descripcion": "Pistola, corazón y forma de araña",
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
    ("uno", "UN JUGADOR", pygame.Rect(300, 190, 400, 64)),
    ("local", "2 JUGADORES (MISMO PC)", pygame.Rect(300, 266, 400, 64)),
    ("online", "ONLINE", pygame.Rect(300, 342, 400, 64)),
    ("controles", "CONTROLES", pygame.Rect(300, 418, 400, 64)),
]

BOTONES_ONLINE = [
    ("host", "CREAR PARTIDA (RED LOCAL / IP)", pygame.Rect(300, 170, 400, 54)),
    ("unirse", "UNIRSE POR IP", pygame.Rect(300, 232, 400, 54)),
    ("sala_inet", "CREAR SALA EN INTERNET", pygame.Rect(300, 294, 400, 54)),
    ("unirse_inet", "UNIRSE CON CÓDIGO", pygame.Rect(300, 356, 400, 54)),
    ("volver", "VOLVER", pygame.Rect(300, 418, 400, 54)),
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

DEFINICION_ANTLER = {
    "clave": "criatura",
    "nombre": "ANTLER QUEEN",
    "prefijos": ("AntlerQueen",),
    "cuentas": dict(CUENTAS_BASE, B=8, A2=4),
    "especial": (5, 3),
    "escala_proyectil": 0.6,
}

animaciones_antler = cargar_plantilla(DEFINICION_ANTLER)
if animaciones_antler is None:
    detalle = avisos_personajes[-1] if avisos_personajes else "revisa la consola"
    raise FileNotFoundError(f"No se pudo cargar a la Antler Queen: {detalle}")
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


PUERTO_RELAY = 5556

MENSAJES_RELAY = {
    "sala_no_existe": "Esa sala no existe. Revisa el código.",
    "sala_llena": "La sala está llena.",
    "sin_respuesta": "El anfitrión no respondió. Intenta de nuevo.",
    "sala_cerrada": "La sala ya se cerró.",
    "sin_servidor": "No se pudo contactar al servidor. Revisa la dirección (F2).",
    "servidor_lleno": "El servidor está lleno. Intenta más tarde.",
}


def leer_linea_socket(sock, limite=80, espera=8.0):
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


def cargar_config_online():
    ruta = os.path.join(carpeta_juego(), "config_online.json")
    try:
        with open(ruta, encoding="utf-8") as archivo:
            datos = json.load(archivo)
        if isinstance(datos, dict):
            return datos
    except (OSError, ValueError):
        pass
    return {}


def guardar_config_online(datos):
    ruta = os.path.join(carpeta_juego(), "config_online.json")
    try:
        with open(ruta, "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


def parsear_direccion(texto):
    texto = (texto or "").strip()
    if not texto:
        return None
    host = texto
    puerto = PUERTO_RELAY
    if texto.count(":") > 1:
        return None
    if texto.count(":") == 1:
        host, parte = texto.split(":")
        try:
            puerto = int(parte)
        except ValueError:
            return None
    host = host.strip()
    if not host or not 1 <= puerto <= 65535:
        return None
    if not all(c.isalnum() or c in ".-_" for c in host):
        return None
    return (host, puerto)


def obtener_ip_publica(destino):
    def tarea():
        for url in ("https://api.ipify.org", "https://ifconfig.me/ip"):
            try:
                with urllib.request.urlopen(url, timeout=4) as respuesta:
                    texto = respuesta.read().decode("utf-8", "replace").strip()
                if 7 <= len(texto) <= 45:
                    destino["ip"] = texto
                    return
            except Exception:
                continue
        destino["ip"] = "no disponible"

    threading.Thread(target=tarea, daemon=True).start()


class Red:
    def __init__(self):
        self.servidor = None
        self.sock = None
        self.buffer = b""
        self.conectado = False
        self.estado_conexion = None
        self.error = ""

    def conectar_relay(self, direccion, codigo):
        self.estado_conexion = "conectando"
        self.error = ""

        def tarea():
            try:
                s = socket.create_connection(direccion, timeout=6)
                s.sendall(("UNIRSE " + codigo + "\n").encode("utf-8"))
                respuesta = leer_linea_socket(s, 80, 22.0)
                if respuesta == "OK":
                    s.settimeout(None)
                    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    self.sock = s
                    self.conectado = True
                    self.estado_conexion = "ok"
                else:
                    self.error = (respuesta or "sin_respuesta").replace("ERROR ", "")
                    s.close()
                    self.estado_conexion = "error"
            except (OSError, UnicodeError):
                self.error = "sin_servidor"
                self.estado_conexion = "error"

        threading.Thread(target=tarea, daemon=True).start()

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


class Anfitrion:
    def __init__(self):
        self.servidor = None
        self.conexiones = []
        self.control = None
        self.relay = None
        self.codigo = ""
        self.relay_estado = None
        self.relay_error = ""
        self.listos = queue.Queue()
        self.buffer_control = b""

    def iniciar_relay(self, direccion):
        self.relay = direccion
        self.relay_estado = "conectando"
        self.relay_error = ""

        def tarea():
            try:
                s = socket.create_connection(direccion, timeout=6)
                s.sendall(b"HOST\n")
                respuesta = leer_linea_socket(s, 80, 8.0)
                if respuesta and respuesta.startswith("CODIGO "):
                    s.settimeout(None)
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    self.codigo = respuesta.split()[1]
                    self.control = s
                    self.relay_estado = "ok"
                else:
                    self.relay_error = (respuesta or "sin_respuesta").replace("ERROR ", "")
                    s.close()
                    self.relay_estado = "error"
            except (OSError, UnicodeError):
                self.relay_error = "sin_servidor"
                self.relay_estado = "error"

        threading.Thread(target=tarea, daemon=True).start()

    def aceptar_relay(self, identificador):
        direccion = self.relay
        codigo = self.codigo

        def tarea():
            try:
                s = socket.create_connection(direccion, timeout=6)
                s.sendall(f"ACEPTAR {codigo} {identificador}\n".encode("utf-8"))
                respuesta = leer_linea_socket(s, 80, 8.0)
                if respuesta == "OK":
                    s.settimeout(None)
                    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    red = Red()
                    red.sock = s
                    red.conectado = True
                    self.listos.put(red)
                else:
                    s.close()
            except (OSError, UnicodeError):
                pass

        threading.Thread(target=tarea, daemon=True).start()

    def leer_control(self):
        if self.control is None:
            return
        try:
            listos, _, _ = select.select([self.control], [], [], 0)
            if not listos:
                return
            datos = self.control.recv(256)
        except OSError:
            datos = b""
        if not datos:
            try:
                self.control.close()
            except OSError:
                pass
            self.control = None
            self.relay_estado = "error"
            self.relay_error = "servidor_caido"
            return
        self.buffer_control += datos
        while b"\n" in self.buffer_control:
            linea, self.buffer_control = self.buffer_control.split(b"\n", 1)
            partes = linea.decode("utf-8", "replace").split()
            if len(partes) == 2 and partes[0] == "NUEVO":
                try:
                    self.aceptar_relay(int(partes[1]))
                except ValueError:
                    pass

    def crear_servidor(self):
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            servidor.bind(("", PUERTO))
            servidor.listen(MAX_JUGADORES)
        except OSError:
            servidor.close()
            raise
        self.servidor = servidor

    def aceptar(self):
        nuevos = []
        if self.servidor is None and self.control is None:
            return nuevos
        while self.servidor is not None and len(self.conexiones) < MAX_JUGADORES - 1:
            listos, _, _ = select.select([self.servidor], [], [], 0)
            if not listos:
                break
            conexion, _ = self.servidor.accept()
            conexion.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            red = Red()
            red.sock = conexion
            red.conectado = True
            self.conexiones.append(red)
            nuevos.append(len(self.conexiones))
        if self.control is not None:
            self.leer_control()
        while True:
            try:
                red = self.listos.get_nowait()
            except queue.Empty:
                break
            if len(self.conexiones) < MAX_JUGADORES - 1:
                self.conexiones.append(red)
                nuevos.append(len(self.conexiones))
            else:
                red.cerrar()
        return nuevos

    def dejar_de_aceptar(self):
        if self.control is not None:
            try:
                self.control.close()
            except OSError:
                pass
            self.control = None
        if self.servidor is not None:
            try:
                self.servidor.close()
            except OSError:
                pass
            self.servidor = None

    def recibir(self):
        mensajes = []
        for k, red in enumerate(self.conexiones):
            for msg in red.recibir():
                mensajes.append((k + 1, msg))
        return mensajes

    def enviar(self, indice, datos):
        if 1 <= indice <= len(self.conexiones):
            self.conexiones[indice - 1].enviar(datos)

    def difundir(self, datos, excepto=None):
        for k, red in enumerate(self.conexiones):
            if excepto is not None and k + 1 == excepto:
                continue
            red.enviar(datos)

    def todos_conectados(self):
        return len(self.conexiones) > 0 and all(r.conectado for r in self.conexiones)

    def limpiar_caidos(self):
        antes = len(self.conexiones)
        self.conexiones = [r for r in self.conexiones if r.conectado]
        if len(self.conexiones) != antes:
            for k, red in enumerate(self.conexiones):
                red.enviar({"tipo": "hola", "indice": k + 1})
            return True
        return False

    def total(self):
        return 1 + len(self.conexiones)

    def cerrar(self):
        self.dejar_de_aceptar()
        for red in self.conexiones:
            red.cerrar()
        self.conexiones = []


class Jugador:
    def __init__(self, nombre, inicio_x, mira_derecha, controles, personaje, indice=0):
        self.indice = indice
        self.vida_max = VIDA_MAXIMA
        self.es_reina = False
        self.puede_atacar = True
        self.puede_transformar = True
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
        self.vida = self.vida_max
        self.hora_muerte = None
        self.golpes_recibidos = set()
        self.golpeado_hasta = 0
        self.defendiendo = False
        self.inicio_defensa = 0
        self.estado_golpe = None
        self.inicio_golpe = 0
        self.estado_final = None
        self.inicio_final = 0
        self.buffer = None
        self.conecto = False
        self.listo_especial_en = 0
        self.combo = 0
        self.ultimo_golpe_recibido = 0

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

        if ahora - self.ultimo_golpe_recibido <= 900:
            self.combo += 1
        else:
            self.combo = 1
        self.ultimo_golpe_recibido = ahora
        dano = max(1, int(dano * max(MINIMO_ESCALADO, 1 - ESCALADO_COMBO * (self.combo - 1))))
        if self.combo >= GOLPES_PARA_DERRIBO:
            derriba = True

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
            self.buffer = None
            if fase == "caida":
                self.combo = 0
        else:
            self.golpeado_hasta = ahora + 250

    def iniciar_ataque(self, tipo, ahora):
        self.atacando = True
        self.tipo_ataque = tipo
        self.inicio_ataque = ahora
        self.proyectil_lanzado = False
        self.defendiendo = False
        self.conecto = False
        self.buffer = None
        self.id_ataque += 1
        if tipo == "especial":
            self.listo_especial_en = ahora + ENFRIAMIENTO_ESPECIAL

    def carga_especial(self, ahora):
        restante = self.listo_especial_en - ahora
        if restante <= 0 or ENFRIAMIENTO_ESPECIAL <= 0:
            return 1.0
        return 1.0 - restante / float(ENFRIAMIENTO_ESPECIAL)

    def puede_cancelar(self, indice, total):
        if self.tipo_ataque == "especial":
            return False
        progreso = (indice + 0.5) / total
        if self.conecto and progreso >= ATAQUES[self.tipo_ataque]["ventana"][0]:
            return True
        return progreso >= 0.8

    def tecla_presionada(self, tecla, ahora):
        c = self.controles
        if c is None or self.vida <= 0 or self.estado_golpe is not None:
            return

        if tecla in c["transformar"]:
            if not self.atacando and self.puede_transformar:
                formas = PERSONAJES[self.personaje]["formas"]
                if len(formas) > 1:
                    self.forma = formas[(formas.index(self.forma) + 1) % len(formas)]
                    self.indice_cuadro = 0
                    self.accion_anterior = "quieta"
            return

        animaciones = ANIMACIONES[self.forma]
        pedido = None
        for tipo in ("ataque", "fuerte", "patada", "patada_fuerte", "especial"):
            if tecla in c[tipo] and animaciones.get(tipo):
                pedido = tipo
                break
        if pedido is None or not self.puede_atacar:
            return
        if pedido == "especial" and ahora < self.listo_especial_en:
            return

        if self.atacando:
            self.buffer = (pedido, ahora)
        elif not (pedido == "especial" and self.en_salto):
            self.iniciar_ataque(pedido, ahora)

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

        if self.combo and ahora - self.ultimo_golpe_recibido > 1200:
            self.combo = 0

        quiere_defender = bool(
            animaciones.get("defensa")
            and alguna(teclas, c["defensa"])
            and not self.atacando
            and not self.en_salto
        )
        if quiere_defender and not self.defendiendo:
            self.inicio_defensa = ahora
        self.defendiendo = quiere_defender

        indice_ataque = 0
        n_ataque = 1
        cancelable = False
        if self.atacando:
            n_ataque = len(animaciones[self.tipo_ataque])
            por_cuadro = ATAQUES[self.tipo_ataque]["duracion"] / n_ataque
            indice_ataque = int((ahora - self.inicio_ataque) / por_cuadro)
            if indice_ataque >= n_ataque:
                self.atacando = False
            else:
                cancelable = self.puede_cancelar(indice_ataque, n_ataque)

        if self.buffer is not None and ahora - self.buffer[1] > 300:
            self.buffer = None
        if self.buffer is not None and (not self.atacando or cancelable):
            tipo_pedido = self.buffer[0]
            especial_bloqueado = tipo_pedido == "especial" and (self.en_salto or ahora < self.listo_especial_en)
            if animaciones.get(tipo_pedido) and not especial_bloqueado:
                self.iniciar_ataque(tipo_pedido, ahora)
                indice_ataque = 0
                n_ataque = len(animaciones[tipo_pedido])
                cancelable = False
            else:
                self.buffer = None

        se_mueve = False
        corriendo = alguna(teclas, c["correr"])
        velocidad_actual = VELOCIDAD_CORRER if corriendo else VELOCIDAD

        if (not self.atacando or self.en_salto) and not self.defendiendo:
            if alguna(teclas, c["izq"]):
                self.x -= velocidad_actual
                self.mirando_derecha = False
                se_mueve = True
            if alguna(teclas, c["der"]):
                self.x += velocidad_actual
                self.mirando_derecha = True
                se_mueve = True

        self.x = max(0, min(self.x, ANCHO - 100))

        quiere_saltar = alguna(teclas, c["salto"])
        if quiere_saltar and not self.en_salto and not self.defendiendo and (not self.atacando or cancelable):
            self.atacando = False
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
            fijo = RETENCION_DEFENSA.get(self.forma, len(cuadros) - 1)
            transcurrido = int((ahora - self.inicio_defensa) / VELOCIDAD_DEFENSA)
            self.indice_cuadro = max(0, min(fijo, len(cuadros) - 1, transcurrido))
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
            "ata": self.tipo_ataque,
            "id_ataque": self.id_ataque,
            "combo": self.combo,
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
        self.tipo_ataque = e["ata"]
        self.id_ataque = e["id_ataque"]
        self.combo = e.get("combo", 0)
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
            partes.append(f"{nombre_tecla(c[tipo][0])} {etiqueta}")
    if animaciones.get("defensa"):
        partes.append(f"{nombre_tecla(c['defensa'][0])} defensa")
    if len(PERSONAJES[jugador.personaje]["formas"]) > 1:
        partes.append(f"{nombre_tecla(c['transformar'][0])} transformar")
    return " | ".join(partes)


def permiso_dano(atacante, defensor):
    return True


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
    if not permiso_dano(duenio, rival):
        return
    cuerpo = rival.rect_cuerpo()
    animaciones = ANIMACIONES.get(duenio.forma, animaciones_shauna)
    cuadros = animaciones.get("proyectil") or []
    for p in duenio.proyectiles:
        if not p["golpeo"] and rect_proyectil(p, cuadros).colliderect(cuerpo):
            p["golpeo"] = True
            p["resto"] = 6


def marcar_conexion(atacante, rival):
    if not atacante.atacando or atacante.conecto or rival.vida <= 0:
        return
    if not permiso_dano(atacante, rival):
        return
    tipo = atacante.tipo_ataque
    if tipo not in ATAQUES or tipo == "especial":
        return
    cfg = ATAQUES[tipo]
    animaciones = ANIMACIONES.get(atacante.forma, animaciones_shauna)
    n = max(1, len(animaciones.get(tipo) or [None]))
    progreso = (atacante.indice_cuadro + 0.5) / n
    if cfg["ventana"][0] <= progreso <= cfg["ventana"][1]:
        if atacante.rect_golpe(cfg["alcance"]).colliderect(rival.rect_cuerpo()):
            atacante.conecto = True


def aplicar_golpes(atacante, defensor, ahora):
    if defensor.vida <= 0 or defensor.invulnerable():
        return
    if not permiso_dano(atacante, defensor):
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


CARTA_REINA = ("Q", "corazon")
CARTAS_NORMALES = [
    ("A", "pica"), ("K", "trebol"), ("J", "diamante"), ("10", "pica"),
    ("7", "trebol"), ("9", "diamante"), ("K", "diamante"),
]
COLORES_JUGADOR = [(90, 170, 255), (255, 110, 110), (110, 220, 130), (245, 205, 70)]
POSICIONES_INICIALES = {1: [150], 2: [150, 750], 3: [100, 450, 800], 4: [60, 320, 580, 840]}

OPCIONES_JUEGO = [
    (
        "survivor", "SURVIVOR",
        "Todos contra todos, como en un Street Fighter o un Smash. El último en pie gana.",
        pygame.Rect(120, 170, 360, 290),
    ),
    (
        "caceria", "CACERÍA",
        "Una carta decide quién es la Reina de Corazones. La Reina tiene el doble de vida y no "
        "puede atacar hasta la mitad de la partida, cuando se transforma en Antler Queen. Antes "
        "de la mitad solo se puede atacar a la Reina. Después es todos contra todos. "
        "El primero en morir es el único que pierde.",
        pygame.Rect(520, 170, 360, 290),
    ),
]

BOTON_EMPEZAR = pygame.Rect(375, 470, 250, 55)


def dibujar_simbolo(sup, palo, centro, tam):
    x, y = centro
    r = max(2, tam // 4)
    rojo = (200, 30, 50)
    negro = (25, 25, 30)
    if palo == "corazon":
        pygame.draw.circle(sup, rojo, (x - r, y - r), r)
        pygame.draw.circle(sup, rojo, (x + r, y - r), r)
        pygame.draw.polygon(sup, rojo, [(x - 2 * r + 1, y - r + 2), (x + 2 * r - 1, y - r + 2), (x, y + 2 * r)])
    elif palo == "diamante":
        pygame.draw.polygon(sup, rojo, [(x, y - 2 * r), (x + int(1.4 * r), y), (x, y + 2 * r), (x - int(1.4 * r), y)])
    elif palo == "pica":
        pygame.draw.circle(sup, negro, (x - r, y + r // 2), r)
        pygame.draw.circle(sup, negro, (x + r, y + r // 2), r)
        pygame.draw.polygon(sup, negro, [(x - 2 * r + 1, y + r // 2 - 2), (x + 2 * r - 1, y + r // 2 - 2), (x, y - 2 * r)])
        pygame.draw.polygon(sup, negro, [(x, y + r // 2), (x - r, y + 2 * r + r // 2), (x + r, y + 2 * r + r // 2)])
    else:
        pygame.draw.circle(sup, negro, (x, y - r), r)
        pygame.draw.circle(sup, negro, (x - r, y + r // 2), r)
        pygame.draw.circle(sup, negro, (x + r, y + r // 2), r)
        pygame.draw.polygon(sup, negro, [(x, y), (x - r, y + 2 * r + r // 2), (x + r, y + 2 * r + r // 2)])


def superficie_carta(ancho, alto, valor=None, palo=None):
    sup = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    if valor is None:
        pygame.draw.rect(sup, (150, 25, 45), (0, 0, ancho, alto), border_radius=10)
        pygame.draw.rect(sup, (240, 220, 220), (8, 8, ancho - 16, alto - 16), 3, border_radius=6)
        for k in range(18, ancho - 8, 20):
            pygame.draw.line(sup, (200, 70, 90), (k, 10), (k, alto - 10), 1)
        for k in range(18, alto - 8, 20):
            pygame.draw.line(sup, (200, 70, 90), (10, k), (ancho - 10, k), 1)
        dibujar_simbolo(sup, "corazon", (ancho // 2, alto // 2), 40)
        return sup
    reina = valor == "Q"
    pygame.draw.rect(sup, (250, 250, 245), (0, 0, ancho, alto), border_radius=10)
    borde = (230, 180, 40) if reina else (60, 60, 70)
    pygame.draw.rect(sup, borde, (0, 0, ancho, alto), 4, border_radius=10)
    color = (200, 30, 50) if palo in ("corazon", "diamante") else (25, 25, 30)
    etiqueta = fuente.render(valor, True, color)
    sup.blit(etiqueta, (10, 8))
    dibujar_simbolo(sup, palo, (ancho // 2, alto // 2), 54)
    giro = pygame.transform.rotate(etiqueta, 180)
    sup.blit(giro, (ancho - giro.get_width() - 10, alto - giro.get_height() - 8))
    return sup


SEL_COLS = 4
SEL_TILE_W = 66
SEL_TILE_H = 80
SEL_HUECO = 8
SEL_SESGO = 10

SEL_NAVY = (7, 12, 30)
SEL_NAVY2 = (13, 24, 52)
SEL_NAVY3 = (26, 46, 92)
SEL_DORADO = (255, 196, 28)
SEL_ORO = (255, 226, 110)
SEL_CREMA = (246, 240, 222)
SEL_SOMBRA = (2, 5, 14)
SEL_COLOR_P = [(255, 196, 28), (90, 175, 255)]

FICHAS = {
    "shauna": {"tipo": "Equilibrada", "alcance": "Medio", "dificultad": "Media"},
    "cazadora": {"tipo": "Poder", "alcance": "Largo", "dificultad": "Media"},
    "misty": {"tipo": "Trampas", "alcance": "Medio", "dificultad": "Difícil"},
    "van": {"tipo": "Velocidad", "alcance": "Corto", "dificultad": "Fácil"},
    "jackie": {"tipo": "Control", "alcance": "Largo", "dificultad": "Media"},
    "taissa": {"tipo": "Disparos", "alcance": "Largo", "dificultad": "Media"},
}

CACHE_SEL = {}


def mezcla_sel(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return (int(c1[0] + (c2[0] - c1[0]) * t), int(c1[1] + (c2[1] - c1[1]) * t), int(c1[2] + (c2[2] - c1[2]) * t))


def fuente_sel(tam, titulo=False):
    clave = ("fuente", tam, titulo)
    if clave not in CACHE_SEL:
        nombres = "impact,bahnschrift,arialblack,arial" if titulo else "bahnschrift,arial"
        CACHE_SEL[clave] = pygame.font.SysFont(nombres, tam, bold=True)
    return CACHE_SEL[clave]


def texto_sel(texto, fuente_, color, pos, al="izq", alfa=255, sombra=True):
    alfa = max(0, min(255, int(alfa)))
    imagen = fuente_.render(texto, True, color)
    rect = imagen.get_rect()
    setattr(rect, {"izq": "topleft", "centro": "midtop", "der": "topright"}[al], pos)
    if sombra:
        proyeccion = fuente_.render(texto, True, SEL_SOMBRA)
        if alfa < 255:
            proyeccion.set_alpha(int(alfa))
        ventana.blit(proyeccion, rect.move(2, 3))
    if alfa < 255:
        imagen.set_alpha(int(alfa))
    ventana.blit(imagen, rect)
    return rect


def texto_neon(texto, fuente_, color, centro_x, y, pulso):
    clave = ("neon", texto, id(fuente_), color)
    if clave not in CACHE_SEL:
        base = fuente_.render(texto, True, color)
        ancho, alto = base.get_size()
        chico = pygame.transform.smoothscale(base, (max(1, ancho // 5), max(1, alto // 5)))
        halo = pygame.transform.smoothscale(chico, (ancho + 50, alto + 50))
        nucleo = fuente_.render(texto, True, SEL_CREMA)
        CACHE_SEL[clave] = (base, halo, nucleo)
    base, halo, nucleo = CACHE_SEL[clave]
    halo.set_alpha(int(110 + 90 * pulso))
    ventana.blit(halo, (centro_x - halo.get_width() // 2, y - 25))
    ventana.blit(base, (centro_x - base.get_width() // 2, y))
    nucleo.set_alpha(int(60 + 60 * pulso))
    ventana.blit(nucleo, (centro_x - nucleo.get_width() // 2, y))


def poligono_tile(rect, sesgo=SEL_SESGO):
    return [(rect.x + sesgo, rect.y), (rect.right, rect.y), (rect.right - sesgo, rect.bottom), (rect.x, rect.bottom)]


def resplandor_sel(radio, color):
    clave = ("glow", radio, color)
    if clave not in CACHE_SEL:
        sup = pygame.Surface((radio * 2, radio * 2), pygame.SRCALPHA)
        for r in range(radio, 0, -3):
            a = int(255 * (1 - r / float(radio)) ** 2 * 0.55)
            pygame.draw.circle(sup, (color[0], color[1], color[2], max(0, min(255, a))), (radio, radio), r)
        CACHE_SEL[clave] = sup
    return CACHE_SEL[clave]


def retrato_tile(clave):
    k = ("retrato", clave)
    if k in CACHE_SEL:
        return CACHE_SEL[k]
    ancho, alto = SEL_TILE_W, SEL_TILE_H
    frames = ANIMACIONES[PERSONAJES[clave]["forma_inicial"]]["quieta"]
    img = frames[0]
    caja = img.get_bounding_rect(min_alpha=40)
    if caja.width < 4 or caja.height < 4:
        caja = img.get_rect()
    lado = max(8, min(caja.width + 10, img.get_width()))
    recorte = pygame.Rect(0, 0, lado, min(img.get_height(), int(lado * alto / float(ancho))))
    recorte.midtop = (caja.centerx, max(0, caja.top - 4))
    recorte = recorte.clamp(img.get_rect())
    pieza = pygame.transform.scale(img.subsurface(recorte).copy(), (ancho, alto))
    salida = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    for y in range(alto):
        fondo_linea = mezcla_sel(SEL_NAVY2, SEL_NAVY3, y / float(alto))
        pygame.draw.line(salida, (fondo_linea[0], fondo_linea[1], fondo_linea[2], 255), (0, y), (ancho, y))
    salida.blit(pieza, (0, 0))
    mascara = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    pygame.draw.polygon(mascara, (255, 255, 255, 255), [(SEL_SESGO, 0), (ancho, 0), (ancho - SEL_SESGO, alto), (0, alto)])
    salida.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    CACHE_SEL[k] = salida
    return salida


def arte_grande(clave, indice, voltear):
    k = ("arte", clave, indice, voltear)
    if k not in CACHE_SEL:
        frames = ANIMACIONES[PERSONAJES[clave]["forma_inicial"]]["quieta"]
        img = frames[indice % len(frames)]
        escala = 400.0 / max(1, img.get_height())
        grande = pygame.transform.scale(img, (max(1, int(img.get_width() * escala)), max(1, int(img.get_height() * escala))))
        if voltear:
            grande = pygame.transform.flip(grande, True, False)
        CACHE_SEL[k] = grande
    return CACHE_SEL[k]


def reflejo_arte(clave, indice, voltear):
    k = ("reflejo", clave, indice, voltear)
    if k not in CACHE_SEL:
        grande = arte_grande(clave, indice, voltear)
        invertida = pygame.transform.flip(grande, False, True)
        alto = min(110, invertida.get_height())
        parte = invertida.subsurface(pygame.Rect(0, 0, invertida.get_width(), alto)).copy()
        parte.set_alpha(55)
        CACHE_SEL[k] = parte
    return CACHE_SEL[k]


class Aplicacion:
    def __init__(self):
        self.red = Red()
        self.anfitrion = Anfitrion()
        self.ip_propia = ""
        self.config_online = cargar_config_online()
        self.reiniciar_todo("")

    def reiniciar_todo(self, mensaje):
        self.red.cerrar()
        self.anfitrion.cerrar()
        self.red = Red()
        self.anfitrion = Anfitrion()
        self.estado = "menu"
        self.modo = None
        self.juego = "survivor"
        self.mensaje = mensaje
        self.texto_ip = ""
        self.votos = {nombre: 0 for nombre in escenarios}
        self.voto_actual = None
        self.escenario = None
        self.jugadores = []
        self.locales = []
        self.local = None
        self.terminada = False
        self.desconectado = False
        self.ganador = ""
        self.subtitulo = ""
        self.eleccion = []
        self.modo_ingreso = "ip"
        self.siguiente_tras_relay = None
        self.via_relay = False
        self.ip_publica = {"ip": ""}
        self.cfg = None
        self.sel = None
        self.personajes_elegidos = {}
        self.mi_personaje = None
        self.mi_indice = 0
        self.n_jugadores = 1
        self.sala_n = 1
        self.reina_indice = None
        self.cartas = []
        self.reveladas = {}
        self.cartas_fin = None
        self.cache_cartas = {}
        self.fase2 = False
        self.inicio_partida = 0
        self.aviso_fase2 = 0

    def es_online(self):
        return self.modo in ("online_host", "online_cliente")

    def permiso(self, atacante, defensor):
        if self.juego != "caceria":
            return True
        if self.fase2:
            return True
        if atacante.es_reina:
            return False
        return defensor.es_reina

    def preparar_cartas(self, n):
        self.reina_indice = random.randrange(n)
        normales = random.sample(range(len(CARTAS_NORMALES)), n - 1)
        self.cartas = []
        k = 0
        for i in range(n):
            if i == self.reina_indice:
                self.cartas.append(-1)
            else:
                self.cartas.append(normales[k])
                k += 1
        self.reveladas = {}
        self.cartas_fin = None
        self.cache_cartas = {}

    def continuar(self):
        self.sel = None
        if self.juego == "caceria" and self.n_jugadores >= 2:
            if self.modo == "local":
                self.preparar_cartas(self.n_jugadores)
            self.estado = "cartas"
        else:
            self.iniciar_partida()

    def iniciar_partida(self):
        global permiso_dano
        permiso_dano = self.permiso
        n = self.n_jugadores
        posiciones = POSICIONES_INICIALES[n]
        online = self.es_online()
        self.terminada = False
        self.desconectado = False
        self.ganador = ""
        self.subtitulo = ""
        self.fase2 = False
        self.aviso_fase2 = 0
        self.inicio_partida = pygame.time.get_ticks()
        self.jugadores = []

        for i in range(n):
            if self.modo == "local":
                controles = CONTROLES_J1 if i == 0 else CONTROLES_J2
            elif online:
                controles = CONTROLES_J1 if i == self.mi_indice else None
            else:
                controles = CONTROLES_J1
            personaje = self.personajes_elegidos[i]
            es_reina = self.juego == "caceria" and n >= 2 and i == self.reina_indice
            if es_reina:
                personaje = "shauna"
            nombre = f"JUGADOR {i + 1}"
            jugador = Jugador(nombre, posiciones[i], posiciones[i] < ANCHO // 2, controles, personaje, i)
            if es_reina:
                jugador.nombre = nombre + " (REINA)"
                jugador.es_reina = True
                jugador.vida_max = VIDA_REINA
                jugador.vida = VIDA_REINA
                jugador.puede_atacar = False
                jugador.puede_transformar = False
            self.jugadores.append(jugador)

        self.locales = [j for j in self.jugadores if j.controles is not None]
        self.local = self.jugadores[self.mi_indice] if online else None
        self.estado = "juego"

    def activar_fase2(self, ahora):
        self.fase2 = True
        self.aviso_fase2 = ahora
        for j in self.jugadores:
            if j.es_reina:
                j.forma = "criatura"
                j.puede_atacar = True
                j.indice_cuadro = 0
                j.accion_anterior = "quieta"

    def actualizar_fases(self, ahora):
        if self.juego != "caceria" or self.fase2:
            return
        if self.modo == "online_cliente":
            return
        if (ahora - self.inicio_partida) / 1000 >= DURACION_FASE1:
            self.activar_fase2(ahora)
            if self.modo == "online_host":
                self.anfitrion.difundir({"tipo": "fase2"})

    def enviar_a_todos(self, datos):
        if self.modo == "online_host":
            self.anfitrion.difundir(datos)
        elif self.modo == "online_cliente":
            self.red.enviar(datos)

    def red_conectada(self):
        if self.modo == "online_host":
            return self.anfitrion.todos_conectados()
        if self.modo == "online_cliente":
            return self.red.conectado
        return True

    def leer_red(self):
        if self.modo == "online_host":
            for origen, msg in self.anfitrion.recibir():
                if not isinstance(msg, dict):
                    continue
                msg["i"] = origen
                self.procesar_mensaje(msg)
                if msg.get("tipo") in ("listo", "volteo", "estado"):
                    self.anfitrion.difundir(msg, excepto=origen)
        elif self.modo == "online_cliente":
            for msg in self.red.recibir():
                self.procesar_mensaje(msg)

    def procesar_mensaje(self, msg):
        if not isinstance(msg, dict):
            return
        tipo = msg.get("tipo")
        try:
            if tipo == "hola":
                self.mi_indice = int(msg["indice"])
            elif tipo == "sala":
                self.sala_n = int(msg["n"])
            elif tipo == "inicio":
                self.procesar_inicio(msg)
            elif tipo == "listo":
                indice = int(msg["i"])
                personaje = msg["personaje"]
                if personaje in PERSONAJES and 0 <= indice < MAX_JUGADORES:
                    self.personajes_elegidos[indice] = personaje
                    self.revisar_listos()
            elif tipo == "volteo":
                indice = int(msg["i"])
                if 0 <= indice < MAX_JUGADORES and indice not in self.reveladas:
                    self.reveladas[indice] = pygame.time.get_ticks()
            elif tipo == "fase2":
                if self.estado == "juego" and not self.fase2:
                    self.activar_fase2(pygame.time.get_ticks())
            elif tipo == "estado":
                indice = int(msg["i"])
                if 0 <= indice < len(self.jugadores):
                    jugador = self.jugadores[indice]
                    if jugador.controles is None:
                        jugador.aplicar_estado(msg)
        except (KeyError, TypeError, ValueError):
            pass

    def procesar_inicio(self, msg):
        if self.modo != "online_cliente" or self.estado != "esperando_inicio":
            return
        escenario = msg["escenario"]
        juego = msg["juego"]
        n = int(msg["n"])
        if escenario not in mapas or juego not in ("survivor", "caceria") or not 2 <= n <= MAX_JUGADORES:
            return
        cartas = [int(c) for c in msg.get("cartas", [])]
        if juego == "caceria" and len(cartas) != n:
            return
        self.escenario = escenario
        self.juego = juego
        self.n_jugadores = n
        self.reina_indice = msg.get("reina")
        self.cartas = cartas
        self.reveladas = {}
        self.cartas_fin = None
        self.cache_cartas = {}
        self.personajes_elegidos = {}
        self.mi_personaje = None
        self.estado = "personaje"

    def revisar_listos(self):
        if self.estado != "personaje":
            return
        if len(self.personajes_elegidos) >= self.n_jugadores:
            self.continuar()

    def al_presionar_escape(self):
        if self.estado == "menu":
            return
        if self.estado == "controles":
            if self.cfg is not None and self.cfg.get("captura") is not None:
                self.cfg["captura"] = None
                self.cfg["mensaje"] = "Cambio cancelado."
            else:
                guardar_controles()
                self.estado = "menu"
            return
        if self.estado == "online":
            self.estado = "menu"
            self.mensaje = ""
        elif self.estado in ("esperando_jugador", "ingresar_ip"):
            self.red.cerrar()
            self.anfitrion.cerrar()
            self.red = Red()
            self.anfitrion = Anfitrion()
            self.modo_ingreso = "ip"
            self.via_relay = False
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
        elif self.estado == "esperando_jugador":
            self.evento_sala(evento)
        elif self.estado == "ingresar_ip":
            self.evento_ip(evento)
        elif self.estado == "modo_juego":
            self.evento_modo_juego(evento)
        elif self.estado == "votacion":
            self.evento_votacion(evento)
        elif self.estado == "controles":
            self.evento_controles(evento)
        elif self.estado == "personaje":
            self.evento_personaje(evento)
        elif self.estado == "cartas":
            self.evento_cartas(evento, ahora)
        elif self.estado == "juego":
            self.evento_juego(evento, ahora)

    def evento_menu(self, evento):
        accion = None
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            for clave, _, rect in BOTONES_MENU:
                if rect.collidepoint(evento.pos):
                    accion = clave
        elif evento.type == pygame.KEYDOWN:
            accion = {pygame.K_1: "uno", pygame.K_2: "local", pygame.K_3: "online", pygame.K_4: "controles"}.get(evento.key)

        if accion == "uno":
            self.modo = "uno"
            self.juego = "survivor"
            self.n_jugadores = 1
            self.estado = "votacion"
            self.mensaje = ""
        elif accion == "local":
            self.modo = "local"
            self.n_jugadores = 2
            self.estado = "modo_juego"
            self.mensaje = ""
        elif accion == "online":
            self.estado = "online"
            self.mensaje = ""
        elif accion == "controles":
            self.cfg = {"captura": None, "mensaje": ""}
            self.estado = "controles"
            self.mensaje = ""

    def evento_online(self, evento):
        accion = None
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            for clave, _, rect in BOTONES_ONLINE:
                if rect.collidepoint(evento.pos):
                    accion = clave
        elif evento.type == pygame.KEYDOWN:
            accion = {pygame.K_1: "host", pygame.K_2: "unirse", pygame.K_3: "sala_inet",
                      pygame.K_4: "unirse_inet", pygame.K_5: "volver"}.get(evento.key)

        if accion == "host":
            try:
                self.anfitrion.crear_servidor()
                self.ip_propia = ip_local()
                self.ip_publica = {"ip": "..."}
                obtener_ip_publica(self.ip_publica)
                self.via_relay = False
                self.modo = "online_host"
                self.mi_indice = 0
                self.sala_n = 1
                self.estado = "esperando_jugador"
                self.mensaje = ""
            except OSError:
                self.anfitrion = Anfitrion()
                self.mensaje = "No se pudo abrir el puerto. Puede que ya haya otra partida abierta."
        elif accion == "unirse":
            self.modo_ingreso = "ip"
            self.estado = "ingresar_ip"
            self.texto_ip = ""
            self.mensaje = ""
        elif accion in ("sala_inet", "unirse_inet"):
            self.asegurar_relay(accion)
        elif accion == "volver":
            self.estado = "menu"
            self.mensaje = ""

    def asegurar_relay(self, siguiente):
        if parsear_direccion(self.config_online.get("relay", "")) is None:
            self.modo_ingreso = "relay"
            self.siguiente_tras_relay = siguiente
            self.texto_ip = ""
            self.estado = "ingresar_ip"
            self.mensaje = ""
            return
        self.seguir_con_relay(siguiente)

    def seguir_con_relay(self, siguiente):
        direccion = parsear_direccion(self.config_online.get("relay", ""))
        if siguiente == "sala_inet":
            self.red.cerrar()
            self.anfitrion.cerrar()
            self.red = Red()
            self.anfitrion = Anfitrion()
            self.anfitrion.iniciar_relay(direccion)
            self.via_relay = True
            self.modo = "online_host"
            self.mi_indice = 0
            self.sala_n = 1
            self.estado = "esperando_jugador"
            self.mensaje = ""
        else:
            self.modo_ingreso = "codigo"
            self.texto_ip = ""
            self.estado = "ingresar_ip"
            self.mensaje = ""

    def evento_sala(self, evento):
        empezar = False
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            empezar = BOTON_EMPEZAR.collidepoint(evento.pos)
        elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_RETURN:
            empezar = True
        if empezar and self.anfitrion.total() >= 2:
            self.anfitrion.dejar_de_aceptar()
            self.n_jugadores = self.anfitrion.total()
            self.estado = "modo_juego"

    def evento_ip(self, evento):
        if evento.type != pygame.KEYDOWN:
            return
        if evento.key == pygame.K_BACKSPACE:
            self.texto_ip = self.texto_ip[:-1]
        elif evento.key == pygame.K_F2 and self.modo_ingreso == "codigo":
            self.modo_ingreso = "relay"
            self.siguiente_tras_relay = "unirse_inet"
            self.texto_ip = self.config_online.get("relay", "")
            self.mensaje = ""
        elif evento.key == pygame.K_RETURN:
            texto = self.texto_ip.strip()
            if not texto or self.red.estado_conexion == "conectando":
                return
            if self.modo_ingreso == "relay":
                if parsear_direccion(texto) is None:
                    self.mensaje = "Escribe algo como midominio.com:5556"
                    return
                self.config_online["relay"] = texto
                guardar_config_online(self.config_online)
                self.seguir_con_relay(self.siguiente_tras_relay or "unirse_inet")
            elif self.modo_ingreso == "codigo":
                direccion = parsear_direccion(self.config_online.get("relay", ""))
                self.red = Red()
                self.red.conectar_relay(direccion, texto.upper())
                self.mensaje = "Conectando (puede tardar unos segundos)..."
            else:
                self.red = Red()
                self.red.conectar(texto)
                self.mensaje = "Conectando..."
        elif evento.unicode and evento.unicode.isprintable():
            if self.modo_ingreso == "codigo":
                letra = evento.unicode.upper()
                if letra.isalnum() and len(self.texto_ip) < 8:
                    self.texto_ip += letra
            elif len(self.texto_ip) < 60:
                self.texto_ip += evento.unicode

    def evento_modo_juego(self, evento):
        elegido = None
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            for clave, _, _, rect in OPCIONES_JUEGO:
                if rect.collidepoint(evento.pos):
                    elegido = clave
        elif evento.type == pygame.KEYDOWN:
            elegido = {pygame.K_1: "survivor", pygame.K_2: "caceria"}.get(evento.key)
        if elegido is not None:
            self.juego = elegido
            self.estado = "votacion"

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
                self.eleccion = []
                self.personajes_elegidos = {}
                self.mi_personaje = None
                if self.modo == "online_host":
                    self.n_jugadores = self.anfitrion.total()
                    if self.juego == "caceria":
                        self.preparar_cartas(self.n_jugadores)
                    self.anfitrion.difundir({
                        "tipo": "inicio",
                        "escenario": self.escenario,
                        "juego": self.juego,
                        "n": self.n_jugadores,
                        "reina": self.reina_indice if self.juego == "caceria" else None,
                        "cartas": self.cartas if self.juego == "caceria" else [],
                    })
                self.estado = "personaje"

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
            self.personajes_elegidos = {0: clave}
            self.continuar()
        elif self.modo == "local":
            self.eleccion.append(clave)
            self.personajes_elegidos[len(self.eleccion) - 1] = clave
            if len(self.eleccion) == 2:
                self.continuar()
        else:
            self.mi_personaje = clave
            self.personajes_elegidos[self.mi_indice] = clave
            self.enviar_a_todos({"tipo": "listo", "i": self.mi_indice, "personaje": clave})
            self.revisar_listos()

    def datos_seleccion(self):
        if self.sel is None:
            claves = list(PERSONAJES.keys())
            filas = max(3, -(-(len(claves) + 1) // SEL_COLS))
            slots = claves + ["azar"]
            slots += [None] * (SEL_COLS * filas - len(slots))
            cursores = 2 if self.modo == "local" else 1
            inicio = [0, 1 if len(claves) > 1 else 0][:cursores]
            ahora = pygame.time.get_ticks()
            self.sel = {
                "slots": slots,
                "filas": filas,
                "cursor": inicio,
                "visual": [list(self.rect_slot(i, filas).topleft) for i in inicio],
                "conf": [None] * cursores,
                "t_conf": [0] * cursores,
                "cambio": [ahora] * cursores,
                "previo": [None] * cursores,
                "listo_en": None,
                "flash": -10000,
                "t0": ahora,
            }
        return self.sel

    def rect_slot(self, indice, filas=3):
        columna = indice % SEL_COLS
        fila = indice // SEL_COLS
        ancho_total = SEL_COLS * (SEL_TILE_W + SEL_HUECO) - SEL_HUECO
        x0 = ANCHO // 2 - ancho_total // 2
        return pygame.Rect(x0 + columna * (SEL_TILE_W + SEL_HUECO), 112 + fila * (SEL_TILE_H + SEL_HUECO), SEL_TILE_W, SEL_TILE_H)

    def clave_de_slot(self, slot):
        if slot is None:
            return None
        if slot == "azar":
            return "azar"
        return slot

    def mover_cursor(self, jugador, dx, dy):
        sel = self.datos_seleccion()
        filas = sel["filas"]
        actual = sel["cursor"][jugador]
        columna = actual % SEL_COLS
        fila = actual // SEL_COLS
        c = columna
        f = fila
        for _ in range(max(SEL_COLS, filas)):
            c += dx
            f += dy
            if c < 0 or c >= SEL_COLS or f < 0 or f >= filas:
                return
            if sel["slots"][f * SEL_COLS + c] is not None:
                sel["cursor"][jugador] = f * SEL_COLS + c
                return

    def confirmar_seleccion(self, jugador, ahora):
        sel = self.datos_seleccion()
        if sel["conf"][jugador] is not None:
            return
        slot = sel["slots"][sel["cursor"][jugador]]
        if slot is None:
            return
        clave = random.choice(list(PERSONAJES.keys())) if slot == "azar" else slot
        sel["conf"][jugador] = clave
        sel["t_conf"][jugador] = ahora
        sel["flash"] = ahora
        if self.modo == "local":
            if all(c is not None for c in sel["conf"]):
                sel["listo_en"] = ahora + 900
        else:
            self.elegir_personaje(clave)

    def cancelar_seleccion(self, jugador):
        sel = self.datos_seleccion()
        if self.es_online() and self.mi_personaje is not None:
            return
        sel["conf"][jugador] = None
        sel["listo_en"] = None

    def acciones_de_tecla(self, tecla):
        acciones = []
        cursores = 2 if self.modo == "local" else 1
        for p in range(cursores):
            c = CONTROLES_J1 if p == 0 else CONTROLES_J2
            if tecla in c["izq"]:
                acciones.append((p, "izq"))
            if tecla in c["der"]:
                acciones.append((p, "der"))
            if tecla in c["salto"]:
                acciones.append((p, "arriba"))
            if tecla in c["defensa"]:
                acciones.append((p, "abajo"))
            if tecla in c["ataque"]:
                acciones.append((p, "ok"))
            if tecla in c["fuerte"]:
                acciones.append((p, "atras"))
        if self.modo != "local":
            c2 = CONTROLES_J2
            if tecla in c2["izq"]:
                acciones.append((0, "izq"))
            if tecla in c2["der"]:
                acciones.append((0, "der"))
            if tecla in c2["salto"]:
                acciones.append((0, "arriba"))
            if tecla in c2["defensa"]:
                acciones.append((0, "abajo"))
            if tecla in (pygame.K_RETURN, pygame.K_SPACE):
                acciones.append((0, "ok"))
        else:
            if tecla == pygame.K_RETURN:
                acciones.append((1, "ok"))
        if tecla == pygame.K_r:
            acciones.append((0, "azar"))
        return acciones

    def filas_controles(self):
        filas = []
        for jugador in range(2):
            x = 40 if jugador == 0 else 520
            for numero, accion in enumerate(ACCIONES):
                filas.append((jugador, accion, pygame.Rect(x, 142 + numero * 30, 440, 27)))
        return filas

    def botones_controles(self):
        return {
            "restablecer": pygame.Rect(40, 498, 270, 46),
            "volver": pygame.Rect(690, 498, 270, 46),
        }

    def evento_controles(self, evento):
        cfg = self.cfg
        if cfg is None:
            return
        if evento.type == pygame.KEYDOWN and cfg["captura"] is not None:
            jugador, accion = cfg["captura"]
            controles = CONTROLES_J1 if jugador == 0 else CONTROLES_J2
            for otra in ACCIONES:
                if otra != accion and evento.key in controles[otra]:
                    cfg["mensaje"] = f"Esa tecla ya se usa en {ETIQUETAS_ACCION[otra]}. Elige otra."
                    return
            controles[accion] = [evento.key]
            cfg["captura"] = None
            guardar_controles()
            cfg["mensaje"] = f"J{jugador + 1}: {ETIQUETAS_ACCION[accion]} = {nombre_tecla(evento.key)}"
            return
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            botones = self.botones_controles()
            if botones["restablecer"].collidepoint(evento.pos):
                restablecer_controles()
                cfg["captura"] = None
                cfg["mensaje"] = "Controles restablecidos."
                return
            if botones["volver"].collidepoint(evento.pos):
                guardar_controles()
                self.estado = "menu"
                return
            for jugador, accion, rect in self.filas_controles():
                if rect.collidepoint(evento.pos):
                    cfg["captura"] = (jugador, accion)
                    cfg["mensaje"] = "Presiona la nueva tecla (ESC cancela)."
                    return

    def dibujar_controles(self, ahora):
        if self.cfg is None:
            self.cfg = {"captura": None, "mensaje": ""}
        cfg = self.cfg
        pulso = 0.5 + 0.5 * math.sin(ahora / 300.0)
        ventana.fill(SEL_NAVY)
        for y in range(0, ALTO, 6):
            pygame.draw.rect(ventana, mezcla_sel(SEL_NAVY, SEL_NAVY2, y / float(ALTO)), (0, y, ANCHO, 6))
        for k in range(4):
            desplazo = int((ahora * 0.03 + k * 300) % (ANCHO + 500)) - 250
            pygame.draw.polygon(ventana, mezcla_sel(SEL_NAVY2, SEL_DORADO, 0.06),
                                [(desplazo, 0), (desplazo + 70, 0), (desplazo - 120, ALTO), (desplazo - 190, ALTO)])
        texto_neon("CONTROLES", fuente_sel(44, True), SEL_DORADO, ANCHO // 2, 18, pulso)
        texto_sel("Haz clic en una acción y presiona la tecla nueva. Se guarda sola.", fuente_sel(15, False),
                  SEL_ORO, (ANCHO // 2, 84), "centro", sombra=False)
        posicion = pygame.mouse.get_pos()
        for jugador in range(2):
            color = SEL_COLOR_P[jugador]
            x = 40 if jugador == 0 else 520
            cabecera = pygame.Rect(x, 106, 440, 30)
            pygame.draw.polygon(ventana, color, poligono_tile(cabecera, 10))
            texto_sel(f"JUGADOR {jugador + 1}", fuente_sel(20, True), SEL_NAVY, (cabecera.centerx, cabecera.y + 3), "centro", sombra=False)
        for jugador, accion, rect in self.filas_controles():
            color = SEL_COLOR_P[jugador]
            controles = CONTROLES_J1 if jugador == 0 else CONTROLES_J2
            activa = cfg["captura"] == (jugador, accion)
            encima = rect.collidepoint(posicion)
            relleno = mezcla_sel(SEL_NAVY2, SEL_NAVY3, 0.9 if (activa or encima) else 0.2)
            pygame.draw.polygon(ventana, relleno, poligono_tile(rect, 8))
            borde = mezcla_sel(color, SEL_CREMA, pulso * 0.6) if activa else mezcla_sel(SEL_NAVY3, color, 0.5 if encima else 0.0)
            pygame.draw.polygon(ventana, borde, poligono_tile(rect, 8), 2 if activa else 1)
            texto_sel(ETIQUETAS_ACCION[accion], fuente_sel(15, True), SEL_CREMA, (rect.x + 18, rect.y + 4), "izq", sombra=False)
            chip = pygame.Rect(rect.right - 190, rect.y + 3, 176, rect.height - 6)
            pygame.draw.rect(ventana, color if activa else SEL_NAVY, chip, border_radius=4)
            pygame.draw.rect(ventana, color, chip, 1, border_radius=4)
            if activa:
                nombre_teclas = "PRESIONA UNA TECLA"
                color_texto = SEL_NAVY
            else:
                nombre_teclas = " / ".join(nombre_tecla(k) for k in controles[accion])
                color_texto = SEL_ORO
            texto_sel(nombre_teclas, fuente_sel(13, True), color_texto, (chip.centerx, chip.y + 3), "centro", sombra=False)
        if cfg["mensaje"]:
            texto_sel(cfg["mensaje"], fuente_sel(16, True), SEL_ORO, (ANCHO // 2, 468), "centro", sombra=False)
        botones = self.botones_controles()
        for clave, rect in botones.items():
            encima = rect.collidepoint(posicion)
            pygame.draw.polygon(ventana, SEL_DORADO if encima else SEL_NAVY3, poligono_tile(rect, 12))
            pygame.draw.polygon(ventana, SEL_ORO, poligono_tile(rect, 12), 2)
            etiqueta = "RESTABLECER" if clave == "restablecer" else "GUARDAR Y VOLVER"
            texto_sel(etiqueta, fuente_sel(22, True), SEL_NAVY if encima else SEL_CREMA, (rect.centerx, rect.y + 10), "centro", sombra=False)
        texto_sel("ESC: guardar y volver", fuente_sel(14, False), SEL_CREMA, (ANCHO // 2, ALTO - 26), "centro", sombra=False)

    def evento_personaje(self, evento):
        sel = self.datos_seleccion()
        ahora = pygame.time.get_ticks()
        if self.es_online() and self.mi_personaje is not None:
            return
        cursores = len(sel["conf"])
        if evento.type == pygame.KEYDOWN:
            for jugador, accion in self.acciones_de_tecla(evento.key):
                if sel["conf"][jugador] is not None and accion != "atras":
                    continue
                if accion == "izq":
                    self.mover_cursor(jugador, -1, 0)
                elif accion == "der":
                    self.mover_cursor(jugador, 1, 0)
                elif accion == "arriba":
                    self.mover_cursor(jugador, 0, -1)
                elif accion == "abajo":
                    self.mover_cursor(jugador, 0, 1)
                elif accion == "ok":
                    self.confirmar_seleccion(jugador, ahora)
                elif accion == "atras":
                    self.cancelar_seleccion(jugador)
                elif accion == "azar":
                    sel["cursor"][jugador] = sel["slots"].index("azar")
                    self.confirmar_seleccion(jugador, ahora)
            return
        activo = 0
        for p in range(cursores):
            if sel["conf"][p] is None:
                activo = p
                break
        else:
            return
        if evento.type == pygame.MOUSEMOTION or (evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1):
            for i, slot in enumerate(sel["slots"]):
                if slot is not None and self.rect_slot(i, sel["filas"]).collidepoint(evento.pos):
                    sel["cursor"][activo] = i
                    if evento.type == pygame.MOUSEBUTTONDOWN:
                        self.confirmar_seleccion(activo, ahora)
                    break

    def actualizar_seleccion(self, ahora):
        sel = self.sel
        if sel is None or self.modo != "local":
            return
        if sel["listo_en"] is not None and ahora >= sel["listo_en"]:
            if all(c is not None for c in sel["conf"]):
                self.eleccion = list(sel["conf"])
                self.personajes_elegidos = {0: sel["conf"][0], 1: sel["conf"][1]}
                self.continuar()

    def dibujar_personaje(self, ahora):
        sel = self.datos_seleccion()
        t = ahora / 1000.0
        pulso = 0.5 + 0.5 * math.sin(t * 3.2)
        ventana.fill(SEL_NAVY)
        for y in range(0, ALTO, 6):
            pygame.draw.rect(ventana, mezcla_sel(SEL_NAVY, SEL_NAVY2, y / float(ALTO)), (0, y, ANCHO, 6))
        for k in range(5):
            desplazo = int((ahora * 0.035 + k * 250) % (ANCHO + 500)) - 250
            pygame.draw.polygon(ventana, mezcla_sel(SEL_NAVY2, SEL_DORADO, 0.07 + 0.03 * pulso),
                                [(desplazo, 0), (desplazo + 70, 0), (desplazo - 120, ALTO), (desplazo - 190, ALTO)])

        cursores = len(sel["conf"])
        claves_hover = []
        for p in range(cursores):
            slot = sel["slots"][sel["cursor"][p]]
            claves_hover.append(slot)
            if slot != sel["previo"][p]:
                sel["previo"][p] = slot
                sel["cambio"][p] = ahora

        rival = None
        if cursores == 1 and self.es_online():
            for indice, clave in self.personajes_elegidos.items():
                if indice != self.mi_indice:
                    rival = clave
                    break

        lados = [(0, 185, False)]
        if cursores == 2:
            lados.append((1, 815, True))
        else:
            lados.append((None, 815, True))

        for jugador, centro_x, voltear in lados:
            if jugador is None:
                clave = rival
                slot = rival
                color = SEL_COLOR_P[1]
                etiqueta = "RIVAL"
                cambio = sel["t0"]
            else:
                slot = claves_hover[jugador]
                clave = slot if slot in PERSONAJES else None
                color = SEL_COLOR_P[jugador]
                etiqueta = "P" + str(jugador + 1)
                cambio = sel["cambio"][jugador]
            entrada = max(0.0, min(1.0, (ahora - cambio) / 280.0))
            entrada = 1 - (1 - entrada) ** 3
            suelo = 512
            ventana.blit(resplandor_sel(210, color), (centro_x - 210, 330 - 210), special_flags=0)
            sombra_suelo = resplandor_sel(90, (0, 0, 0))
            if "sombra_suelo" not in CACHE_SEL:
                CACHE_SEL["sombra_suelo"] = pygame.transform.smoothscale(sombra_suelo, (230, 44))
            ventana.blit(CACHE_SEL["sombra_suelo"], (centro_x - 115, suelo - 22))
            if clave is not None:
                indice = int(ahora / 140)
                arte = arte_grande(clave, indice, voltear)
                desplazo_x = int((1 - entrada) * (-90 if not voltear else 90))
                arte.set_alpha(max(0, min(255, int(255 * entrada))))
                ventana.blit(arte, (centro_x - arte.get_width() // 2 + desplazo_x, suelo - arte.get_height()))
                reflejo = reflejo_arte(clave, indice, voltear)
                ventana.blit(reflejo, (centro_x - reflejo.get_width() // 2 + desplazo_x, suelo + 2))
                nombre = PERSONAJES[clave]["nombre"]
                ficha = FICHAS.get(clave, {"tipo": "—", "alcance": "—", "dificultad": "—"})
            else:
                signo = fuente_sel(150, True).render("?", True, mezcla_sel(SEL_NAVY3, SEL_CREMA, 0.25))
                ventana.blit(signo, (centro_x - signo.get_width() // 2, suelo - 260))
                nombre = "ALEATORIO" if slot == "azar" else ("ESPERANDO..." if jugador is None else "ELIGE")
                ficha = {"tipo": "?", "alcance": "?", "dificultad": "?"}
            if voltear:
                x_nombre = ANCHO - 26
                alinear = "der"
            else:
                x_nombre = 26
                alinear = "izq"
            tag = pygame.Rect(0, 0, 46, 22)
            if voltear:
                tag.topright = (x_nombre, 20)
            else:
                tag.topleft = (x_nombre, 20)
            pygame.draw.polygon(ventana, color, poligono_tile(tag, 6))
            texto_sel(etiqueta, fuente_sel(16, True), SEL_NAVY, (tag.centerx, tag.y + 3), "centro", sombra=False)
            titulo = fuente_sel(64, True)
            nombre_rect = texto_sel(nombre, titulo, SEL_CREMA, (x_nombre, 40), alinear, alfa=int(255 * entrada))
            ancho_linea = max(120, nombre_rect.width + 30)
            if voltear:
                linea = [(ANCHO - 26 - ancho_linea, 112), (ANCHO - 20, 112), (ANCHO - 30, 120), (ANCHO - 36 - ancho_linea, 120)]
            else:
                linea = [(20, 112), (26 + ancho_linea, 112), (16 + ancho_linea, 120), (10, 120)]
            pygame.draw.polygon(ventana, color, linea)
            panel = pygame.Rect(0, 0, 250, 118)
            if voltear:
                panel.bottomright = (ANCHO - 18, 548)
            else:
                panel.bottomleft = (18, 548)
            fondo_panel = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
            pygame.draw.polygon(fondo_panel, (SEL_NAVY[0], SEL_NAVY[1], SEL_NAVY[2], 190),
                                poligono_tile(pygame.Rect(0, 0, panel.width, panel.height), 12))
            ventana.blit(fondo_panel, panel.topleft)
            pygame.draw.polygon(ventana, color, poligono_tile(panel, 12), 2)
            filas_ficha = (("TIPO", ficha["tipo"]), ("ALCANCE", ficha["alcance"]), ("DIFICULTAD", ficha["dificultad"]))
            for numero, (etiq, valor) in enumerate(filas_ficha):
                y = panel.y + 10 + numero * 36
                texto_sel(etiq, fuente_sel(14, False), color, (panel.x + 22, y), "izq", sombra=False)
                texto_sel(valor, fuente_sel(22, True), SEL_CREMA, (panel.x + 22, y + 13), "izq")

        titulo_neon = fuente_sel(40, True)
        texto_neon("ELIGE TU PERSONAJE", titulo_neon, SEL_DORADO, ANCHO // 2, 24, pulso)
        if self.juego == "caceria":
            texto_sel("Si te sale la Reina de Corazones, jugarás como Shauna / Antler Queen", fuente_sel(14, False),
                      SEL_ORO, (ANCHO // 2, 78), "centro", sombra=False)

        ancho_total = SEL_COLS * (SEL_TILE_W + SEL_HUECO) - SEL_HUECO
        marco = pygame.Rect(ANCHO // 2 - ancho_total // 2 - 14, 98, ancho_total + 28, sel["filas"] * (SEL_TILE_H + SEL_HUECO) + 14)
        capa = pygame.Surface((marco.width, marco.height), pygame.SRCALPHA)
        capa.fill((SEL_NAVY[0], SEL_NAVY[1], SEL_NAVY[2], 140))
        ventana.blit(capa, marco.topleft)

        for i, slot in enumerate(sel["slots"]):
            rect = self.rect_slot(i, sel["filas"])
            puntos = poligono_tile(rect)
            if slot is None:
                pygame.draw.polygon(ventana, mezcla_sel(SEL_NAVY, SEL_NAVY2, 0.6), puntos)
                pygame.draw.polygon(ventana, (40, 54, 90), puntos, 2)
                candado = pygame.Rect(rect.centerx - 7, rect.centery - 2, 14, 11)
                pygame.draw.rect(ventana, (52, 68, 108), candado, border_radius=2)
                pygame.draw.arc(ventana, (52, 68, 108), pygame.Rect(candado.x + 2, candado.y - 9, 10, 14), 0, 3.14, 2)
                continue
            if slot == "azar":
                pygame.draw.polygon(ventana, SEL_NAVY3, puntos)
                signo = fuente_sel(46, True).render("?", True, SEL_ORO)
                ventana.blit(signo, (rect.centerx - signo.get_width() // 2 + 2, rect.centery - signo.get_height() // 2 - 6))
                texto_sel("AZAR", fuente_sel(12, True), SEL_CREMA, (rect.centerx + 3, rect.bottom - 17), "centro", sombra=False)
            else:
                ventana.blit(retrato_tile(slot), rect.topleft)
            pygame.draw.polygon(ventana, mezcla_sel(SEL_NAVY3, SEL_CREMA, 0.25), puntos, 2)
            for p in range(cursores):
                if sel["conf"][p] is not None and sel["cursor"][p] == i:
                    capa_conf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                    pygame.draw.polygon(capa_conf, (SEL_COLOR_P[p][0], SEL_COLOR_P[p][1], SEL_COLOR_P[p][2], 95),
                                        [(SEL_SESGO, 0), (rect.width, 0), (rect.width - SEL_SESGO, rect.height), (0, rect.height)])
                    ventana.blit(capa_conf, rect.topleft)

        for p in range(cursores):
            destino = self.rect_slot(sel["cursor"][p], sel["filas"])
            visual = sel["visual"][p]
            visual[0] += (destino.x - visual[0]) * 0.35
            visual[1] += (destino.y - visual[1]) * 0.35
            caja = pygame.Rect(int(visual[0]) - 3, int(visual[1]) - 3, SEL_TILE_W + 6, SEL_TILE_H + 6)
            color = SEL_COLOR_P[p]
            grosor = 3 + int(2 * pulso)
            confirmado = sel["conf"][p] is not None
            brillo = mezcla_sel(color, SEL_CREMA, 0.6 if confirmado else 0.25 * pulso)
            pygame.draw.polygon(ventana, brillo, poligono_tile(caja, SEL_SESGO + 2), grosor)
            etiqueta = pygame.Rect(0, 0, 30, 17)
            etiqueta.bottomleft = (caja.x + SEL_SESGO, caja.y - 1)
            pygame.draw.polygon(ventana, color, poligono_tile(etiqueta, 5))
            texto_sel("P" + str(p + 1), fuente_sel(13, True), SEL_NAVY, (etiqueta.centerx + 1, etiqueta.y + 1), "centro", sombra=False)
            if confirmado:
                texto_sel("LISTO", fuente_sel(13, True), color, (caja.centerx + 3, caja.bottom + 3), "centro")

        barra = pygame.Surface((ANCHO, 44), pygame.SRCALPHA)
        barra.fill((SEL_NAVY[0], SEL_NAVY[1], SEL_NAVY[2], 205))
        ventana.blit(barra, (0, ALTO - 44))
        pygame.draw.line(ventana, SEL_DORADO, (0, ALTO - 44), (ANCHO, ALTO - 44), 2)
        if self.es_online() and self.mi_personaje is not None:
            mensaje = f"Esperando a los demás ({len(self.personajes_elegidos)}/{self.n_jugadores})..."
        elif self.modo == "local":
            todos = all(c is not None for c in sel["conf"])
            mensaje = "¡Listos! Comienza el combate..." if todos else "Cada jugador elige con su cursor."
        else:
            mensaje = "Elige a tu personaje."
        texto_sel(mensaje, fuente_sel(17, True), SEL_ORO, (18, ALTO - 38), "izq", sombra=False)
        if self.modo == "local":
            j1 = CONTROLES_J1
            j2 = CONTROLES_J2
            ayuda = (f"J1: {nombre_tecla(j1['izq'][0])}{nombre_tecla(j1['der'][0])}{nombre_tecla(j1['salto'][0])}"
                     f"{nombre_tecla(j1['defensa'][0])} mover, {nombre_tecla(j1['ataque'][0])} elegir, {nombre_tecla(j1['fuerte'][0])} atrás"
                     f"     J2: flechas, {nombre_tecla(j2['ataque'][0])} elegir, {nombre_tecla(j2['fuerte'][0])} atrás     R: aleatorio")
        else:
            ayuda = (f"Mouse o flechas / {nombre_tecla(CONTROLES_J1['izq'][0])}{nombre_tecla(CONTROLES_J1['der'][0])}"
                     f"{nombre_tecla(CONTROLES_J1['salto'][0])}{nombre_tecla(CONTROLES_J1['defensa'][0])}   ENTER: confirmar   R: aleatorio   ESC: salir")
        texto_sel(ayuda, fuente_sel(14, False), SEL_CREMA, (ANCHO - 18, ALTO - 36), "der", sombra=False)

        dest = min(1.0, 1 - (ahora - sel["flash"]) / 220.0)
        if dest > 0:
            velo = pygame.Surface((ANCHO, ALTO))
            velo.fill((255, 240, 190))
            velo.set_alpha(int(110 * dest))
            ventana.blit(velo, (0, 0))

    def rects_cartas(self):
        n = self.n_jugadores
        total = n * 130 + (n - 1) * 40
        inicio = (ANCHO - total) // 2
        return [pygame.Rect(inicio + i * 170, 210, 130, 190) for i in range(n)]

    def evento_cartas(self, evento, ahora):
        if evento.type != pygame.MOUSEBUTTONDOWN or evento.button != 1:
            return
        for i, rect in enumerate(self.rects_cartas()):
            if rect.collidepoint(evento.pos) and i not in self.reveladas:
                if self.modo == "local":
                    self.reveladas[i] = ahora
                elif self.es_online() and i == self.mi_indice:
                    self.reveladas[i] = ahora
                    self.enviar_a_todos({"tipo": "volteo", "i": i})

    def evento_juego(self, evento, ahora):
        if evento.type != pygame.KEYDOWN:
            return
        if self.terminada or self.desconectado:
            if evento.key == pygame.K_RETURN and self.modo == "local" and self.terminada:
                self.continuar()
            return
        for j in self.locales:
            j.tecla_presionada(evento.key, ahora)

    def x_rival_cercano(self, jugador):
        otros = [o for o in self.jugadores if o is not jugador and o.vida > 0]
        if not otros:
            return None
        return min(otros, key=lambda o: abs(o.x - jugador.x)).x

    def revisar_fin(self, ahora):
        if len(self.jugadores) < 2:
            return
        for j in self.jugadores:
            if j.vida <= 0 and j.hora_muerte is None:
                j.hora_muerte = ahora
                j.estado_final = "perdedor"
                j.inicio_final = ahora
        caidos = [j for j in self.jugadores if j.vida <= 0]
        vivos = [j for j in self.jugadores if j.vida > 0]

        if self.juego == "caceria":
            if not caidos:
                return
            primero = min(caidos, key=lambda j: (j.hora_muerte, j.indice))
            self.terminada = True
            self.ganador = f"PIERDE {primero.nombre}"
            self.subtitulo = "¡GANAN LOS DEMÁS!"
            for j in self.jugadores:
                if j is not primero:
                    j.estado_final = "ganador"
                    j.inicio_final = ahora
        else:
            if len(vivos) > 1:
                return
            self.terminada = True
            self.subtitulo = ""
            if vivos:
                self.ganador = f"GANA {vivos[0].nombre}"
                vivos[0].estado_final = "ganador"
                vivos[0].inicio_final = ahora
            else:
                self.ganador = "EMPATE"

    def actualizar(self, ahora):
        if self.estado == "esperando_jugador":
            if self.via_relay and self.anfitrion.relay_estado == "error":
                motivo = MENSAJES_RELAY.get(self.anfitrion.relay_error, "Se perdió la conexión con el servidor.")
                self.red.cerrar()
                self.anfitrion.cerrar()
                self.red = Red()
                self.anfitrion = Anfitrion()
                self.estado = "online"
                self.mensaje = motivo
                return
            self.anfitrion.recibir()
            cambio = self.anfitrion.limpiar_caidos()
            nuevos = self.anfitrion.aceptar()
            for indice in nuevos:
                self.anfitrion.enviar(indice, {"tipo": "hola", "indice": indice})
            if cambio or nuevos or self.anfitrion.total() != self.sala_n:
                self.sala_n = self.anfitrion.total()
                self.anfitrion.difundir({"tipo": "sala", "n": self.sala_n})
        elif self.estado == "ingresar_ip":
            if self.red.estado_conexion == "ok":
                self.modo = "online_cliente"
                self.estado = "esperando_inicio"
                self.mensaje = ""
            elif self.red.estado_conexion == "error":
                self.red.estado_conexion = None
                if self.modo_ingreso == "codigo":
                    self.mensaje = MENSAJES_RELAY.get(self.red.error, "No se pudo unir a la sala.")
                else:
                    self.mensaje = "No se pudo conectar. Revisa la IP y que el anfitrión esté esperando."
        elif self.estado == "esperando_inicio":
            self.leer_red()
            if self.estado == "esperando_inicio" and not self.red.conectado:
                self.reiniciar_todo("El anfitrión cerró la partida.")
        elif self.estado in ("modo_juego", "votacion", "personaje", "cartas") and self.es_online():
            self.leer_red()
            if self.estado in ("modo_juego", "votacion", "personaje", "cartas") and not self.red_conectada():
                self.reiniciar_todo("Un jugador se desconectó.")
        if self.estado == "personaje":
            self.actualizar_seleccion(ahora)
        if self.estado == "cartas":
            if len(self.reveladas) >= self.n_jugadores:
                if self.cartas_fin is None:
                    self.cartas_fin = max(self.reveladas.values()) + 2500
                elif ahora >= self.cartas_fin:
                    self.iniciar_partida()
        if self.estado == "juego":
            self.actualizar_juego(ahora)

    def actualizar_juego(self, ahora):
        teclas = pygame.key.get_pressed()
        online = self.es_online()

        if online:
            self.leer_red()
            if not self.red_conectada() and not self.terminada:
                self.desconectado = True
                if self.modo == "online_host":
                    self.anfitrion.cerrar()

        if not self.terminada and not self.desconectado:
            self.actualizar_fases(ahora)
            for j in self.locales:
                if j.vida > 0:
                    j.actualizar(teclas, ahora, self.x_rival_cercano(j))
                else:
                    j.actualizar_final(ahora)
            for atacante in self.locales:
                for rival in self.jugadores:
                    if rival is not atacante:
                        marcar_conexion(atacante, rival)
                        marcar_proyectiles(atacante, rival)
            for defensor in self.locales:
                for atacante in self.jugadores:
                    if atacante is not defensor:
                        aplicar_golpes(atacante, defensor, ahora)
            self.revisar_fin(ahora)

        if self.terminada:
            for j in self.locales:
                j.actualizar_final(ahora)

        if online and self.red_conectada() and self.local is not None:
            datos = self.local.estado()
            datos["tipo"] = "estado"
            datos["i"] = self.mi_indice
            self.enviar_a_todos(datos)

    def dibujar(self, ahora):
        ventana.fill((20, 20, 30))
        if self.estado == "menu":
            self.dibujar_menu()
        elif self.estado == "online":
            self.dibujar_online()
        elif self.estado == "esperando_jugador":
            self.dibujar_sala()
        elif self.estado == "ingresar_ip":
            self.dibujar_ingresar_ip()
        elif self.estado == "modo_juego":
            self.dibujar_modo_juego()
        elif self.estado == "votacion":
            self.dibujar_votacion()
        elif self.estado == "controles":
            self.dibujar_controles(ahora)
        elif self.estado == "personaje":
            self.dibujar_personaje(ahora)
        elif self.estado == "cartas":
            self.dibujar_cartas(ahora)
        elif self.estado == "esperando_inicio":
            dibujar_texto("CONECTADO", fuente_grande, (255, 255, 255), (ANCHO // 2, 170), "centro")
            dibujar_texto(
                f"Jugadores en la sala: {self.sala_n}", fuente, (255, 255, 255), (ANCHO // 2, 270), "centro"
            )
            dibujar_texto(
                "Esperando a que el anfitrión elija el modo y el escenario...",
                fuente, (255, 215, 0), (ANCHO // 2, 330), "centro"
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
            "Tambien puedes presionar 1, 2, 3 o 4",
            fuente_chica, (200, 200, 200), (ANCHO // 2, 500), "centro"
        )
        self.dibujar_aviso()

    def dibujar_online(self):
        dibujar_texto("ONLINE", fuente_grande, (255, 255, 255), (ANCHO // 2, 70), "centro")
        dibujar_texto("UNO CREA LA PARTIDA Y LOS DEMAS SE UNEN (HASTA 4)", fuente, (255, 215, 0), (ANCHO // 2, 150), "centro")
        for _, texto, rect in BOTONES_ONLINE:
            dibujar_boton(rect, texto)
        dibujar_texto(
            "Conexion directa: misma red WiFi o puerto abierto en el router",
            fuente_chica, (200, 200, 200), (ANCHO // 2, 490), "centro"
        )
        self.dibujar_aviso()

    def dibujar_sala(self):
        dibujar_texto("SALA DE ESPERA", fuente_grande, (255, 255, 255), (ANCHO // 2, 60), "centro")
        dibujar_texto(f"Tu IP: {self.ip_propia}", fuente_grande, (255, 215, 0), (ANCHO // 2, 150), "centro")
        dibujar_texto(f"Puerto: {PUERTO}", fuente, (255, 255, 255), (ANCHO // 2, 225), "centro")
        dibujar_texto(
            "Los demás eligen UNIRSE y escriben esa IP",
            fuente, (200, 200, 200), (ANCHO // 2, 275), "centro"
        )
        dibujar_texto(
            "Por internet hay que abrir el puerto en el router o usar una VPN como Tailscale",
            fuente_chica, (200, 200, 200), (ANCHO // 2, 315), "centro"
        )
        total = self.anfitrion.total()
        for i in range(MAX_JUGADORES):
            rect = pygame.Rect(260 + i * 120, 365, 100, 60)
            ocupado = i < total
            pygame.draw.rect(ventana, COLORES_JUGADOR[i] if ocupado else (60, 60, 70), rect, border_radius=8)
            etiqueta = "TU" if i == 0 else (f"J{i + 1}" if ocupado else "...")
            dibujar_texto(etiqueta, fuente, (20, 20, 30) if ocupado else (140, 140, 150), (rect.centerx, rect.y + 18), "centro")
        if total >= 2:
            dibujar_boton(BOTON_EMPEZAR, "EMPEZAR (ENTER)")
        else:
            dibujar_texto("Esperando al menos a un jugador más...", fuente, (255, 215, 0), (ANCHO // 2, 485), "centro")
        dibujar_texto("ESC: cancelar", fuente_chica, (200, 200, 200), (ANCHO // 2, 555), "centro")
        self.dibujar_aviso()

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

    def dibujar_modo_juego(self):
        dibujar_texto("ELIGE EL MODO DE JUEGO", fuente_grande, (255, 255, 255), (ANCHO // 2, 60), "centro")
        posicion = pygame.mouse.get_pos()
        for clave, titulo, descripcion, rect in OPCIONES_JUEGO:
            color = (90, 90, 110) if rect.collidepoint(posicion) else (70, 70, 85)
            pygame.draw.rect(ventana, color, rect, border_radius=12)
            pygame.draw.rect(ventana, (200, 40, 60), rect, 3, border_radius=12)
            dibujar_texto(titulo, fuente_grande, (255, 215, 0), (rect.centerx, rect.y + 18), "centro")
            for numero, linea in enumerate(lineas_ajustadas(descripcion, fuente_chica, rect.width - 30)):
                dibujar_texto(linea, fuente_chica, (255, 255, 255), (rect.x + 15, rect.y + 90 + numero * 22))
        dibujar_texto("Tambien puedes presionar 1 o 2", fuente_chica, (200, 200, 200), (ANCHO // 2, 520), "centro")

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

    def superficie_de_carta(self, indice, cara):
        clave = (indice, cara)
        if clave not in self.cache_cartas:
            if not cara:
                self.cache_cartas[clave] = superficie_carta(130, 190)
            else:
                carta = CARTA_REINA if self.cartas[indice] < 0 else CARTAS_NORMALES[self.cartas[indice]]
                self.cache_cartas[clave] = superficie_carta(130, 190, carta[0], carta[1])
        return self.cache_cartas[clave]

    def dibujar_cartas(self, ahora):
        if self.modo == "local":
            titulo = "CADA JUGADOR VOLTEA UNA CARTA"
        else:
            titulo = "VOLTEA TU CARTA"
        dibujar_texto(titulo, fuente_grande, (255, 255, 255), (ANCHO // 2, 50), "centro")
        dibujar_texto(
            "Quien saque la Reina de Corazones será el cazado",
            fuente, (255, 215, 0), (ANCHO // 2, 125), "centro"
        )
        for i, rect in enumerate(self.rects_cartas()):
            t0 = self.reveladas.get(i)
            progreso = 0.0 if t0 is None else min(1.0, (ahora - t0) / 450)
            cara = progreso >= 0.5
            factor = abs(1 - 2 * progreso)
            superficie = self.superficie_de_carta(i, cara)
            ancho_visible = max(4, int(rect.width * factor))
            escalada = pygame.transform.smoothscale(superficie, (ancho_visible, rect.height))
            ventana.blit(escalada, (rect.centerx - ancho_visible // 2, rect.y))
            etiqueta = f"JUGADOR {i + 1}"
            if self.es_online() and i == self.mi_indice:
                etiqueta += " (TU)"
            dibujar_texto(etiqueta, fuente_chica, COLORES_JUGADOR[i], (rect.centerx, rect.bottom + 12), "centro")
        if self.cartas_fin is not None and self.reina_indice is not None:
            dibujar_texto(
                f"¡JUGADOR {self.reina_indice + 1} ES LA REINA DE CORAZONES!",
                fuente_grande, (255, 90, 110), (ANCHO // 2, 480), "centro"
            )
        dibujar_texto("ESC: salir", fuente_chica, (200, 200, 200), (ANCHO // 2, 565), "centro")

    def dibujar_barras(self, ahora):
        n = len(self.jugadores)
        separacion = 14
        ancho = min(380, (ANCHO - 40 - (n - 1) * separacion) // n)
        total = n * ancho + (n - 1) * separacion
        inicio = (ANCHO - total) // 2
        for i, j in enumerate(self.jugadores):
            barra = pygame.Rect(inicio + i * (ancho + separacion), 20, ancho, 22)
            pygame.draw.rect(ventana, (40, 40, 50), barra)
            proporcion = max(0, j.vida) / j.vida_max
            relleno = pygame.Rect(barra.x, barra.y, int(barra.width * proporcion), barra.height)
            if proporcion > 0.5:
                color = (60, 200, 90)
            elif proporcion > 0.25:
                color = (230, 200, 50)
            else:
                color = (220, 50, 60)
            pygame.draw.rect(ventana, color, relleno)
            pygame.draw.rect(ventana, COLORES_JUGADOR[i], barra, 3)
            nombre = j.nombre
            if self.local is not None and j is self.local:
                nombre += " (TU)"
            if j.vida <= 0:
                nombre += " - KO"
            dibujar_texto(nombre, fuente_mini, COLORES_JUGADOR[i], (barra.x, 46))

    def dibujar_juego(self, ahora):
        ventana.blit(mapas[self.escenario], (0, 0))

        for j in self.jugadores:
            j.dibujar(ahora)

        if len(self.jugadores) >= 2:
            self.dibujar_barras(ahora)
            for j in self.jugadores:
                if j.combo >= 2:
                    dibujar_texto(
                        f"COMBO x{j.combo}", fuente, (255, 215, 0),
                        (int(j.x) + 50, SUELO - int(j.altura) - 235), "centro"
                    )

        if self.juego == "caceria":
            if self.fase2:
                texto_fase = "FASE 2: TODOS CONTRA TODOS"
            else:
                restante = max(0, DURACION_FASE1 - int((ahora - self.inicio_partida) / 1000))
                texto_fase = f"FASE 1: CAZA A LA REINA - {restante // 60}:{restante % 60:02d}"
            dibujar_texto(texto_fase, fuente_chica, (255, 215, 0), (ANCHO // 2, 72), "centro")
            if self.fase2 and ahora - self.aviso_fase2 < 3500:
                dibujar_texto(
                    "¡LA REINA SE TRANSFORMÓ EN ANTLER QUEEN!",
                    fuente_grande, (255, 90, 110), (ANCHO // 2, 170), "centro"
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
            dibujar_texto(titulo, fuente_grande, (255, 215, 0), (ANCHO // 2, 200), "centro")
            if self.subtitulo and not self.desconectado:
                dibujar_texto(self.subtitulo, fuente, blanco, (ANCHO // 2, 280), "centro")
            if self.modo == "local" and self.terminada:
                ayuda = "ENTER: revancha | ESC: menu"
            else:
                ayuda = "ESC: menu"
            dibujar_texto(ayuda, fuente, blanco, (ANCHO // 2, 340), "centro")

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
        self.anfitrion.cerrar()


import yj_ui
yj_ui.instalar(globals())

Aplicacion().ejecutar()
pygame.quit()