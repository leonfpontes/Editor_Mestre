"""Comandos de apoio: `marcas`, `estilos`, `biblioteca` e `conferir`."""
import json
import re
import sys
import urllib.parse
import urllib.request

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .bibliotecas import baixar_faixa, buscar, catalogo, itens, permitido
from .config import BIBLIOTECA
from .marca import CFG, ativar, ler_marca, listar_marcas, politica_musica
from .util import sh

FLUENT = "https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/"


def cmd_marcas(a):
    for mid in listar_marcas():
        c = ler_marca(mid)
        cta = (c.get("cta") or {}).get("url") or "sem CTA"
        print(f"{mid:14s} {c['nome']}")
        print(f"{'':14s} vinheta {c['intro']['tipo']} · fundo {c['fundo_motivo']} · Leo {'sim' if c.get('leo') else 'não'} · "
              f"música {politica_musica(c)} · CTA {cta}")
        print(f"{'':14s} termos exclusivos: {', '.join(c['exclusivo']['termos'])}")


def cmd_estilos(a):
    from .estilos import LOOKS, PRESETS
    from .planos import PLANOS
    print("Estilos (\"estilo\" no EDL ou analisar --estilo):")
    for k, v in PRESETS.items():
        print(f"  {k:18s} {v['descricao']}")
    print("\nPlanos (\"plano\" em cada segmento):")
    for k, v in PLANOS.items():
        print(f"  {k:18s} {v}")
    print("\nLooks de cor (\"look\" em cada segmento):")
    for k, v in LOOKS.items():
        print(f"  {k:18s} {v}")
    print("\nGuia completo: docs/estilos-de-referencia.md")


def catalogo_motor(qual):
    """Catálogos que saem do código do motor: efeitos, transições, looks de cor e letreiros (títulos)."""
    if qual == "efeitos":
        from .efeitos import catalogo_efeitos
        return catalogo_efeitos()
    if qual == "transicoes":
        from .transicoes import catalogo_transicoes
        return catalogo_transicoes()
    if qual == "looks":
        from .estilos import GRADES, LOOKS
        return [{"id": k, "categoria": "grade" if k in GRADES else "classico", "descricao": v} for k, v in LOOKS.items()]
    from .letreiros import catalogo_letreiros
    from .motion import TIPOS
    classicos = [{"id": k, "categoria": "tipo", "descricao": (c.__doc__ or "").strip().split("\n")[0]} for k, c in TIPOS.items()
                 if k != "letreiro"]
    classicos.append({"id": "som (com rotulo)", "categoria": "tipo", "descricao": "Rótulo do som que toca (♪ nome), no canto da tela."})
    return classicos + [dict(it, categoria="letreiro") for it in catalogo_letreiros()]


def _linha(qual, it):
    if qual == "musicas":
        return (f"{it['id']:28s} {it.get('bpm') or '—':>4} bpm  {it['duracao_txt']:>5}  energia {it.get('energia', '?')}  "
                f"{'sob fala' if it.get('sob_fala') else '        '}  {', '.join(it.get('clima', []))}  · {it['genero']}")
    if qual == "3d":
        return f"{it['id']:22s} {it['tipo']:9s} {it['categoria']:14s} {', '.join(it.get('tags', [])[:6])}"
    if qual == "sons":
        return f"{it['id']:18s} {it['categoria']:10s} {it['duracao']:5.2f}s  {it['usos']}"
    return f"{it['id']:24s} {it.get('categoria', ''):12s} {it['descricao']}"


def cmd_biblioteca(a):
    if a.marca:
        ativar(a.marca)
    if a.acao == "listar":
        if not a.qual:
            sys.exit("diga qual biblioteca: 3d, musicas, efeitos, sons, transicoes, looks ou titulos")
        if a.qual in ("efeitos", "transicoes", "looks", "titulos"):
            lista = catalogo_motor(a.qual)
            lista = [e for e in lista if not a.categoria or e.get("categoria") == a.categoria]
            termo = " ".join(a.termo).lower()
            lista = [e for e in lista if termo in json.dumps(e, ensure_ascii=False).lower()]
        else:
            lista = buscar(a.qual, " ".join(a.termo) or None, clima=a.clima, categoria=a.categoria, genero=a.genero)
        if a.json:
            print(json.dumps(lista, ensure_ascii=False, indent=1))
        else:
            for it in lista:
                print(_linha(a.qual, it))
            print(f"\n{len(lista)} itens" + (f" que servem à marca {a.marca}" if a.marca else ""))
    elif a.acao == "baixar":
        if a.qual in (None, "musicas"):
            for it in itens("musicas"):
                if (a.marca and not permitido(it)) or (a.termo and it["id"] not in a.termo):
                    continue
                print(f"  {it['id']}…", end=" ", flush=True)
                baixar_faixa(it)
                print("ok")
        if a.qual == "3d":
            for nome in a.termo:
                baixar_fluent(nome)
    elif a.acao == "criar":
        if a.qual != "3d":
            sys.exit("só a biblioteca 3d cria objetos: editor.py biblioteca criar 3d <nome> [--fluent N] [--emoji E] [--texto T --marca X]")
        from .criar3d import criar_3d
        nome = " ".join(a.termo)
        iid, como = criar_3d(nome, a.fluent, a.emoji, a.texto)
        sys.exit(f"não criei {nome}: {como}") if not iid else print(f"criado: {iid} ({como})")
    elif a.acao == "verificar":
        sys.exit(0 if verificar_bibliotecas() else 1)
    elif a.acao == "catalogo":
        from .efeitos import catalogo_efeitos
        p = BIBLIOTECA / "efeitos" / "catalogo.json"
        p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps({"versao": 1, "fonte": "gerado de motor/efeitos.py (`editor.py biblioteca catalogo`)",
                                 "itens": catalogo_efeitos()}, ensure_ascii=False, indent=1) + "\n")
        print(f"gravado: {p}")
    elif a.acao == "previa":
        if not a.marca:
            sys.exit("a prévia usa a paleta de uma marca: passe --marca")
        saida = a.saida or f"previa-{a.qual}-{a.marca}.png"
        if a.qual == "efeitos":
            img = previa_efeitos(categoria=a.categoria)
        else:
            img = {"3d": previa_3d, "transicoes": previa_transicoes, "looks": previa_looks, "titulos": previa_titulos}[a.qual]()
        cv2.imwrite(saida, img)
        print(f"gravado: {saida}")


def verificar_bibliotecas():
    """Confere catálogos, licenças e arquivos. Devolve True se estiver tudo certo."""
    from .bibliotecas import LICENCAS_LIVRES
    from .efeitos import catalogo_efeitos
    ok = True
    for qual in ("3d", "musicas", "sons"):
        ids = set()
        for it in itens(qual):
            if it["id"] in ids:
                print(f"[{qual}] id repetido: {it['id']}")
                ok = False
            ids.add(it["id"])
            if it.get("licenca") not in LICENCAS_LIVRES:
                print(f"[{qual}] {it['id']}: licença fora da lista livre: {it.get('licenca')}")
                ok = False
            p = BIBLIOTECA / qual / it["arquivo"]
            if qual in ("3d", "sons") and not p.exists():
                print(f"[{qual}] {it['id']}: arquivo ausente {p}")
                ok = False
            for m in it.get("marcas", []):
                if m not in listar_marcas():
                    print(f"[{qual}] {it['id']}: marca desconhecida em \"marcas\": {m}")
                    ok = False
    baixadas = sum((BIBLIOTECA / "musicas" / it["arquivo"]).exists() for it in itens("musicas"))
    gravado = json.loads((BIBLIOTECA / "efeitos" / "catalogo.json").read_text())["itens"]
    if gravado != json.loads(json.dumps(catalogo_efeitos(), ensure_ascii=False)):
        print("[efeitos] catalogo.json desatualizado: rode `editor.py biblioteca catalogo`")
        ok = False
    for e in catalogo_efeitos():
        if e.get("som") and e["som"] not in {it["id"] for it in itens("sons")}:
            print(f"[efeitos] {e['id']}: som padrão desconhecido: {e['som']}")
            ok = False
    print(f"3D: {len(itens('3d'))} objetos · músicas: {len(itens('musicas'))} faixas ({baixadas} baixadas) · "
          f"efeitos: {len(catalogo_efeitos())} · sons: {len(itens('sons'))}")
    print("TUDO OK" if ok else "HÁ PROBLEMAS")
    return ok


def baixar_fluent(nome):
    """Acrescenta um emoji 3D do Microsoft Fluent Emoji (MIT) à biblioteca, pelo nome da pasta (ex.: "Rocket")."""
    pasta = urllib.parse.quote(nome)
    meta = json.loads(urllib.request.urlopen(FLUENT + pasta + "/metadata.json", timeout=60).read())
    slug = re.sub(r"[^a-z0-9-]+", "_", nome.lower()).strip("_")
    for sub in [f"{d}{s}_3d{x}.png" for s in {slug, slug.replace("-", "_")} for d, x in (("3D/", ""), ("Default/3D/", "_default"))]:
        try:
            png = urllib.request.urlopen(FLUENT + pasta + "/" + urllib.parse.quote(sub), timeout=60).read()
            break
        except Exception:
            png = None
    if not png:
        sys.exit(f"não achei a versão 3D de {nome}")
    iid = slug.replace("_", "-")
    destino = BIBLIOTECA / "3d" / "renders" / f"{iid}.png"
    destino.write_bytes(png)
    cat = json.loads((BIBLIOTECA / "3d" / "catalogo.json").read_text())
    if not any(it["id"] == iid for it in cat["itens"]):
        cat["itens"].append({"id": iid, "nome": nome, "tipo": "render", "categoria": "outros",
                             "tags": meta.get("keywords", [])[:8], "arquivo": f"renders/{iid}.png",
                             "fonte": "Microsoft Fluent Emoji 3D", "licenca": "MIT", "fluent": nome})
        (BIBLIOTECA / "3d" / "catalogo.json").write_text(json.dumps(cat, ensure_ascii=False, indent=1) + "\n")
    print(f"acrescentado: {iid} ({destino})")


def _grade(quadros, rotulos, colunas, w=270, h=480, titulo_cor=(255, 255, 255)):
    from .graficos import fonte
    f = fonte("Bold", 22)
    celulas = []
    for q, r in zip(quadros, rotulos):
        im = Image.fromarray(cv2.cvtColor(cv2.resize(q, (w, h), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB))
        d = ImageDraw.Draw(im)
        d.rectangle([0, h - 40, w, h], fill=(0, 0, 0))
        d.text((w / 2, h - 20), r, font=f, fill=titulo_cor, anchor="mm")
        celulas.append(cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR))
    while len(celulas) % colunas:
        celulas.append(np.zeros_like(celulas[0]))
    linhas = [np.hstack(celulas[i:i + colunas]) for i in range(0, len(celulas), colunas)]
    return np.vstack(linhas)


def previa_efeitos(W=540, H=960, categoria=None, nomes=None, colunas=10):
    from .efeitos import REGISTRO, quadro_exemplo
    from .fundo import FundoMarca
    fundo = FundoMarca(W, H)
    instante = {"confete": 0.55, "flash": 0.12, "glitch": 0.1, "tremor": 0.08, "brilhos": 0.7, "contador": 1.4,
                "vazamento_luz": 0.9, "chuva_3d": 1.2, "check": 0.8, "xis": 0.8, "persiana": 0.3, "cortina_luz": 0.4}
    nomes = nomes or sorted(n for n, c in REGISTRO.items() if not categoria or c.categoria == categoria)
    q = [quadro_exemplo(n, W, H, instante.get(n, 1.0), fundo) for n in nomes]
    return _grade(q, nomes, colunas)


def _quadros_ab(W, H):
    """Dois quadros bem diferentes da marca ativa para mostrar uma transição (A sai, B entra)."""
    from .fundo import FundoMarca
    from .graficos import fonte
    fundo = FundoMarca(W, H)
    a = fundo.quadro(0.5)
    b = cv2.cvtColor(cv2.flip(fundo.quadro(1.5), 1), cv2.COLOR_BGR2HSV)
    b[..., 0] = (b[..., 0].astype(np.int32) + 30) % 180
    b = cv2.cvtColor(b, cv2.COLOR_HSV2BGR)
    for img, t in ((a, "A"), (b, "B")):
        im = Image.fromarray(img)
        ImageDraw.Draw(im).text((W / 2, H / 2), t, font=fonte("Black", int(W * 0.5)), fill=(240, 240, 240), anchor="mm")
        img[:] = np.array(im)
    return a, b


def previa_transicoes(W=540, H=960, p=0.4):
    from .camera import transicao
    from .transicoes import catalogo_transicoes
    a, b = _quadros_ab(W, H)
    nomes = [t["id"] for t in catalogo_transicoes()]
    return _grade([transicao(a, b, p, n, W, H) for n in nomes], nomes, 12)


def previa_looks(foto=None):
    from .estilos import LOOKS, aplicar_look
    f = cv2.imread(str(foto or BIBLIOTECA.parent / "docs" / "img" / "vitrine-leopontesrp.jpg"))
    f = cv2.resize(f, (540, int(540 * f.shape[0] / f.shape[1])))[:960]
    alfa = np.zeros(f.shape[:2] + (1,), np.float32)
    alfa[f.shape[0] // 5:, f.shape[1] // 4:3 * f.shape[1] // 4] = 1
    nomes = list(LOOKS)
    return _grade([aplicar_look(f.copy(), n, alfa) for n in nomes], nomes, 10)


def previa_titulos(W=1080, H=1920, dt=1.5):
    from .fundo import FundoMarca
    from .letreiros import ENTRADAS, TRATAMENTOS, Letreiro
    fundo = FundoMarca(W // 2, H // 2)
    q, nomes = [], []
    for t in TRATAMENTOS:  # um quadro por tratamento (as entradas só mudam o movimento)
        f = fundo.quadro(1.0)
        sp = Letreiro({"estilo": f"{t}_surge", "texto": "O problema certo/vem antes"}, W, H).render(dt, 2.0)
        s = min((f.shape[1] - 20) / sp.shape[1], 0.5)
        sp = cv2.resize(sp, (int(sp.shape[1] * s), int(sp.shape[0] * s)), interpolation=cv2.INTER_AREA)
        y0, x0 = (f.shape[0] - sp.shape[0]) // 2, (f.shape[1] - sp.shape[1]) // 2
        al = sp[..., 3:4] / 255.0
        roi = f[y0:y0 + sp.shape[0], x0:x0 + sp.shape[1]]
        roi[:] = (roi * (1 - al) + sp[..., 2::-1] * al).astype(np.uint8)
        q.append(f)
        nomes.append(f"{t} ×{len(ENTRADAS)}")
    return _grade(q, nomes, 6)


def previa_3d(lado=180):
    from .graficos import fonte
    lst = [it for it in itens("3d") if not CFG or permitido(it)]
    f = fonte("Bold", 16)
    col = 10
    cel = []
    for it in lst:
        im = Image.new("RGB", (lado, lado + 28), (24, 24, 28))
        obj = Image.open(BIBLIOTECA / "3d" / it["arquivo"]).convert("RGBA")
        obj = obj.crop(obj.getbbox())
        obj.thumbnail((lado - 30, lado - 30), Image.LANCZOS)
        im.paste(obj, ((lado - obj.width) // 2, (lado - obj.height) // 2), obj)
        ImageDraw.Draw(im).text((lado / 2, lado + 12), it["id"], font=f, fill=(230, 230, 230), anchor="mm")
        cel.append(np.array(im))
    while len(cel) % col:
        cel.append(np.full_like(cel[0], 24))
    return cv2.cvtColor(np.vstack([np.hstack(cel[i:i + col]) for i in range(0, len(cel), col)]), cv2.COLOR_RGB2BGR)


def cmd_conferir(a):
    """Lê o selo gravado no vídeo pelo render (comment=marca=<id>) e compara com a marca esperada."""
    out = json.loads(sh(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", a.video]))
    comentario = out["format"].get("tags", {}).get("comment", "")
    m = re.search(r"marca=([a-z0-9_]+)", comentario)
    if not m:
        sys.exit(f"{a.video}: sem selo de marca (não saiu deste editor, ou é de uma versão antiga)")
    if m.group(1) != a.marca:
        sys.exit(f"{a.video}: é da marca {m.group(1)}, não de {a.marca}. NÃO entregue.")
    print(f"{a.video}: marca {m.group(1)} confere.")


__all__ = ["cmd_marcas", "cmd_biblioteca", "cmd_conferir", "catalogo"]
