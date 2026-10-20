import pygame
import random
import os

pygame.init()

ANCHO = 1000
ALTO = 600

ventana = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Reina de Corazones")

fuente = pygame.font.SysFont(None, 32)
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

votos = {
    "Avion en el bosque": 0,
    "Cabaña abandonada": 0,
    "Lago congelado": 0
}

voto_actual = None
votacion_cerrada = False
escenario_ganador = None

boton_confirmar = pygame.Rect(375, 500, 250, 55)


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


# Si la hoja idle tiene 5 frames, usa 5. Si no, cámbialo.
animaciones_shauna = {
    "quieta": cargar_animacion("Personajes/Shauna.png", 5),
    "caminar": cargar_animacion("Personajes/ShaunaW.png", 7),
    "correr": cargar_animacion("Personajes/ShaunaR.png", 7),
    "ataque": cargar_animacion("Personajes/ShaunaA.png", 9)
}

animaciones_antler = {
    "quieta": cargar_animacion("Personajes/AntlerQueen.png", 5),
    "caminar": cargar_animacion("Personajes/AntlerQueenW.png", 7),
    "correr": cargar_animacion("Personajes/AntlerQueenR.png", 7),
    "ataque": cargar_animacion("Personajes/AntlerQueenA.png", 9)
}

forma_actual = "humana"

x = 100
suelo = 500
velocidad = 4
velocidad_correr = 7

indice_cuadro = 0
ultima_actualizacion = pygame.time.get_ticks()
mirando_derecha = True
accion_anterior = "quieta"

ejecutando = True

while ejecutando:
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            ejecutando = False

        elif evento.type == pygame.MOUSEBUTTONDOWN:
            if evento.button == 1 and not votacion_cerrada:
                for nombre, rectangulo in tarjetas.items():
                    if rectangulo.collidepoint(evento.pos):
                        if voto_actual is not None:
                            votos[voto_actual] -= 1

                        voto_actual = nombre
                        votos[voto_actual] += 1

                if boton_confirmar.collidepoint(evento.pos):
                    if voto_actual is not None:
                        maximo_votos = max(votos.values())
                        empatados = [
                            nombre
                            for nombre, cantidad in votos.items()
                            if cantidad == maximo_votos
                        ]
                        escenario_ganador = random.choice(empatados)
                        votacion_cerrada = True

        elif evento.type == pygame.KEYDOWN and votacion_cerrada:
            if evento.key == pygame.K_f:
                if forma_actual == "humana":
                    forma_actual = "criatura"
                else:
                    forma_actual = "humana"

                indice_cuadro = 0
                accion_anterior = "quieta"

    ventana.fill((20, 20, 30))

    if not votacion_cerrada:

        titulo = fuente.render(
            "ELIGE EL ESCENARIO", True, (255, 255, 255)
        )
        ventana.blit(titulo, (350, 60))

        for nombre, rectangulo in tarjetas.items():
            pygame.draw.rect(ventana, (70, 70, 85), rectangulo)

            ventana.blit(
                imagenes_tarjetas[nombre],
                (rectangulo.x + 5, rectangulo.y + 5)
            )

            texto = fuente.render(nombre, True, (255, 255, 255))
            ventana.blit(
                texto,
                (rectangulo.x + 10, rectangulo.y + 230)
            )

            texto_votos = fuente.render(
                f"Votos: {votos[nombre]}",
                True,
                (255, 215, 0)
            )
            ventana.blit(
                texto_votos,
                (rectangulo.x + 10, rectangulo.y + 265)
            )

            if voto_actual == nombre:
                pygame.draw.rect(
                    ventana, (255, 50, 70), rectangulo, 4
                )

        pygame.draw.rect(
            ventana, (200, 40, 60), boton_confirmar, border_radius=8
        )

        texto_boton = fuente.render(
            "CONFIRMAR VOTO", True, (255, 255, 255)
        )
        ventana.blit(
            texto_boton,
            texto_boton.get_rect(center=boton_confirmar.center)
        )

    else:

        ventana.blit(mapas[escenario_ganador], (0, 0))

        teclas = pygame.key.get_pressed()

        moviendose = False
        corriendo = (
            teclas[pygame.K_LSHIFT] or teclas[pygame.K_RSHIFT]
        )

        velocidad_actual = (
            velocidad_correr if corriendo else velocidad
        )

        if teclas[pygame.K_a]:
            x -= velocidad_actual
            mirando_derecha = False
            moviendose = True

        if teclas[pygame.K_d]:
            x += velocidad_actual
            mirando_derecha = True
            moviendose = True

        x = max(0, min(x, ANCHO - 100))

        if forma_actual == "humana":
            animaciones = animaciones_shauna
        else:
            animaciones = animaciones_antler

        if moviendose:
            if corriendo:
                accion = "correr"
            else:
                accion = "caminar"
        else:
            accion = "quieta"

        if accion != accion_anterior:
            indice_cuadro = 0
            accion_anterior = accion

        cuadros = animaciones[accion]

        ahora = pygame.time.get_ticks()

        if ahora - ultima_actualizacion >= 100:
            indice_cuadro += 1
            ultima_actualizacion = ahora

        indice_cuadro %= len(cuadros)

        personaje = cuadros[indice_cuadro]

        alto_personaje = 180
        ancho_personaje = max(
            1,
            int(
                personaje.get_width()
                * alto_personaje
                / personaje.get_height()
            )
        )

        personaje = pygame.transform.scale(
            personaje,
            (ancho_personaje, alto_personaje)
        )

        if not mirando_derecha:
            personaje = pygame.transform.flip(
                personaje, True, False
            )

        ventana.blit(personaje, (x, suelo - alto_personaje))

        texto_ganador = fuente.render(
            f"ESCENARIO: {escenario_ganador}",
            True,
            (255, 255, 255)
        )
        ventana.blit(texto_ganador, (20, 15))

        texto_forma = fuente.render(
            f"Forma: {forma_actual.upper()}",
            True,
            (255, 215, 0)
        )
        ventana.blit(texto_forma, (20, 55))

        texto_control = fuente.render(
            "A/D: mover | SHIFT: correr | F: transformar",
            True,
            (255, 255, 255)
        )
        ventana.blit(texto_control, (20, 90))

    pygame.display.flip()
    reloj.tick(60)

pygame.quit()
