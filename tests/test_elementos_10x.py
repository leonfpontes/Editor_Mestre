"""Bibliotecas ampliadas: 280 efeitos, 113 transições, 80 looks e 160 títulos (144 letreiros). Todos desenham sem erro,
são determinísticos, usam só a paleta da marca e terminam onde devem."""
import json

import numpy as np
import pytest

from motor.audio import som_padrao
from motor.camera import CLASSICAS, transicao
from motor.config import BIBLIOTECA
from motor.efeitos import EXEMPLOS, REGISTRO, criar_efeito
from motor.estilos import GRADES, LOOKS, aplicar_look
from motor.guarda import conferir_edl
from motor.letreiros import ENTRADAS, ESTILOS, TRATAMENTOS, Letreiro
from motor.marca import ErroDeMarca
from motor.transicoes import TRANSICOES

W, H = 270, 480
IDS_SONS = {s["id"] for s in json.loads((BIBLIOTECA / "sons" / "catalogo.json").read_text())["itens"]}


def test_tamanho_das_bibliotecas():
    assert len(REGISTRO) >= 280
    assert len(CLASSICAS) + len(TRANSICOES) >= 110
    assert len(LOOKS) >= 80 and len(GRADES) >= 72
    assert len(ESTILOS) == len(TRATAMENTOS) * len(ENTRADAS) >= 144


def _fundo():
    f = np.zeros((H, W, 3), np.uint8)
    f[:] = np.linspace(40, 180, H)[:, None, None].astype(np.uint8)
    return f


@pytest.mark.parametrize("nome", sorted(REGISTRO))
def test_efeito_desenha_e_e_deterministico(ativa, nome):
    ativa("girahub")
    e = dict({"tipo": "efeito", "nome": nome, "x": 0.5, "y": 0.45, "ini": 0, "fim": 3}, **EXEMPLOS.get(nome, {}))
    if nome == "chuva_3d":
        pytest.skip("depende de renders 3D baixados")
    q = []
    for _ in range(2):
        f = _fundo()
        criar_efeito(e, W, H, 3).desenhar(f, 0.9, 1.5)
        q.append(f)
    assert q[0].dtype == np.uint8 and q[0].shape == (H, W, 3)
    assert np.array_equal(q[0], q[1])


def test_efeitos_recusam_cor_fora_da_paleta(ativa):
    ativa("pontes_brain")
    with pytest.raises(ErroDeMarca):
        criar_efeito({"nome": "traco_oval", "cor": "#ff0000"}, W, H, 0)


@pytest.mark.parametrize("nome", sorted(TRANSICOES))
def test_transicao_vai_do_antigo_ao_novo(ativa, nome):
    ativa("pontes_brain")
    a = np.full((H, W, 3), 30, np.uint8)
    b = np.full((H, W, 3), 200, np.uint8)
    for p in (0.25, 0.5, 0.75):
        m = transicao(a, b, p, nome, W, H)
        assert m.shape == a.shape and m.dtype == np.uint8
    assert np.abs(transicao(a, b, 0.02, nome, W, H).astype(int) - a).mean() < 40  # começa no quadro antigo
    assert np.abs(transicao(a, b, 0.98, nome, W, H).astype(int) - b).mean() < 40  # termina no novo
    assert som_padrao("transicoes", nome) in IDS_SONS


@pytest.mark.parametrize("nome", sorted(GRADES))
def test_grades_de_cor(ativa, nome):
    ativa("leopontesrp")
    f = np.random.default_rng(1).integers(0, 255, (64, 48, 3), dtype=np.uint8)
    out = aplicar_look(f, nome, pele=False)
    assert out.shape == f.shape and out.dtype == np.uint8
    if GRADES[nome][1].get("mono") and "tom" not in GRADES[nome][1] and "s" not in GRADES[nome][1] and "tritom" not in GRADES[nome][1]:
        assert np.array_equal(out[..., 0], out[..., 1])


def test_grade_da_marca_muda_com_a_marca(ativa):
    f = np.full((8, 8, 3), 40, np.uint8)
    ativa("pontes_brain")
    a = aplicar_look(f, "marca_sombras", pele=False)
    ativa("girahub")
    b = aplicar_look(f, "marca_sombras", pele=False)
    assert not np.array_equal(a, b)


@pytest.mark.parametrize("estilo", sorted(ESTILOS))
def test_letreiro_anima_e_some(ativa, estilo):
    ativa("pontes_brain")
    L = Letreiro({"estilo": estilo, "texto": "Primeira linha/segunda"}, 540, 960)
    cheio = L.render(2.0, 2.0)
    assert cheio.ndim == 3 and cheio.shape[2] == 4 and cheio[..., 3].max() > 200
    assert L.render(0.01, 2.0)[..., 3].sum() < cheio[..., 3].sum()  # entra animado
    assert L.render(1.0, 0.0)[..., 3].max() == 0  # some no fim


def test_guarda_recusa_nomes_desconhecidos(ativa):
    ativa("pontes_brain")
    edl = {"marca": "pontes_brain", "segmentos": [{"ini": 0, "fim": 2, "transicao": "cortina_lado_nenhum"}],
           "elementos": [{"tipo": "letreiro", "estilo": "tarja_voa", "texto": "x", "ini": 0, "fim": 1}]}
    with pytest.raises(ErroDeMarca) as err:
        conferir_edl(edl)
    assert "transicao desconhecida" in str(err.value) and "letreiro com estilo desconhecido" in str(err.value)
