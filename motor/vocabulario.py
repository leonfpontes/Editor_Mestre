"""Vocabulário do diretor: palavras da fala que pedem uma peça da biblioteca ampliada (traço à mão, partícula, forma de
motion, transição). Só entra o que está dito, ancorado na palavra exata, poucas vezes por vídeo e longe do rosto.

Cada entrada: gatilhos (palavras ou expressões, sem acento), o elemento e se ele cabe numa marca de ritmo calmo
(`"diretor": {"calmo": true}`, como o GiraHub, onde nada de festa, glitch ou impacto entra em fala de fé).
"""
from .diretor import norm, sem_acento

# posição de um desenho ao lado da cabeça, alternando os lados (o rosto fica no centro do quadro)
LADOS = ((0.24, 0.22), (0.76, 0.22))

VOCABULARIO = [
    # (gatilhos, elemento, cabe em marca calma, motivo)
    (("ideia", "ideias", "insight", "sacada"), {"nome": "traco_lampada", "largura": 0.17}, True, "ideia → lâmpada desenhada"),
    (("pergunta", "duvida", "duvidas", "sera que", "quer saber", "sabia que", "sabe por que"), {"nome": "traco_interrogacao", "largura": 0.12}, True,
     "dúvida → interrogação"),
    (("atencao", "cuidado", "alerta", "importante"), {"nome": "traco_exclamacao", "largura": 0.1}, False, "alerta → exclamação"),
    (("pensar", "pensando", "pensamento", "imagina", "imagine"), {"nome": "traco_nuvem", "largura": 0.22}, True, "pensar → nuvem"),
    (("conversa", "conversar", "dialogo", "perguntei", "falei pra"), {"nome": "traco_balao_fala", "largura": 0.2}, True, "conversa → balão"),
    (("perspectiva", "enxergar", "repara", "olha so", "visao"), {"nome": "traco_olho", "largura": 0.18}, True, "olhar → olho desenhado"),
    (("foco", "objetivo", "meta", "alvo"), {"nome": "forma_mira_fino", "tamanho": 0.1}, False, "foco → mira"),
    (("crescer", "crescimento", "cresceu", "aumentar", "aumentou", "subiu", "pra cima", "para cima"), {"nome": "marcador_seta_cima", "largura": 0.16}, True,
     "crescer → seta para cima"),
    (("caiu", "queda", "diminuir", "diminuiu", "perdeu", "pra baixo", "para baixo"), {"nome": "marcador_seta_baixo", "largura": 0.16}, True,
     "queda → seta para baixo"),
    (("energia", "rapido", "rapida", "velocidade"), {"nome": "traco_raio", "largura": 0.12}, False, "energia → raio"),
    (("ciclo", "rotina", "repetir", "de novo", "sempre igual", "giro", "girar", "dar uma volta"), {"nome": "traco_ciclo", "largura": 0.16}, True,
     "ciclo → setas em círculo"),
    (("o melhor", "a melhor", "campeao", "numero um", "rei", "rainha"), {"nome": "marcador_coroa", "largura": 0.16}, False, "o melhor → coroa"),
    (("amor", "carinho", "gratidao", "grato", "grata", "familia"), {"nome": "coracoes_subindo", "quantidade": 14}, True,
     "afeto → corações subindo"),
    (("parabens", "comemorar", "comemoracao", "festa", "aniversario"), {"nome": "chuva_confete"}, False, "festa → confete"),
    (("sucesso", "conquista", "conquistei", "venci", "vitoria"), {"nome": "estouro_estrelas", "y": 0.3, "raio": 0.25}, False,
     "conquista → estrelas"),
    (("luz", "iluminar", "iluminou", "clareza", "clareou"), {"nome": "raios_topo", "intensidade": 0.7}, True, "luz → raios do alto"),
    (("sonho", "sonhar", "lembranca", "memoria", "saudade"), {"nome": "poeira_dourada", "quantidade": 30}, True, "memória → poeira dourada"),
    (("dinheiro", "lucro", "faturamento", "faturar", "riqueza"), {"nome": "diamantes", "y": 0.25, "raio": 0.22}, False,
     "dinheiro → diamantes"),
    (("musica", "podcast", "audio", "som"), {"nome": "forma_equalizador_bloco", "y": 0.2, "tamanho": 0.12}, True, "som → equalizador"),
    (("processo", "progresso", "etapa", "etapas", "quase la"), {"nome": "forma_barra_progresso_fino", "y": 0.18}, True,
     "processo → barra de progresso"),
    (("frio", "inverno", "natal", "neve"), {"nome": "neve"}, True, "frio → neve"),
    (("chuva", "chorar", "chorei", "lagrima", "lagrimas"), {"nome": "gotas_caindo", "intensidade": 0.7}, True, "chuva → gotas"),
    (("relogio", "prazo", "cronometro"), {"nome": "forma_arco_progresso_fino", "y": 0.2, "tamanho": 0.12}, True, "prazo → círculo que se fecha"),
]

# começo de trecho que pede transição: (expressões, transição normal, transição em marca calma)
TRANSICOES_FALA = [
    (("antigamente", "anos atras", "quando eu era", "la atras", "no passado", "eu lembro", "lembro que"), "relogio_anti", "fusao_desfocada"),
    (("anos depois", "hoje em dia", "hoje eu", "daqui a pouco", "no futuro"), "relogio", "mergulho_papel"),
    (("vamos seguir", "seguindo", "agora vamos", "continuando", "proximo ponto", "outra coisa"), "forma_circulo_dourada", "dissolver_nuvem"),
    (("vou dar um giro", "dar um giro", "dando um giro"), "girar_horario", "fusao_desfocada"),
    (("vou ampliar", "olha so", "repara", "vou mostrar", "deixa eu mostrar"), "zoom_saida", "foco_rack"),
    (("por fim", "pra fechar", "para fechar", "pra terminar", "resumindo"), "camadas_esquerda", "mergulho_marinho"),
]

PALAVRAS_FE = {"fe", "oracao", "rezar", "orixa", "orixas", "axe", "terreiro", "umbanda", "candomble", "espiritualidade", "espiritual",
               "guia", "guias", "entidade", "entidades", "firmeza", "bencao", "gira"}


def _tokens(ws):
    return [sem_acento(norm(w["t"])) for w in ws]


def _casa(toks, i, gatilho):
    partes = gatilho.split()
    return toks[i:i + len(partes)] == partes


def sugerir(ws, mantidas, calmo=False, ocupados=(), max_n=5, espaco=4.0):
    """Elementos da biblioteca pedidos pela fala. `ocupados`: instantes já com elemento (o diretor não empilha)."""
    from .diretor import ancora
    toks = _tokens(ws)
    out, usados, tempos = [], set(), []
    lado = 0
    for i in mantidas:
        if len(out) >= max_n:
            break
        t = ws[i]["ini"]
        # entre desenhos, `espaco`; perto de reação de cena (que segue a mão) basta não nascer no mesmo instante
        if any(abs(t - x) < espaco for x in tempos) or any(abs(t - x) < 1.5 for x in ocupados):
            continue
        for k, (gatilhos, el, cabe_calmo, motivo) in enumerate(VOCABULARIO):
            if k in usados or (calmo and not cabe_calmo):
                continue
            g = next((g for g in gatilhos if _casa(toks, i, g)), None)
            if not g:
                continue
            na, oc = ancora(ws, i, len(g.split()))
            e = dict({"tipo": "efeito", "na": na, "segura": 1.6}, **el)
            if "x" not in el and (el["nome"].startswith(("traco_", "marcador_")) or el["nome"].startswith("forma_mira")):
                e["x"], e["y"] = LADOS[lado % 2]
                lado += 1
            if oc > 1:
                e["ocorrencia"] = oc
            e["_motivo"] = f"vocabulário: {motivo}"
            out.append(e)
            usados.add(k)
            tempos.append(t)
            break
    return out


def transicoes_pela_fala(segs, palavras, calmo=False):
    """Põe a transição pedida pelo começo da fala do trecho (só onde o trecho ainda está em corte seco)."""
    linhas = []
    for s in segs[1:]:
        if s.get("transicao") or not s.get("texto") or s["texto"] == "(sem fala)":
            continue
        toks = [sem_acento(norm(x)) for x in s["texto"].split()]
        while toks and toks[0] in ("e", "eu", "entao"):  # "Eu vou dar um giro" casa com "vou dar um giro"
            toks = toks[1:]
        ini = " ".join(toks[:5])
        for frases, normal, suave in TRANSICOES_FALA:
            f = next((f for f in frases if f" {ini} ".startswith(f" {f} ")), None)
            if f:
                s["transicao"] = suave if calmo else normal
                linhas.append(f"transição {s['transicao']} em {s['ini']:.1f}s (\"{f}\")")
                break
    return linhas


def look_sugerido(palavras, calmo=False):
    """Look de cor sugerido para o vídeo inteiro pelo assunto (só sugestão no relatório: a cor é decisão do editor)."""
    toks = _tokens(palavras)
    fe = sum(t in PALAVRAS_FE for t in toks)
    if fe >= 3:
        return "espiritual", f"{fe} palavras de fé na fala"
    return None, ""


# ───────────────────────────── lista falada ─────────────────────────────
ORDINAIS_LISTA = {"primeiro": 1, "primeira": 1, "segundo": 2, "segunda": 2, "terceiro": 3, "terceira": 3, "quarto": 4,
                  "quarta": 4, "quinto": 5, "quinta": 5, "sexto": 6, "sexta": 6, "setimo": 7, "setima": 7, "ultimo": 0,
                  "ultima": 0}
_DEPOIS_DO_ORDINAL = {"dela", "delas", "dele", "deles", "dessas", "desses", "item", "ferramenta", "ferramentas", "dica",
                      "aqui"}
_FIM_DO_NOME = {"ele", "ela", "eles", "elas", "que", "e", "sao", "vai", "faz", "tem", "para", "pra", "porque"}
LETREIRO_LISTA = {False: "tarja_destaque_desliza", True: "serifa_surge"}  # marca normal, marca calma


_NUMEROS = {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10, "um": 1, "dois": 2, "tres": 3,
            "quatro": 4, "cinco": 5}
_ANTES_DO_ITEM = {"e", "eu", "gosto", "muito", "mais", "de", "do", "da", "sendo", "o", "a", "que", "fica", "com", "vai", "pra",
                  "para"}


def _ranking_falado(ws, toks, mant):
    """Ranking dito como "top 1, é X", "segundo lugar, eu gosto de Y": (índice, número, nome). O marcador precisa fechar
    com vírgula (ou "é"), para não confundir com o anúncio ("top 3 coisas que…"). Tomada repetida: vale a primeira mantida."""
    achados = {}
    for i, t in enumerate(toks):
        if i not in mant:
            continue
        if t == "top" and i + 1 < len(toks) and toks[i + 1] in _NUMEROS:
            n, fim = _NUMEROS[toks[i + 1]], i + 1
        elif t in ORDINAIS_LISTA and ORDINAIS_LISTA[t] and i + 1 < len(toks) and toks[i + 1] == "lugar":
            n, fim = ORDINAIS_LISTA[t], i + 1
        else:
            continue
        if n in achados or fim not in mant:
            continue
        if ws[fim]["t"][-1:] not in ",.:;!" and not (fim + 1 < len(toks) and toks[fim + 1] == "e"):
            continue
        j = fim + 1
        while j < len(toks) and toks[j] in _ANTES_DO_ITEM and j in mant:
            j += 1
        nome = []
        while j < len(toks) and j in mant and len(nome) < 4 and toks[j] not in _FIM_DO_NOME:
            bruto = ws[j]["t"]
            nome.append(bruto.strip(".,!?;:\"'"))
            j += 1
            if bruto[-1:] in ".,!?;:":
                break
        while nome and sem_acento(nome[-1].lower()) in ("o", "a", "com", "de", "do", "da", "e", "das", "dos", "em", "no", "na"):
            nome.pop()
        if nome:
            nome[0] = nome[0][:1].upper() + nome[0][1:]
        achados[n] = (i, n, " ".join(nome) if nome else "")
    return sorted(achados.values())


def lista_falada(ws, mantidas, calmo=False):
    """Itens de uma lista dita em voz alta ("a primeira delas é o X", "o segundo é o Y", "o último é o Z"): um letreiro
    "1 de 5 / X" em cada item. Só vale com 3 itens ou mais; "primeiro passo" e afins ficam com as regras do diretor."""
    toks = _tokens(ws)
    mant = set(mantidas)
    itens = []
    for i, t in enumerate(toks):
        if t not in ORDINAIS_LISTA or i not in mant or i == 0:
            continue
        if toks[i - 1] not in ("o", "a") and not (ORDINAIS_LISTA[t] == 0 and toks[i - 1] == "por"):  # "e por último é o X"
            continue
        j = i + 1
        while j < len(toks) and toks[j] in _DEPOIS_DO_ORDINAL:
            j += 1
        if j >= len(toks) or toks[j] != "e":  # "é" sem acento
            continue
        j += 1
        if j < len(toks) and toks[j] in ("o", "a", "um", "uma"):
            j += 1
        nome = []
        while j < len(toks) and len(nome) < 5 and toks[j] not in _FIM_DO_NOME:
            bruto = ws[j]["t"]
            nome.append(bruto.strip(".,!?;:\"'"))
            j += 1
            if bruto[-1:] in ".,!?;:":
                break
        while nome and sem_acento(nome[-1].lower()) in ("o", "a", "com", "de", "do", "da", "e", "junto"):
            nome.pop()  # não termina em artigo ou preposição
        if nome:
            itens.append((i, ORDINAIS_LISTA[t], " ".join(nome)))
    ranking = False
    if len(itens) < 3:
        itens, ranking = _ranking_falado(ws, toks, mant), True
    if len(itens) < 3:
        return []
    maior = max(n for _, n, _ in itens)
    total = maior + (1 if any(n == 0 for _, n, _ in itens) else 0)
    out = []
    from .diretor import ancora
    for i, n, nome in itens:
        num = n or total
        na, oc = ancora(ws, i - 1, 2)
        rotulo = f"Top {num}" if ranking else f"{num} de {total}"
        e = {"tipo": "letreiro", "estilo": LETREIRO_LISTA[calmo], "texto": f"{rotulo}/{nome}", "na": na,
             "segura": 2.4, "y": 0.14, "_motivo": f"lista falada: item {num} de {total}"}
        if oc > 1:
            e["ocorrencia"] = oc
        out.append(e)
    return out


def cta_comenta(ws, mantidas):
    """'Comenta SKILL', 'comente a palavra X': a barra de comentário com a palavra digitada, ancorada na fala."""
    toks = _tokens(ws)
    for i in mantidas:
        if toks[i] in ("comenta", "comente") and i + 1 < len(toks):
            j = i + 1
            while j < len(toks) and toks[j] in ("ai", "aqui", "a", "palavra", "o", "nos", "comentarios", "embaixo"):
                j += 1
            if j < len(toks) and len(toks[j]) >= 3 and toks[j] not in ("que", "pra", "para", "se"):
                from .diretor import ancora
                na, oc = ancora(ws, i, 1)
                e = {"tipo": "comentario", "texto": ws[j]["t"].strip(".,!?;:\"'“”").upper(), "na": na, "segura": 2.0,
                     "_motivo": "CTA de comentário"}
                if oc > 1:
                    e["ocorrencia"] = oc
                return [e]
    return []
