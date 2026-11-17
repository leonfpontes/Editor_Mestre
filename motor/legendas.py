"""Legenda palavra a palavra com a marcação na cor de destaque da marca.

Estilos ("estilo" em legendas):
- "marcada" (padrão): palavra atual com marcação na cor de destaque, contorno escuro.
- "limpa": 1 ou 2 palavras, branco quase puro, sem caixa e sem contorno, só uma sombra macia (tutorial em passos).
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .graficos import fonte, pil2np
from .marca import CORES
from .movimento import clamp01, ease_out, lerp, mola


class Legendas:
    """Legenda palavra a palavra: cada palavra surge com mola no instante em que é falada e a
    marcação champanhe desliza de uma palavra para a próxima."""

    def __init__(self, palavras, cfg, W, H, keep):
        self.cfg, self.W, self.H = cfg, W, H
        corr = {k.lower(): v for k, v in cfg.get("correcoes", {}).items()}
        enf = {e.lower().strip(".,!?") for e in cfg.get("enfase", [])}
        dentro = lambda t: any(a <= t < b for a, b in keep)
        ws = []
        for w in palavras:
            if not dentro((w["ini"] + w["fim"]) / 2):
                continue
            t = corr.get(w["t"].lower(), w["t"])
            if cfg.get("sem_pontuacao", True):
                t = t.rstrip(",.;:") if not t.endswith(("?", "!")) else t
            if t:
                ws.append(dict(w, t=t, orig=w["t"], enf=t.lower().strip(".,!?;:") in enf))
        n = cfg.get("palavras_por_bloco", 3)
        self.blocos, cur = [], []
        for i, w in enumerate(ws):
            cur.append(w)
            fim_frase = w["orig"][-1] in ".!?:,"
            pausa = i + 1 < len(ws) and ws[i + 1]["ini"] - w["fim"] > 0.4
            if len(cur) >= n or fim_frase or pausa or i == len(ws) - 1:
                self.blocos.append(cur)
                cur = []
        self.limpa = cfg.get("estilo") == "limpa"
        tam = cfg.get("tamanho", (64 if self.limpa else 76) if W < 1500 else 56)
        self.f = fonte("Bold" if self.limpa else "Black", tam)
        self.lay = {}

    def bloco_em(self, t):
        for i, b in enumerate(self.blocos):
            fim = self.blocos[i + 1][0]["ini"] if i + 1 < len(self.blocos) else b[-1]["fim"] + 0.5
            fim = min(fim, b[-1]["fim"] + 0.7)
            if b[0]["ini"] - 0.04 <= t < fim:
                return i
        return None

    def layout(self, i):
        if i in self.lay:
            return self.lay[i]
        b, f, gap = self.blocos[i], self.f, 20
        up = self.cfg.get("maiusculas")
        txt = [w["t"].upper() if up else w["t"] for w in b]
        larg = [f.getlength(x) for x in txt]
        linhas = [list(range(len(txt)))]
        if sum(larg) + gap * (len(txt) - 1) > self.W * 0.82 and len(txt) > 1:
            m = (len(txt) + 1) // 2
            linhas = [list(range(m)), list(range(m, len(txt)))]
        lh = int(f.size * 1.34)
        Wc = int(max(sum(larg[k] for k in L) + gap * (len(L) - 1) for L in linhas)) + 80
        Hc = lh * len(linhas) + 40
        pos = {}
        for li, L in enumerate(linhas):
            x = (Wc - (sum(larg[k] for k in L) + gap * (len(L) - 1))) / 2
            for k in L:
                pos[k] = (x, 18 + li * lh, larg[k])
                x += larg[k] + gap
        sprites = []
        for k, t in enumerate(txt):
            def spr(cor, stroke):
                im = Image.new("RGBA", (int(larg[k]) + 24, lh + 12), (0, 0, 0, 0))
                ImageDraw.Draw(im).text((12, 4), t, font=f, fill=cor, stroke_width=stroke, stroke_fill=CORES["marinho"])
                return im
            normal = spr(CORES["champanhe"] if b[k]["enf"] else (255, 255, 255), 7)
            sprites.append((normal, spr(CORES["marinho"], 0)))
        self.lay[i] = (Wc, Hc, pos, sprites, lh)
        return self.lay[i]

    def render(self, i, t):
        if self.limpa:
            return self.render_limpa(i, t)
        b = self.blocos[i]
        Wc, Hc, pos, sprites, lh = self.layout(i)
        im = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0))
        cur = max([k for k, w in enumerate(b) if w["ini"] - 0.03 <= t] or [0])
        # marcação desliza da palavra anterior para a atual
        pr = ease_out((t - b[cur]["ini"]) / 0.12)
        x, y, w = pos[cur]
        if cur > 0 and pos[cur - 1][1] == y:
            px, _, pw = pos[cur - 1]
            x, w = lerp(px, x, pr), lerp(pw, w, pr)
            esc = 1.0
        else:
            esc = 0.6 + 0.4 * clamp01(mola((t - b[cur]["ini"]) / 0.35))
        cx, cy = x + w / 2, y + lh / 2 + 2
        hw, hh = (w / 2 + 16) * esc, (lh / 2 + 2) * esc
        ImageDraw.Draw(im).rounded_rectangle([cx - hw, cy - hh, cx + hw, cy + hh], 10, fill=CORES["champanhe"] + (255,))
        for k, wd in enumerate(b):
            dt = t - wd["ini"]
            if dt < -0.03:
                continue
            p = clamp01(mola(max(dt, 0) / 0.32, 8, 13))
            sp = sprites[k][1] if k == cur else sprites[k][0]
            s = 0.55 + 0.45 * p
            if s < 0.995:
                sp = sp.resize((max(2, int(sp.width * s)), max(2, int(sp.height * s))), Image.BILINEAR)
            x, y, w = pos[k]
            dy = (1 - clamp01(p)) * 22
            im.alpha_composite(sp, (int(x + w / 2 - sp.width / 2), int(y + lh / 2 + 4 - sp.height / 2 + dy)))
        return pil2np(im)


    def render_limpa(self, i, t):
        """Palavras brancas com sombra macia; cada uma sobe 10 px e acende quando é falada. Sem marcação."""
        b = self.blocos[i]
        Wc, Hc, pos, _, lh = self.layout(i)
        txt = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0))
        d = ImageDraw.Draw(txt)
        up = self.cfg.get("maiusculas")
        for k, wd in enumerate(b):
            dt = t - wd["ini"]
            if dt < -0.03:
                continue
            p = clamp01(max(dt, 0) / 0.14)
            x, y, _ = pos[k]
            cor = CORES["champanhe"] if wd["enf"] else CORES["papel_2"]
            d.text((x + 12, y + 4 + (1 - p) * 10), wd["t"].upper() if up else wd["t"], font=self.f,
                   fill=tuple(cor) + (int(255 * (0.35 + 0.65 * p)),))
        a = np.array(txt)[..., 3]
        sombra = Image.fromarray(a).filter(ImageFilter.GaussianBlur(9))
        out = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0))
        camada = Image.new("RGBA", (Wc, Hc), tuple(CORES["marinho"]) + (0,))
        camada.putalpha(sombra.point(lambda v: int(v * 0.75)))
        out.alpha_composite(camada, (0, 4))
        out.alpha_composite(txt)
        return pil2np(out)
