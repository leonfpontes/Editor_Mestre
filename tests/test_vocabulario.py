"""Vocabulário do diretor: a fala pede peças da biblioteca ampliada, ancoradas na palavra, respeitando marca calma."""
from motor.efeitos import REGISTRO
from motor.transicoes import TRANSICOES
from motor.vocabulario import TRANSICOES_FALA, VOCABULARIO, look_sugerido, sugerir, transicoes_pela_fala
from tests.test_diretor import fala


def test_todo_elemento_do_vocabulario_existe():
    for _, el, _, _ in VOCABULARIO:
        assert el["nome"] in REGISTRO, el["nome"]
    for _, normal, suave in TRANSICOES_FALA:
        assert normal in TRANSICOES and suave in TRANSICOES


def test_sugere_pela_fala_e_ancora_na_palavra():
    ws = fala("tive uma ideia ontem e foi muito bom . depois veio o sucesso de verdade com a equipe toda junta aqui", dur=0.4)
    els = sugerir(ws, range(len(ws)))
    nomes = {e["nome"]: e for e in els}
    assert "traco_lampada" in nomes and "estouro_estrelas" in nomes
    assert nomes["traco_lampada"]["na"] == "ideia"
    assert all(e["_motivo"].startswith("vocabulário") for e in els)
    assert nomes["traco_lampada"]["x"] in (0.24, 0.76)  # desenho ao lado da cabeça, não no rosto


def test_marca_calma_so_recebe_pecas_serenas():
    ws = fala("foi uma festa e uma conquista linda . muito amor pela familia", dur=0.6)
    nomes = {e["nome"] for e in sugerir(ws, range(len(ws)), calmo=True)}
    assert "chuva_confete" not in nomes and "estouro_estrelas" not in nomes
    assert "coracoes_subindo" in nomes


def test_nao_empilha_nem_repete():
    ws = fala("ideia ideia ideia pergunta", dur=0.2)
    els = sugerir(ws, range(len(ws)))
    assert len(els) == 1  # tudo cabe em 4 s: só a primeira peça entra
    assert not sugerir(ws, range(len(ws)), ocupados=[0.0, 0.6])  # já há reação de cena em cada palavra


def test_transicoes_pela_fala():
    segs = [{"ini": 0, "texto": "oi gente"}, {"ini": 5, "texto": "Antigamente eu fazia tudo errado"},
            {"ini": 9, "texto": "por fim, o recado"}, {"ini": 12, "texto": "antigamente", "transicao": "zoom"}]
    linhas = transicoes_pela_fala(segs, [])
    assert segs[1]["transicao"] == "relogio_anti" and segs[2]["transicao"] == "camadas_esquerda"
    assert segs[3]["transicao"] == "zoom" and len(linhas) == 2  # não troca a que o editor já escolheu
    segs = [{"ini": 0, "texto": "x"}, {"ini": 5, "texto": "antigamente era assim"}]
    transicoes_pela_fala(segs, [], calmo=True)
    assert segs[1]["transicao"] == "fusao_desfocada"


def test_look_sugerido():
    assert look_sugerido(fala("a fé no terreiro e a força do orixá"))[0] == "espiritual"
    assert look_sugerido(fala("hoje vou falar de produto"))[0] is None
