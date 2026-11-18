"""Estilos de edição prontos (docs/estilos-de-referencia.md): presets do EDL, fontes de estilo e looks de cor.

Um estilo não traz identidade: cores saem sempre da paleta da marca ativa. Ele só muda ritmo, composição,
legenda e tipografia. No EDL:

    {"estilo": "tutorial_passos", ...}

O preset preenche o que o EDL não disse (o EDL sempre vence) e fica abaixo dos padrões da marca só no que a
marca proíbe (política de música, CTA, intro): esses continuam valendo.
"""
import copy

import cv2
import numpy as np
from PIL import ImageFont

from .config import FONTES_DIR
from .marca import CFG, CORES, ErroDeMarca

# Presets: o mínimo que cada estilo precisa para sair com a cara dele.
PRESETS = {
    "tutorial_passos": {
        "descricao": "Tutorial falado em passos: rosto, tela dividida e só motion em corte seco; legenda de 1 a 2 palavras.",
        "edl": {
            "legendas": {"ativo": True, "estilo": "limpa", "palavras_por_bloco": 2, "maiusculas": False, "enfase": []},
            "audio": {"sfx_transicoes": False},
            "corte_pausa_max": 0.4,
            "parado_max": 3.0,
        },
    },
    "tela_perspectiva": {
        "descricao": "Narração sobre gravação de tela num plano 3D com câmera, profundidade de campo e luz quente.",
        "edl": {
            "legendas": {"ativo": False},
            "audio": {"sfx_transicoes": False},
            "corte_pausa_max": 0.6,
        },
    },
    "vitrine": {
        "descricao": "Peça de lançamento: um look por frase, texto atrás da pessoa, HUD, som visível e CTA em neon.",
        "edl": {
            "legendas": {"ativo": False},
            "audio": {"sfx_transicoes": True, "sfx_elementos": True},
            "corte_pausa_max": 0.35,
            "parado_max": 2.0,
        },
    },
}


def _mesclar(base, cima):
    """cima vence; dicionários são mesclados em profundidade."""
    out = copy.deepcopy(base)
    for k, v in cima.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _mesclar(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def aplicar_estilo(edl):
    """EDL com o preset do estilo por baixo. Sem "estilo", devolve o próprio EDL."""
    nome = edl.get("estilo")
    if not nome:
        return edl
    if nome not in PRESETS:
        raise ErroDeMarca(f"estilo desconhecido: {nome} (opções: {', '.join(PRESETS)})")
    return _mesclar(PRESETS[nome]["edl"], edl)


# ───────────────────────────── fontes de estilo ─────────────────────────────
# Fontes da biblioteca (OFL, veja biblioteca/fontes/LICENCAS.md). A marca pode trocar qualquer uma em
# "fontes": {"estilo": {"serifa_italica": "...ttf", ...}} no marca.json.
FONTES_ESTILO = {
    "serifa_italica": "DMSerifDisplay-Italic.ttf",
    "serifa": "DMSerifDisplay-Regular.ttf",
    "condensada": "Anton-Regular.ttf",
    "mono": "SpaceMono-Bold.ttf",
    "mono_leve": "SpaceMono-Regular.ttf",
    "manuscrita": "Caveat-Variable.ttf",
}
_cache_fontes = {}


def fonte_estilo(papel, tam):
    """Fonte de um papel de estilo. "sans" e "sans_leve" usam a fonte de texto da marca."""
    from .graficos import fonte
    if papel == "sans":
        return fonte("Bold", tam, "texto")
    if papel == "sans_forte":
        return fonte("Black", tam, "texto")
    if papel == "sans_leve":
        return fonte("Regular", tam, "texto")
    arq = (CFG.get("fontes", {}).get("estilo") or {}).get(papel) or FONTES_ESTILO.get(papel)
    if not arq:
        raise ErroDeMarca(f"fonte de estilo desconhecida: {papel} (opções: sans, sans_forte, sans_leve, {', '.join(FONTES_ESTILO)})")
    chave = (arq, tam)
    if chave not in _cache_fontes:
        f = ImageFont.truetype(str(FONTES_DIR / arq), tam)
        if "Variable" in arq:
            try:
                f.set_variation_by_axes([700])
            except (OSError, AttributeError):
                pass
        _cache_fontes[chave] = f
    return _cache_fontes[chave]


# ───────────────────────────── looks de cor por segmento ─────────────────────────────
LOOKS = {
    "pb": "Preto e branco com contraste de cinema.",
    "pb_acento": "Preto e branco; só os elementos gráficos têm cor (use com texto_atras).",
    "duotom": "Sombras no tom escuro da marca e luzes no claro.",
    "quente": "Mais calor e contraste, pele dourada.",
    "frio": "Azulado e contido, bom para tecnologia.",
    "limpo": "Clareado, pouco saturado, sombras abertas: calmo e minimalista.",
    "noite": "Escuro e saturado, com sombras azuladas e luzes quentes.",
    "adesivo": "Pessoa recortada em preto e branco com contorno na cor de acento sobre fundo chapado da marca.",
}


def _bgr(rgb):
    return np.array((rgb[2], rgb[1], rgb[0]), np.float32)


# ───────────────────────────── grades de cor (biblioteca de looks) ─────────────────────────────
# Cada grade é uma LUT por canal (balanço, contraste, gama, preto levantado, teto, tons de sombra e de luz) mais a
# saturação. Tons são ganhos por canal (b, g, r), não cores soltas; os looks "marca_*" puxam sombras e luzes para
# papéis da paleta da marca ativa. "pele": True devolve a pele perto do tom original (como os looks de cor clássicos).
GRADES = {
    # cinema
    "teal_laranja": ("Sombras verde-azuladas e pele alaranjada, o look de blockbuster.",
                   dict(c=1.12, sat=1.1, s=(1.18, 1.05, 0.82), l=(0.85, 0.98, 1.12), pele=True)),
    "bleach_bypass": ("Pouca cor e muito contraste, prata de cinema (bleach bypass).", dict(c=1.3, sat=0.45, g=1.05)),
    "filme_kodak": ("Filme quente com pretos suaves e vermelhos ricos.", dict(c=1.08, lev=0.04, wb=(0.92, 1.0, 1.08), sat=1.08, pele=True)),
    "filme_fuji": ("Filme com verdes frescos e sombras levemente azuis.", dict(c=1.06, lev=0.03, wb=(1.02, 1.04, 0.96), s=(1.08, 1.04, 0.95), pele=True)),
    "cinema_frio": ("Cinema contido e frio, de thriller.", dict(c=1.15, wb=(1.1, 1.0, 0.9), sat=0.8, g=1.05, pele=True)),
    "blockbuster": ("Muito contraste e cor saturada, cena de ação.", dict(c=1.25, sat=1.25, s=(1.1, 1.0, 0.9), l=(0.92, 1.0, 1.08), pele=True)),
    "noir": ("Preto e branco duro, sombras fechadas (filme noir).", dict(mono=True, c=1.5, g=1.15)),
    "western": ("Quente, seco e dessaturado, poeira de faroeste.", dict(wb=(0.8, 0.98, 1.12), sat=0.7, c=1.1, lev=0.03)),
    "matrix": ("Tudo puxado para o verde, digital e frio.", dict(wb=(0.9, 1.12, 0.88), c=1.15, sat=0.85)),
    "anos70": ("Anos 70: quente, desbotado e amarelado.", dict(wb=(0.82, 1.0, 1.08), lev=0.08, teto=0.94, sat=0.85, c=0.95)),
    "anos80": ("Anos 80: magenta nas luzes e cor estourada.", dict(sat=1.3, l=(1.06, 0.92, 1.08), c=1.1)),
    "anos90": ("Anos 90: filme de revelação de farmácia, verde nas sombras.", dict(s=(0.98, 1.08, 0.94), lev=0.05, sat=1.05, c=1.05)),
    # natural
    "natural": ("Correção neutra: um pouco mais de contraste e cor, sem mudar o clima.", dict(c=1.06, sat=1.06, pele=True)),
    "natural_vivo": ("Natural com cor viva, para dia claro e produto.", dict(c=1.1, sat=1.22, pele=True)),
    "pastel": ("Cores pastel, claras e suaves.", dict(c=0.85, lev=0.1, sat=0.75, g=0.9)),
    "suave": ("Contraste baixo e pele macia.", dict(c=0.9, lev=0.05, sat=0.92, pele=True)),
    "arejado": ("Claro e arejado, estilo blog de casa.", dict(g=0.82, lev=0.06, sat=0.85, wb=(1.03, 1.0, 0.98), pele=True)),
    "manha": ("Luz fria e limpa de manhã cedo.", dict(wb=(1.06, 1.01, 0.95), g=0.92, c=1.02, pele=True)),
    "hora_dourada": ("Fim de tarde dourado, sol baixo.", dict(wb=(0.84, 0.98, 1.12), l=(0.9, 1.0, 1.08), sat=1.1, pele=True)),
    "nublado": ("Dia nublado: cinza, contido e calmo.", dict(sat=0.7, c=0.92, wb=(1.03, 1.0, 0.98), lev=0.03)),
    "praia": ("Azuis e cianos limpos, praia e verão.", dict(wb=(1.06, 1.03, 0.96), sat=1.2, g=0.9, c=1.05, pele=True)),
    "natureza": ("Verdes ricos e terra quente.", dict(wb=(0.95, 1.05, 1.0), sat=1.15, c=1.08, pele=True)),
    # clima
    "melancolia": ("Azulado e sem cor, para uma fala triste.", dict(wb=(1.12, 1.0, 0.9), sat=0.55, c=0.95, lev=0.04)),
    "drama": ("Contraste alto e sombras profundas, peso na fala.", dict(c=1.35, g=1.12, sat=0.9)),
    "misterio": ("Escuro e esverdeado, segredo.", dict(g=1.2, wb=(1.0, 1.06, 0.92), sat=0.75, c=1.1)),
    "sonho": ("Claro, rosado e leve, como lembrança boa.", dict(g=0.85, lev=0.08, l=(1.04, 0.98, 1.05), sat=0.85, c=0.9)),
    "nostalgia": ("Quente e desbotado, foto antiga de família.", dict(wb=(0.85, 0.97, 1.08), lev=0.09, teto=0.93, sat=0.7)),
    "aconchego": ("Quente e macio, casa e conforto.", dict(wb=(0.88, 0.99, 1.08), c=0.95, lev=0.03, pele=True)),
    "energia": ("Cor e contraste no máximo, energia e movimento.", dict(c=1.2, sat=1.35)),
    "calma": ("Frio leve, baixo contraste, respiração.", dict(wb=(1.05, 1.01, 0.96), c=0.88, sat=0.85, lev=0.04)),
    "tensao": ("Verde-amarelado e duro, desconforto.", dict(wb=(0.9, 1.06, 1.0), c=1.25, sat=0.8, g=1.08)),
    "romance": ("Rosado e quente nas luzes.", dict(l=(1.02, 0.95, 1.1), sat=1.05, c=0.95, lev=0.03, pele=True)),
    # preto e branco
    "pb_suave": ("Preto e branco suave, sem contraste duro.", dict(mono=True, c=0.9, lev=0.04)),
    "pb_alto_contraste": ("Preto e branco de alto contraste, retrato forte.", dict(mono=True, c=1.45)),
    "pb_fosco": ("Preto e branco fosco, pretos levantados.", dict(mono=True, lev=0.12, teto=0.92)),
    "sepia": ("Sépia de foto antiga.", dict(mono=True, tom=(0.75, 0.93, 1.1), lev=0.04)),
    "cianotipia": ("Azul de cianotipia (blueprint antigo).", dict(mono=True, tom=(1.18, 0.95, 0.68), c=1.1)),
    "selenio": ("Viragem de selênio: pretos frios arroxeados.", dict(mono=True, s=(1.1, 0.96, 1.02), c=1.15)),
    "pb_quente": ("Preto e branco levemente quente.", dict(mono=True, tom=(0.94, 1.0, 1.05), c=1.1)),
    "pb_frio": ("Preto e branco levemente frio.", dict(mono=True, tom=(1.06, 1.0, 0.95), c=1.1)),
    # marca (cores da paleta da marca ativa)
    "marca_sombras": ("Sombras puxadas para o tom escuro da marca.", dict(marca=("marinho", None, 0.35), c=1.05, pele=True)),
    "marca_luzes": ("Luzes puxadas para o tom de destaque da marca.", dict(marca=(None, "champanhe", 0.25), pele=True)),
    "marca_split": ("Sombras no escuro da marca e luzes no destaque (split toning da marca).",
                    dict(marca=("marinho", "champanhe", 0.3), c=1.08, pele=True)),
    "marca_duotom_suave": ("Duotom da marca mais suave, ainda com um pouco da cor original.", dict(marca=("marinho", "papel_2", 0.6), sat=0.5)),
    "marca_tritom": ("Três tons da marca: escuro, destaque e claro.", dict(mono=True, tritom=("marinho", "champanhe", "papel_2"))),
    "marca_fosco": ("Fosco com pretos no tom escuro da marca.", dict(marca=("marinho", None, 0.5), lev=0.08, teto=0.95, sat=0.85)),
    "marca_quente": ("Quente, com luzes no bronze da marca.", dict(marca=(None, "bronze", 0.25), wb=(0.92, 1.0, 1.05), pele=True)),
    "marca_noite": ("Noite na cor escura da marca, luzes no destaque.", dict(marca=("marinho", "champanhe", 0.45), g=1.15, c=1.1)),
    "marca_papel": ("Claro e fosco, como impresso no papel da marca.", dict(marca=(None, "papel", 0.35), lev=0.1, sat=0.75, c=0.9)),
    "marca_mono": ("Monocromático tingido pelo destaque da marca.", dict(mono=True, tritom=("marinho", "champanhe", "champanhe"))),
    # fotografia
    "polaroid": ("Foto instantânea: fosca, amarelada nas luzes, ciano nas sombras.",
                   dict(lev=0.08, teto=0.94, s=(1.08, 1.02, 0.92), l=(0.9, 1.0, 1.04), sat=0.85)),
    "instantanea": ("Instantânea moderna: quente, clara e com grão de cor suave.", dict(wb=(0.92, 1.0, 1.05), g=0.9, lev=0.05, sat=0.95)),
    "cross_process": ("Revelação cruzada: amarelo e ciano fortes, contraste alto.", dict(s=(1.15, 1.0, 0.85), l=(0.75, 1.05, 1.08), c=1.2, sat=1.2)),
    "lomo": ("Lomografia: cor estourada e contraste alto.", dict(c=1.35, sat=1.35, s=(1.08, 1.0, 0.94))),
    "desbotado": ("Cores desbotadas pelo tempo.", dict(sat=0.6, lev=0.1, teto=0.92, c=0.92)),
    "fosco": ("Pretos levantados, acabamento fosco moderno.", dict(lev=0.1, c=1.05, pele=True)),
    "vintage": ("Vintage: quente, desbotado e esverdeado nas sombras.", dict(wb=(0.88, 0.98, 1.06), s=(0.95, 1.08, 0.95), lev=0.07, sat=0.75)),
    "verao_retro": ("Verão retrô: amarelo forte e céu ciano.", dict(wb=(0.85, 1.02, 1.08), sat=1.25, c=1.1, lev=0.03)),
    "kodachrome": ("Kodachrome: vermelhos e azuis densos, contraste de slide.", dict(c=1.18, sat=1.2, g=1.06, wb=(0.98, 0.98, 1.04), pele=True)),
    "slide": ("Filme slide: saturado, pretos profundos.", dict(c=1.25, sat=1.3, g=1.1)),
    "revista": ("Capa de revista: pele limpa, contraste alto, cor controlada.", dict(c=1.15, sat=0.95, g=0.95, pele=True)),
    "editorial": ("Editorial de moda: frio, contido e elegante.", dict(wb=(1.05, 1.0, 0.95), sat=0.75, c=1.1, lev=0.03)),
    # nichos
    "tecnologia": ("Frio e limpo, azul nas sombras: tecnologia e produto.", dict(wb=(1.08, 1.01, 0.94), s=(1.12, 1.0, 0.9), c=1.08, pele=True)),
    "saude": ("Claro, limpo e levemente frio: saúde e bem-estar.", dict(g=0.88, wb=(1.03, 1.01, 0.97), sat=0.9, pele=True)),
    "comida": ("Quente e saturado, comida apetitosa.", dict(wb=(0.9, 1.0, 1.08), sat=1.3, c=1.1)),
    "moda": ("Contraste alto e cor contida, moda.", dict(c=1.2, sat=0.85, g=1.02, pele=True)),
    "luxo": ("Escuro, dourado e denso: luxo.", dict(g=1.15, l=(0.88, 1.0, 1.08), c=1.15, sat=0.9)),
    "corporativo": ("Neutro, limpo e confiável: institucional.", dict(c=1.04, sat=0.92, wb=(1.02, 1.0, 0.99), pele=True)),
    "podcast": ("Estúdio de podcast: quente nas luzes, fundo escuro e denso.", dict(g=1.1, l=(0.92, 1.0, 1.06), c=1.12, pele=True)),
    "esporte": ("Esporte: contraste duro, cor viva, frio nas sombras.", dict(c=1.3, sat=1.2, s=(1.1, 1.0, 0.92))),
    "festa": ("Festa: magenta e roxo nas luzes, cor forte.", dict(l=(1.1, 0.9, 1.06), sat=1.3, c=1.12)),
    "espiritual": ("Suave, claro e dourado: fé, oração e respeito (bom para o GiraHub).",
                   dict(g=0.9, lev=0.04, wb=(0.94, 1.0, 1.04), sat=0.9, c=0.95, pele=True)),
}


def _lut_grade(spec):
    """LUT 1×256×3 (b, g, r) da grade."""
    x = np.arange(256, dtype=np.float32)[:, None] / 255 * np.ones((1, 3), np.float32)
    x = np.clip(x * np.array(spec.get("wb", (1, 1, 1)), np.float32), 0, 1)
    x = np.clip((x - 0.5) * spec.get("c", 1.0) + 0.5, 0, 1) ** spec.get("g", 1.0)
    lev, teto = spec.get("lev", 0.0), spec.get("teto", 1.0)
    x = lev + x * (teto - lev)
    peso_s = np.clip(1 - x * 2, 0, 1)  # sombras: abaixo do meio
    peso_l = np.clip(x * 2 - 1, 0, 1)  # luzes: acima do meio
    if "s" in spec:
        x = x * (1 + (np.array(spec["s"], np.float32) - 1) * peso_s)
    if "l" in spec:
        x = x * (1 + (np.array(spec["l"], np.float32) - 1) * peso_l)
    if "tom" in spec:
        x = x * np.array(spec["tom"], np.float32)
    x = np.clip(x, 0, 1) * 255
    if "marca" in spec:
        sombra, luz, k = spec["marca"]
        if sombra:
            x = x * (1 - peso_s * k) + _bgr(CORES[sombra]) * peso_s * k
        if luz:
            x = x * (1 - peso_l * k) + _bgr(CORES[luz]) * peso_l * k
    if "tritom" in spec:
        a, b, c = (_bgr(CORES[n]) for n in spec["tritom"])
        t = x.mean(1, keepdims=True) / 255
        x = np.where(t < 0.5, a * (1 - t * 2) + b * (t * 2), b * (2 - t * 2) + c * (t * 2 - 1))
    return np.clip(x, 0, 255).astype(np.uint8)[None]


_CACHE_GRADE = {}


def _aplicar_grade(f, nome):
    spec = GRADES[nome][1]
    chave = (nome, tuple(map(tuple, (CORES[k] for k in sorted(CORES)))))  # a LUT muda com a marca ativa
    if chave not in _CACHE_GRADE:
        _CACHE_GRADE[chave] = _lut_grade(spec)
    if spec.get("mono"):
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        f = cv2.merge([g, g, g])
    out = cv2.LUT(f, _CACHE_GRADE[chave])
    sat = spec.get("sat", 1.0)
    if sat != 1.0 and not spec.get("mono"):
        g = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
        out = cv2.addWeighted(out, sat, cv2.merge([g, g, g]), 1 - sat, 0)
    return out


LOOKS.update({n: d for n, (d, _) in GRADES.items()})


def _curva(f, contraste=1.0, gama=1.0, levanta=0.0):
    x = np.arange(256, dtype=np.float32) / 255
    y = np.clip((x - 0.5) * contraste + 0.5, 0, 1) ** gama
    y = levanta + y * (1 - levanta)
    return cv2.LUT(f, (y * 255).clip(0, 255).astype(np.uint8))


def _lut3(func):
    """LUT de 3 canais (1×256×3) a partir de func(x) -> (b, g, r) em float, com x = 0..255."""
    x = np.arange(256, dtype=np.float32)[:, None].repeat(3, 1)
    return func(x).clip(0, 255).astype(np.uint8)[None]


_LUTS_FIXOS = {
    "quente": _lut3(lambda x: (x * np.array((0.9, 1.0, 1.1), np.float32) - 128) * 1.08 + 128),
    "frio": _lut3(lambda x: (x * np.array((1.1, 1.02, 0.9), np.float32) - 128) * 1.05 + 128),
}


def _lut_duotom():
    """Cinza -> tom escuro da marca nas sombras e claro nas luzes (depende da marca ativa)."""
    escuro, claro = _bgr(CORES["marinho"]), _bgr(CORES["papel_2"])
    g = np.clip((np.arange(256, dtype=np.float32) / 255 - 0.5) * 1.15 + 0.5, 0, 1)[:, None]
    return (escuro * (1 - g) + claro * g).astype(np.uint8)[None]


def precisa_recorte(look):
    return look == "adesivo"


PROTEGE_PELE = {"quente", "frio", "noite", "limpo"} | {n for n, (_, g) in GRADES.items() if g.get("pele")}
# (os looks estilizados, como pb e duotom, mudam a pele de propósito)


def aplicar_look(f, look, alfa=None, pele=True):
    """Aplica o look ao quadro BGR. alfa (H×W×1, 0..1): recorte da pessoa, exigido pelo look "adesivo".
    pele: nos looks de cor, devolve a pele perto do tom original."""
    if not look:
        return f
    if look not in LOOKS:
        raise ErroDeMarca(f"look desconhecido: {look} (opções: {', '.join(LOOKS)})")
    if pele and look in PROTEGE_PELE:
        from .cor import proteger_pele
        return proteger_pele(f, _look(f, look, alfa))
    return _look(f, look, alfa)


def _look(f, look, alfa=None):
    if look in GRADES:
        return _aplicar_grade(f, look)
    if look in ("pb", "pb_acento"):
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        g = _curva(g, 1.25, 1.05)
        return cv2.merge([g, g, g])
    if look == "duotom":
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        return cv2.LUT(cv2.merge([g, g, g]), _lut_duotom())
    if look in ("quente", "frio"):
        return cv2.LUT(f, _LUTS_FIXOS[look])
    if look == "noite":  # sombras azuladas, luzes quentes: x·(a + b·lum) + c, canal a canal (rápido no OpenCV)
        lum = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32) * (1 / 255)
        sombra, luz, k = np.array((1.18, 0.98, 0.85)), np.array((0.85, 0.98, 1.12)), 0.85 * 1.15
        out = []
        for ch, sa, lu in zip(cv2.split(f), sombra, luz):
            ch = ch.astype(np.float32)
            v = cv2.addWeighted(ch, float(sa * k), cv2.multiply(ch, lum), float((lu - sa) * k), 110 - 110 * 1.15)
            out.append(cv2.convertScaleAbs(cv2.max(v, 0)))  # satura em 0..255
        return cv2.merge(out)
    if look == "limpo":
        hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
        hsv[..., 1] = (hsv[..., 1].astype(np.float32) * 0.45).astype(np.uint8)
        g = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        return _curva(g, 0.85, 0.85, 0.08)
    if look == "adesivo":
        if alfa is None:
            raise ErroDeMarca("o look \"adesivo\" precisa do recorte da pessoa")
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        g = _curva(g, 1.3, 1.0)
        pessoa = cv2.merge([g, g, g])
        a = np.ascontiguousarray(alfa[..., 0] if alfa.ndim == 3 else alfa, np.float32)
        H, W = a.shape
        r = max(6, W // 90)
        # contornos calculados em meia resolução (a dilatação com elipse grande é o que pesa) e ampliados
        bin_ = (cv2.resize(a, (W // 2, H // 2), interpolation=cv2.INTER_AREA) > 0.5).astype(np.uint8)
        el = lambda d: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * d + 1, 2 * d + 1))
        # 0 = fundo chapado, 1 = contorno claro, 2 = contorno na cor de acento; a cor sai por LUT
        nivel = cv2.add(cv2.dilate(bin_, el(r // 2)), cv2.dilate(bin_, el(r)))
        nivel = cv2.resize(nivel, (W, H), interpolation=cv2.INTER_NEAREST)
        tab = np.zeros((1, 256, 3), np.uint8)
        tab[0, :3] = [_bgr(CORES[k]) for k in ("papel", "papel_2", "champanhe")]
        out = cv2.LUT(cv2.merge([nivel, nivel, nivel]), tab)
        return cv2.blendLinear(pessoa, out, a, 1 - a)
    return f
