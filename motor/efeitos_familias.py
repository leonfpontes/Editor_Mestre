"""Famílias de efeitos: centenas de layers a partir de poucos geradores (traços à mão, partículas, luz e textura,
formas animadas). Cada combinação registrada tem nome, descrição e som próprios e aparece no catálogo como qualquer
outro efeito (`editor.py biblioteca listar efeitos`).

As regras são as mesmas da biblioteca: cor só por papel da paleta, nada de `random` (o acaso vem de `self.rng` e
`self.rng_quadro(dt)`), e o mesmo EDL dá sempre o mesmo quadro.
"""
import math

import cv2
import numpy as np

from .efeitos import Efeito, _bgr, cor_marca, efeito
from .movimento import clamp01, ease_in_out, ease_out, mola

TAU = 2 * math.pi


# ═════════════════════════════ 1. traços à mão (marcação) ═════════════════════════════
# Cada forma é uma lista de polilinhas numa caixa de -1 a 1 (y para baixo). O traço se desenha na ordem.

def _arco(cx, cy, rx, ry, a0, a1, n=60):
    t = np.linspace(a0, a1, n)
    return np.stack([cx + rx * np.cos(t), cy + ry * np.sin(t)], 1)


def _linha(*pts, n=24):
    out = []
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        t = np.linspace(0, 1, n)[:, None]
        out.append(np.array([x0, y0]) * (1 - t) + np.array([x1, y1]) * t)
    return np.vstack(out)


def _ponta(x, y, ang, tam=0.28):
    """Ponta de seta em (x, y) apontando para o ângulo ang."""
    a, b = ang + math.radians(150), ang - math.radians(150)
    return [_linha((x + tam * math.cos(a), y + tam * math.sin(a)), (x, y), (x + tam * math.cos(b), y + tam * math.sin(b)))]


def _estrela(n, r0, r1, rot=-math.pi / 2):
    pts = []
    for k in range(2 * n + 1):
        r = r0 if k % 2 == 0 else r1
        a = rot + k * math.pi / n
        pts.append((r * math.cos(a), r * math.sin(a)))
    return _linha(*pts, n=10)


def _coracao():
    t = np.linspace(0, TAU, 120)
    x = 16 * np.sin(t) ** 3
    y = -(13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t))
    return np.stack([x / 17, y / 17], 1)


def _espiral():
    t = np.linspace(0, 3.2 * TAU, 200)
    r = 0.08 + 0.92 * t / t[-1]
    return np.stack([r * np.cos(t), r * np.sin(t)], 1)


def _onda(y, amp=0.12, voltas=3):
    x = np.linspace(-1, 1, 80)
    return np.stack([x, y + amp * np.sin((x + 1) * voltas * math.pi)], 1)


def _nuvem():
    pts = []
    for cx, cy, r, a0, a1 in ((-0.55, 0.15, 0.4, 0.5 * math.pi, 1.6 * math.pi), (-0.15, -0.2, 0.45, 1.1 * math.pi, 1.95 * math.pi),
                              (0.35, -0.12, 0.42, 1.25 * math.pi, 2.1 * math.pi), (0.6, 0.2, 0.36, 1.5 * math.pi, 2.5 * math.pi)):
        pts.append(_arco(cx, cy, r, r, a0, a1, 30))
    pts.append(_linha((0.62, 0.56), (-0.55, 0.55)))
    return [np.vstack(pts)]


FORMAS = {
    "oval": ("Oval feito à mão em volta de algo", lambda: [_arco(0, 0, 1, 0.6, -2.6, -2.6 + TAU * 1.1, 120)]),
    "circulo_duplo": ("Círculo dado duas vezes, como quem insiste", lambda: [np.vstack([_arco(0, 0, 1, 0.62, -2.8, -2.8 + TAU, 90),
                                                                                       _arco(0.02, 0.03, 0.93, 0.56, -2.8, -2.8 + TAU, 90)])]),
    "retangulo": ("Retângulo à mão em volta de um trecho", lambda: [_linha((-1, -0.55), (1, -0.6), (1.02, 0.58), (-0.98, 0.6), (-1, -0.5))]),
    "caixa_arredondada": ("Caixa de cantos redondos em volta de um trecho", lambda: [np.vstack(
        [_arco(-0.75, -0.35, 0.25, 0.25, math.pi, 1.5 * math.pi, 12), _arco(0.75, -0.35, 0.25, 0.25, 1.5 * math.pi, 2 * math.pi, 12),
         _arco(0.75, 0.35, 0.25, 0.25, 0, 0.5 * math.pi, 12), _arco(-0.75, 0.35, 0.25, 0.25, 0.5 * math.pi, math.pi, 12),
         [[-1, -0.35]]])]),
    "colchetes": ("Colchetes [ ] abraçando uma palavra", lambda: [_linha((-0.75, -0.6), (-1, -0.6), (-1, 0.6), (-0.75, 0.6)),
                                                                   _linha((0.75, -0.6), (1, -0.6), (1, 0.6), (0.75, 0.6))]),
    "chaves": ("Chaves { } em volta de um grupo", lambda: [np.vstack([_arco(-0.75, -0.35, 0.15, 0.25, -0.5 * math.pi, -math.pi, 10),
                                                                      _arco(-1.05, -0.0, 0.15, 0.1, 0, 0.5 * math.pi, 8)[::-1],
                                                                      _arco(-0.75, 0.35, 0.15, 0.25, math.pi, 0.5 * math.pi, 10)]),
                                                           np.vstack([_arco(0.75, -0.35, 0.15, 0.25, -0.5 * math.pi, 0, 10),
                                                                      _arco(1.05, 0.0, 0.15, 0.1, math.pi, 0.5 * math.pi, 8),
                                                                      _arco(0.75, 0.35, 0.15, 0.25, 0, 0.5 * math.pi, 10)])]),
    "parenteses": ("Parênteses ( ) em volta de um detalhe", lambda: [_arco(0.3, 0, 1.2, 0.75, 0.75 * math.pi, 1.25 * math.pi, 40),
                                                                     _arco(-0.3, 0, 1.2, 0.75, 0.25 * math.pi, -0.25 * math.pi, 40)]),
    "cantos": ("Quatro cantos marcando uma área, como um visor", lambda: [_linha((-1, -0.3), (-1, -0.6), (-0.7, -0.6)),
                                                                          _linha((0.7, -0.6), (1, -0.6), (1, -0.3)),
                                                                          _linha((1, 0.3), (1, 0.6), (0.7, 0.6)),
                                                                          _linha((-0.7, 0.6), (-1, 0.6), (-1, 0.3))]),
    "sublinhado_duplo": ("Dois sublinhados sob uma palavra-chave", lambda: [_onda(0.0, 0.04, 2), _onda(0.22, 0.04, 2.5)]),
    "zigue_zague": ("Sublinhado em zigue-zague, enfático", lambda: [_linha(*[(-1 + k * 0.2, 0.12 * (-1) ** k) for k in range(11)], n=8)]),
    "riscado": ("Risco atravessando uma palavra (o que não vale mais)", lambda: [_linha((-1.05, 0.05), (1.05, -0.08))]),
    "rabisco": ("Rabisco cobrindo algo, como apagar à caneta", lambda: [np.stack([np.linspace(-1, 1, 160),
                                                                                  0.35 * np.sin(np.linspace(0, 22 * math.pi, 160))
                                                                                  + 0.05 * np.sin(np.linspace(0, 3, 160))], 1)]),
    "x_marcado": ("X à mão sobre o que está errado", lambda: [_linha((-0.8, -0.8), (0.8, 0.8)), _linha((0.8, -0.8), (-0.8, 0.8))]),
    "check_marcado": ("Visto à mão no que está certo", lambda: [_linha((-0.8, 0.0), (-0.25, 0.6), (0.85, -0.75), n=30)]),
    "estrela": ("Estrela de cinco pontas desenhada", lambda: [_estrela(5, 1.0, 0.42)]),
    "coracao": ("Coração desenhado à mão", lambda: [_coracao()]),
    "seta_direita": ("Seta reta apontando para a direita", lambda: [_linha((-1, 0), (1, 0))] + _ponta(1, 0, 0)),
    "seta_esquerda": ("Seta reta apontando para a esquerda", lambda: [_linha((1, 0), (-1, 0))] + _ponta(-1, 0, math.pi)),
    "seta_cima": ("Seta reta apontando para cima", lambda: [_linha((0, 1), (0, -1))] + _ponta(0, -1, -math.pi / 2)),
    "seta_baixo": ("Seta reta apontando para baixo", lambda: [_linha((0, -1), (0, 1))] + _ponta(0, 1, math.pi / 2)),
    "seta_laco": ("Seta com um laço no meio, descontraída", lambda: [np.vstack([_linha((-1, 0.4), (-0.3, 0.2), n=20),
                                                                                 _arco(-0.1, -0.05, 0.3, 0.3, 2.4, 2.4 + TAU, 50),
                                                                                 _linha((0.05, 0.2), (0.95, -0.4), n=20)])]
                  + _ponta(0.95, -0.4, math.atan2(-0.6, 0.9))),
    "seta_curva": ("Seta em arco, de baixo para cima", lambda: [_arco(0, 0.9, 1, 1.4, math.pi, 1.75 * math.pi, 50)]
                   + _ponta(0.707, 0.9 - 0.99, -0.3)),
    "seta_dupla": ("Seta de duas pontas (troca, ida e volta)", lambda: [_linha((-1, 0), (1, 0))] + _ponta(1, 0, 0) + _ponta(-1, 0, math.pi)),
    "exclamacao": ("Ponto de exclamação desenhado", lambda: [_linha((0, -1), (0.02, 0.45)), _arco(0.02, 0.85, 0.06, 0.06, 0, TAU, 14)]),
    "interrogacao": ("Ponto de interrogação desenhado", lambda: [np.vstack([_arco(0, -0.45, 0.5, 0.5, math.pi * 1.05, math.pi * 2.4, 40),
                                                                             _linha((0.2, 0.02), (0.0, 0.35), n=10)]),
                                                                  _arco(0.0, 0.85, 0.06, 0.06, 0, TAU, 14)]),
    "aspas": ("Aspas grandes para uma citação", lambda: [_arco(-0.5, -0.3, 0.25, 0.4, -0.3, 2.2, 20), _arco(0.3, -0.3, 0.25, 0.4, -0.3, 2.2, 20)]),
    "raio": ("Raio desenhado, energia ou ideia rápida", lambda: [_linha((0.3, -1), (-0.4, 0.1), (0.15, 0.05), (-0.3, 1), n=16)]),
    "espiral": ("Espiral, para confusão ou hipnose", lambda: [_espiral()]),
    "alvo": ("Alvo: dois anéis e o centro", lambda: [_arco(0, 0, 1, 1, 0, TAU, 80), _arco(0, 0, 0.55, 0.55, 0, TAU, 60),
                                                     _arco(0, 0, 0.12, 0.12, 0, TAU, 20)]),
    "nuvem": ("Nuvem de pensamento", _nuvem),
    "balao_fala": ("Balão de fala com rabinho", lambda: [np.vstack([_arco(0, -0.15, 1, 0.65, 0.62 * math.pi, 2.38 * math.pi + TAU * 0, 90),
                                                                     _linha((0.68, 0.33), (0.85, 0.85), (0.25, 0.47), n=10)])]),
    "sol": ("Sol com raios, para clareza ou dia bom", lambda: [_arco(0, 0, 0.45, 0.45, 0, TAU, 50)] + [
        _linha((0.6 * math.cos(a), 0.6 * math.sin(a)), (0.95 * math.cos(a), 0.95 * math.sin(a)), n=6) for a in np.linspace(0, TAU, 9)[:-1]]),
    "explosao": ("Explosão de quadrinho em volta de um impacto", lambda: [_estrela(9, 1.0, 0.62, -0.2)]),
    "ondas": ("Três linhas onduladas (som, cheiro, calor)", lambda: [_onda(-0.4, 0.1), _onda(0.0, 0.1), _onda(0.4, 0.1)]),
    "asterisco": ("Asterisco: um detalhe, uma ressalva", lambda: [_linha((0, -1), (0, 1)), _linha((-0.87, -0.5), (0.87, 0.5)),
                                                                  _linha((0.87, -0.5), (-0.87, 0.5))]),
    "mais": ("Sinal de mais desenhado", lambda: [_linha((0, -0.9), (0, 0.9)), _linha((-0.9, 0), (0.9, 0))]),
    "igual": ("Sinal de igual (uma coisa é a outra)", lambda: [_linha((-0.9, -0.25), (0.9, -0.25)), _linha((-0.9, 0.25), (0.9, 0.25))]),
    "triangulo": ("Triângulo de alerta desenhado", lambda: [_linha((0, -0.95), (0.95, 0.75), (-0.95, 0.75), (0, -0.95))]),
    "losango": ("Losango desenhado", lambda: [_linha((0, -1), (0.75, 0), (0, 1), (-0.75, 0), (0, -1))]),
    "coroa": ("Coroa desenhada, para o melhor ou o vencedor", lambda: [_linha((-0.9, 0.6), (-0.9, -0.4), (-0.45, 0.05), (0, -0.7),
                                                                               (0.45, 0.05), (0.9, -0.4), (0.9, 0.6), (-0.9, 0.6), n=14)]),
    "lampada": ("Lâmpada desenhada, para uma ideia", lambda: [np.vstack([_arco(0, -0.3, 0.6, 0.6, 0.75 * math.pi, 2.25 * math.pi, 60),
                                                                          _linha((0.42, 0.12), (0.25, 0.55), (-0.25, 0.55), (-0.42, 0.12), n=10)]),
                                                               _linha((-0.25, 0.75), (0.25, 0.75)), _linha((-0.15, 0.92), (0.15, 0.92))]),
    "pino": ("Pino de mapa sobre um lugar", lambda: [np.vstack([_arco(0, -0.3, 0.6, 0.6, 0.8 * math.pi, 2.2 * math.pi, 60),
                                                                _linha((0.46, 0.08), (0, 1), (-0.46, 0.08), n=14)]),
                                                     _arco(0, -0.3, 0.2, 0.2, 0, TAU, 20)]),
    "brilho": ("Brilho de quatro pontas desenhado", lambda: [_estrela(4, 1.0, 0.22)]),
    "ciclo": ("Duas setas em círculo (ciclo, repetir)", lambda: [_arco(0, 0, 0.9, 0.9, 0.15 * math.pi, 0.85 * math.pi, 40),
                                                                 _arco(0, 0, 0.9, 0.9, 1.15 * math.pi, 1.85 * math.pi, 40)]
              + _ponta(0.9 * math.cos(0.85 * math.pi), 0.9 * math.sin(0.85 * math.pi), 0.85 * math.pi + math.pi / 2, 0.25)
              + _ponta(0.9 * math.cos(1.85 * math.pi), 0.9 * math.sin(1.85 * math.pi), 1.85 * math.pi + math.pi / 2, 0.25)),
}
FORMAS["olho"] = ("Olho desenhado, para atenção", lambda: [_arco(0, 0.75, 1.25, 1.25, 1.2 * math.pi, 1.8 * math.pi, 40),
                                                           _arco(0, -0.75, 1.25, 1.25, 0.2 * math.pi, 0.8 * math.pi, 40),
                                                           _arco(0, 0, 0.3, 0.3, 0, TAU, 30)])

ESTILOS_TRACO = {
    "traco": ("caneta", "Traço fino de caneta, com leve tremor de mão e sombra curta."),
    "marcador": ("marcador", "Marca-texto largo e translúcido na cor de destaque."),
}


class TracoForma(Efeito):
    forma = "oval"
    estilo = "traco"

    def preparar(self):
        larg = self.W * self.e.get("largura", 0.36) / 2
        alt = self.W * self.e.get("altura", self.e.get("largura", 0.36)) / 2
        polis = FORMAS[self.forma][1]()
        r = self.rng
        self.polis = []
        for pl in polis:
            pl = np.asarray(pl, np.float32)
            if self.estilo == "traco":  # tremor de mão, suave ao longo do traço
                n = len(pl)
                ruido = np.cumsum(r.normal(0, 0.012, (n, 2)), 0)
                ruido -= np.linspace(ruido[0], ruido[-1], n)
                pl = pl + ruido
            self.polis.append(np.stack([self.x + pl[:, 0] * larg, self.y + pl[:, 1] * alt], 1))
        comp = [float(np.sum(np.hypot(*np.diff(p, axis=0).T))) for p in self.polis]
        self.comp, self.total = comp, max(sum(comp), 1.0)
        self.dur = float(self.e.get("desenho", 0.35 + min(0.5, self.total / self.W * 0.35)))

    def desenhar(self, frame, dt, rest):
        p = ease_out(clamp01(dt / self.dur))
        alpha = clamp01(rest / 0.25) * self.forca
        if alpha <= 0.01:
            return
        resta = p * self.total
        marcador = self.estilo == "marcador"
        esp = int(self.W * (0.03 if marcador else 0.011))
        cor = _bgr(self.cor)
        ov = frame.copy()
        sombra = None if marcador else frame.copy()
        for pl, c in zip(self.polis, self.comp):
            if resta <= 0:
                break
            f = min(1.0, resta / max(c, 1e-6))
            resta -= c
            n = max(2, int(len(pl) * f))
            pts = np.int32(pl[:n])
            if sombra is not None:
                cv2.polylines(sombra, [pts + [0, 5]], False, (10, 10, 10), esp + 2, cv2.LINE_AA)
            cv2.polylines(ov, [pts], False, cor, esp, cv2.LINE_AA)
            if not marcador:
                for x, y in (pts[0], pts[-1]):
                    cv2.circle(ov, (int(x), int(y)), esp // 2, cor, -1, cv2.LINE_AA)
        if sombra is not None:
            frame[:] = cv2.addWeighted(sombra, 0.25 * alpha, frame, 1 - 0.25 * alpha, 0)
            ov = np.where((ov != sombra).any(2, keepdims=True), ov, frame)
        frame[:] = cv2.addWeighted(ov, (0.55 if marcador else 1.0) * alpha, frame, 1 - (0.55 if marcador else 1.0) * alpha, 0)


for _forma, (_desc, _) in FORMAS.items():
    for _est, (_rot, _edesc) in ESTILOS_TRACO.items():
        _nome = f"{_est}_{_forma}"
        _cls = type(f"Traco_{_forma}_{_est}", (TracoForma,), {"forma": _forma, "estilo": _est})
        efeito(_nome, "marcacao", f"{_desc}. {_edesc}",
               {"x": "centro 0 a 1", "y": "centro 0 a 1", "largura": "fração da largura (padrão 0.36)",
                "altura": "fração da largura (padrão = largura)", "desenho": "segundos para desenhar"},
               som="lapis")(_cls)


# ═════════════════════════════ 2. partículas ═════════════════════════════

def _poligono(forma, s, ang):
    """Vértices (N×2) de uma partícula de tamanho s, girada de ang."""
    if forma in ("ponto", "circulo", "anel", "bolha"):
        return None
    if forma == "estrela4":
        v = [(s if k % 2 == 0 else s * 0.25, k * math.pi / 4) for k in range(8)]
    elif forma == "estrela5":
        v = [(s if k % 2 == 0 else s * 0.42, k * math.pi / 5 - math.pi / 2) for k in range(10)]
    elif forma == "coracao":
        c = _coracao() * s
        v = None
        pts = c
    elif forma == "quadrado":
        v = [(s, math.pi / 4 + k * math.pi / 2) for k in range(4)]
    elif forma == "confete":
        pts = np.array([[-s, -s * 0.45], [s, -s * 0.45], [s, s * 0.45], [-s, s * 0.45]])
        v = None
    elif forma == "triangulo":
        v = [(s, -math.pi / 2 + k * TAU / 3) for k in range(3)]
    elif forma == "losango":
        pts = np.array([[0, -s], [s * 0.6, 0], [0, s], [-s * 0.6, 0]])
        v = None
    elif forma == "hexagono":
        v = [(s, k * TAU / 6) for k in range(6)]
    elif forma == "cruz":
        a, b = s, s * 0.3
        pts = np.array([[-b, -a], [b, -a], [b, -b], [a, -b], [a, b], [b, b], [b, a], [-b, a], [-b, b], [-a, b], [-a, -b], [-b, -b]])
        v = None
    elif forma == "gota":
        t = np.linspace(0, TAU, 30)
        pts = np.stack([s * 0.6 * np.sin(t) * (1 - np.cos(t)) / 2 * 1.6, -s * np.cos(t)], 1)
        v = None
    elif forma == "folha":
        t = np.linspace(0, TAU, 30)
        pts = np.stack([s * 0.45 * np.sin(t), s * np.cos(t) * (0.8 + 0.2 * np.sin(t))], 1)
        v = None
    elif forma == "linha":
        pts = np.array([[-s * 1.4, -s * 0.12], [s * 1.4, -s * 0.12], [s * 1.4, s * 0.12], [-s * 1.4, s * 0.12]])
        v = None
    elif forma == "floco":
        pts = None
        v = None
    else:
        v = [(s, k * TAU / 8) for k in range(8)]
    if v is not None:
        pts = np.array([[r * math.cos(a), r * math.sin(a)] for r, a in v])
    if pts is None:
        return None
    c, sn = math.cos(ang), math.sin(ang)
    return pts @ np.array([[c, sn], [-sn, c]])


def _desenhar_particula(cam, masc, forma, x, y, s, ang, cor, a):
    if a <= 0.02 or s < 0.6:
        return
    cor = tuple(float(v) for v in cor)
    if forma in ("ponto", "circulo", "bolha"):
        cv2.circle(cam, (int(x), int(y)), max(1, int(s)), cor, -1, cv2.LINE_AA)
        cv2.circle(masc, (int(x), int(y)), max(1, int(s)), a, -1, cv2.LINE_AA)
        if forma == "bolha":  # reflexo da bolha
            cv2.circle(cam, (int(x - s * 0.35), int(y - s * 0.35)), max(1, int(s * 0.22)), (250, 250, 250), -1, cv2.LINE_AA)
        return
    if forma == "anel":
        esp = max(1, int(s * 0.28))
        cv2.circle(cam, (int(x), int(y)), max(1, int(s)), cor, esp, cv2.LINE_AA)
        cv2.circle(masc, (int(x), int(y)), max(1, int(s)), a, esp, cv2.LINE_AA)
        return
    if forma == "floco":
        for k in range(3):
            an = ang + k * math.pi / 3
            p0 = (int(x - s * math.cos(an)), int(y - s * math.sin(an)))
            p1 = (int(x + s * math.cos(an)), int(y + s * math.sin(an)))
            esp = max(1, int(s * 0.18))
            cv2.line(cam, p0, p1, cor, esp, cv2.LINE_AA)
            cv2.line(masc, p0, p1, a, esp, cv2.LINE_AA)
        return
    pts = _poligono(forma, s, ang)
    pts = np.int32(pts + [x, y])
    cv2.fillPoly(cam, [pts], cor, cv2.LINE_AA)
    cv2.fillPoly(masc, [pts], a, cv2.LINE_AA)


# movimento: (descrição, área) — "tela" = o quadro inteiro; "ponto" = em volta de (x, y)
MOVIMENTOS = {
    "sobe": ("sobem devagar pela tela", "tela"),
    "cai": ("caem do alto da tela", "tela"),
    "chuva": ("caem em diagonal, como chuva com vento", "tela"),
    "flutua": ("flutuam no ar, sem rumo", "tela"),
    "explode": ("explodem de um ponto e caem com a gravidade", "ponto"),
    "orbita": ("giram em órbita em volta de um ponto", "ponto"),
    "espiral": ("saem de um ponto em espiral", "ponto"),
    "pisca": ("acendem e apagam em volta de um ponto", "ponto"),
    "fonte": ("jorram para cima de um ponto, como uma fonte", "ponto"),
    "redemoinho": ("rodam num redemoinho que se fecha no ponto", "ponto"),
}

# (forma, movimento, nome curto, motivo na fala)
PARTICULAS = [
    ("ponto", "sobe", "poeira_dourada", "clima de sonho, memória"), ("ponto", "flutua", "poeira_no_ar", "calma, luz da manhã"),
    ("ponto", "explode", "faiscas", "impacto, ideia que acende"), ("ponto", "orbita", "pontos_em_orbita", "algo que gira em torno de um tema"),
    ("ponto", "pisca", "cintilar", "detalhe valioso"), ("ponto", "fonte", "fonte_de_luz", "energia que sobe"),
    ("circulo", "sobe", "bolinhas_subindo", "leveza, alegria"), ("circulo", "cai", "bolinhas_caindo", "fim, queda leve"),
    ("circulo", "explode", "estouro_bolinhas", "festa, surpresa"), ("circulo", "redemoinho", "redemoinho_bolinhas", "foco, concentração"),
    ("bolha", "sobe", "bolhas", "leveza, respirar, limpeza"), ("bolha", "flutua", "bolhas_no_ar", "brincadeira, infância"),
    ("anel", "sobe", "aneis_subindo", "elegância, conquista"), ("anel", "pisca", "aneis_piscando", "atenção num ponto"),
    ("anel", "explode", "aneis_estouro", "revelação"), ("anel", "espiral", "aneis_espiral", "transformação"),
    ("estrela4", "pisca", "brilhos_piscando", "algo novo, mágico"), ("estrela4", "cai", "brilhos_caindo", "encanto, presente"),
    ("estrela4", "explode", "estouro_brilhos", "conquista"), ("estrela4", "orbita", "brilhos_em_orbita", "algo especial no centro"),
    ("estrela4", "fonte", "fonte_brilhos", "sucesso que cresce"), ("estrela5", "cai", "estrelas_caindo", "sonho, desejo"),
    ("estrela5", "explode", "estouro_estrelas", "nota máxima, vitória"), ("estrela5", "sobe", "estrelas_subindo", "elogio, avaliação"),
    ("estrela5", "orbita", "estrelas_em_orbita", "tontura, ficar zonzo"), ("estrela5", "espiral", "estrelas_espiral", "magia"),
    ("coracao", "sobe", "coracoes_subindo", "carinho, gratidão, família"), ("coracao", "explode", "estouro_coracoes", "amor, reação"),
    ("coracao", "flutua", "coracoes_no_ar", "romance"), ("coracao", "fonte", "fonte_coracoes", "muito amor"),
    ("coracao", "orbita", "coracoes_em_orbita", "apaixonado"), ("coracao", "pisca", "coracoes_piscando", "afeto num detalhe"),
    ("confete", "cai", "chuva_confete", "celebração, aniversário"), ("confete", "fonte", "canhao_confete", "lançamento, festa"),
    ("confete", "redemoinho", "redemoinho_confete", "virada"), ("quadrado", "cai", "quadrados_caindo", "dados, tecnologia"),
    ("quadrado", "explode", "estouro_quadrados", "quebra de padrão"), ("quadrado", "sobe", "pixels_subindo", "digital, upload"),
    ("triangulo", "explode", "estouro_triangulos", "energia, ataque"), ("triangulo", "flutua", "triangulos_no_ar", "geometria, método"),
    ("triangulo", "orbita", "triangulos_em_orbita", "sistema"), ("losango", "pisca", "diamantes", "valor, premium"),
    ("losango", "cai", "diamantes_caindo", "riqueza, bônus"), ("losango", "explode", "estouro_diamantes", "prêmio"),
    ("hexagono", "flutua", "hexagonos_no_ar", "ciência, colmeia, rede"), ("hexagono", "sobe", "hexagonos_subindo", "inovação"),
    ("cruz", "pisca", "cruzes_piscando", "saúde, mais"), ("cruz", "explode", "estouro_mais", "somar, ganho"),
    ("gota", "cai", "gotas_caindo", "chuva, choro, água"), ("gota", "chuva", "chuva_gotas", "tempo ruim, tristeza"),
    ("gota", "explode", "respingo", "suor, esforço"), ("folha", "cai", "folhas_caindo", "outono, mudança, desapego"),
    ("folha", "chuva", "folhas_ao_vento", "vento, passagem do tempo"), ("folha", "redemoinho", "redemoinho_folhas", "recomeço"),
    ("folha", "sobe", "folhas_subindo", "crescimento, natureza"), ("linha", "explode", "estilhacos", "rompimento, quebra"),
    ("linha", "chuva", "riscos_de_chuva", "temporal, pressão"), ("linha", "fonte", "faiscas_subindo", "fogo, motivação"),
    ("linha", "espiral", "rastro_espiral", "velocidade"), ("floco", "cai", "neve", "frio, Natal, fim de ano"),
    ("floco", "flutua", "neve_no_ar", "inverno, calma"), ("floco", "chuva", "nevasca", "frio intenso"),
    ("floco", "pisca", "cristais", "pureza, novidade"), ("anel", "fonte", "aneis_subindo_do_ponto", "algo que borbulha"),
]


class Particulas(Efeito):
    forma, mov = "ponto", "sobe"

    def preparar(self):
        r = self.rng
        n = int(self.e.get("quantidade", {"tela": 42, "ponto": 26}[MOVIMENTOS[self.mov][1]]))
        self.n = n
        self.u, self.v = r.random(n), r.random(n)
        self.vel = r.uniform(0.6, 1.4, n)
        self.fase = r.uniform(0, TAU, n)
        self.tam = r.uniform(0.6, 1.4, n) * float(self.e.get("tamanho", 1.0))
        self.giro = r.uniform(-3, 3, n)
        self.ang = r.uniform(0, TAU, n)
        self.atraso = r.uniform(0, 0.35, n)
        self.alt = r.random(n) < 0.35  # um terço na segunda cor
        self.local = MOVIMENTOS[self.mov][1] == "ponto"
        self.R = int(self.W * self.e.get("raio", 0.3))
        self.escala = 2  # desenha em meia resolução

    def _pos(self, k, t):
        """(x, y) em pixels do quadro, alfa e escala da partícula k no tempo t (s desde a entrada)."""
        W, H, R = self.W, self.H, self.R
        u, v, vel, fa = self.u[k], self.v[k], self.vel[k], self.fase[k]
        m = self.mov
        if m == "sobe":
            return u * W + 18 * math.sin(t * 1.3 + fa), ((v - 0.07 * vel * t) % 1.1 - 0.05) * H, 1, 1
        if m == "cai":
            return u * W + 22 * math.sin(t * 1.1 + fa), ((v + 0.09 * vel * t) % 1.1 - 0.05) * H, 1, 1
        if m == "chuva":
            return ((u - 0.12 * vel * t) % 1.1 - 0.05) * W, ((v + 0.35 * vel * t) % 1.1 - 0.05) * H, 1, 1
        if m == "flutua":
            return (u + 0.03 * math.sin(t * 0.7 * vel + fa)) * W, (v + 0.025 * math.cos(t * 0.6 * vel + fa * 1.3)) * H, 1, 1
        t = max(0.0, t - self.atraso[k])
        if m == "explode":
            ang, vv = fa, (0.45 + 0.55 * u) * R * 2.2
            x = self.x + math.cos(ang) * vv * t
            y = self.y + math.sin(ang) * vv * t + 0.5 * R * 3.2 * t * t
            return x, y, clamp01(1.4 - t * 0.9), 1
        if m == "orbita":
            a = fa + t * 1.6 * vel
            r = R * (0.55 + 0.45 * v)
            return self.x + r * math.cos(a), self.y + r * 0.45 * math.sin(a), 0.55 + 0.45 * math.sin(a), 0.75 + 0.35 * math.sin(a)
        if m == "espiral":
            a = fa + t * 3.0
            r = R * clamp01(t * 0.9 * vel) * (0.4 + 0.6 * u)
            return self.x + r * math.cos(a), self.y + r * math.sin(a), clamp01(1.6 - t * 0.6), 1
        if m == "pisca":
            r = R * math.sqrt(u)
            a = v * TAU
            brilho = max(0.0, math.sin(t * 4 * vel + fa))
            return self.x + r * math.cos(a), self.y + r * math.sin(a), brilho, 0.4 + 0.8 * brilho
        if m == "fonte":
            ang = -math.pi / 2 + (u - 0.5) * 0.9
            vv = (0.7 + 0.5 * v) * R * 2.6
            tt = (t * vel) % 1.6
            return (self.x + math.cos(ang) * vv * tt, self.y + math.sin(ang) * vv * tt + 0.5 * R * 4.5 * tt * tt,
                    clamp01(1.6 - tt) * clamp01(t * 6), 1)
        if m == "redemoinho":
            a = fa + t * 2.4 * vel
            r = R * (0.3 + 0.7 * u) * max(0.08, 1 - t * 0.35)
            return self.x + r * math.cos(a), self.y + r * 0.8 * math.sin(a), 1, 1
        return u * W, v * H, 1, 1

    def desenhar(self, frame, dt, rest):
        pres = self.presenca(dt, rest, 0.25, 0.35) * self.forca
        if pres <= 0.01:
            return
        if self.local:
            lado = int(self.R * 3.2)
            x0, y0 = int(self.x - lado / 2), int(self.y - lado / 2)
            w, h = lado, lado
        else:
            x0, y0, w, h = 0, 0, self.W, self.H
        e = self.escala
        cam = np.zeros((h // e + 1, w // e + 1, 3), np.float32)
        masc = np.zeros((h // e + 1, w // e + 1), np.float32)
        base = self.W * (0.012 if self.forma in ("ponto", "linha") else 0.02) / e
        for k in range(self.n):
            x, y, a, s = self._pos(k, dt)
            cor = _bgr(self.cor2 if self.alt[k] else self.cor)
            ang = self.ang[k] + self.giro[k] * dt
            _desenhar_particula(cam, masc, self.forma, (x - x0) / e, (y - y0) / e, base * self.tam[k] * s, ang, cor, a)
        brilho = self.forma in ("ponto", "estrela4", "linha", "anel")
        cam = cv2.resize(cam, (w, h))
        masc = cv2.resize(masc, (w, h))[..., None] * pres
        xa, ya, xb, yb = max(0, x0), max(0, y0), min(self.W, x0 + w), min(self.H, y0 + h)
        if xa >= xb or ya >= yb:
            return
        c = cam[ya - y0:yb - y0, xa - x0:xb - x0]
        m = masc[ya - y0:yb - y0, xa - x0:xb - x0]
        roi = frame[ya:yb, xa:xb].astype(np.float32)
        out = roi * (1 - m) + c * m
        if brilho:  # halo de luz em volta das partículas que brilham
            halo = cv2.GaussianBlur(c * m, (0, 0), 6)
            out = 255 - (255 - out) * (255 - np.clip(halo * 0.9, 0, 255)) / 255
        frame[ya:yb, xa:xb] = np.clip(out, 0, 255).astype(np.uint8)


_SOM_PART = {"explode": "pop-bolha", "fonte": "riser-curto", "pisca": "brilho", "orbita": "brilho", "espiral": "whoosh-giro",
             "redemoinho": "whoosh-giro"}
for _forma, _mov, _nome, _motivo in PARTICULAS:
    _cls = type(f"Part_{_nome}", (Particulas,), {"forma": _forma, "mov": _mov})
    _d, _area = MOVIMENTOS[_mov]
    efeito(_nome, "particulas", f"Partículas ({_forma.replace('4', ' de 4 pontas').replace('5', ' de 5 pontas')}) que {_d}. "
                                f"Motivo na fala: {_motivo}.",
           dict({"quantidade": "número de partículas", "tamanho": "multiplicador (padrão 1)", "intensidade": "0 a 1"},
                **({"x": "centro 0 a 1", "y": "centro 0 a 1", "raio": "fração da largura (padrão 0.3)"} if _area == "ponto" else {})),
           pop=_mov == "explode", som=_SOM_PART.get(_mov))(_cls)


# ═════════════════════════════ 3. luz e textura (quadro inteiro) ═════════════════════════════

def _grade(W, H, escala=4):
    """Coordenadas normalizadas (0 a 1) numa grade reduzida, para máscaras baratas que depois sobem de tamanho."""
    w, h = max(2, W // escala), max(2, H // escala)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return xx / (w - 1), yy / (h - 1) * (H / W), (w, h)


def _subir(m, W, H):
    return cv2.resize(m.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)


class LuzTextura(Efeito):
    """Efeito de quadro inteiro desenhado por `tipo` e `arg`. Máscaras fixas saem prontas do `preparar`."""
    tipo, arg = "vazamento", None

    def preparar(self):
        W, H, t = self.W, self.H, self.tipo
        xx, yy, _ = _grade(W, H)
        ah = H / W
        if t == "vazamento":  # vazamento de luz vindo de uma borda ou canto
            ox, oy = {"esq": (-0.1, 0.5), "dir": (1.1, 0.5), "topo": (0.5, -0.1), "base": (0.5, 1.1), "canto_se": (-0.05, -0.05),
                      "canto_sd": (1.05, -0.05), "canto_ie": (-0.05, 1.05), "canto_id": (1.05, 1.05)}[self.arg[0]]
            d = np.hypot(xx - ox, yy - oy * ah)
            self.m = _subir(np.exp(-(d / 0.55) ** 2), W, H)
            self.cor = cor_marca(self.e.get("cor", self.arg[1]))
        elif t == "raios":  # raios de luz entrando
            ox, oy = {"topo": (0.5, -0.15), "canto_se": (-0.1, -0.1), "canto_sd": (1.1, -0.1), "centro": (0.5, 0.45)}[self.arg]
            self.o = (ox, oy * ah)
            self.ang = np.arctan2(yy - oy * ah, xx - ox)
            self.d = np.hypot(xx - ox, yy - oy * ah)
        elif t in ("vinheta_suave", "vinheta_forte", "vinheta_marinho"):
            d = np.hypot(xx - 0.5, (yy - 0.5 * ah) / ah * 1.0)
            k = {"vinheta_suave": 0.75, "vinheta_forte": 0.55, "vinheta_marinho": 0.6}[t]
            self.m = _subir(clamp01_np((d - k * 0.45) / 0.4), W, H)
        elif t in ("holofote", "foco_suave"):
            d = np.hypot(xx - self.x / W, yy - self.y / W)
            r = float(self.e.get("raio", 0.28))
            self.m = _subir(clamp01_np((d - r) / (r * 0.8)), W, H)
        elif t == "tilt_shift":
            cy = self.y / H
            self.m = _subir(clamp01_np(np.abs(yy / ah - cy) / 0.25 - 0.3), W, H)
        elif t == "desfoque_radial":
            d = np.hypot(xx - self.x / W, yy - self.y / W)
            self.m = _subir(clamp01_np((d - 0.15) / 0.5), W, H)
        elif t == "sombra_janela":  # gobo: sombra de janela com caixilhos
            u = (xx * 0.8 + yy * 0.35) * 5
            v = (yy * 0.9 - xx * 0.2) * 3.2
            luz = ((u % 1) > 0.12) & ((v % 1) > 0.12) & (u > 1) & (u < 4.2) & (v > 0.6) & (v < 3.6)
            self.m = cv2.GaussianBlur(_subir(luz, W, H), (0, 0), W * 0.012)
        elif t == "meio_tom":
            p = max(6, W // 90)
            yy2, xx2 = np.mgrid[0:H, 0:W]
            self.cel = ((xx2 % p) - p / 2) ** 2 + ((yy2 % p) - p / 2) ** 2
            self.p = p
        elif t == "papel":
            r = self.rng
            fib = cv2.GaussianBlur(r.normal(0, 1, (H // 2, W // 2)).astype(np.float32), (0, 0), 1.2)
            fib += cv2.GaussianBlur(r.normal(0, 1, (H // 2, W // 2)).astype(np.float32), (0, 0), 9) * 2.5
            self.m = _subir(fib / (np.abs(fib).max() + 1e-6), W, H)
        elif t == "caustica":
            self.xx, self.yy = xx, yy
        elif t == "scanlines":
            linhas = (np.arange(H) % 4 < 2).astype(np.float32)
            self.m = np.repeat(linhas[:, None], W, 1)
        elif t == "persiana":
            self.yy1 = np.linspace(0, 1, H, dtype=np.float32)
        elif t == "bokeh":
            r = self.rng
            self.pts = [(r.random() * W, r.random() * H, W * r.uniform(0.03, 0.08), r.uniform(0, TAU), r.random() < 0.4) for _ in range(18)]
        elif t == "nevoa":
            r = self.rng
            base = cv2.GaussianBlur(r.random((H // 16, W // 16)).astype(np.float32), (0, 0), 2.5)
            base = (base - base.min()) / (np.ptp(base) + 1e-6)
            self.m = _subir(np.tile(base, (1, 2)), W * 2, H)

    def _cor(self, papel):
        return np.array(_bgr(cor_marca(papel) if isinstance(papel, str) else papel), np.float32)

    def desenhar(self, frame, dt, rest):
        a = self.presenca(dt, rest, 0.3, 0.35) * self.forca
        if a <= 0.01:
            return
        t, W, H = self.tipo, self.W, self.H
        f = frame.astype(np.float32)
        if t == "vazamento":
            resp = 0.75 + 0.25 * math.sin(dt * 1.7)
            luz = self.m[..., None] * self._cor(self.cor) * (0.85 * a * resp)
            out = 255 - (255 - f) * (255 - luz) / 255
        elif t == "raios":
            gira = 0.08 * math.sin(dt * 0.6)
            fa = np.abs(np.sin((self.ang + gira) * 9)) ** 6 * np.exp(-self.d * 1.6)
            luz = _subir(fa, W, H)[..., None] * self._cor(self.cor) * (0.7 * a)
            out = 255 - (255 - f) * (255 - luz) / 255
        elif t.startswith("varredura"):
            p = (dt * 0.7) % 1.6 - 0.3
            xs = np.linspace(0, 1, W, dtype=np.float32)
            ys = np.linspace(0, 1, H, dtype=np.float32)
            if t == "varredura_h":
                c = xs[None, :] + 0 * ys[:, None]
            elif t == "varredura_v":
                c = ys[:, None] + 0 * xs[None, :]
            else:
                c = xs[None, :] * 0.6 + ys[:, None] * 0.4
            luz = np.exp(-((c - p) / 0.06) ** 2)[..., None] * self._cor(self.cor) * 0.55 * a
            out = 255 - (255 - f) * (255 - luz) / 255
        elif t in ("vinheta_suave", "vinheta_forte", "vinheta_marinho"):
            k = {"vinheta_suave": 0.45, "vinheta_forte": 0.8, "vinheta_marinho": 0.7}[t] * a
            alvo = self._cor("marinho") if t == "vinheta_marinho" else np.zeros(3, np.float32)
            m = self.m[..., None] * k
            out = f * (1 - m) + alvo * m
        elif t == "holofote":
            m = self.m[..., None] * 0.7 * a
            out = f * (1 - m)
            out = out * (1 + 0.12 * a * (1 - self.m[..., None]))
        elif t in ("tilt_shift", "desfoque_radial"):
            borr = cv2.GaussianBlur(frame, (0, 0), W * 0.008).astype(np.float32)
            m = self.m[..., None] * a
            out = f * (1 - m) + borr * m
        elif t == "sombra_janela":
            m = self.m[..., None]
            luz = self._cor("champanhe") * m * 0.35 * a
            out = (f * (1 - 0.35 * a * (1 - m))) + luz * 0.5
        elif t == "meio_tom":
            cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            pp = self.p
            peq = cv2.resize(cinza, (W // pp + 1, H // pp + 1), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
            r2 = cv2.resize(peq, (W // pp * pp + pp, H // pp * pp + pp), interpolation=cv2.INTER_NEAREST)[:H, :W]
            ponto = (self.cel < (r2 * pp * 0.62) ** 2).astype(np.float32)[..., None]
            tinta = self._cor("marinho") * (1 - ponto) + self._cor("papel") * ponto
            out = f * (1 - 0.8 * a) + tinta * 0.8 * a
        elif t == "papel":
            out = f * (1 + self.m[..., None] * 0.07 * a)
            out = out * (1 - 0.06 * a) + self._cor("papel") * 0.06 * a
        elif t == "poeira":
            r = self.rng_quadro(dt)
            ov = np.zeros((H, W), np.float32)
            for _ in range(int(r.integers(6, 16))):
                cv2.circle(ov, (int(r.random() * W), int(r.random() * H)), int(r.integers(1, max(2, W // 300))), 1.0, -1, cv2.LINE_AA)
            for _ in range(int(r.integers(0, 3))):
                x0, y0 = int(r.random() * W), int(r.random() * H)
                cv2.line(ov, (x0, y0), (x0 + int(r.normal(0, W * 0.02)), y0 + int(r.normal(0, W * 0.02))), 1.0, 1, cv2.LINE_AA)
            out = f * (1 - ov[..., None] * 0.6 * a) + 230 * ov[..., None] * 0.6 * a
        elif t == "riscos_filme":
            r = self.rng_quadro(dt)
            ov = np.zeros((H, W), np.float32)
            for _ in range(int(r.integers(1, 4))):
                x0 = int(r.random() * W)
                cv2.line(ov, (x0, 0), (x0 + int(r.normal(0, 6)), H), float(r.uniform(0.3, 0.9)), 1, cv2.LINE_AA)
            tremor = 1 + 0.05 * a * float(r.normal())
            out = (f * tremor) * (1 - ov[..., None] * 0.5 * a) + 220 * ov[..., None] * 0.5 * a
        elif t == "ruido_cor":
            r = self.rng_quadro(dt)
            ru = cv2.resize(r.normal(0, 1, (H // 3, W // 3, 3)).astype(np.float32), (W, H))
            out = f + ru * 16 * a
        elif t == "pixelado":
            n = int(4 + 40 * a * self.forca)
            peq = cv2.resize(frame, (max(4, W // n), max(4, H // n)), interpolation=cv2.INTER_AREA)
            out = cv2.resize(peq, (W, H), interpolation=cv2.INTER_NEAREST).astype(np.float32)
        elif t == "aberracao":
            d = int(W * 0.006 * a) + 1
            out = f.copy()
            out[:, d:, 2] = f[:, :-d, 2]
            out[:, :-d, 0] = f[:, d:, 0]
        elif t == "pulso_brilho":
            k = 0.5 + 0.5 * math.sin(dt * TAU * float(self.e.get("bpm", 100)) / 60)
            out = f * (1 + 0.14 * k * a)
        elif t == "persiana":
            p = clamp01(dt / 0.6) if rest > 0.6 else clamp01(rest / 0.6)
            faixa = ((self.yy1 * 12) % 1 < 1 - ease_in_out(p))[:, None, None]
            out = np.where(faixa, f * (1 - a) + self._cor("marinho") * a, f)
        elif t == "caustica":
            xx, yy = self.xx, self.yy
            c = np.sin(xx * 23 + dt * 1.3 + np.sin(yy * 17 + dt)) + np.sin(yy * 19 - dt * 1.1 + np.sin(xx * 13 - dt * 0.7))
            luz = _subir(clamp01_np(c - 1.1) ** 2, W, H)[..., None] * self._cor("nevoa") * 0.45 * a
            out = 255 - (255 - f) * (255 - luz) / 255
        elif t == "estrobo":
            ligado = int(dt * float(self.e.get("hz", 6))) % 2 == 0
            out = f * (1 + 0.35 * a) if ligado else f * (1 - 0.2 * a)
        elif t == "bokeh":
            ov = np.zeros((H // 2, W // 2, 3), np.float32)
            for x, y, r, fa, alt in self.pts:
                yy_ = (y - dt * W * 0.02) % H
                cv2.circle(ov, (int(x / 2), int(yy_ / 2)), int(r / 2), _bgr(self.cor2 if alt else self.cor), -1, cv2.LINE_AA)
            luz = cv2.GaussianBlur(cv2.resize(ov, (W, H)), (0, 0), W * 0.006) * 0.45 * a
            out = 255 - (255 - f) * (255 - luz) / 255
        elif t == "nevoa":
            dx = int((dt * W * 0.03) % W)
            m = self.m[:, dx:dx + W][..., None] * 0.35 * a
            out = f * (1 - m) + self._cor("nevoa") * m
        elif t == "vela":
            r = self.rng_quadro(dt)
            k = 0.06 * math.sin(dt * 9) + 0.04 * float(r.normal())
            quente = self._cor("bronze") * 0.12 * a
            out = f * (1 + k * a) + quente * 0.5
        elif t == "bloom":
            luz = np.clip(f - 170, 0, 255)
            luz = cv2.GaussianBlur(luz, (0, 0), W * 0.015) * 1.4 * a
            out = 255 - (255 - f) * (255 - np.clip(luz, 0, 255)) / 255
        elif t == "sonho":
            borr = cv2.GaussianBlur(frame, (0, 0), W * 0.01).astype(np.float32)
            out = 255 - (255 - f) * (255 - borr * 0.45 * a) / 255
        elif t == "contraluz":
            borr = cv2.GaussianBlur(frame, (0, 0), W * 0.03).astype(np.float32)
            luz = self._cor("champanhe") * 0.25 * a
            out = f * (1 - 0.15 * a) + borr * 0.15 * a + luz * np.clip(borr.mean(2, keepdims=True) / 255, 0, 1)
        elif t == "cortina_luz":
            p = clamp01(dt / 0.8)
            xs = np.linspace(0, 1, W, dtype=np.float32)[None, :, None]
            m = np.exp(-((xs - (1.3 * ease_in_out(p) - 0.15)) / 0.08) ** 2) * 0.9 * a
            out = f * (1 - m) + 250 * m
        else:
            return
        frame[:] = np.clip(out, 0, 255).astype(np.uint8)


def clamp01_np(v):
    return np.clip(v, 0.0, 1.0)


_SO_FORA_DA_FE = " Evite em vídeo de fé (GiraHub)."
LUZES = []
_ORIGENS = {"esq": "da esquerda", "dir": "da direita", "topo": "do alto", "base": "de baixo", "canto_se": "do canto superior esquerdo",
            "canto_sd": "do canto superior direito", "canto_ie": "do canto inferior esquerdo", "canto_id": "do canto inferior direito"}
for _o, _od in _ORIGENS.items():
    for _c, _cd in (("champanhe", "dourada"), ("bronze", "quente")):
        LUZES.append((f"vazamento_{_o}_{'dourado' if _c == 'champanhe' else 'quente'}", "luz", "vazamento", (_o, _c),
                      f"Vazamento de luz {_cd} entrando {_od}, respirando devagar. Clima de memória, abertura, emoção.", None))
for _o, _od in (("topo", "do alto"), ("canto_se", "do canto esquerdo"), ("canto_sd", "do canto direito"), ("centro", "de trás da pessoa")):
    LUZES.append((f"raios_{_o}", "luz", "raios", _o, f"Raios de luz entrando {_od}, girando de leve. Revelação, esperança, momento solene.", None))
for _n, _d in (("varredura_h", "da esquerda para a direita"), ("varredura_v", "de cima para baixo"), ("varredura_diagonal", "na diagonal")):
    LUZES.append((_n, "luz", _n, None, f"Faixa de brilho varrendo o quadro {_d}, como reflexo em vidro. Novidade, premium.", "vidro-shimmer"))
LUZES += [
    ("vinheta_suave", "textura", "vinheta_suave", None, "Vinheta leve que puxa o olhar para o centro.", None),
    ("vinheta_forte", "textura", "vinheta_forte", None, "Vinheta escura e fechada, para tensão ou confissão.", None),
    ("vinheta_marinho", "textura", "vinheta_marinho", None, "Vinheta na cor escura da marca, para emoldurar uma fala importante.", None),
    ("holofote", "luz", "holofote", None, "Holofote: escurece tudo menos um círculo em (x, y). Destaque de um objeto ou do rosto.", "interruptor"),
    ("tilt_shift", "textura", "tilt_shift", None, "Desfoca o alto e o pé do quadro, mantendo nítida a faixa em y. Efeito miniatura.", None),
    ("desfoque_radial", "textura", "desfoque_radial", None, "Desfoca as bordas e mantém nítido o ponto (x, y). Foco na pessoa.", None),
    ("sombra_janela", "luz", "sombra_janela", None, "Luz de fim de tarde entrando por uma janela, com a sombra dos caixilhos. Casa, aconchego.", None),
    ("meio_tom", "textura", "meio_tom", None, "Retícula de pontos (meio-tom de jornal) nas cores da marca. Pop art, notícia, memória.", "pagina"),
    ("papel", "textura", "papel", None, "Textura de papel com fibra por cima do vídeo. Artesanal, caderno, estudo.", None),
    ("poeira", "textura", "poeira", None, "Poeira e fiapos de filme antigo passando. Nostalgia.", None),
    ("riscos_filme", "textura", "riscos_filme", None, "Riscos verticais e tremor de projetor de cinema." + _SO_FORA_DA_FE, None),
    ("ruido_cor", "textura", "ruido_cor", None, "Ruído de cor de câmera no escuro." + _SO_FORA_DA_FE, None),
    ("pixelado", "impacto", "pixelado", None, "Pixeliza o quadro (censura, segredo, digital)." + _SO_FORA_DA_FE, "glitch"),
    ("aberracao", "impacto", "aberracao", None, "Aberração cromática: vermelho e azul se separam." + _SO_FORA_DA_FE, "glitch"),
    ("pulso_brilho", "luz", "pulso_brilho", None, "O quadro pulsa de brilho no ritmo da música (bpm). Energia, batida.", None),
    ("persiana", "impacto", "persiana", None, "Faixas horizontais abrindo como persiana. Entrada ou revelação.", "deslizar"),
    ("caustica", "luz", "caustica", None, "Reflexo de água (cáustica) dançando no quadro. Mar, piscina, calma, limpeza.", None),
    ("estrobo", "impacto", "estrobo", None, "Luz piscando como estroboscópio (hz). Festa, balada, ritmo." + _SO_FORA_DA_FE, None),
    ("bokeh_desfocado", "luz", "bokeh", None, "Grandes bolas de luz desfocadas subindo devagar. Festa, noite, clima.", None),
    ("nevoa", "luz", "nevoa", None, "Névoa leve atravessando o quadro. Mistério, frio, manhã.", None),
    ("vela", "luz", "vela", None, "Luz quente que tremula como chama de vela. Intimidade, oração, noite.", None),
    ("bloom", "luz", "bloom", None, "As partes claras ganham um brilho que vaza (bloom). Sonho, glamour.", None),
    ("sonho", "luz", "sonho", None, "Glow difuso no quadro inteiro (filtro de sonho). Lembrança, delicadeza.", None),
    ("contraluz", "luz", "contraluz", None, "Luz dourada por trás, como contraluz de fim de tarde.", None),
    ("cortina_luz", "impacto", "cortina_luz", None, "Uma faixa de luz branca atravessa o quadro uma vez. Virada de assunto.", "whoosh-suave"),
]

for _nome, _cat, _tipo, _arg, _desc, _som in LUZES:
    _cls = type(f"Luz_{_nome}", (LuzTextura,), {"tipo": _tipo, "arg": _arg})
    _params = {"intensidade": "0 a 1"}
    if _tipo in ("holofote", "desfoque_radial"):
        _params.update({"x": "centro 0 a 1", "y": "centro 0 a 1", "raio": "fração da largura (holofote)"})
    if _tipo == "tilt_shift":
        _params["y"] = "faixa nítida, 0 a 1"
    if _tipo == "pulso_brilho":
        _params["bpm"] = "batidas por minuto (padrão 100)"
    if _tipo == "estrobo":
        _params["hz"] = "piscadas por segundo (padrão 6)"
    efeito(_nome, _cat, _desc, _params, fase="pos", som=_som)(_cls)


# ═════════════════════════════ 4. formas geométricas animadas ═════════════════════════════

def _reg_poligono(n, r, ang, cx, cy):
    return np.int32([[cx + r * math.cos(ang + k * TAU / n), cy + r * math.sin(ang + k * TAU / n)] for k in range(n)])


class FormaAnimada(Efeito):
    """Forma de motion design desenhada em vetor: `fino` é contorno na cor de destaque; `bloco` é cheio e translúcido."""
    tipo, estilo = "anel_pulso", "fino"

    def preparar(self):
        self.R = self.W * float(self.e.get("tamanho", 0.18))
        self.esp = max(2, int(self.W * (0.006 if self.estilo == "fino" else 0.016)))

    def _poly(self, ov, pts, cor, fechado=True):
        if self.estilo == "bloco" and fechado:
            cv2.fillPoly(ov, [pts], cor, cv2.LINE_AA)
        else:
            cv2.polylines(ov, [pts], fechado, cor, self.esp, cv2.LINE_AA)

    def _circ(self, ov, c, r, cor, cheio=None):
        cheio = self.estilo == "bloco" if cheio is None else cheio
        cv2.circle(ov, (int(c[0]), int(c[1])), max(1, int(r)), cor, -1 if cheio else self.esp, cv2.LINE_AA)

    def desenhar(self, frame, dt, rest):
        a = self.presenca(dt, rest, 0.25, 0.3) * self.forca
        if a <= 0.01:
            return
        W, H, R, x, y, t = self.W, self.H, self.R, self.x, self.y, self.tipo
        cor = _bgr(self.cor)
        cor2 = _bgr(self.cor2)
        ent = mola(clamp01(dt / 0.5))
        ov = frame.copy()
        esp = self.esp
        if t == "anel_pulso":
            for k in range(3):
                p = ((dt * 0.8 + k / 3) % 1)
                cv2.circle(ov, (int(x), int(y)), int(R * (0.3 + 0.9 * p)), cor, max(1, int(esp * (1 - p) + 1)), cv2.LINE_AA)
        elif t == "aneis_concentricos":
            for k in range(4):
                self._circ(ov, (x, y), R * (0.25 + 0.25 * k) * ent, cor if k % 2 == 0 else cor2, cheio=False)
        elif t in ("quadrado_girando", "triangulo_girando", "hexagono_girando", "losango_girando", "pentagono_girando"):
            n = {"quadrado_girando": 4, "triangulo_girando": 3, "hexagono_girando": 6, "losango_girando": 4, "pentagono_girando": 5}[t]
            self._poly(ov, _reg_poligono(n, R * ent, dt * 1.2 + (0 if t != "losango_girando" else math.pi / 2), x, y), cor)
            if self.estilo == "fino":
                self._poly(ov, _reg_poligono(n, R * 0.7 * ent, -dt * 0.9, x, y), cor2)
        elif t == "estrela_girando":
            pts = [(x + (R if k % 2 == 0 else R * 0.45) * ent * math.cos(dt + k * math.pi / 5),
                    y + (R if k % 2 == 0 else R * 0.45) * ent * math.sin(dt + k * math.pi / 5)) for k in range(10)]
            self._poly(ov, np.int32(pts), cor)
        elif t == "burst_raios":
            n = 16
            for k in range(n):
                an = k * TAU / n + dt * 0.3
                r0, r1 = R * 0.55 * ent, R * (1.0 + 0.15 * math.sin(dt * 6 + k)) * ent
                cv2.line(ov, (int(x + r0 * math.cos(an)), int(y + r0 * math.sin(an))), (int(x + r1 * math.cos(an)), int(y + r1 * math.sin(an))),
                         cor, esp, cv2.LINE_AA)
        elif t == "linhas_velocidade":  # linhas radiais na borda, mangá
            r = self.rng_quadro(dt)
            for _ in range(40 if self.estilo == "fino" else 34):
                an = r.random() * TAU
                r0 = W * (r.uniform(0.45, 0.6) if self.estilo == "fino" else r.uniform(0.3, 0.4))
                p0 = (W / 2 + r0 * math.cos(an), H / 2 + r0 * math.sin(an) * H / W)
                p1 = (W / 2 + W * math.cos(an), H / 2 + W * math.sin(an) * H / W)
                if self.estilo == "fino":
                    cv2.line(ov, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), cor2, esp, cv2.LINE_AA)
                else:  # cunhas cheias de mangá: finas na ponta de dentro, largas na borda
                    lg = W * r.uniform(0.02, 0.045)
                    nx, ny = -math.sin(an) * lg, math.cos(an) * lg
                    cv2.fillPoly(ov, [np.int32([p0, (p1[0] + nx, p1[1] + ny), (p1[0] - nx, p1[1] - ny)])], cor, cv2.LINE_AA)
        elif t == "linhas_horizontais":
            r = self.rng_quadro(dt)
            for _ in range(14 if self.estilo == "fino" else 7):
                yy = r.random() * H
                x0 = r.random() * W
                x1 = x0 + W * r.uniform(0.1, 0.35)
                if self.estilo == "fino":
                    cv2.line(ov, (int(x0), int(yy)), (int(x1), int(yy)), cor2, max(1, esp // 2), cv2.LINE_AA)
                else:  # faixas grossas e arredondadas na cor de destaque
                    cv2.line(ov, (int(x0), int(yy)), (int(x1), int(yy)), cor, esp * 2, cv2.LINE_AA)
        elif t == "grade_pontos":
            p = max(10, int(W / 14))
            for i in range(0, W + p, p):
                for j in range(0, H + p, p):
                    d = math.hypot(i - x, j - y) / W
                    s = max(0.0, math.sin(dt * 3 - d * 12)) * esp * 1.2
                    if s > 0.5:
                        cv2.circle(ov, (i, j), int(s), cor, -1, cv2.LINE_AA)
        elif t == "grade_linhas":
            p = max(10, int(W / 8))
            off = int(dt * p * 0.5) % p
            if self.estilo == "bloco":  # xadrez de células cheias que desliza
                for i in range(-p, W + p, p):
                    for j in range(-p, H + p, p):
                        if ((i // p) + (j // p)) % 2 == 0:
                            cv2.rectangle(ov, (i + off, j + off), (i + off + p, j + off + p), cor2, -1)
            for i in range(-p, W + p, p):
                cv2.line(ov, (i + off, 0), (i + off, H), cor2, 1, cv2.LINE_AA)
            for j in range(-p, H + p, p):
                cv2.line(ov, (0, j + off), (W, j + off), cor2, 1, cv2.LINE_AA)
        elif t == "barra_progresso":
            p = ease_in_out(clamp01(dt / max(0.5, dt + rest - 0.3)))
            w0 = W * 0.6
            x0 = int(x - w0 / 2)
            cv2.rectangle(ov, (x0, int(y - esp * 2)), (int(x0 + w0), int(y + esp * 2)), cor2, 1 if self.estilo == "fino" else -1, cv2.LINE_AA)
            cv2.rectangle(ov, (x0, int(y - esp * 2)), (int(x0 + w0 * p), int(y + esp * 2)), cor, -1, cv2.LINE_AA)
        elif t == "spinner":
            a0 = dt * 300
            cv2.ellipse(ov, (int(x), int(y)), (int(R * 0.5), int(R * 0.5)), a0, 0, 270, cor, esp * 2, cv2.LINE_AA)
        elif t == "arco_progresso":
            p = clamp01(dt / max(0.5, dt + rest - 0.3))
            cv2.ellipse(ov, (int(x), int(y)), (int(R * 0.6), int(R * 0.6)), -90, 0, 360, cor2, esp, cv2.LINE_AA)
            cv2.ellipse(ov, (int(x), int(y)), (int(R * 0.6), int(R * 0.6)), -90, 0, 360 * ease_in_out(p), cor, esp * 2, cv2.LINE_AA)
        elif t == "pontos_carregando":
            for k in range(3):
                dy = -abs(math.sin(dt * 5 - k * 0.6)) * R * 0.25
                self._circ(ov, (x + (k - 1) * R * 0.35, y + dy), R * 0.1, cor, cheio=True)
        elif t == "equalizador":
            for k in range(7):
                h = R * (0.25 + 0.75 * abs(math.sin(dt * (4 + k * 0.7) + k)))
                cx = int(x + (k - 3) * R * 0.22)
                cv2.rectangle(ov, (cx - int(R * 0.07), int(y)), (cx + int(R * 0.07), int(y - h)), cor if k % 2 else cor2, -1, cv2.LINE_AA)
        elif t == "onda_seno":
            xs = np.linspace(0, W, 120)
            ys = y + R * 0.3 * np.sin(xs / W * 4 * math.pi - dt * 4)
            if self.estilo == "bloco":  # faixa ondulada cheia (fita de som)
                faixa = np.vstack([np.stack([xs, ys], 1), np.stack([xs[::-1], ys[::-1] + R * 0.18], 1)])
                cv2.fillPoly(ov, [np.int32(faixa)], cor, cv2.LINE_AA)
            cv2.polylines(ov, [np.int32(np.stack([xs, ys], 1))], False, cor, esp, cv2.LINE_AA)
        elif t == "mira":
            r = R * (1.4 - 0.4 * ent)
            cv2.circle(ov, (int(x), int(y)), int(r * 0.6), cor, esp, cv2.LINE_AA)
            for k in range(4):
                an = k * math.pi / 2 + dt * 0.5
                cv2.line(ov, (int(x + r * 0.3 * math.cos(an)), int(y + r * 0.3 * math.sin(an))),
                         (int(x + r * 0.9 * math.cos(an)), int(y + r * 0.9 * math.sin(an))), cor, esp, cv2.LINE_AA)
        elif t == "cantos_camera":
            m, L = int(W * 0.06), int(W * 0.08)
            for cx, cy, sx, sy in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)):
                cv2.polylines(ov, [np.int32([(cx, cy + sy * L), (cx, cy), (cx + sx * L, cy)])], False, cor2, esp, cv2.LINE_AA)
            if int(dt * 2) % 2 == 0:
                cv2.circle(ov, (int(m + W * 0.05), int(m + W * 0.05)), int(W * 0.012), cor, -1, cv2.LINE_AA)
            if self.estilo == "bloco":  # etiqueta de gravação e barra de nível de áudio
                tx, ty = int(m + W * 0.08), int(m + W * 0.065)
                cv2.rectangle(ov, (tx - 6, ty - int(W * 0.035)), (tx + int(W * 0.11), ty + 8), (20, 20, 20), -1)
                cv2.putText(ov, "REC", (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, W / 1080 * 1.1, cor2, max(1, int(W / 500)), cv2.LINE_AA)
                for k in range(10):
                    h = int(W * 0.025 * (0.3 + 0.7 * abs(math.sin(dt * 7 + k * 1.3))))
                    cx = int(W - m - W * 0.03 - k * W * 0.014)
                    cv2.rectangle(ov, (cx, int(H - m - W * 0.02 - h)), (cx + int(W * 0.008), int(H - m - W * 0.02)), cor, -1)
        elif t == "barras_cinema":
            h = int(H * (0.11 if self.estilo == "fino" else 0.17) * ease_out(clamp01(dt / 0.5)) * clamp01(rest / 0.4))
            cv2.rectangle(ov, (0, 0), (W, h), (8, 8, 8), -1)
            cv2.rectangle(ov, (0, H - h), (W, H), (8, 8, 8), -1)
        elif t == "moldura":
            m = int(W * 0.04 * ent)
            cv2.rectangle(ov, (m, m), (W - m, H - m), cor, esp, cv2.LINE_AA)
            if self.estilo == "bloco":
                cv2.rectangle(ov, (m + esp * 2, m + esp * 2), (W - m - esp * 2, H - m - esp * 2), cor2, max(1, esp // 3), cv2.LINE_AA)
        elif t == "orbita":
            cv2.ellipse(ov, (int(x), int(y)), (int(R), int(R * 0.35)), -15, 0, 360, cor2, max(1, esp // 2), cv2.LINE_AA)
            for k in range(3):
                an = dt * 1.8 + k * TAU / 3
                px, py = R * math.cos(an), R * 0.35 * math.sin(an)
                c, s = math.cos(math.radians(-15)), math.sin(math.radians(-15))
                self._circ(ov, (x + px * c - py * s, y + px * s + py * c), R * 0.07, cor, cheio=True)
        elif t == "setas_convergindo":
            for k in range(4):
                an = k * math.pi / 2 + math.pi / 4
                d = R * (1.3 - 0.6 * ent)
                px, py = x + d * math.cos(an), y + d * math.sin(an)
                tx, ty = x + (d - R * 0.4) * math.cos(an), y + (d - R * 0.4) * math.sin(an)
                cv2.arrowedLine(ov, (int(px), int(py)), (int(tx), int(ty)), cor, esp, cv2.LINE_AA, tipLength=0.4)
        elif t == "cruz_girando":
            an = dt * 2
            for k in range(2):
                b = an + k * math.pi / 2
                cv2.line(ov, (int(x - R * 0.6 * math.cos(b)), int(y - R * 0.6 * math.sin(b))),
                         (int(x + R * 0.6 * math.cos(b)), int(y + R * 0.6 * math.sin(b))), cor, esp * 2, cv2.LINE_AA)
        elif t == "circulo_crescente":
            self._circ(ov, (x, y), R * ent, cor)
        elif t == "x_grande":
            L = R * ent
            cv2.line(ov, (int(x - L), int(y - L)), (int(x + L), int(y + L)), cor, esp * 2, cv2.LINE_AA)
            cv2.line(ov, (int(x + L), int(y - L)), (int(x - L), int(y + L)), cor, esp * 2, cv2.LINE_AA)
        elif t == "listras_diagonais":
            p = int(W * 0.07)
            off = int(dt * p * 1.5) % (2 * p)
            for i in range(-H, W + H, 2 * p):
                pts = np.int32([(i + off, 0), (i + off + p, 0), (i + off + p - H, H), (i + off - H, H)])
                cv2.fillPoly(ov, [pts], cor2, cv2.LINE_AA)
        alfa = (0.9 if self.estilo == "fino" else 0.6) * a
        if t in ("listras_diagonais", "grade_linhas") or (t == "linhas_velocidade" and self.estilo == "fino"):
            alfa *= 0.35
        if t == "barras_cinema":
            alfa = a
        frame[:] = cv2.addWeighted(ov, alfa, frame, 1 - alfa, 0)


FORMAS_ANIM = {
    "anel_pulso": ("Três anéis pulsando para fora de um ponto. Notificação, chamar atenção.", "ui-sobe"),
    "aneis_concentricos": ("Anéis concêntricos que se abrem. Alvo, foco, meta.", None),
    "quadrado_girando": ("Quadrado girando em volta de um ponto. Método, estrutura.", None),
    "triangulo_girando": ("Triângulo girando. Energia, direção.", None),
    "hexagono_girando": ("Hexágono girando. Tecnologia, ciência, sistema.", None),
    "losango_girando": ("Losango girando. Valor, premium.", None),
    "pentagono_girando": ("Pentágono girando. Equilíbrio entre partes.", None),
    "estrela_girando": ("Estrela girando, que abre com mola. Destaque, nota máxima.", "brilho"),
    "burst_raios": ("Raios em explosão em volta de um ponto (sunburst). Novidade, oferta, impacto.", "impacto-seco"),
    "linhas_velocidade": ("Linhas de velocidade nas bordas, estilo mangá. Susto, pressa, revelação.", "whoosh-rapido"),
    "linhas_horizontais": ("Riscos horizontais passando rápido. Velocidade, correria.", "whoosh-curto"),
    "grade_pontos": ("Grade de pontos que pulsa em onda a partir de um ponto. Dados, rede, digital.", None),
    "grade_linhas": ("Quadriculado que desliza ao fundo. Planejamento, blueprint.", None),
    "barra_progresso": ("Barra de progresso enchendo até o fim do elemento. Etapa, processo, quase lá.", "rolagem"),
    "spinner": ("Spinner girando. Carregando, esperando, pensando.", None),
    "arco_progresso": ("Círculo de progresso que se fecha até o fim do elemento. Contagem, meta.", None),
    "pontos_carregando": ("Três pontinhos pulando (digitando...). Suspense, pensando.", "teclado"),
    "equalizador": ("Barras de equalizador dançando. Música, áudio, podcast.", None),
    "onda_seno": ("Onda que corre o quadro. Voz, frequência, fluxo.", None),
    "mira": ("Mira que se fecha sobre um ponto. Alvo, foco, encontrar o problema.", "clique"),
    "cantos_camera": ("Cantos de visor de câmera com luz piscando. Gravando, bastidor, ao vivo.", None),
    "barras_cinema": ("Faixas pretas de cinema que entram e saem. Momento épico, cena.", None),
    "moldura": ("Moldura que fecha o quadro. Destaque de uma frase ou de um momento.", "deslizar"),
    "orbita": ("Três pontos em órbita elíptica em volta de algo. Ecossistema, gira em torno de.", None),
    "setas_convergindo": ("Quatro setas apontando para o centro. Foco, convergir, o ponto principal.", "whoosh-curto"),
}
# 25 formas × 2 estilos = 50 efeitos
for _t, (_desc, _som) in FORMAS_ANIM.items():
    for _est, _ed in (("fino", "contorno fino na cor de destaque"), ("bloco", "forma cheia e translúcida")):
        _cls = type(f"Forma_{_t}_{_est}", (FormaAnimada,), {"tipo": _t, "estilo": _est})
        efeito(f"forma_{_t}_{_est}", "formas", f"{_desc} Estilo {_ed}.",
               {"x": "centro 0 a 1", "y": "centro 0 a 1", "tamanho": "raio, fração da largura (padrão 0.18)", "intensidade": "0 a 1"},
               som=_som)(_cls)
