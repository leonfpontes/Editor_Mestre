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


def _curva(f, contraste=1.0, gama=1.0, levanta=0.0):
    x = np.arange(256, dtype=np.float32) / 255
    y = np.clip((x - 0.5) * contraste + 0.5, 0, 1) ** gama
    y = levanta + y * (1 - levanta)
    return cv2.LUT(f, (y * 255).clip(0, 255).astype(np.uint8))


def precisa_recorte(look):
    return look == "adesivo"


def aplicar_look(f, look, alfa=None):
    """Aplica o look ao quadro BGR. alfa (H×W×1, 0..1): recorte da pessoa, exigido pelo look "adesivo"."""
    if not look:
        return f
    if look not in LOOKS:
        raise ErroDeMarca(f"look desconhecido: {look} (opções: {', '.join(LOOKS)})")
    if look in ("pb", "pb_acento"):
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        g = _curva(g, 1.25, 1.05)
        return cv2.merge([g, g, g])
    if look == "duotom":
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)[..., None] / 255
        g = np.clip((g - 0.5) * 1.15 + 0.5, 0, 1)
        escuro, claro = _bgr(CORES["marinho"]), _bgr(CORES["papel_2"])
        return (escuro * (1 - g) + claro * g).astype(np.uint8)
    if look in ("quente", "frio", "noite"):
        x = f.astype(np.float32)
        if look == "quente":
            x *= np.array((0.9, 1.0, 1.1), np.float32)
            x = (x - 128) * 1.08 + 128
        elif look == "frio":
            x *= np.array((1.1, 1.02, 0.9), np.float32)
            x = (x - 128) * 1.05 + 128
        else:
            lum = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)[..., None] / 255
            sombra, luz = np.array((1.18, 0.98, 0.85), np.float32), np.array((0.85, 0.98, 1.12), np.float32)
            x = x * (sombra * (1 - lum) + luz * lum) * 0.85
            x = (x - 110) * 1.15 + 110
        return x.clip(0, 255).astype(np.uint8)
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
        pessoa = cv2.merge([g, g, g]).astype(np.float32)
        a = alfa[..., 0] if alfa.ndim == 3 else alfa
        H, W = a.shape
        r = max(6, W // 90)
        bin_ = (a > 0.5).astype(np.uint8)
        borda = cv2.dilate(bin_, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
        borda2 = cv2.dilate(bin_, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (4 * r + 1, 4 * r + 1)))
        fundo = np.empty_like(pessoa)
        fundo[:] = _bgr(CORES["papel"])
        out = fundo
        branco = borda2[..., None].astype(np.float32)
        out = out * (1 - branco) + _bgr(CORES["papel_2"]) * branco
        cor = borda[..., None].astype(np.float32)
        out = out * (1 - cor) + _bgr(CORES["champanhe"]) * cor
        m = a[..., None].astype(np.float32)
        return (out * (1 - m) + pessoa * m).clip(0, 255).astype(np.uint8)
    return f
