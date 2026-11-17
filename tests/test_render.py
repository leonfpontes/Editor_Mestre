"""Peças do render: divisão em trechos paralelos, caminhos relativos ao EDL e LUTs de cor."""
import numpy as np

from motor.cor import aplicar_cor, lut_cor
from motor.renderizar import caminho_edl, dividir_trechos, resolver_caminhos


def segs(*ns):
    return [{"n": n} for n in ns]


def test_trechos_cobrem_tudo_em_ordem():
    for lst in (segs(90), segs(30, 30, 30, 30, 30, 30), segs(200, 10, 10, 10, 300, 45)):
        for n in (1, 2, 4, 12):
            g = dividir_trechos(lst, n)
            assert g[0][0] == 0 and g[-1][1] == len(lst)
            assert all(a[1] == b[0] for a, b in zip(g, g[1:]))
            assert len(g) <= n


def test_trechos_nao_ficam_curtos_demais():
    assert len(dividir_trechos(segs(10, 10, 10), 8)) == 1  # 1 s de vídeo não vale vários processos


def test_caminhos_relativos_a_pasta_do_edl(tmp_path):
    (tmp_path / "tela.png").write_bytes(b"x")
    assert caminho_edl("tela.png", tmp_path) == str(tmp_path / "tela.png")
    assert caminho_edl("id-da-biblioteca", tmp_path) == "id-da-biblioteca"
    assert caminho_edl("/abs/x.mp4", tmp_path) == "/abs/x.mp4"
    edl = resolver_caminhos({"elementos": [{"tipo": "broll", "arquivo": "tela.png"}]}, tmp_path)
    assert edl["elementos"][0]["arquivo"] == str(tmp_path / "tela.png")


def test_lut_de_cor_igual_ao_calculo_canal_a_canal():
    c = {"contraste": 1.1, "calor": 0.05}
    f = np.random.default_rng(0).integers(0, 255, (40, 30, 3), np.uint8)
    x = np.arange(256, dtype=np.float32)
    y = (x - 128) * 1.1 + 128
    ref = np.stack([np.clip(y * 0.95, 0, 255).astype(np.uint8)[f[..., 0]], np.clip(y, 0, 255).astype(np.uint8)[f[..., 1]],
                    np.clip(y * 1.05, 0, 255).astype(np.uint8)[f[..., 2]]], -1)
    assert np.array_equal(aplicar_cor(f, lut_cor(c), c), ref)
