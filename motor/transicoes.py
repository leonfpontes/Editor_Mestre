"""Biblioteca de transições além das clássicas de `camera.transicao`: cortinas, íris de formas, persianas, relógio,
movimentos, mergulhos de cor, luz, formas da marca que cobrem a tela e cortes digitais.

Cada transição é `f(a, b, p, W, H)`: `a` é o último quadro do trecho anterior, `b` o novo, `p` vai de 0 a 1. Registro em
`TRANSICOES` com descrição e som padrão (ids da biblioteca de sons). Regras: cor só pela paleta da marca, nada de acaso
(o mesmo EDL dá sempre o mesmo quadro) e nenhuma borda esticada ou vazia: o que sobra da tela é sempre o outro quadro.
"""
import math

import cv2
import numpy as np

from .graficos import cobrir
from .marca import CORES
from .movimento import clamp01, ease_in, ease_in_out, ease_out
from .util import bgr

TAU = 2 * math.pi
TRANSICOES = {}  # nome → (função, descrição, [sons])
SO_FORA_DA_FE = " Evite em vídeo de fé (GiraHub)."


def transicao_reg(nome, descricao, sons=None):
    def deco(fn):
        TRANSICOES[nome] = (fn, descricao, list(sons or []))
        return fn
    return deco


def _cor(papel):
    return np.array(bgr(CORES[papel]), np.float32)


_GRADE = {}


def _grade(W, H, k=4):
    """x, y normalizados (0 a 1) numa grade reduzida, e o tamanho dela (cache por resolução)."""
    if (W, H, k) not in _GRADE:
        w, h = max(2, W // k), max(2, H // k)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        _GRADE[(W, H, k)] = (xx / (w - 1), yy / (h - 1))
    return _GRADE[(W, H, k)]


def _misturar(a, b, m, W, H):
    """m (grade reduzida, 1 = quadro novo) sobe para o quadro e mistura a com b."""
    m = cv2.resize(m.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    return (a.astype(np.float32) * (1 - m) + b.astype(np.float32) * m).astype(np.uint8)


def _degrau(v, borda):
    """0→1 suave em volta de 0 (largura `borda`)."""
    return np.clip(0.5 + v / max(borda, 1e-4), 0, 1)


def _com_faixa(out, m, W, H, papel="champanhe", larg=0.035):
    """Pinta uma faixa da cor da marca na fronteira da máscara (onde m está perto de 0,5)."""
    f = np.clip(1 - np.abs(m - 0.5) / larg * 0.5, 0, 1) ** 2
    f = cv2.resize(f.astype(np.float32), (W, H))[..., None]
    return (out.astype(np.float32) * (1 - f) + _cor(papel) * f).astype(np.uint8)


# ───────────────────────────── 1. cortinas (wipe) em 8 direções, suave ou com faixa ─────────────────────────────
DIRECOES = {"direita": (1, 0, "da esquerda para a direita"), "esquerda": (-1, 0, "da direita para a esquerda"),
            "baixo": (0, 1, "de cima para baixo"), "cima": (0, -1, "de baixo para cima"),
            "diag_sd": (1, 1, "do canto superior esquerdo para o inferior direito"),
            "diag_se": (-1, 1, "do canto superior direito para o inferior esquerdo"),
            "diag_id": (1, -1, "do canto inferior esquerdo para o superior direito"),
            "diag_ie": (-1, -1, "do canto inferior direito para o superior esquerdo")}


def _cortina(dx, dy, faixa):
    def fn(a, b, p, W, H):
        xx, yy = _grade(W, H)
        n = abs(dx) + abs(dy)
        u = ((xx if dx > 0 else 1 - xx) * abs(dx) + (yy if dy > 0 else 1 - yy) * abs(dy)) / n
        e = ease_in_out(p)
        m = _degrau((e * 1.2 - 0.1) - u, 0.06 if not faixa else 0.01)
        out = _misturar(a, b, m, W, H)
        return _com_faixa(out, m, W, H) if faixa and 0.02 < p < 0.98 else out
    return fn


for _d, (_dx, _dy, _dd) in DIRECOES.items():
    transicao_reg(f"cortina_{_d}", f"Cortina suave que passa {_dd}. Troca limpa de assunto.", ["deslizar"])(_cortina(_dx, _dy, False))
    transicao_reg(f"cortina_faixa_{_d}", f"Cortina com uma faixa dourada da marca na borda, passando {_dd}.",
                  ["whoosh-suave", "deslizar"])(_cortina(_dx, _dy, True))


# ───────────────────────────── 2. íris de formas (abre e fecha) ─────────────────────────────
def _dist_forma(forma, xx, yy, ah):
    """Distância 'de forma' ao centro, normalizada para a forma caber no quadro com r = 1."""
    x, y = (xx - 0.5) * 2, (yy - 0.5) * 2 * ah
    if forma == "circulo":
        return np.hypot(x, y)
    if forma == "quadrado":
        return np.maximum(np.abs(x), np.abs(y))
    if forma == "losango":
        return (np.abs(x) + np.abs(y)) / 1.0
    if forma == "hexagono":
        return np.maximum(np.abs(x) * 0.866 + np.abs(y) * 0.5, np.abs(y))
    ang = np.arctan2(y, x)
    r = np.hypot(x, y)
    if forma == "estrela":
        k = 0.5 + 0.5 * np.cos(5 * (ang + math.pi / 2))
        return r / (0.55 + 0.45 * k)
    if forma == "triangulo":
        return np.maximum.reduce([y * 1.0, -y * 0.5 + x * 0.866, -y * 0.5 - x * 0.866]) * 2
    if forma == "coracao":  # raio do contorno do coração em cada ângulo (forma estrelada a partir do centro)
        t = np.linspace(0, TAU, 720)
        hx, hy = 16 * np.sin(t) ** 3 / 17, -(13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)) / 17 + 0.1
        ha, hr = np.arctan2(hy, hx), np.hypot(hx, hy)
        o = np.argsort(ha)
        rh = np.interp(ang - 0.0, ha[o], hr[o], period=TAU)
        return np.hypot(x, y - 0.1 * 0) / np.maximum(rh, 0.05)
    return np.hypot(x, y)


FORMAS_IRIS = {"circulo": "círculo", "quadrado": "quadrado", "losango": "losango", "hexagono": "hexágono", "estrela": "estrela",
               "triangulo": "triângulo", "coracao": "coração"}


def _iris(forma, abre):
    cache = {}

    def fn(a, b, p, W, H):
        if (W, H) not in cache:
            xx, yy = _grade(W, H)
            d = _dist_forma(forma, xx, yy, H / W)
            cache[(W, H)] = d / np.percentile(d, 99.5)
        d = cache[(W, H)]
        e = ease_in_out(p)
        if abre:  # o quadro novo nasce do centro
            m = _degrau(e * 1.15 - d, 0.03)
        else:  # o antigo encolhe para o centro e some
            m = 1 - _degrau((1 - e) * 1.15 - d, 0.03)
        return _misturar(a, b, m, W, H)
    return fn


for _f, _fd in FORMAS_IRIS.items():
    transicao_reg(f"iris_{_f}_abre", f"Íris em forma de {_fd} que abre do centro mostrando a cena nova.", ["whoosh-suave"])(_iris(_f, True))
    transicao_reg(f"iris_{_f}_fecha", f"Íris em forma de {_fd} que fecha a cena antiga no centro.", ["whoosh-curto"])(_iris(_f, False))


# ───────────────────────────── 3. persianas, xadrez, relógio, dissoluções ─────────────────────────────
def _persiana(eixo, n, escalonada=False):
    def fn(a, b, p, W, H):
        xx, yy = _grade(W, H)
        u = yy if eixo == "h" else xx
        v = xx if eixo == "h" else yy
        e = ease_in_out(p)
        atraso = (v * 0.4) if escalonada else 0
        local = (u * n) % 1
        prog = np.clip((e * (1.4 if escalonada else 1.0) - atraso), 0, 1)
        return _misturar(a, b, _degrau(prog - local, 0.08), W, H)
    return fn


transicao_reg("persiana_horizontal", "Persiana de 8 lâminas horizontais que se fecham na cena nova.", ["rolagem"])(_persiana("h", 8))
transicao_reg("persiana_vertical", "Persiana de 8 lâminas verticais.", ["rolagem"])(_persiana("v", 8))
transicao_reg("persiana_fina", "Persiana de 20 lâminas finas horizontais, como um scanner.", ["rolagem"])(_persiana("h", 20))
transicao_reg("persiana_escalonada", "Persiana horizontal que fecha em onda de um lado ao outro.", ["deslizar"])(_persiana("h", 10, True))
transicao_reg("colunas_escalonadas", "Colunas verticais que caem uma depois da outra.", ["deslizar"])(_persiana("v", 6, True))


@transicao_reg("xadrez", "Quadradinhos em xadrez que viram a cena nova, em duas levas.", ["clique"])
def _xadrez(a, b, p, W, H):
    xx, yy = _grade(W, H)
    n = 6
    i, j = np.floor(xx * n), np.floor(yy * n * H / W)
    atraso = ((i + j) % 2) * 0.45 + (i + j) / (2 * n * H / W + n) * 0.25
    return _misturar(a, b, np.clip((p - atraso) / 0.3, 0, 1), W, H)


@transicao_reg("mosaico", "A tela se divide em blocos que trocam em ordem fixa embaralhada. Tecnologia, dados.", ["teclado"])
def _mosaico(a, b, p, W, H):
    xx, yy = _grade(W, H)
    n = 8
    i, j = np.floor(xx * n * 0.999), np.floor(yy * n * H / W)
    ordem = np.sin(i * 12.9898 + j * 78.233) * 43758.5453 % 1  # embaralhado, mas fixo
    return _misturar(a, b, (p * 1.3 - np.abs(ordem) > 0).astype(np.float32), W, H)


def _relogio(horario):
    def fn(a, b, p, W, H):
        xx, yy = _grade(W, H)
        ang = (np.arctan2((xx - 0.5), -(yy - 0.5) * H / W) / TAU) % 1
        if not horario:
            ang = 1 - ang
        return _misturar(a, b, _degrau(ease_in_out(p) * 1.02 - ang, 0.01), W, H)
    return fn


transicao_reg("relogio", "Ponteiro de relógio que varre a tela no sentido horário. Passagem de tempo.", ["tique"])(_relogio(True))
transicao_reg("relogio_anti", "Relógio no sentido anti-horário. Voltar no tempo, lembrar.", ["reverso"])(_relogio(False))


@transicao_reg("espiral", "A cena nova entra numa espiral a partir do centro.", ["whoosh-giro"])
def _espiral(a, b, p, W, H):
    xx, yy = _grade(W, H)
    x, y = xx - 0.5, (yy - 0.5) * H / W
    r = np.hypot(x, y) / 0.9
    ang = (np.arctan2(y, x) / TAU) % 1
    return _misturar(a, b, _degrau(ease_in_out(p) * 2.2 - (r + ang * 0.25) * 1.6, 0.05), W, H)


def _ruido_fixo(W, H, escala, semente):
    r = np.random.default_rng(semente)
    w, h = max(2, W // escala), max(2, H // escala)
    n = r.random((h, w)).astype(np.float32)
    return n


_RUIDOS = {}


def _ruido(W, H, tipo):
    if (W, H, tipo) not in _RUIDOS:
        if tipo == "pixel":
            n = _ruido_fixo(W, H, max(4, W // 60), 11)
            n = cv2.resize(n, (W // 4, H // 4), interpolation=cv2.INTER_NEAREST)
        else:
            n = sum(cv2.resize(_ruido_fixo(W, H, s, 7 + s), (W // 4, H // 4), interpolation=cv2.INTER_CUBIC) * w
                    for s, w in ((W // 6, 0.55), (W // 18, 0.3), (W // 50, 0.15)))
            n = (n - n.min()) / (np.ptp(n) + 1e-6)
        _RUIDOS[(W, H, tipo)] = n
    return _RUIDOS[(W, H, tipo)]


@transicao_reg("dissolver_pixels", "Dissolve em pixels grandes que trocam aos poucos. Digital, retrô.", ["teclado"])
def _diss_pix(a, b, p, W, H):
    return _misturar(a, b, (_ruido(W, H, "pixel") < ease_in_out(p)).astype(np.float32), W, H)


@transicao_reg("dissolver_nuvem", "Dissolve em manchas como nuvem ou fumaça. Sonho, memória.", ["whoosh-sopro"])
def _diss_nuvem(a, b, p, W, H):
    return _misturar(a, b, _degrau(ease_in_out(p) * 1.2 - 0.1 - _ruido(W, H, "nuvem"), 0.08), W, H)


@transicao_reg("queimar", "A cena antiga queima como papel, com borda incandescente na cor quente da marca.", ["papel-rasgo"])
def _queimar(a, b, p, W, H):
    n = _ruido(W, H, "nuvem")
    v = ease_in_out(p) * 1.25 - 0.12 - n
    m = _degrau(v, 0.02)
    out = _misturar(a, b, m, W, H)
    brasa = np.clip(1 - np.abs(v - 0.02) / 0.04, 0, 1) ** 2
    brasa = cv2.resize(brasa.astype(np.float32), (W, H))[..., None]
    out = out.astype(np.float32) * (1 - brasa) + (_cor("bronze") * 0.6 + 255 * 0.4) * brasa
    return np.clip(out, 0, 255).astype(np.uint8)


@transicao_reg("tinta", "Mancha de tinta que se espalha do centro e engole a tela. Arte, criatividade.", ["pop-bolha"])
def _tinta(a, b, p, W, H):
    xx, yy = _grade(W, H)
    d = np.hypot(xx - 0.5, (yy - 0.5) * H / W) / 1.1 + (_ruido(W, H, "nuvem") - 0.5) * 0.35
    return _misturar(a, b, _degrau(ease_in(p) * 1.3 - d, 0.02), W, H)


# ───────────────────────────── 4. portas e divisões ─────────────────────────────
@transicao_reg("portas_abrem", "A cena antiga se abre ao meio como duas portas, revelando a nova atrás.", ["deslizar"])
def _portas_abrem(a, b, p, W, H):
    e = ease_in_out(p)
    out = b.copy()
    off = int(e * W / 2)
    meio = W // 2
    if meio - off > 0:
        out[:, :meio - off] = a[:, off:meio]
        out[:, meio + off:] = a[:, meio:W - off]
    return out


@transicao_reg("portas_fecham", "A cena nova entra pelos dois lados e se fecha no meio, como portas.", ["deslizar"])
def _portas_fecham(a, b, p, W, H):
    e = ease_in_out(p)
    out = a.copy()
    off = int(e * W / 2)
    meio = W // 2
    if off > 0:
        out[:, :off] = b[:, meio - off:meio]
        out[:, W - off:] = b[:, meio:meio + off]
    return out


@transicao_reg("portas_verticais", "A cena antiga se abre para cima e para baixo, como uma boca, revelando a nova.", ["deslizar"])
def _portas_v(a, b, p, W, H):
    e = ease_in_out(p)
    out = b.copy()
    off = int(e * H / 2)
    meio = H // 2
    if meio - off > 0:
        out[:meio - off] = a[off:meio]
        out[meio + off:] = a[meio:H - off]
    return out


@transicao_reg("quatro_cantos", "A cena antiga se parte em quatro e cada parte sai por um canto.", ["whoosh-ar"])
def _quatro(a, b, p, W, H):
    e = ease_in(p)
    out = b.copy()
    mx, my = W // 2, H // 2
    ox, oy = int(e * mx), int(e * my)
    if ox < mx and oy < my:
        out[:my - oy, :mx - ox] = a[oy:my, ox:mx]
        out[:my - oy, mx + ox:] = a[oy:my, mx:W - ox]
        out[my + oy:, :mx - ox] = a[my:H - oy, ox:mx]
        out[my + oy:, mx + ox:] = a[my:H - oy, mx:W - ox]
    return out


# ───────────────────────────── 5. movimento: empurrar, cobrir, revelar ─────────────────────────────
def _deslocar(f, dx, dy, W, H):
    """Recorta f deslocado de (dx, dy) pixels. Devolve o quadro e a máscara do que ficou visível."""
    out = np.zeros_like(f)
    m = np.zeros((H, W), bool)
    x0, x1 = max(0, dx), min(W, W + dx)
    y0, y1 = max(0, dy), min(H, H + dy)
    if x0 < x1 and y0 < y1:
        out[y0:y1, x0:x1] = f[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
        m[y0:y1, x0:x1] = True
    return out, m


VETORES = {"esquerda": (-1, 0), "direita": (1, 0), "cima": (0, -1), "baixo": (0, 1)}


def _mover(modo, vx, vy):
    def fn(a, b, p, W, H):
        e = ease_in_out(p)
        vel = math.sin(math.pi * p)
        if modo == "empurrar":
            fa, _ = _deslocar(a, int(vx * e * W), int(vy * e * H), W, H)
            fb, mb = _deslocar(b, int(vx * (e - 1) * W), int(vy * (e - 1) * H), W, H)
            out = np.where(mb[..., None], fb, fa)
        elif modo == "cobrir":  # o novo desliza por cima do antigo, que fica parado e escurece um pouco
            fb, mb = _deslocar(b, int(vx * (e - 1) * W), int(vy * (e - 1) * H), W, H)
            fundo = (a.astype(np.float32) * (1 - 0.35 * e)).astype(np.uint8)
            out = np.where(mb[..., None], fb, fundo)
        else:  # revelar: o antigo sai e mostra o novo parado atrás
            fa, ma = _deslocar(a, int(vx * e * W), int(vy * e * H), W, H)
            fundo = (b.astype(np.float32) * (0.65 + 0.35 * e)).astype(np.uint8)
            out = np.where(ma[..., None], fa, fundo)
        k = int(4 + 60 * vel)
        if k > 2:
            out = cv2.blur(out, (k, 1) if vx else (1, k))
        return out
    return fn


_NOMES_DIR = {"esquerda": "para a esquerda", "direita": "para a direita", "cima": "para cima", "baixo": "para baixo"}
for _d, (_vx, _vy) in VETORES.items():
    if _d != "esquerda":  # empurrar para a esquerda é o "push" clássico
        transicao_reg(f"empurrar_{_d}", f"Empurra a cena antiga {_NOMES_DIR[_d]}, a nova vem colada.", ["whoosh-ar"])(_mover("empurrar", _vx, _vy))
    transicao_reg(f"cobrir_{_d}", f"A cena nova desliza {_NOMES_DIR[_d]} por cima da antiga, que escurece.", ["deslizar"])(_mover("cobrir", _vx, _vy))
    transicao_reg(f"revelar_{_d}", f"A cena antiga sai {_NOMES_DIR[_d]} e revela a nova, parada atrás.", ["whoosh-suave"])(_mover("revelar", _vx, _vy))


@transicao_reg("chicote_vertical", "Chicote rápido para cima com borrão de movimento. Corte com energia.", ["whoosh-rapido"])
def _chicote_v(a, b, p, W, H):
    out = _mover("empurrar", 0, -1)(a, b, p, W, H)
    k = int(6 + 160 * math.sin(math.pi * p))
    return cv2.blur(out, (1, k))


@transicao_reg("chicote_diagonal", "Chicote rápido com borrão de movimento na diagonal. Energia, virada.", ["whoosh-rapido"])
def _chicote_d(a, b, p, W, H):
    out = _mover("empurrar", -1, 0)(a, b, p, W, H)
    k = int(6 + 120 * math.sin(math.pi * p))
    ker = np.zeros((k, k), np.float32)
    cv2.line(ker, (0, k // 4), (k - 1, k - 1 - k // 4), 1.0, 1)
    return cv2.filter2D(out, -1, ker / ker.sum(), borderType=cv2.BORDER_REFLECT)


# ───────────────────────────── 6. zoom, giro e escala ─────────────────────────────
@transicao_reg("zoom_saida", "A cena antiga se afasta (zoom out) e a nova chega de perto. Abrir o assunto.", ["whoosh-profundo"])
def _zoom_saida(a, b, p, W, H):
    if p < 0.5:
        q = ease_in(p / 0.5)
        f, k = cobrir(a, W, H, 1.6 - 0.6 * (1 - q)), int(1 + 26 * q) | 1
    else:
        q = 1 - ease_out((p - 0.5) / 0.5)
        f, k = cobrir(b, W, H, 1 + 0.5 * q), int(1 + 26 * q) | 1
    return cv2.GaussianBlur(f, (k, k), 0)


def _girar_cheio(f, graus, W, H, zoom=1.0):
    """Gira o quadro com zoom suficiente para os cantos nunca aparecerem."""
    th = math.radians(abs(graus) % 180)
    cobre = abs(math.cos(th)) + abs(math.sin(th)) * max(W / H, H / W)
    M = cv2.getRotationMatrix2D((W / 2, H / 2), graus, cobre * zoom)
    return cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def _girar(sentido):
    def fn(a, b, p, W, H):
        e = ease_in_out(p)
        g = sentido * 180 * e
        f = a if e < 0.5 else b
        out = _girar_cheio(f, g if e < 0.5 else g - sentido * 180, W, H, 1 + 0.25 * math.sin(math.pi * p))
        k = int(1 + 24 * math.sin(math.pi * p)) | 1
        return cv2.GaussianBlur(out, (k, k), 0)
    return fn


transicao_reg("girar_horario", "A tela gira no sentido horário com zoom e borrão (sem cantos vazios). Reviravolta.", ["whoosh-giro"])(_girar(-1))
transicao_reg("girar_anti", "A tela gira no sentido anti-horário com zoom e borrão.", ["whoosh-giro"])(_girar(1))


@transicao_reg("zoom_giro", "Zoom para dentro girando de leve, e a cena nova sai do giro. Entrar no assunto.", ["whoosh-giro"])
def _zoom_giro(a, b, p, W, H):
    if p < 0.5:
        q = ease_in(p / 0.5)
        out = _girar_cheio(a, -25 * q, W, H, 1 + 0.6 * q)
    else:
        q = 1 - ease_out((p - 0.5) / 0.5)
        out = _girar_cheio(b, 25 * q, W, H, 1 + 0.4 * q)
    k = int(1 + 28 * q) | 1
    return cv2.GaussianBlur(out, (k, k), 0)


@transicao_reg("zoom_cruzado", "Zoom com borrão radial nos dois quadros ao mesmo tempo. Impacto, velocidade.", ["whoosh-profundo"])
def _zoom_cruzado(a, b, p, W, H):
    e = ease_in_out(p)
    f = cv2.addWeighted(cobrir(a, W, H, 1 + 0.5 * e), 1 - e, cobrir(b, W, H, 1.5 - 0.5 * e), e, 0)
    q = math.sin(math.pi * p)
    acc = f.astype(np.float32)
    for k in range(1, 5):  # borrão radial: média de cópias com zoom crescente
        acc += cobrir(f, W, H, 1 + 0.03 * k * q).astype(np.float32)
    return (acc / 5).astype(np.uint8)


@transicao_reg("cartao_encolhe", "A cena antiga vira um cartão que encolhe e sai pelo alto, sobre a nova.", ["whoosh-suave"])
def _cartao(a, b, p, W, H):
    e = ease_in_out(p)
    s = 1 - 0.55 * e
    out = (b.astype(np.float32) * (0.6 + 0.4 * e)).astype(np.uint8)
    w, h = max(2, int(W * s)), max(2, int(H * s))
    peq = cv2.resize(a, (w, h), interpolation=cv2.INTER_AREA)
    x0 = (W - w) // 2
    y0 = int((H - h) / 2 - e * e * H * 0.9)
    ya, yb = max(0, y0), min(H, y0 + h)
    if yb > ya:
        sombra = int(W * 0.015)
        sy0, sy1 = max(0, ya + sombra), min(H, yb + sombra)
        out[sy0:sy1, x0 + sombra:x0 + w + sombra] = (out[sy0:sy1, x0 + sombra:x0 + w + sombra] * 0.6).astype(np.uint8)
        out[ya:yb, x0:x0 + w] = peq[ya - y0:yb - y0]
    return out


@transicao_reg("cartao_chega", "A cena nova chega como cartão de baixo para cima e cresce até ocupar a tela.", ["ui-sobe"])
def _cartao_chega(a, b, p, W, H):
    return _cartao(b, a, 1 - p, W, H)


@transicao_reg("virar_vertical", "Giro 3D no eixo horizontal: a cena vira para cima como uma placa.", ["whoosh-giro"])
def _virar_v(a, b, p, W, H):
    from .camera import _giro
    return cv2.rotate(_giro(cv2.rotate(a, cv2.ROTATE_90_CLOCKWISE), cv2.rotate(b, cv2.ROTATE_90_CLOCKWISE), p, H, W),
                      cv2.ROTATE_90_COUNTERCLOCKWISE)


# ───────────────────────────── 7. mergulhos de cor, luz e foco ─────────────────────────────
def _mergulho(papel, preto=False):
    def fn(a, b, p, W, H):
        base = a if p < 0.5 else b
        q = 1 - abs(p - 0.5) * 2
        q = ease_in(q) if p < 0.5 else ease_out(q)
        cor = np.zeros(3, np.float32) if preto else _cor(papel)
        return (base.astype(np.float32) * (1 - q) + cor * q).astype(np.uint8)
    return fn


transicao_reg("mergulho_preto", "A cena escurece até o preto e a nova clareia. Fim de capítulo, passagem de tempo.", ["whoosh-lento"])(
    _mergulho(None, True))
transicao_reg("mergulho_marinho", "Mergulho na cor escura da marca e volta. Elegante, troca de bloco.", ["whoosh-sopro"])(_mergulho("marinho"))
transicao_reg("mergulho_champanhe", "Mergulho na cor de destaque da marca. Leve, celebração.", ["brilho"])(_mergulho("champanhe"))
transicao_reg("mergulho_papel", "Mergulho no claro (papel) da marca. Recomeço, página nova.", ["pagina"])(_mergulho("papel"))


@transicao_reg("fusao_desfocada", "Fusão em que as duas cenas desfocam no meio. Sonho, lembrança, tempo.", ["whoosh-sopro"])
def _fusao_desf(a, b, p, W, H):
    e = ease_in_out(p)
    f = cv2.addWeighted(a, 1 - e, b, e, 0)
    k = int(1 + W * 0.05 * math.sin(math.pi * p)) | 1
    return cv2.GaussianBlur(f, (k, k), 0)


@transicao_reg("fusao_luminosa", "Fusão pela luz: as partes claras da cena nova aparecem primeiro. Poético.", ["whoosh-sopro"])
def _fusao_luma(a, b, p, W, H):
    lum = cv2.resize(cv2.cvtColor(b, cv2.COLOR_BGR2GRAY), (W // 4, H // 4)).astype(np.float32) / 255
    return _misturar(a, b, _degrau(ease_in_out(p) * 1.4 - (1 - lum) * 1.0 - 0.2, 0.25), W, H)


@transicao_reg("fusao_sombria", "Fusão pela sombra: as partes escuras da cena nova chegam primeiro. Suspense.", ["whoosh-lento"])
def _fusao_sombra(a, b, p, W, H):
    lum = cv2.resize(cv2.cvtColor(b, cv2.COLOR_BGR2GRAY), (W // 4, H // 4)).astype(np.float32) / 255
    return _misturar(a, b, _degrau(ease_in_out(p) * 1.4 - lum - 0.2, 0.25), W, H)


def _vazamento(ox, oy):
    def fn(a, b, p, W, H):
        base = a if p < 0.5 else b
        q = 1 - abs(p - 0.5) * 2
        xx, yy = _grade(W, H, 6)
        d = np.hypot(xx - ox, (yy - oy) * H / W)
        g = np.exp(-(d / (0.25 + 1.0 * q)) ** 2) * q
        g = cv2.resize(g.astype(np.float32), (W, H))[..., None]
        cam = _cor("champanhe") * g * 1.1 + _cor("bronze") * g * 0.3
        f = base.astype(np.float32)
        out = 255 - (255 - f) * (255 - np.clip(cam, 0, 255)) / 255
        return np.clip(out, 0, 255).astype(np.uint8)
    return fn


for _o, (_ox, _oy, _od) in {"esquerda": (0.0, 0.5, "da esquerda"), "direita": (1.0, 0.5, "da direita"), "topo": (0.5, 0.0, "do alto"),
                            "canto": (1.0, 0.0, "do canto")}.items():
    transicao_reg(f"vazamento_{_o}", f"Rajada de luz dourada vinda {_od} que lava a tela na troca. Emoção, memória.",
                  ["whoosh-sopro", "brilho"])(_vazamento(_ox, _oy))


@transicao_reg("flash_duplo", "Dois flashes rápidos claros na troca, como câmera fotográfica.", ["clique"])
def _flash_duplo(a, b, p, W, H):
    base = a if p < 0.5 else b
    lum = max(math.exp(-((p - 0.35) / 0.07) ** 2), math.exp(-((p - 0.6) / 0.07) ** 2))
    return cv2.addWeighted(base, 1 - 0.85 * lum, np.full_like(base, bgr(CORES["papel_2"])), 0.85 * lum, 0)


@transicao_reg("foco_rack", "Troca de foco: a cena antiga desfoca e a nova entra em foco. Cinema.", ["whoosh-suave"])
def _foco(a, b, p, W, H):
    base = a if p < 0.5 else b
    q = 1 - abs(p - 0.5) * 2
    k = int(1 + W * 0.04 * q) | 1
    return cv2.GaussianBlur(base, (k, k), 0)


# ───────────────────────────── 8. cortes digitais ─────────────────────────────
@transicao_reg("glitch_corte", "Corte com falha digital: faixas deslocadas e canais separados." + SO_FORA_DA_FE, ["glitch"])
def _glitch(a, b, p, W, H):
    base = a if p < 0.5 else b
    q = math.sin(math.pi * p)
    r = np.random.default_rng(int(p * 1000))  # fixo para cada p: determinístico
    out = base.copy()
    for _ in range(int(3 + 12 * q)):
        y0 = int(r.random() * H)
        h = int(r.uniform(0.01, 0.06) * H)
        dx = int(r.normal(0, W * 0.08 * q))
        out[y0:y0 + h] = np.roll(out[y0:y0 + h], dx, axis=1)
    d = int(W * 0.015 * q) + 1
    out[:, d:, 2] = out[:, :-d, 2]
    return out


@transicao_reg("rgb_separado", "Os canais de cor se separam e voltam na cena nova." + SO_FORA_DA_FE, ["glitch"])
def _rgb(a, b, p, W, H):
    base = cv2.addWeighted(a, 1 - ease_in_out(p), b, ease_in_out(p), 0)
    d = int(W * 0.04 * math.sin(math.pi * p)) + 1
    out = base.copy()
    out[:, d:, 2] = base[:, :-d, 2]
    out[:, :-d, 0] = base[:, d:, 0]
    return out


@transicao_reg("pixelar", "A cena pixeliza até blocos grandes e volta já na nova. Digital, game.", ["teclado"])
def _pixelar(a, b, p, W, H):
    base = a if p < 0.5 else b
    q = 1 - abs(p - 0.5) * 2
    n = int(1 + 60 * q * q)
    if n < 2:
        return base
    peq = cv2.resize(base, (max(2, W // n), max(2, H // n)), interpolation=cv2.INTER_AREA)
    return cv2.resize(peq, (W, H), interpolation=cv2.INTER_NEAREST)


@transicao_reg("tv_desliga", "A cena antiga se fecha numa linha de luz como TV antiga, e a nova liga." + SO_FORA_DA_FE, ["interruptor"])
def _tv(a, b, p, W, H):
    out = np.empty_like(a)
    out[:] = bgr(CORES["marinho"])
    if p < 0.5:
        q = ease_in(p / 0.5)
        f = a
    else:
        q = 1 - ease_out((p - 0.5) / 0.5)
        f = b
    h = max(2, int(H * (1 - q)))
    peq = cv2.resize(f, (W, h))
    y0 = (H - h) // 2
    out[y0:y0 + h] = peq
    if h < H * 0.1:
        cv2.line(out, (0, H // 2), (W, H // 2), bgr(CORES["papel_2"]), max(2, int(H * 0.004)), cv2.LINE_AA)
    return out


# ───────────────────────────── 9. formas da marca que cobrem a tela ─────────────────────────────
def _forma_cobre(forma, papel):
    def fn(a, b, p, W, H):
        base = a if p < 0.5 else b
        q = (1 - abs(p - 0.5) * 2) ** 1.6  # cresce até cobrir no meio e encolhe já na cena nova
        xx, yy = _grade(W, H)
        x, y = (xx - 0.5) * 2, (yy - 0.5) * 2 * H / W
        if forma == "circulo":
            d = np.hypot(x, y) / math.hypot(1, H / W)
        elif forma == "quadrado":
            d = np.maximum(np.abs(x), np.abs(y) * W / H)
        elif forma == "losango":
            d = (np.abs(x) + np.abs(y) * W / H) / 2
        elif forma == "faixa":  # faixa diagonal larga que atravessa
            d = np.abs(x * 0.6 + y * 0.8 * W / H * 0.5) / 1.2
        elif forma == "onda":
            d = np.abs(y * W / H + 0.15 * np.sin(x * 6 + p * 8))
        else:  # gota: círculo que sai de baixo e sobe
            d = np.hypot(x, y - H / W) / math.hypot(1, 2 * H / W)
        m = 1 - _degrau(d - q * 1.08, 0.015)
        m = cv2.resize(m.astype(np.float32), (W, H))[..., None]
        return (base.astype(np.float32) * (1 - m) + _cor(papel) * m).astype(np.uint8)
    return fn


_FORMAS_COBRE = {"circulo": "um círculo", "quadrado": "um quadrado", "losango": "um losango", "faixa": "uma faixa diagonal",
                 "onda": "uma onda", "gota": "uma bolha que sobe de baixo"}
for _f, _fd in _FORMAS_COBRE.items():
    for _p, _pd in (("champanhe", "dourado"), ("marinho", "escuro")):
        transicao_reg(f"forma_{_f}_{'dourada' if _p == 'champanhe' else 'escura'}",
                      f"{_fd[0].upper() + _fd[1:]} {_pd} da marca cresce, cobre a tela e se abre na cena nova. Troca com identidade.",
                      ["whoosh-suave", "pop-limpo"])(_forma_cobre(_f, _p))


def _camadas(vx, vy):
    def fn(a, b, p, W, H):
        """Três faixas da paleta passam em sequência; a cena troca escondida atrás da última."""
        out = (a if p < 0.55 else b).copy()
        for k, papel in enumerate(("champanhe", "papel_2", "marinho")):
            q = clamp01((p - k * 0.12) / 0.64)
            e = ease_in_out(q)
            # entra (0 → cobre) e sai (cobre → passa) ao longo do mesmo movimento
            pos = -1 + 2 * e
            if vx:
                x0 = int((pos * vx) * W)
                xa, xb = max(0, x0), min(W, x0 + W)
                if xa < xb:
                    out[:, xa:xb] = bgr(CORES[papel])
            else:
                y0 = int((pos * vy) * H)
                ya, yb = max(0, y0), min(H, y0 + H)
                if ya < yb:
                    out[ya:yb] = bgr(CORES[papel])
        # depois que a última faixa passa, a cena nova aparece atrás dela
        if p >= 0.55:
            ult = ease_in_out(clamp01((p - 0.24) / 0.64))
            pos = -1 + 2 * ult
            if vx:
                x0 = int(pos * vx * W)
                m = np.zeros(W, bool)
                if vx > 0:
                    m[:max(0, min(W, x0))] = True
                else:
                    m[max(0, min(W, W + x0)):] = True
                out[:, m] = b[:, m]
            else:
                y0 = int(pos * vy * H)
                m = np.zeros(H, bool)
                if vy > 0:
                    m[:max(0, min(H, y0))] = True
                else:
                    m[max(0, min(H, H + y0)):] = True
                out[m] = b[m]
        return out
    return fn


for _d, (_vx, _vy) in VETORES.items():
    transicao_reg(f"camadas_{_d}", f"Três faixas da paleta da marca passam {_NOMES_DIR[_d]} e trazem a cena nova. Motion design.",
                  ["whoosh-ar", "deslizar"])(_camadas(_vx, _vy))


def catalogo_transicoes():
    """Todas as transições: as clássicas de camera.py e as desta biblioteca."""
    from .camera import CLASSICAS
    return [{"id": n, "descricao": d} for n, d in CLASSICAS.items()] + [{"id": n, "descricao": d} for n, (_, d, _s) in TRANSICOES.items()]
