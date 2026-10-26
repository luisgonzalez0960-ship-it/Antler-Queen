"""
YELLOWJACKETS: THE GAME - tema visual
Paleta amarillo / azul marino, fondo animado de bosque nocturno, titulo con brillo,
avispa animada, botones con hover, transiciones, HUD con barra fantasma, chispas de golpe,
banners de fase, confeti de victoria.

Uso (en el archivo principal, justo antes de `Aplicacion().ejecutar()`):
    import yj_ui
    yj_ui.instalar(globals())
"""
import math
import random
import pygame

NAVY = (7, 12, 30)
NAVY2 = (13, 24, 52)
NAVY3 = (26, 46, 92)
AMARILLO = (255, 196, 28)
ORO = (255, 226, 110)
AMBAR = (214, 142, 10)
CREMA = (246, 240, 222)
SOMBRA = (2, 5, 14)
ROJO = (232, 74, 62)
JUGADORES = [AMARILLO, (90, 175, 255), CREMA, (255, 128, 48)]


def mezcla(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def suave(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def salida(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def rebote(t):
    t = max(0.0, min(1.0, t))
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def instalar(g):
    W, H = g["ANCHO"], g["ALTO"]
    SUELO = g["SUELO"]
    ALTO_PJ = g["ALTO_PERSONAJE"]
    V = g["ventana"]
    App = g["Aplicacion"]
    pygame.display.set_caption("Yellowjackets: The Game")

    def fnt(nombres, tam, bold=True):
        return pygame.font.SysFont(nombres, tam, bold=bold)

    F_H0 = fnt("impact,bahnschrift,arialblack,arial", 84)
    F_TIT = fnt("impact,bahnschrift,arialblack,arial", 118)
    F_H1 = fnt("impact,bahnschrift,arialblack,arial", 56)
    F_H2 = fnt("bahnschrift,arial", 32)
    F_H3 = fnt("bahnschrift,arial", 25)
    F_BTN = fnt("bahnschrift,arial", 28)
    F_TXT = fnt("bahnschrift,arial", 22, False)
    F_MINI = fnt("bahnschrift,arial", 17, False)
    F_AYUDA = fnt("bahnschrift,arial", 15, False)

    g["COLORES_JUGADOR"][:] = JUGADORES

    def txt(texto, fuente, color, pos, al="centro", alpha=255, esp=0, sombra=True):
        if alpha <= 0:
            return
        if esp:
            imgs = [fuente.render(c, True, color) for c in texto]
            w = sum(i.get_width() for i in imgs) + esp * (len(imgs) - 1)
            x = pos[0] - w // 2 if al == "centro" else (pos[0] - w if al == "der" else pos[0])
            for i in imgs:
                if sombra:
                    s = fuente.render(texto[imgs.index(i)], True, SOMBRA)
                    s.set_alpha(alpha)
                    V.blit(s, (x + 2, pos[1] + 3))
                i.set_alpha(alpha)
                V.blit(i, (x, pos[1]))
                x += i.get_width() + esp
            return
        img = fuente.render(texto, True, color)
        rect = img.get_rect()
        setattr(rect, {"centro": "midtop", "izq": "topleft", "der": "topright"}[al], pos)
        if sombra:
            s = fuente.render(texto, True, SOMBRA)
            s.set_alpha(alpha)
            V.blit(s, rect.move(2, 3))
        img.set_alpha(alpha)
        V.blit(img, rect)

    def txt_fit(texto, fuente, color, pos, maxw):
        img = fuente.render(texto, True, color)
        if img.get_width() > maxw:
            k = maxw / img.get_width()
            img = pygame.transform.smoothscale(img, (maxw, int(img.get_height() * k)))
        V.blit(img, img.get_rect(midtop=pos))

    def resplandor(radio, color):
        s = pygame.Surface((radio * 2, radio * 2), pygame.SRCALPHA)
        for r in range(radio, 0, -2):
            a = int(255 * (1 - r / radio) ** 2 * 0.6)
            pygame.draw.circle(s, color + (a,), (radio, radio), r)
        return s

    def panel(rect, alpha=205, borde=AMARILLO, esquinas=True):
        s = pygame.Surface(rect.size, pygame.SRCALPHA)
        s.fill(NAVY2 + (alpha,))
        V.blit(s, rect)
        pygame.draw.rect(V, mezcla(NAVY3, borde, 0.45), rect, 2)
        if esquinas:
            L = 20
            for (x, y, dx, dy) in ((rect.left, rect.top, 1, 1), (rect.right - 1, rect.top, -1, 1),
                                   (rect.left, rect.bottom - 1, 1, -1), (rect.right - 1, rect.bottom - 1, -1, -1)):
                pygame.draw.line(V, borde, (x, y), (x + dx * L, y), 4)
                pygame.draw.line(V, borde, (x, y), (x, y + dy * L), 4)

    HOV = {}

    def hv(self, clave, hover):
        k = HOV.get(clave, 0.0)
        k = max(0.0, min(1.0, k + (1 if hover else -1) * self._dt * 9))
        HOV[clave] = k
        return suave(k)

    cuerpo = pygame.Surface((100, 52), pygame.SRCALPHA)
    for k in range(0, 100, 14):
        pygame.draw.rect(cuerpo, AMARILLO if (k // 14) % 2 == 0 else NAVY, (k, 0, 14, 52))
    mascara = pygame.Surface((100, 52), pygame.SRCALPHA)
    pygame.draw.ellipse(mascara, (255, 255, 255, 255), (0, 0, 100, 52))
    cuerpo.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    pygame.draw.ellipse(cuerpo, (10, 14, 30), (0, 0, 100, 52), 3)

    def avispa_sup(t):
        s = pygame.Surface((220, 150), pygame.SRCALPHA)
        ale = 0.5 + 0.5 * abs(math.sin(t * 30))
        ala = pygame.Surface((220, 150), pygame.SRCALPHA)
        for cx, cy, w, h in ((100, 52, 78, 14 + 34 * ale), (124, 56, 64, 10 + 28 * ale)):
            r = pygame.Rect(0, 0, int(w), int(h))
            r.center = (cx, int(cy - h / 4))
            pygame.draw.ellipse(ala, (200, 220, 255, 110), r)
            pygame.draw.ellipse(ala, (255, 255, 255, 170), r, 2)
        s.blit(ala, (0, 0))
        for a, b in (((76, 108), (70, 134)), ((88, 110), (90, 138)), ((100, 108), (112, 134))):
            pygame.draw.line(s, CREMA, a, b, 3)
        s.blit(cuerpo, (92, 60))
        pygame.draw.polygon(s, CREMA, [(190, 84), (214, 90), (190, 96)])
        pygame.draw.circle(s, (22, 28, 52), (84, 86), 24)
        pygame.draw.circle(s, AMARILLO, (84, 86), 24, 3)
        pygame.draw.circle(s, (22, 28, 52), (52, 90), 16)
        pygame.draw.circle(s, AMARILLO, (52, 90), 16, 2)
        pygame.draw.ellipse(s, AMARILLO, (38, 84, 12, 9))
        pygame.draw.line(s, AMARILLO, (48, 76), (30, 46), 3)
        pygame.draw.line(s, AMARILLO, (56, 75), (46, 42), 3)
        pygame.draw.circle(s, AMARILLO, (30, 46), 4)
        pygame.draw.circle(s, AMARILLO, (46, 42), 4)
        return s

    def dibujar_avispa(cx, cy, escala, t, voltear=False):
        s = avispa_sup(t)
        if voltear:
            s = pygame.transform.flip(s, True, False)
        if escala != 1:
            s = pygame.transform.smoothscale(s, (int(220 * escala), int(150 * escala)))
        V.blit(s, s.get_rect(center=(cx, cy)))

    DEGRADADO = pygame.Surface((W, H))
    for y in range(H):
        t = y / H
        c = mezcla(NAVY, NAVY3, t ** 1.2)
        c = mezcla(c, (110, 84, 24), max(0, (t - 0.72) * 2.2) * 0.45)
        pygame.draw.line(DEGRADADO, c, (0, y), (W, y))

    rnd = random.Random(7)
    ESTRELLAS = [(rnd.randint(0, W), rnd.randint(0, int(H * 0.55)), rnd.choice((1, 1, 2)), rnd.uniform(0, 6.28))
                 for _ in range(80)]

    def pino(s, x, base, alto, color):
        ancho = alto * 0.36
        pygame.draw.rect(s, color, (x - 4, base - alto * 0.12, 8, alto * 0.14))
        for k in range(4):
            top = base - alto + k * alto * 0.21
            bot = top + alto * 0.44
            hw = ancho * (0.4 + 0.2 * k)
            pygame.draw.polygon(s, color, [(x, top), (x - hw, bot), (x + hw, bot)])

    def capa_pinos(semilla, amin, amax, color, n, base):
        r = random.Random(semilla)
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        for _ in range(n):
            x = r.randint(0, W)
            a = r.randint(amin, amax)
            for dx in (-W, 0, W):
                pino(s, x + dx, base, a, color)
        pygame.draw.rect(s, color, (0, base - 2, W, H - base + 2))
        return s

    CAPAS = [
        (capa_pinos(1, 200, 300, (16, 30, 62), 15, H - 40), 5),
        (capa_pinos(2, 170, 260, (10, 19, 42), 17, H - 10), 12),
        (capa_pinos(3, 140, 220, (5, 10, 24), 18, H + 20), 26),
    ]
    BRILLOS = {r: resplandor(r, AMARILLO) for r in (8, 10, 13)}
    MOON_GLOW = resplandor(170, ORO)
    LUC = [dict(x=random.uniform(0, W), y=random.uniform(0, H), vx=random.uniform(-14, 14),
                vy=random.uniform(-26, -6), f=random.uniform(0, 6.28), r=random.choice((8, 10, 13)))
           for _ in range(42)]

    pq = pygame.Surface((80, 50), pygame.SRCALPHA)
    for yy in range(50):
        for xx in range(80):
            d = math.hypot((xx - 40) / 40, (yy - 25) / 25)
            pq.set_at((xx, yy), (0, 0, 8, int(min(255, max(0, d - 0.55) * 260))))
    VIGNETA = pygame.transform.smoothscale(pq, (W, H))
    VIGNETA_J = VIGNETA.copy()
    VIGNETA_J.set_alpha(120)
    DESTELLO = pygame.Surface((W, H))
    DESTELLO.fill((255, 230, 150))

    def fondo(t, dt):
        V.blit(DEGRADADO, (0, 0))
        for x, y, r, f in ESTRELLAS:
            c = mezcla(NAVY, CREMA, 0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * 1.7 + f)))
            pygame.draw.circle(V, c, (x, y), r)
        mx, my = 800, 120
        MOON_GLOW.set_alpha(int(150 + 40 * math.sin(t * 0.8)))
        V.blit(MOON_GLOW, (mx - 170, my - 170))
        pygame.draw.circle(V, CREMA, (mx, my), 50)
        for cx, cy, r in ((-14, -10, 11), (16, 8, 14), (-6, 22, 7), (20, -22, 6)):
            pygame.draw.circle(V, mezcla(CREMA, NAVY3, 0.22), (mx + cx, my + cy), r)
        for surf, vel in CAPAS:
            off = int((t * vel) % W)
            V.blit(surf, (-off, 0))
            V.blit(surf, (W - off, 0))
        for l in LUC:
            l["x"] += l["vx"] * dt
            l["y"] += l["vy"] * dt
            if l["y"] < -20:
                l["y"] = H + 20
                l["x"] = random.uniform(0, W)
            spr = BRILLOS[l["r"]]
            spr.set_alpha(int(50 + 205 * (0.5 + 0.5 * math.sin(t * 2.2 + l["f"]))))
            V.blit(spr, (l["x"] - l["r"], l["y"] - l["r"]))
        V.blit(VIGNETA, (0, 0))

    def construir_titulo():
        base = F_TIT.render("YELLOWJACKETS", True, (255, 255, 255))
        if base.get_width() > 880:
            k = 880 / base.get_width()
            base = pygame.transform.smoothscale(base, (880, int(base.get_height() * k)))
        w, h = base.get_size()
        grad = pygame.Surface((w, h))
        for y in range(h):
            t = y / h
            c = mezcla(ORO, AMARILLO, t / 0.6) if t < 0.6 else mezcla(AMARILLO, AMBAR, (t - 0.6) / 0.4)
            pygame.draw.line(grad, c, (0, y), (w, y))
        relleno = base.copy()
        relleno.blit(grad, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        pad = 34
        sil = pygame.mask.from_surface(base).to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))

        def tinte(color):
            s = sil.copy()
            s.fill(color + (255,), special_flags=pygame.BLEND_RGBA_MULT)
            return s

        oscuro, extr, amar = tinte(NAVY), tinte((120, 76, 6)), tinte(AMARILLO)
        glow = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        glow.blit(amar, (pad, pad))
        peq = pygame.transform.smoothscale(glow, (glow.get_width() // 7, glow.get_height() // 7))
        glow = pygame.transform.smoothscale(peq, (w + pad * 2, h + pad * 2))
        out = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        for d in range(1, 9):
            out.blit(extr, (pad, pad + d))
        for a in range(0, 360, 30):
            out.blit(oscuro, (pad + int(4 * math.cos(math.radians(a))), pad + int(4 * math.sin(math.radians(a)))))
        out.blit(relleno, (pad, pad))
        return out, glow

    TITULO, TITULO_GLOW = construir_titulo()
    TRAIL = []

    def bloque_titulo(te, t):
        p = rebote(te / 1.0)
        y = int(2 - (1 - p) * 320)
        x = W // 2 - TITULO.get_width() // 2
        flick = 0.4 if math.sin(t * 41) * math.sin(t * 6.7) > 0.9 else 1.0
        TITULO_GLOW.set_alpha(int((90 + 60 * math.sin(t * 2.3)) * flick))
        V.blit(TITULO_GLOW, (x, y))
        TITULO.set_alpha(int(255 * min(1, te / 0.3)))
        V.blit(TITULO, (x, y))

        ts = te - 0.9
        if ts > 0:
            a = int(255 * min(1, ts / 0.4))
            s = "THE GAME"
            tw = sum(F_H2.size(c)[0] for c in s) + 16 * (len(s) - 1)
            txt(s, F_H2, CREMA, (W // 2, 168), esp=16, alpha=a)
            ln = int(170 * salida(ts / 0.7))
            for sg in (-1, 1):
                x0 = W // 2 + sg * (tw // 2 + 26)
                x1 = x0 + sg * ln
                pygame.draw.line(V, AMARILLO, (x0, 186), (x1, 186), 3)
                pygame.draw.polygon(V, AMARILLO, [(x0, 180), (x0 + sg * 6, 186), (x0, 192), (x0 - sg * 6, 186)])
            txt("SOBREVIVE  ·  CAZA  ·  NO CONFÍES EN NADIE", F_MINI, AMARILLO, (W // 2, 212),
                alpha=int(a * (0.7 + 0.3 * math.sin(t * 2))), esp=3)

        wx = W // 2 + int(440 * math.sin(t * 0.55))
        wy = int(196 + 26 * math.sin(t * 1.3))
        TRAIL.append((wx, wy))
        del TRAIL[:-18]
        for k, (a, b) in enumerate(TRAIL):
            BRILLOS[8].set_alpha(k * 9)
            V.blit(BRILLOS[8], (a - 8, b - 8))
        dibujar_avispa(wx, wy, 0.42, t, math.cos(t * 0.55) > 0)

    def encabezado(self, titulo, sub=None):
        te = self._te
        p = salida(te / 0.5)
        y = 24 - int((1 - p) * 70)
        txt(titulo, F_H1, CREMA, (W // 2, y), alpha=int(255 * p))
        tw = F_H1.size(titulo)[0]
        ln = int(160 * p)
        for sg in (-1, 1):
            x0 = W // 2 + sg * (tw // 2 + 24)
            pygame.draw.line(V, AMARILLO, (x0, y + 36), (x0 + sg * ln, y + 36), 4)
            pygame.draw.polygon(V, AMARILLO, [(x0, y + 28), (x0 + sg * 8, y + 36), (x0, y + 44), (x0 - sg * 8, y + 36)])
        if sub:
            txt(sub, F_TXT, AMARILLO, (W // 2, 92), alpha=int(255 * salida((te - 0.3) / 0.4)))

    def boton(self, rect, texto, idx, num=None, activo=True):
        ent = salida((self._te - 0.25 - idx * 0.12) / 0.45)
        if ent <= 0:
            return
        r = rect.move(int(-(1 - ent) * 520), 0)
        hover = activo and ent > 0.95 and rect.collidepoint(pygame.mouse.get_pos())
        e = hv(self, tuple(rect), hover)
        rr = r.inflate(int(e * 16), int(e * 6))
        sl = 14
        pts = [(rr.x + sl, rr.y), (rr.right, rr.y), (rr.right - sl, rr.bottom), (rr.x, rr.bottom)]
        pygame.draw.polygon(V, SOMBRA, [(a + 4, b + 5) for a, b in pts])
        pygame.draw.polygon(V, mezcla(NAVY2, AMARILLO, e) if activo else NAVY, pts)
        pygame.draw.polygon(V, AMARILLO if activo else (70, 80, 110), pts, 3)
        col = mezcla(CREMA, NAVY, e) if activo else (110, 120, 150)
        if num:
            c = (rr.x + 40, rr.centery)
            pygame.draw.circle(V, mezcla(AMARILLO, NAVY, e), c, 16)
            n = F_H3.render(num, True, mezcla(NAVY, AMARILLO, e))
            V.blit(n, n.get_rect(center=c))
        et = F_BTN.render(texto, True, col)
        V.blit(et, et.get_rect(center=(rr.centerx + (14 if num else 0), rr.centery)))
        if e > 0.05:
            ax = rr.right - 38 + int(e * 8)
            pygame.draw.polygon(V, NAVY, [(ax, rr.centery - 9), (ax + 12, rr.centery), (ax, rr.centery + 9)])

    def transicion(te):
        D = 0.6
        if te >= D:
            return
        x = int(-120 + suave(te / D) * (W + 240))
        pygame.draw.polygon(V, NAVY, [(x + 36, 0), (W + 10, 0), (W + 10, H), (x - 54, H)])
        pygame.draw.polygon(V, AMARILLO, [(x, 0), (x + 36, 0), (x - 54, H), (x - 90, H)])

    def banda(texto, y, p, sub=None, fuente=None, queda=False):
        fuente = fuente or F_H0
        ab = salida(p / 0.2) if queda else min(salida(p / 0.2), salida((1 - p) / 0.2))
        h = int(104 * ab)
        if h < 4:
            return
        pts = [(-20, y - h // 2 + 8), (W + 20, y - h // 2 - 8), (W + 20, y + h // 2 - 8), (-20, y + h // 2 + 8)]
        pygame.draw.polygon(V, SOMBRA, [(a, b + 6) for a, b in pts])
        pygame.draw.polygon(V, AMARILLO, pts)
        pygame.draw.line(V, NAVY, pts[0], pts[1], 3)
        pygame.draw.line(V, NAVY, pts[3], pts[2], 3)
        if ab > 0.7:
            txt_fit(texto, fuente, NAVY, (W // 2, y - fuente.get_height() // 2), W - 80)
        if sub and ab > 0.9:
            txt(sub, F_H3, CREMA, (W // 2, y + h // 2 + 14))

    def m_aviso(self):
        if self.mensaje:
            r = pygame.Rect(0, 0, min(W - 60, F_TXT.size(self.mensaje)[0] + 40), 40)
            r.center = (W // 2, 540)
            panel(r, 230, ROJO, False)
            txt(self.mensaje, F_TXT, CREMA, (W // 2, r.y + 8), sombra=False)

    def m_menu(self, ahora):
        bloque_titulo(self._te, self._t)
        for i, (_, tx, r) in enumerate(g["BOTONES_MENU"]):
            boton(self, r, tx, i, str(i + 1))
        a = int(255 * salida((self._te - 1.4) / 0.5))
        txt("PRESIONA 1, 2, 3 O 4 PARA ELEGIR", F_MINI, CREMA, (W // 2, 506),
            alpha=int(a * (0.55 + 0.45 * math.sin(self._t * 3))), esp=2)
        txt("PROYECTO DE FANS  ·  NO OFICIAL  ·  1-4 JUGADORES", F_MINI, mezcla(NAVY3, CREMA, 0.55),
            (W // 2, H - 28), alpha=a, esp=1)
        m_aviso(self)

    def m_online(self, ahora):
        encabezado(self, "ONLINE", "UNO CREA LA PARTIDA Y LOS DEMÁS SE UNEN (HASTA 4)")
        for i, (_, tx, r) in enumerate(g["BOTONES_ONLINE"]):
            boton(self, r, tx, i, str(i + 1))
        txt("Red local / IP: misma red WiFi o puerto abierto en el router", F_MINI, CREMA, (W // 2, 488))
        txt("Internet: el servidor relay conecta redes distintas sin abrir puertos", F_MINI, AMARILLO, (W // 2, 510))
        m_aviso(self)

    def m_sala(self, ahora):
        encabezado(self, "SALA DE ESPERA")
        r = pygame.Rect(240, 105, 520, 150)
        panel(r)
        if getattr(self, "via_relay", False):
            codigo = self.anfitrion.codigo
            txt("CÓDIGO DE SALA", F_MINI, AMARILLO, (W // 2, r.y + 16), esp=3)
            if codigo:
                txt(codigo, F_H1, CREMA, (W // 2, r.y + 40), esp=14)
                txt("SERVIDOR RELAY", F_H3, AMARILLO, (W // 2, r.y + 108))
            else:
                txt("CONECTANDO AL SERVIDOR" + "." * (int(self._t * 2) % 4), F_H3, CREMA, (W // 2, r.y + 62))
            txt("Los demás eligen UNIRSE CON CÓDIGO y lo escriben", F_TXT, CREMA, (W // 2, 274))
            txt("Funciona entre redes distintas, sin abrir puertos", F_MINI,
                mezcla(NAVY3, CREMA, 0.65), (W // 2, 304))
        else:
            txt("TU DIRECCIÓN IP (RED LOCAL)", F_MINI, AMARILLO, (W // 2, r.y + 16), esp=3)
            txt(self.ip_propia, F_H1, CREMA, (W // 2, r.y + 40))
            txt(f"PUERTO {g['PUERTO']}", F_H3, AMARILLO, (W // 2, r.y + 108))
            txt("Los demás eligen UNIRSE POR IP y escriben esa IP", F_TXT, CREMA, (W // 2, 274))
            txt(f"Otra red: IP pública {self.ip_publica.get('ip', '...')} y puerto {g['PUERTO']} abierto en tu router",
                F_MINI, mezcla(NAVY3, CREMA, 0.65), (W // 2, 304))
        total = self.anfitrion.total()
        for i in range(g["MAX_JUGADORES"]):
            s = pygame.Rect(W // 2 - 250 + i * 130, 345, 110, 78)
            if i < total:
                p = 0.5 + 0.5 * math.sin(self._t * 3 + i)
                pygame.draw.rect(V, JUGADORES[i], s, border_radius=6)
                pygame.draw.rect(V, mezcla(JUGADORES[i], CREMA, p), s.inflate(8, 8), 3, border_radius=8)
                txt("TÚ" if i == 0 else f"J{i + 1}", F_H2, NAVY, (s.centerx, s.y + 22), sombra=False)
            else:
                pygame.draw.rect(V, NAVY2, s, border_radius=6)
                pygame.draw.rect(V, (60, 75, 110), s, 2, border_radius=6)
                txt("." * (int(self._t * 2 + i) % 4), F_H2, (90, 105, 140), (s.centerx, s.y + 18), sombra=False)
        if total >= 2:
            boton(self, g["BOTON_EMPEZAR"], "EMPEZAR", 0)
        else:
            txt("ESPERANDO JUGADORES" + "." * (int(self._t * 2) % 4), F_H3, AMARILLO, (W // 2, 488))
        txt("ESC: CANCELAR", F_MINI, CREMA, (W // 2, H - 30), esp=2)
        m_aviso(self)

    def m_ip(self, ahora):
        titulo, sub = {
            "ip": ("IP DEL ANFITRIÓN", "Escribe la dirección que aparece en su sala de espera"),
            "codigo": ("CÓDIGO DE SALA", "Escribe el código que te dio el anfitrión  ·  F2: cambiar servidor"),
            "relay": ("SERVIDOR RELAY", "Dirección del servidor, por ejemplo midominio.com:5556"),
        }[getattr(self, "modo_ingreso", "ip")]
        encabezado(self, titulo, sub)
        caja = pygame.Rect(270, 230, 460, 74)
        panel(caja, 235)
        cur = "|" if int(self._t * 2) % 2 == 0 else ""
        txt(self.texto_ip + cur, F_H1, CREMA, (caja.centerx, caja.y + 8), sombra=False)
        txt("ENTER: CONECTAR   ·   ESC: VOLVER", F_H3, AMARILLO, (W // 2, 340), esp=2)
        m_aviso(self)

    def m_modo(self, ahora):
        encabezado(self, "ELIGE EL MODO DE JUEGO")
        pos = pygame.mouse.get_pos()
        for k, (clave, titulo, desc, rect) in enumerate(g["OPCIONES_JUEGO"]):
            ent = salida((self._te - 0.2 - k * 0.15) / 0.45)
            if ent <= 0:
                continue
            e = hv(self, clave, rect.collidepoint(pos))
            r = rect.move(0, int((1 - ent) * 120 - e * 10))
            panel(r, 235, AMARILLO if e > 0.2 else mezcla(AMARILLO, NAVY3, 0.4))
            if clave == "survivor":
                dibujar_avispa(r.centerx, r.y + 55, 0.5, self._t + k)
            else:
                g["dibujar_simbolo"](V, "corazon", (r.centerx, r.y + 55), 48 + int(6 * math.sin(self._t * 4)))
            txt(titulo, F_H1, AMARILLO, (r.centerx, r.y + 88))
            pygame.draw.line(V, AMARILLO, (r.x + 40, r.y + 152), (r.right - 40, r.y + 152), 2)
            for n, linea in enumerate(g["lineas_ajustadas"](desc, F_MINI, r.width - 44)):
                txt(linea, F_MINI, CREMA, (r.x + 22, r.y + 166 + n * 22), "izq", sombra=False)
            c = (r.x + 28, r.y + 28)
            pygame.draw.circle(V, AMARILLO, c, 15)
            n = F_H3.render(str(k + 1), True, NAVY)
            V.blit(n, n.get_rect(center=c))
        txt("TAMBIÉN PUEDES PRESIONAR 1 O 2", F_MINI, CREMA, (W // 2, 530), esp=2)

    def m_votacion(self, ahora):
        encabezado(self, "ELIGE EL ESCENARIO", "Vota por dónde se librará la cacería")
        pos = pygame.mouse.get_pos()
        for k, (nombre, rect) in enumerate(g["tarjetas"].items()):
            ent = salida((self._te - 0.2 - k * 0.12) / 0.4)
            if ent <= 0:
                continue
            e = hv(self, nombre, rect.collidepoint(pos))
            r = rect.move(0, int((1 - ent) * 90 - e * 8))
            panel(r, 235)
            img = g["imagenes_tarjetas"][nombre]
            V.blit(img, (r.x + 5, r.y + 5))
            pygame.draw.rect(V, mezcla(NAVY3, AMARILLO, e), (r.x + 5, r.y + 5, img.get_width(), img.get_height()), 2)
            txt(nombre, F_H3, CREMA, (r.centerx, r.y + 226))
            txt(f"VOTOS: {self.votos[nombre]}", F_TXT, AMARILLO, (r.centerx, r.y + 262))
            if self.voto_actual == nombre:
                p = 0.5 + 0.5 * math.sin(self._t * 5)
                pygame.draw.rect(V, mezcla(AMARILLO, CREMA, p), r.inflate(10, 10), 4)
                c = (r.right - 20, r.y + 20)
                pygame.draw.circle(V, AMARILLO, c, 15)
                pygame.draw.lines(V, NAVY, False, [(c[0] - 7, c[1]), (c[0] - 2, c[1] + 6), (c[0] + 8, c[1] - 6)], 4)
        boton(self, g["boton_confirmar"], "CONFIRMAR VOTO", 3, activo=self.voto_actual is not None)

    def m_personaje(self, ahora):
        if self.modo == "local":
            titulo = f"JUGADOR {min(len(self.eleccion) + 1, 2)}: ELIGE TU PERSONAJE"
        else:
            titulo = "ELIGE TU PERSONAJE"
        encabezado(self, titulo)
        if self.juego == "caceria":
            txt("Si te sale la Reina de Corazones, jugarás como Shauna / Antler Queen", F_MINI, AMARILLO,
                (W // 2, 98), alpha=int(255 * salida((self._te - 0.4) / 0.4)))
        pos = pygame.mouse.get_pos()
        PERS, ANIM = g["PERSONAJES"], g["ANIMACIONES"]
        for k, (clave, rect) in enumerate(self.tarjetas_personaje().items()):
            ent = salida((self._te - 0.15 - k * 0.1) / 0.4)
            if ent <= 0:
                continue
            datos = PERS[clave]
            e = hv(self, "p" + clave, rect.collidepoint(pos) and self.mi_personaje is None)
            r = rect.move(0, int((1 - ent) * 100 - e * 8))
            panel(r, 235)
            cono = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.polygon(cono, AMARILLO + (int(18 + 30 * e),),
                                [(r.width // 2 - 20, 0), (r.width // 2 + 20, 0), (r.width - 30, 200), (30, 200)])
            V.blit(cono, r)
            pygame.draw.ellipse(V, (0, 0, 0), pygame.Rect(r.centerx - 55, r.y + 188, 110, 16))
            q = ANIM[datos["forma_inicial"]]["quieta"][0]
            bob = int(3 * math.sin(self._t * 2 + k))
            V.blit(q, (r.centerx - q.get_width() // 2, r.y + 15 + bob))
            txt(datos["nombre"], F_H2, AMARILLO, (r.centerx, r.y + 210))
            for n, linea in enumerate(g["lineas_ajustadas"](datos["descripcion"], F_MINI, r.width - 20)):
                txt(linea, F_MINI, CREMA, (r.centerx, r.y + 252 + n * 19), sombra=False)
            if self.mi_personaje == clave:
                p = 0.5 + 0.5 * math.sin(self._t * 5)
                pygame.draw.rect(V, mezcla(AMARILLO, CREMA, p), r.inflate(10, 10), 4)
        for i, aviso in enumerate(g["avisos_personajes"][:3]):
            txt(aviso, F_MINI, ROJO, (W // 2, 462 + i * 18))
        if self.mi_personaje is not None:
            txt(f"ESPERANDO A LOS DEMÁS ({len(self.personajes_elegidos)}/{self.n_jugadores})" +
                "." * (int(self._t * 2) % 4), F_H3, AMARILLO, (W // 2, 505))
        txt("ESC: SALIR", F_MINI, CREMA, (W // 2, 552), esp=2)

    orig_carta = g["superficie_carta"]

    def carta_dorso(w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(s, NAVY2, (0, 0, w, h), border_radius=10)
        s.set_clip(pygame.Rect(12, 12, w - 24, h - 24))
        for k in range(-h, w, 16):
            pygame.draw.line(s, NAVY3, (k, h), (k + h, 0), 2)
        s.set_clip(None)
        pygame.draw.rect(s, AMARILLO, (0, 0, w, h), 4, border_radius=10)
        pygame.draw.rect(s, mezcla(NAVY2, AMARILLO, 0.5), (10, 10, w - 20, h - 20), 2, border_radius=6)
        av = pygame.transform.smoothscale(avispa_sup(0.01), (int(220 * 0.46), int(150 * 0.46)))
        s.blit(av, av.get_rect(center=(w // 2, h // 2)))
        return s

    def superficie_carta_tema(ancho, alto, valor=None, palo=None):
        if valor is None:
            return carta_dorso(ancho, alto)
        return orig_carta(ancho, alto, valor, palo)

    g["superficie_carta"] = superficie_carta_tema

    def m_cartas(self, ahora):
        encabezado(self, "CADA JUGADOR VOLTEA UNA CARTA" if self.modo == "local" else "VOLTEA TU CARTA",
                   "Quien saque la Reina de Corazones será el cazado")
        pos = pygame.mouse.get_pos()
        for i, rect in enumerate(self.rects_cartas()):
            ent = salida((self._te - 0.2 - i * 0.1) / 0.4)
            if ent <= 0:
                continue
            t0 = self.reveladas.get(i)
            prog = 0.0 if t0 is None else min(1.0, (ahora - t0) / 450)
            puede = t0 is None and (self.modo == "local" or i == self.mi_indice)
            e = hv(self, f"c{i}", puede and rect.collidepoint(pos))
            r = rect.move(0, int((1 - ent) * 140 - e * 10))
            if prog >= 1 and self.cartas[i] < 0:
                G = MOON_GLOW
                G.set_alpha(int(170 + 70 * math.sin(self._t * 4)))
                V.blit(G, (r.centerx - 170, r.centery - 170))
            elif puede:
                G = BRILLOS[13]
                pygame.draw.rect(V, mezcla(NAVY3, AMARILLO, 0.5 + 0.5 * math.sin(self._t * 4)), r.inflate(12, 12), 3,
                                 border_radius=12)
            cara = prog >= 0.5
            f = abs(1 - 2 * prog)
            sup = self.superficie_de_carta(i, cara)
            wv = max(4, int(r.width * f))
            V.blit(pygame.transform.smoothscale(sup, (wv, r.height)), (r.centerx - wv // 2, r.y))
            etq = f"JUGADOR {i + 1}" + (" (TÚ)" if self.es_online() and i == self.mi_indice else "")
            txt(etq, F_TXT, JUGADORES[i], (r.centerx, r.bottom + 14))
        if self.cartas_fin is not None and self.reina_indice is not None:
            k = rebote((ahora - (self.cartas_fin - 2500) - 450) / 600)
            img = F_H1.render(f"¡JUGADOR {self.reina_indice + 1} ES LA REINA DE CORAZONES!", True, ROJO)
            if img.get_width() > W - 40:
                img = pygame.transform.smoothscale(img, (W - 40, int(img.get_height() * (W - 40) / img.get_width())))
            if k > 0.02:
                img = pygame.transform.smoothscale(img, (max(1, int(img.get_width() * k)), max(1, int(img.get_height() * k))))
                V.blit(img, img.get_rect(center=(W // 2, 490)))
        txt("ESC: SALIR", F_MINI, CREMA, (W // 2, H - 22), esp=2)

    def m_espera(self, ahora):
        encabezado(self, "CONECTADO")
        r = pygame.Rect(230, 190, 540, 170)
        panel(r)
        txt(f"JUGADORES EN LA SALA: {self.sala_n}", F_H2, CREMA, (W // 2, r.y + 24))
        txt("Esperando a que el anfitrión elija el modo y el escenario" + "." * (int(self._t * 2) % 4),
            F_MINI, AMARILLO, (W // 2, r.y + 80))
        for k in range(5):
            a = self._t * 3 - k * 0.5
            pygame.draw.circle(V, AMARILLO, (W // 2 + int(46 * math.cos(a)), r.y + 135 + int(14 * math.sin(a))), 6 - k // 2)
        txt("ESC: SALIR", F_MINI, CREMA, (W // 2, H - 30), esp=2)

    CHISPAS = []
    CONF = []

    def chispas(x, y, n=16):
        for _ in range(n):
            a = random.uniform(0, 6.283)
            v = random.uniform(120, 440)
            CHISPAS.append([x, y, math.cos(a) * v, math.sin(a) * v - 140, random.uniform(0.3, 0.7),
                            random.choice((AMARILLO, ORO, CREMA))])

    def dibujar_barras(self, ahora):
        n = len(self.jugadores)
        sep = 18
        ancho = min(380, (W - 40 - (n - 1) * sep) // n)
        total = n * ancho + (n - 1) * sep
        inicio = (W - total) // 2
        for i, j in enumerate(self.jugadores):
            x, y, h, sl = inicio + i * (ancho + sep), 16, 26, 10
            col = JUGADORES[i]
            prop = max(0, j.vida) / j.vida_max
            fan = getattr(j, "_fant", prop)
            fan = max(prop, fan - self._dt * 0.35) if fan > prop else prop
            j._fant = fan

            def poli(w):
                w = max(w, sl + 2)
                return [(x + sl, y), (x + w, y), (x + w - sl, y + h), (x, y + h)]

            pygame.draw.polygon(V, SOMBRA, [(a + 3, b + 4) for a, b in poli(ancho)])
            pygame.draw.polygon(V, NAVY, poli(ancho))
            if fan > 0:
                pygame.draw.polygon(V, CREMA, poli(int(ancho * fan)))
            if prop > 0:
                c = AMARILLO if prop > 0.5 else (255, 150, 30) if prop > 0.25 else ROJO
                if prop <= 0.25 and (ahora // 180) % 2:
                    c = (255, 130, 110)
                pygame.draw.polygon(V, c, poli(int(ancho * prop)))
                pygame.draw.line(V, mezcla(c, CREMA, 0.5), (x + sl + 2, y + 5), (x + int(ancho * prop) - 2, y + 5), 2)
            pygame.draw.polygon(V, col, poli(ancho), 3)
            nombre = j.nombre + (" (TÚ)" if self.local is not None and j is self.local else "") + \
                (" - KO" if j.vida <= 0 else "")
            pygame.draw.rect(V, col, (x, y + h + 6, 8, 14))
            txt(nombre, F_AYUDA, col, (x + 14, y + h + 5), "izq")
            if j.controles is not None and j.vida > 0 and getattr(j, "carga_especial", None):
                carga = j.carga_especial(ahora)
                bx, by = x + 14, y + h + 26
                pygame.draw.rect(V, SOMBRA, (bx - 1, by - 1, 92, 8))
                pygame.draw.rect(V, NAVY, (bx, by, 90, 6))
                color_b = AMARILLO if carga >= 1 else mezcla(NAVY3, AMARILLO, carga)
                if carga >= 1 and (ahora // 250) % 2:
                    color_b = CREMA
                pygame.draw.rect(V, color_b, (bx, by, int(90 * carga), 6))
                txt("ESPECIAL LISTO" if carga >= 1 else "ESPECIAL", F_AYUDA,
                    AMARILLO if carga >= 1 else mezcla(NAVY3, CREMA, 0.6), (bx + 98, by - 7), "izq")

    def m_juego(self, ahora):
        V.blit(g["mapas"][self.escenario], (0, 0))
        for j in self.jugadores:
            w = max(40, 90 - int(j.altura) // 3)
            sh = pygame.Surface((w, 16), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (0, 0, 0, 100), sh.get_rect())
            V.blit(sh, (int(j.x) + 50 - w // 2, SUELO - 9))
        for j in self.jugadores:
            j.dibujar(ahora)
        V.blit(VIGNETA_J, (0, 0))

        for i, j in enumerate(self.jugadores):
            pv = getattr(j, "_vida_prev", j.vida)
            if j.vida < pv:
                chispas(int(j.x) + 50, SUELO - int(j.altura) - 95, 18)
                self._flash = ahora
            j._vida_prev = j.vida
            if j.vida > 0 and len(self.jugadores) >= 2:
                cx = int(j.x) + 50
                cy = SUELO - int(j.altura) - ALTO_PJ - 12 + int(3 * math.sin(ahora / 180 + i))
                pygame.draw.polygon(V, SOMBRA, [(cx - 9, cy - 15), (cx + 11, cy - 15), (cx + 1, cy + 3)])
                pygame.draw.polygon(V, JUGADORES[i], [(cx - 10, cy - 18), (cx + 10, cy - 18), (cx, cy)])
        for c in CHISPAS:
            c[0] += c[2] * self._dt
            c[1] += c[3] * self._dt
            c[3] += 700 * self._dt
            c[4] -= self._dt
        CHISPAS[:] = [c for c in CHISPAS if c[4] > 0]
        for c in CHISPAS:
            pygame.draw.line(V, c[5], (c[0], c[1]), (c[0] - c[2] * 0.03, c[1] - c[3] * 0.03), 3)
        fl = 1 - (ahora - getattr(self, "_flash", -999)) / 160
        if fl > 0:
            DESTELLO.set_alpha(int(60 * fl))
            V.blit(DESTELLO, (0, 0))

        if len(self.jugadores) >= 2:
            self.dibujar_barras(ahora)
            for j in self.jugadores:
                if j.combo >= 2:
                    pop = 1 + 0.6 * max(0, 1 - (ahora - j.ultimo_golpe_recibido) / 220)
                    img = F_H2.render(f"COMBO x{j.combo}", True, ORO)
                    img = pygame.transform.smoothscale(img, (int(img.get_width() * pop), int(img.get_height() * pop)))
                    V.blit(img, img.get_rect(center=(int(j.x) + 50, SUELO - int(j.altura) - ALTO_PJ - 50)))

        if self.juego == "caceria":
            if self.fase2:
                tf = "FASE 2: TODOS CONTRA TODOS"
                col = ROJO
            else:
                rest = max(0, g["DURACION_FASE1"] - int((ahora - self.inicio_partida) / 1000))
                tf = f"FASE 1: CAZA A LA REINA  -  {rest // 60}:{rest % 60:02d}"
                col = ROJO if rest <= 10 and (ahora // 300) % 2 else AMARILLO
            r = pygame.Rect(0, 0, 380, 28)
            r.midtop = (W // 2, 78)
            panel(r, 190, AMARILLO, False)
            txt(tf, F_MINI, col, (W // 2, r.y + 5), esp=1)
            if self.fase2 and ahora - self.aviso_fase2 < 3500:
                banda("¡LA REINA SE TRANSFORMÓ!", 250, (ahora - self.aviso_fase2) / 3500,
                      sub="ANTLER QUEEN HA DESPERTADO")
        pi = (ahora - self.inicio_partida) / 1700
        if 0 <= pi < 1 and not self.terminada:
            banda("¡LA CACERÍA COMIENZA!" if self.juego == "caceria" else "¡PELEA!", 260, pi)

        barra = pygame.Surface((W, 58), pygame.SRCALPHA)
        barra.fill(NAVY + (170,))
        V.blit(barra, (0, H - 58))
        pygame.draw.line(V, AMARILLO, (0, H - 58), (W, H - 58), 2)
        if self.modo == "local":
            txt("J1: " + g["texto_ayuda"](self.jugadores[0]), F_AYUDA, CREMA, (14, H - 52), "izq", sombra=False)
            txt("J2: " + g["texto_ayuda"](self.jugadores[1]), F_AYUDA, CREMA, (14, H - 28), "izq", sombra=False)
        else:
            propio = self.local if self.local is not None else self.jugadores[0]
            txt(g["texto_ayuda"](propio) + " | ESC menú", F_AYUDA, CREMA, (14, H - 34), "izq", sombra=False)

        fin = self.terminada or self.desconectado
        if not fin:
            self._fin_t0 = None
            return
        if getattr(self, "_fin_t0", None) is None:
            self._fin_t0 = ahora
            CONF.clear()
            if self.terminada and not self.desconectado:
                for _ in range(110):
                    CONF.append([random.uniform(0, W), random.uniform(-500, -10), random.uniform(110, 270),
                                 random.uniform(0, 6.28), random.choice((AMARILLO, ORO, CREMA, (90, 175, 255)))])
        tf = (ahora - self._fin_t0) / 1000
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill(NAVY + (min(185, int(tf * 420)),))
        V.blit(ov, (0, 0))
        for c in CONF:
            c[1] += c[2] * self._dt
            if c[1] > H + 10:
                c[1] = -10
            pygame.draw.rect(V, c[4], (c[0] + 14 * math.sin(self._t * 2 + c[3]), c[1], 7, 12))
        titulo = "SE PERDIÓ LA CONEXIÓN" if self.desconectado else self.ganador
        banda(titulo, 230, tf, sub=(self.subtitulo if not self.desconectado else None), queda=True)
        ayuda = "ENTER: REVANCHA  |  ESC: MENÚ" if (self.modo == "local" and self.terminada) else "ESC: MENÚ"
        txt(ayuda, F_H3, CREMA, (W // 2, 380), alpha=int(255 * (0.6 + 0.4 * math.sin(self._t * 4))) if tf > 0.6 else 0,
            esp=2)

    def dibujar(self, ahora):
        t = ahora / 1000
        self._dt = min(0.05, max(0.0, t - getattr(self, "_t_ant", t)))
        self._t_ant = t
        if getattr(self, "_est_prev", None) != self.estado:
            self._est_prev = self.estado
            self._est_t0 = ahora
        self._t = t
        self._te = (ahora - self._est_t0) / 1000
        if self.estado == "juego":
            V.fill(NAVY)
        else:
            fondo(t, self._dt)
        e = self.estado
        tabla = {
            "menu": m_menu, "online": m_online, "esperando_jugador": m_sala, "ingresar_ip": m_ip,
            "modo_juego": m_modo, "votacion": m_votacion, "cartas": m_cartas,
            "esperando_inicio": m_espera, "juego": m_juego,
        }
        if e in tabla:
            tabla[e](self, ahora)
        elif hasattr(self, "dibujar_" + e):
            getattr(self, "dibujar_" + e)(ahora)
        transicion(self._te)

    App.dibujar = dibujar
    App.dibujar_barras = dibujar_barras
    App.dibujar_aviso = m_aviso

    g["BOTONES_MENU"][:] = [(c, t, pygame.Rect(290, 246 + i * 62, 420, 54))
                            for i, (c, t, _) in enumerate(g["BOTONES_MENU"])]
    g["BOTONES_ONLINE"][:] = [(c, t, pygame.Rect(290, 164 + i * 62, 420, 54))
                              for i, (c, t, _) in enumerate(g["BOTONES_ONLINE"])]
    g["OPCIONES_JUEGO"][:] = [(c, t, d, pygame.Rect(90 + i * 440, 125, 380, 370))
                              for i, (c, t, d, _) in enumerate(g["OPCIONES_JUEGO"])]
