"""Estilhaços: o quadro quebra em cacos triangulares de vidro que voam (ou se montam), com a borda de cada caco acesa.

Inspirado na abertura de demonstrações de motion design (referência D em docs/estilos-de-referencia.md). A malha é uma
triangulação de Delaunay de pontos fixos (mesma resolução, mesmos cacos), então o mesmo EDL dá sempre o mesmo quadro.
Cada caco sai do ponto de impacto com atraso pela distância, gira, encolhe como se fosse para o fundo e some antes do
fim, para a transição terminar inteira no quadro novo. Embaixo dos cacos está sempre o outro quadro: nada de tela vazia.
"""
import math

import cv2
import numpy as np

from .marca import CORES
from .movimento import clamp01, ease_in, ease_out
from .transicoes import transicao_reg
from .util import bgr

_MALHA = {}


def malha(W, H, n=70, semente=7):
    """Triângulos (k, 3, 2) cobrindo o quadro inteiro, com pontos fixos nas bordas para não sobrar canto."""
    chave = (W, H, n, semente)
    if chave not in _MALHA:
        r = np.random.default_rng(semente)
        cols = max(3, int(round(math.sqrt(n * W / H))))
        lins = max(3, int(round(n / cols)))
        pts = []
        for j in range(lins + 1):
            for i in range(cols + 1):
                x, y = i / cols, j / lins
                if 0 < i < cols:
                    x += r.uniform(-0.35, 0.35) / cols
                if 0 < j < lins:
                    y += r.uniform(-0.35, 0.35) / lins
                pts.append((x * (W - 1), y * (H - 1)))
        sub = cv2.Subdiv2D((0, 0, W, H))
        for p in pts:
            sub.insert((float(p[0]), float(p[1])))
        tri = sub.getTriangleList().reshape(-1, 3, 2)
        dentro = np.all((tri[..., 0] >= -1) & (tri[..., 0] <= W) & (tri[..., 1] >= -1) & (tri[..., 1] <= H), axis=(1,))
        _MALHA[chave] = tri[dentro].astype(np.float32)
    return _MALHA[chave]


def _cor(papel):
    return tuple(int(v) for v in bgr(CORES[papel]))


def _q(pp, atraso):
    """Andamento de um caco: começa depois do atraso e termina antes do fim da transição."""
    return clamp01((pp - atraso) / max(0.35, 0.92 - atraso))


def estilhacar(topo, fundo, p, W, H, impacto=(0.5, 0.45), forca=1.0, borda="champanhe", trinca=0.12):
    """`topo` quebra e voa revelando `fundo`. p de 0 a 1. Até `trinca` só aparecem as rachaduras."""
    tri = malha(W, H)
    out = fundo.copy()
    ix, iy = impacto[0] * W, impacto[1] * H
    diag = math.hypot(W, H)
    cor_borda = _cor(borda)
    if p <= trinca:  # rachaduras saindo do ponto de impacto
        out[:] = topo
        q = ease_out(p / max(trinca, 1e-4))
        ov = out.copy()
        for t in tri:  # só as arestas dos cacos que a trinca já alcançou, mais fortes perto do impacto
            c = t.mean(0)
            d = math.hypot(c[0] - ix, c[1] - iy) / (q * diag * 0.2 + 1e-4)
            if d < 1:
                cv2.polylines(ov, [np.int32(t)], True, cor_borda, max(1, W // 540), cv2.LINE_AA)
        return cv2.addWeighted(ov, 0.7 * q, out, 1 - 0.7 * q, 0)
    pp = (p - trinca) / (1 - trinca)
    r = np.random.default_rng(11)  # velocidades fixas por caco (mesma malha, mesmo voo)
    params = [(r.uniform(0.6, 1.3), r.uniform(-1, 1) * 160) for _ in tri]
    parado = np.zeros((H, W), np.uint8)  # a parte ainda inteira entra de uma vez (sem costura entre cacos)
    for t in tri:
        c = t.mean(0)
        atraso = math.hypot(c[0] - ix, c[1] - iy) / diag * 0.8
        if _q(pp, atraso) < 0.04:  # ainda não saiu do lugar
            cv2.fillConvexPoly(parado, np.int32(np.round(t)), 255)
    if parado.any():
        parado = cv2.dilate(parado, np.ones((3, 3), np.uint8))
        out[parado > 0] = topo[parado > 0]
    for k, t in enumerate(tri):
        c = t.mean(0)
        dx, dy = c[0] - ix, c[1] - iy
        dist = math.hypot(dx, dy) / diag
        vel, giro = params[k]
        atraso = dist * 0.8
        q = _q(pp, atraso)
        if q < 0.04:
            continue
        if q >= 1:
            continue
        e = ease_in(q)
        if dist < 1e-4:
            dx, dy = 0.0, -1.0
        n = math.hypot(dx, dy) or 1.0
        voa = e * diag * 0.55 * vel * forca
        cx, cy = c[0] + dx / n * voa, c[1] + dy / n * voa + e * e * H * 0.25  # sai do impacto e cai
        esc = 1 - 0.55 * e  # vai para o fundo
        th = math.radians(giro * e)
        R = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]], np.float32) * esc
        dst = (t - c) @ R.T + (cx, cy)
        x0, y0 = np.floor(np.minimum(t.min(0), dst.min(0))).astype(int)
        x1, y1 = np.ceil(np.maximum(t.max(0), dst.max(0))).astype(int) + 1
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        if x1 - x0 < 2 or y1 - y0 < 2:
            continue
        M = cv2.getAffineTransform(t.astype(np.float32), dst.astype(np.float32))
        M[:, 2] -= (x0, y0)
        peca = cv2.warpAffine(topo, M, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        m = np.zeros((y1 - y0, x1 - x0), np.uint8)
        cv2.fillConvexPoly(m, np.int32(dst - (x0, y0)), 255, cv2.LINE_AA)
        alfa = (m.astype(np.float32) / 255 * (1 - clamp01((q - 0.75) / 0.25)))[..., None]
        reg = out[y0:y1, x0:x1].astype(np.float32)
        sombra = cv2.GaussianBlur(m, (0, 0), 3).astype(np.float32)[..., None] / 255 * 0.35 * (1 - q)
        reg = reg * (1 - sombra)
        out[y0:y1, x0:x1] = (reg * (1 - alfa) + peca.astype(np.float32) * alfa).astype(np.uint8)
        brilho = 0.6 * (1 - q) * clamp01((q - 0.1) / 0.25)  # aresta acesa só com o caco em voo (montado, o quadro fica limpo)
        if brilho > 0.05:  # aresta de vidro acesa na cor da marca
            ov = out[y0:y1, x0:x1].copy()
            cv2.polylines(ov, [np.int32(dst - (x0, y0))], True, cor_borda, max(1, W // 600), cv2.LINE_AA)
            out[y0:y1, x0:x1] = cv2.addWeighted(ov, brilho, out[y0:y1, x0:x1], 1 - brilho, 0)
    return out


def _quebra(impacto, forca=1.0, borda="champanhe"):
    def fn(a, b, p, W, H):
        return estilhacar(a, b, p, W, H, impacto, forca, borda)
    return fn


def _monta(impacto, borda="champanhe"):
    def fn(a, b, p, W, H):  # o filme ao contrário: os cacos do quadro novo voltam e fecham por cima do antigo
        return estilhacar(b, a, 1 - p, W, H, impacto, 1.0, borda, trinca=0.0)
    return fn


_SOM = ["vidro-shimmer", "impacto-seco"]
transicao_reg("estilhacar", "A tela trinca do centro e quebra em cacos de vidro que voam, revelando a cena nova. Virada forte, "
              "revelação, 'quebrar a regra'.", _SOM, 0.6)(_quebra((0.5, 0.45)))
transicao_reg("estilhacar_toque", "Trinca no ponto do dedo (meio de baixo) e os cacos voam para cima. Clique, toque na tela, "
              "'olha isso'.", _SOM, 0.6)(_quebra((0.55, 0.72)))
transicao_reg("estilhacar_lateral", "Quebra a partir da lateral esquerda e os cacos varrem para a direita. Próximo item de "
              "lista.", _SOM, 0.6)(_quebra((0.0, 0.5), 1.2))
transicao_reg("estilhacar_suave", "Cacos menores e lentos, sem impacto: o quadro se desfaz em vidro. Mudança de assunto "
              "sem susto.", ["vidro-shimmer"], dur=0.6)(_quebra((0.5, 0.5), 0.6, "papel_2"))
transicao_reg("cacos_montam", "Cacos de vidro voam de fora e se encaixam formando a cena nova. Construção, 'montei', "
              "resultado.", ["vidro-shimmer", "acerto"], dur=0.6)(_monta((0.5, 0.45)))
transicao_reg("cacos_montam_lateral", "Os cacos da cena nova chegam pela esquerda e se montam em fila. Lista, item novo.",
              ["vidro-shimmer"], dur=0.6)(_monta((0.0, 0.5)))
