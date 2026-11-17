"""Letreiros: títulos e rótulos de texto em 18 tratamentos × 8 entradas = 144 estilos, todos com a paleta e as fontes
da marca ativa. No EDL: {"tipo": "letreiro", "estilo": "tarja_digita", "texto": "linha 1/linha 2", "na": …, "ate": …}.

Tratamento é o visual parado (tarja, contorno, marca-texto, etiqueta…); entrada é como ele chega (surge, digita,
palavra, desliza, escala, revela, gira, desfoca). `editor.py biblioteca listar titulos` mostra todos.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .estilos import fonte_estilo
from .graficos import pil2np
from .marca import CORES, PAPEIS_COR, ErroDeMarca
from .movimento import clamp01, ease_in, ease_out, ease_out_back, mola


def _c(papel, a=255):
    return tuple(int(v) for v in CORES[papel]) + (int(a),)


# tratamento: (descrição, fonte, cor do texto, extras)
TRATAMENTOS = {
    "tarja": ("Caixa clara justa no texto, texto escuro. O título mais legível sobre qualquer fundo.", "sans_forte", "marinho", {"caixa": "papel_2"}),
    "tarja_escura": ("Caixa escura da marca com texto claro. Sóbrio, institucional.", "sans_forte", "papel_2", {"caixa": "marinho"}),
    "tarja_destaque": ("Caixa na cor de destaque com texto escuro. Chamada forte, oferta.", "sans_forte", "marinho", {"caixa": "champanhe"}),
    "contorno": ("Só o contorno das letras, vazado, com sombra que o separa do fundo. Moderno, leve.", "sans_forte", "papel_2",
                 {"contorno": True, "sombra": True}),
    "sombra_longa": ("Texto com sombra longa na diagonal, estilo pôster.", "condensada", "papel_2", {"sombra_longa": "marinho"}),
    "sublinhado": ("Texto com um traço de destaque que se desenha por baixo.", "sans_forte", "papel_2", {"sublinha": "champanhe"}),
    "marca_texto": ("Marca-texto na cor de destaque passando atrás das palavras.", "sans_forte", "marinho", {"marca_texto": "champanhe"}),
    "etiqueta": ("Pílula arredondada, como tag de app.", "sans", "marinho", {"caixa": "papel_2", "raio": 1.0}),
    "colchetes": ("Texto entre colchetes grandes na cor de destaque.", "sans_forte", "papel_2", {"colchetes": "champanhe"}),
    "aspas": ("Citação com aspas grandes. Para frase dita por alguém.", "serifa_italica", "papel_2", {"aspas": "champanhe"}),
    "caixa_vazada": ("Moldura fina em volta do texto, sem preenchimento.", "sans", "papel_2", {"moldura": "champanhe"}),
    "duas_cores": ("Primeira linha na cor de destaque, as outras em claro.", "sans_forte", "papel_2", {"primeira": "champanhe"}),
    "serifa": ("Serifa elegante, sem caixa, com sombra suave. Editorial, revista.", "serifa", "papel_2", {"sombra": True}),
    "manuscrito": ("Letra de mão na cor de destaque. Pessoal, afetivo.", "manuscrita", "champanhe", {"sombra": True, "escala": 1.3}),
    "gigante": ("Condensada enorme em caixa alta, impacto.", "condensada", "papel_2", {"maiusculas": True, "escala": 1.5, "sombra": True}),
    "tecnico": ("Mono técnico com cursor piscando, estilo terminal.", "mono", "champanhe", {"caixa": "marinho", "cursor": True, "alfa_caixa": 225}),
    "fita": ("Fita adesiva inclinada com o texto, colagem.", "sans_forte", "marinho", {"caixa": "papel", "inclina": -4, "fita": True}),
    "vidro": ("Placa de vidro fosco translúcido com borda clara. Premium.", "sans", "papel_2", {"caixa": "marinho_2", "alfa_caixa": 150, "borda": "papel_2"}),
}

ENTRADAS = {
    "surge": "aparece subindo de leve",
    "digita": "é digitado letra por letra",
    "palavra": "entra palavra por palavra",
    "desliza": "desliza da esquerda revelado por uma máscara",
    "escala": "cresce com mola do centro",
    "revela": "é revelado de baixo para cima",
    "gira": "chega girando de leve e assenta",
    "desfoca": "entra do desfoque para o foco",
}

ESTILOS = {f"{t}_{e}": (t, e) for t in TRATAMENTOS for e in ENTRADAS}


def catalogo_letreiros():
    return [{"id": n, "descricao": f"{TRATAMENTOS[t][0]} O texto {ENTRADAS[e]}."} for n, (t, e) in ESTILOS.items()]


class Letreiro:
    def __init__(self, e, W, H):
        nome = e.get("estilo", "tarja_surge")
        if nome not in ESTILOS:
            raise ErroDeMarca(f"letreiro: estilo desconhecido {nome!r} (veja `editor.py biblioteca listar titulos`)")
        self.trat, self.ent = ESTILOS[nome]
        _d, fonte, cor_txt, self.x = TRATAMENTOS[self.trat]
        if e.get("cor"):
            if e["cor"] not in PAPEIS_COR:
                raise ErroDeMarca(f"cor precisa ser um papel da paleta ({', '.join(PAPEIS_COR)}), não {e['cor']!r}")
            cor_txt = e["cor"]
        txt = e.get("texto", "")
        if self.x.get("maiusculas"):
            txt = txt.upper()
        self.linhas = [x.strip() for x in txt.split("/") if x.strip()] or [" "]
        tam = int(W * e.get("tam", 0.06) * self.x.get("escala", 1.0))
        self.f = fonte_estilo(fonte, tam)
        self.cor_txt = cor_txt
        self.tam = tam
        self.total = sum(len(ln) for ln in self.linhas)
        self.palavras = sum(len(ln.split()) for ln in self.linhas)
        self._medir()
        self._final = None
        self._cache = {}

    # ───── layout ─────
    def _medir(self):
        f, x = self.f, self.x
        self.pad = (int(self.tam * 0.45), int(self.tam * 0.2)) if x.get("caixa") or x.get("moldura") else (int(self.tam * 0.1), 0)
        self.alt_linha = int(f.size * 1.28)
        self.larg = [int(f.getlength(ln)) for ln in self.linhas]
        extra_x = int(self.tam * 0.9) if x.get("colchetes") or x.get("aspas") else 0
        self.extra_x = extra_x
        sl = int(self.tam * 0.35) if x.get("sombra_longa") else 0
        self.sl = sl
        self.W = max(self.larg) + 2 * self.pad[0] + 2 * extra_x + sl + 24 + (int(self.tam * 0.6) if x.get("cursor") else 0)
        self.H = len(self.linhas) * (self.alt_linha + 2 * self.pad[1]) + sl + 24 + (int(self.tam * 0.25) if x.get("sublinha") else 0)

    def _desenhar(self, n_letras, p_extra=1.0):
        """Sprite com as n primeiras letras (o layout é o do texto inteiro). p_extra anima traços e marca-texto."""
        x = self.x
        im = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        resta = n_letras
        y = 12
        cx = self.W // 2 - self.sl // 2
        for k, (ln, lw) in enumerate(zip(self.linhas, self.larg)):
            bw, bh = lw + 2 * self.pad[0], self.alt_linha + 2 * self.pad[1] - (0 if x.get("caixa") else self.pad[1])
            x0 = cx - bw // 2
            raio = bh // 2 if x.get("raio") else int(self.tam * 0.12)
            n_vis = max(0, min(len(ln), resta))
            # na digitação a caixa cresce junto com o texto; linha que ainda não começou não tem caixa
            bw_vis = bw if n_vis >= len(ln) else int(self.f.getlength(ln[:n_vis])) + 2 * self.pad[0]
            if x.get("caixa") and n_vis:
                d.rounded_rectangle([x0, y, x0 + bw_vis, y + bh], min(raio, bw_vis // 2), fill=_c(x["caixa"], x.get("alfa_caixa", 255)),
                                    outline=_c(x["borda"], 160) if x.get("borda") else None, width=2)
            if x.get("moldura") and n_vis:
                d.rectangle([x0, y, x0 + bw_vis, y + bh], outline=_c(x["moldura"]), width=max(2, self.tam // 18))
            if x.get("marca_texto") and p_extra > 0:
                d.rectangle([x0, y + bh * 0.42, x0 + int(bw * p_extra), y + bh * 0.95], fill=_c(x["marca_texto"], 235))
            vis = ln[:max(0, resta)]
            resta -= len(ln)
            tx, ty = x0 + self.pad[0], y + (bh - self.f.size * 1.18) / 2
            cor_l = x["primeira"] if x.get("primeira") and k == 0 else self.cor_txt
            if vis:
                if x.get("sombra_longa"):
                    for s in range(self.sl, 0, -2):
                        d.text((tx + s, ty + s), vis, font=self.f, fill=_c(x["sombra_longa"]))
                if x.get("contorno"):
                    d.text((tx, ty), vis, font=self.f, fill=(0, 0, 0, 0), stroke_width=max(3, self.tam // 22), stroke_fill=_c(cor_l))
                else:
                    d.text((tx, ty), vis, font=self.f, fill=_c(cor_l))
            if x.get("sublinha") and k == len(self.linhas) - 1 and p_extra > 0:
                yy = y + bh + int(self.tam * 0.05)
                d.line([x0, yy, x0 + int(bw * p_extra), yy], fill=_c(x["sublinha"]), width=max(3, self.tam // 10))
            if x.get("cursor") and 0 <= resta < len(ln) + 1 and k == self._linha_do_cursor(n_letras):
                cxr = tx + int(self.f.getlength(vis)) + 4
                d.rectangle([cxr, ty + self.f.size * 0.2, cxr + self.tam * 0.45, ty + self.f.size * 1.15], fill=_c(self.cor_txt, 230))
            y += bh + (self.pad[1] if x.get("caixa") else 0)
        if x.get("colchetes"):
            c, esp = _c(x["colchetes"]), max(3, self.tam // 12)
            L = int(self.tam * 0.4)
            for xx, s in ((6, 1), (self.W - self.sl - 18, -1)):
                d.line([xx + s * L, 8, xx, 8, xx, y - 4, xx + s * L, y - 4], fill=c, width=esp, joint="curve")
        if x.get("aspas"):
            fa = fonte_estilo("serifa", int(self.tam * 2.2))
            d.text((2, -self.tam * 0.25), "“", font=fa, fill=_c(x["aspas"]))
        if x.get("fita"):
            im = im.rotate(x["inclina"], resample=Image.BICUBIC, expand=False)
        if x.get("sombra"):
            sb = Image.new("RGBA", im.size, (0, 0, 0, 0))
            alpha = im.getchannel("A").filter(ImageFilter.GaussianBlur(self.tam * 0.12))
            sb.putalpha(alpha.point(lambda v: int(v * 0.55)))
            base = Image.new("RGBA", im.size, (0, 0, 0, 0))
            base.alpha_composite(sb, (0, int(self.tam * 0.06)))
            base.alpha_composite(im)
            im = base
        return im

    def _linha_do_cursor(self, n):
        for k, ln in enumerate(self.linhas):
            if n <= len(ln):
                return k
            n -= len(ln)
        return len(self.linhas) - 1

    def _sprite(self, n, p_extra):
        chave = (n, round(p_extra, 2))
        if chave not in self._cache:
            if len(self._cache) > 64:
                self._cache.clear()
            self._cache[chave] = self._desenhar(n, p_extra)
        return self._cache[chave]

    # ───── animação ─────
    def render(self, dt, rest):
        e = self.ent
        p_extra = ease_out(clamp01((dt - 0.15) / 0.45))
        n = self.total
        if e == "digita":
            n = min(self.total, int(dt * 22) + 1)
            p_extra = ease_out(clamp01((dt - self.total / 22) / 0.4))
        elif e == "palavra":
            k = min(self.palavras, int(dt / 0.16) + 1)
            n = self._letras_ate_palavra(k)
        if self.x.get("cursor") and int(dt * 2.5) % 2 == 1 and n >= self.total:
            n = self.total + 1  # cursor pisca no fim (sem desenhar a letra extra)
        im = self._sprite(min(n, self.total + 1), p_extra)
        a = 1.0
        if e == "surge":
            p = ease_out(clamp01(dt / 0.35))
            im = _deslocar(im, 0, int((1 - p) * self.tam * 0.6))
            a = p
        elif e == "desliza":
            p = ease_out(clamp01(dt / 0.4))
            w = int(im.width * p)
            cort = Image.new("RGBA", im.size, (0, 0, 0, 0))
            if w > 0:
                cort.alpha_composite(im.crop((0, 0, w, im.height)), (0, 0))
            im = _deslocar(cort, int((1 - p) * self.tam * -0.8), 0)
        elif e == "escala":
            s = max(0.05, mola(clamp01(dt / 0.5)))
            im = _escalar(im, s)
            a = clamp01(dt / 0.15)
        elif e == "revela":
            p = ease_out(clamp01(dt / 0.45))
            h = int(im.height * p)
            cort = Image.new("RGBA", im.size, (0, 0, 0, 0))
            if h > 0:
                cort.alpha_composite(im.crop((0, im.height - h, im.width, im.height)), (0, im.height - h))
            im = cort
        elif e == "gira":
            p = clamp01(dt / 0.5)
            ang = (1 - ease_out_back(p, 1.6)) * 14
            if abs(ang) > 0.2:
                im = im.rotate(ang, resample=Image.BICUBIC, expand=False)
            a = clamp01(dt / 0.2)
        elif e == "desfoca":
            p = ease_out(clamp01(dt / 0.45))
            r = (1 - p) * self.tam * 0.35
            if r > 0.4:
                im = im.filter(ImageFilter.GaussianBlur(r))
            a = p
        a *= 1 - (ease_in(1 - rest / 0.22) if rest < 0.22 else 0.0)
        arr = pil2np(im)
        if a < 0.999:
            arr = arr.copy()
            arr[..., 3] = (arr[..., 3].astype(np.float32) * clamp01(a)).astype(np.uint8)
        return arr

    def _letras_ate_palavra(self, k):
        n = 0
        for ln in self.linhas:
            ws = ln.split(" ")
            for j, w in enumerate(ws):
                if k <= 0:
                    return n
                n += len(w) + (1 if j < len(ws) - 1 else 0)
                k -= 1
        return n


def _deslocar(im, dx, dy):
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.alpha_composite(im, (0, 0)) if dx == dy == 0 else out.paste(im, (dx, dy), im)
    return out


def _escalar(im, s):
    if abs(s - 1) < 0.01:
        return im
    w, h = max(1, int(im.width * s)), max(1, int(im.height * s))
    peq = im.resize((w, h), Image.BICUBIC)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ox, oy = (im.width - w) // 2, (im.height - h) // 2
    if w <= im.width and h <= im.height:
        out.alpha_composite(peq, (ox, oy))
    else:
        out = peq.crop((-ox, -oy, -ox + im.width, -oy + im.height))
    return out

