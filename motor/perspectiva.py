"""Tela em perspectiva: uma gravação de tela (ou print) num plano 3D, com câmera que anda e profundidade de campo.

No EDL, num b-roll:

    {"tipo": "broll", "arquivo": "tela.mp4", "na": "esse aqui", "ate": "embaixo",
     "perspectiva": {"camera": [{"t": 0, "rx": 22, "ry": -18, "zoom": 1.25, "cx": 0.3, "cy": 0.3},
                                {"t": 1, "rx": 10, "ry": 12, "zoom": 1.6, "cx": 0.6, "cy": 0.55}],
                     "foco": 0.6, "luz": true}}

- camera: pontos-chave ao longo do b-roll (t de 0 a 1). rx/ry/rz em graus, zoom, e o ponto da tela que fica no
  centro do quadro (cx, cy de 0 a 1). Entre os pontos, a câmera anda com easing. Sem "camera", um passeio padrão.
- foco: 0 (tudo nítido) a 1 (profundidade bem rasa).
- luz: brilho quente desfocado (cor de destaque da marca), como reflexo de luminária no vidro.
"""
import math

import cv2
import numpy as np

from .marca import CORES
from .movimento import ease_in_out

PADRAO = [{"t": 0, "rx": 24, "ry": -20, "rz": -3, "zoom": 1.2, "cx": 0.35, "cy": 0.3},
          {"t": 0.5, "rx": 16, "ry": 6, "rz": 0, "zoom": 1.45, "cx": 0.5, "cy": 0.5},
          {"t": 1, "rx": 10, "ry": 16, "rz": 2, "zoom": 1.6, "cx": 0.62, "cy": 0.68}]
CHAVES = ("rx", "ry", "rz", "zoom", "cx", "cy")


def _bgr(rgb):
    return np.array((rgb[2], rgb[1], rgb[0]), np.float32)


def camera_em(pontos, p):
    """Interpola os pontos-chave da câmera no instante p (0..1)."""
    pts = sorted(pontos or PADRAO, key=lambda k: k.get("t", 0))
    base = {"rx": 0, "ry": 0, "rz": 0, "zoom": 1.0, "cx": 0.5, "cy": 0.5}
    if p <= pts[0].get("t", 0):
        return dict(base, **pts[0])
    for a, b in zip(pts, pts[1:]):
        ta, tb = a.get("t", 0), b.get("t", 1)
        if ta <= p <= tb:
            q = ease_in_out((p - ta) / max(tb - ta, 1e-6))
            return {k: dict(base, **a)[k] + (dict(base, **b)[k] - dict(base, **a)[k]) * q for k in CHAVES}
    return dict(base, **pts[-1])


class TelaPerspectiva:
    def __init__(self, cfg, W, H):
        self.cfg, self.W, self.H = cfg or {}, W, H
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.dist = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2)
        fundo = np.empty((H, W, 3), np.float32)
        luz = np.clip(1 - self.dist * 1.5, 0, 1)[..., None]
        fundo[:] = _bgr(CORES["marinho"]) * (1 - 0.4 * luz) + _bgr(CORES["marinho_2"]) * 0.4 * luz
        self.fundo = fundo.astype(np.uint8)
        self.luz = None
        if self.cfg.get("luz", True):
            d = np.sqrt(((xx - W * 0.28) / (W * 0.32)) ** 2 + ((yy - H * 0.3) / (H * 0.16)) ** 2)
            g = np.exp(-d ** 2 * 1.2)[..., None]
            self.luz = (g * (_bgr(CORES["champanhe"]) * 0.75 + _bgr(CORES["bronze"]) * 0.25)).astype(np.float32)

    def quadro(self, tela, p):
        """tela: imagem BGR da gravação; p: 0..1 ao longo do b-roll."""
        W, H = self.W, self.H
        c = camera_em(self.cfg.get("camera"), p)
        h0, w0 = tela.shape[:2]
        s = W * 0.95 * c["zoom"] / w0
        rx, ry, rz = (math.radians(c[k]) for k in ("rx", "ry", "rz"))
        Rx = np.array([[1, 0, 0], [0, math.cos(rx), -math.sin(rx)], [0, math.sin(rx), math.cos(rx)]])
        Ry = np.array([[math.cos(ry), 0, math.sin(ry)], [0, 1, 0], [-math.sin(ry), 0, math.cos(ry)]])
        Rz = np.array([[math.cos(rz), -math.sin(rz), 0], [math.sin(rz), math.cos(rz), 0], [0, 0, 1]])
        R = Rz @ Ry @ Rx
        D = W * 1.5
        src, dst = [], []
        for u, v in ((0, 0), (w0, 0), (w0, h0), (0, h0)):
            P = R @ np.array([(u - c["cx"] * w0) * s, (v - c["cy"] * h0) * s, 0.0])
            k = D / max(D + P[2], 1.0)
            src.append((u, v))
            dst.append((W / 2 + P[0] * k, H * 0.48 + P[1] * k))
        M = cv2.getPerspectiveTransform(np.float32(src), np.float32(dst))
        out = cv2.warpPerspective(tela, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_TRANSPARENT,
                                  dst=self.fundo.copy())
        mask = cv2.warpPerspective(np.full((h0, w0), 255, np.uint8), M, (W, H), flags=cv2.INTER_LINEAR)
        borda = cv2.GaussianBlur(mask, (0, 0), 30).astype(np.float32)[..., None] / 255
        sombra = (1 - 0.55 * np.clip(borda - mask[..., None] / 255, 0, 1))
        out = (out.astype(np.float32) * sombra).astype(np.uint8)
        foco = float(self.cfg.get("foco", 0.6))
        if foco > 0:
            pq = cv2.resize(out, (W // 3, H // 3))
            borrado = cv2.resize(cv2.GaussianBlur(pq, (0, 0), 1 + 3 * foco), (W, H))
            m = np.clip((self.dist - 0.2) / (0.5 - 0.2 * foco), 0, 1)[..., None]
            out = (out * (1 - m) + borrado * m).astype(np.uint8)
        if self.luz is not None:
            f = out.astype(np.float32)
            out = (255 - (255 - f) * (255 - self.luz * (0.85 + 0.15 * math.sin(p * 6))) / 255).clip(0, 255).astype(np.uint8)
        return out


def bolha(base, rosto_q, cfg, W, H, rosto=None):
    """Cola o rosto (quadro da câmera já enquadrado) numa bolha circular com anel na cor de destaque.
    rosto: (cx, cy, altura) do rosto no quadro da câmera, para centralizar a bolha nele."""
    cfg = cfg if isinstance(cfg, dict) else {}
    r = int(W * cfg.get("raio", 0.16))
    cx, cy = int(W * cfg.get("x", 0.22)), int(H * cfg.get("y", 0.78))
    fx, fy, fh = rosto if rosto else (W / 2, H * 0.36, H * 0.18)
    lado = int(np.clip(fh * 2.2, r * 2, min(W, H)))
    y0 = int(np.clip(fy - lado * 0.48, 0, H - lado))
    x0 = int(np.clip(fx - lado / 2, 0, W - lado))
    rec = cv2.resize(rosto_q[y0:y0 + lado, x0:x0 + lado], (2 * r, 2 * r), interpolation=cv2.INTER_AREA)
    m = np.zeros((2 * r, 2 * r), np.uint8)
    cv2.circle(m, (r, r), r - 1, 255, -1, cv2.LINE_AA)
    a = m.astype(np.float32)[..., None] / 255
    ya, xa = cy - r, cx - r
    ya0, xa0 = max(ya, 0), max(xa, 0)
    ya1, xa1 = min(ya + 2 * r, H), min(xa + 2 * r, W)
    if ya0 >= ya1 or xa0 >= xa1:
        return base
    sub = base[ya0:ya1, xa0:xa1].astype(np.float32)
    rr, aa = rec[ya0 - ya:ya1 - ya, xa0 - xa:xa1 - xa], a[ya0 - ya:ya1 - ya, xa0 - xa:xa1 - xa]
    base[ya0:ya1, xa0:xa1] = (sub * (1 - aa) + rr * aa).astype(np.uint8)
    c = CORES["champanhe"]
    cv2.circle(base, (cx, cy), r + 3, (int(c[2]), int(c[1]), int(c[0])), max(5, r // 18), cv2.LINE_AA)
    return base
