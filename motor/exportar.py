"""`exportar`: a entrega completa de um vídeo já renderizado, pronta para postar.

Gera, na pasta do EDL:
- `legenda.srt`: legendas com os tempos do vídeo final (para YouTube, LinkedIn e acessibilidade);
- `capa.jpg`: quadro limpo e nítido do vídeo (sem legenda), com o título do EDL se houver (`"capa": {"texto"}`);
- `post.txt`: rascunho da legenda do post: a frase de abertura, o CTA e as hashtags da marca e o crédito da música;
- `reel.mp4`: o final.mp4 dentro do limite de 20 MB do publicador (reencoda só se passar);
- `agenda-entrada.json`: o post no formato da agenda do insta_report (com `--quando`);
- `final_<formato>.mp4`: outros formatos do mesmo EDL (`--formatos feed,horizontal`).

Nada aqui publica: a publicação é do Leonardo (ou do PR na agenda do insta_report).
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import cv2

from .config import FPS, RAIZ
from .graficos import Cartao, blend
from .marca import CFG
from .renderizar import Contexto, Trecho
from .util import sh

LIMITE_MB = 20
CONTAS = {"pontes_brain": ("pontes_brain", "pb"), "girahub": ("GiraHub", "gh"), "leopontesrp": ("leopontesrp", "lp")}


def _tempo_srt(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def blocos_srt(ctx, max_chars=42, max_palavras=8):
    """Blocos de legenda (início, fim, texto) no vídeo final: quebra em pausa, pontuação ou tamanho."""
    corr = {k.lower(): v for k, v in ctx.edl.get("legendas", {}).get("correcoes", {}).items()}
    ws = [dict(w, t=corr.get(w["t"].lower(), w["t"])) for w in ctx.an["palavras"]
          if any(qa <= (w["ini"] + w["fim"]) / 2 < qb for qa, qb in ctx.keep)]
    out, atual = [], []
    for i, w in enumerate(ws):
        atual.append(w)
        prox = ws[i + 1] if i + 1 < len(ws) else None
        txt = " ".join(x["t"] for x in atual)
        quebra = (prox is None or w["t"][-1:] in ".?!" or len(atual) >= max_palavras or len(txt) >= max_chars
                  or ctx.map_out(prox["ini"]) - ctx.map_out(w["fim"]) > 0.4 or (w["t"][-1:] == "," and len(atual) >= 4))
        if quebra:
            a, b = ctx.map_out(atual[0]["ini"]), ctx.map_out(atual[-1]["fim"])
            out.append((ctx.dur_intro + a, ctx.dur_intro + max(b, a + 0.4), txt))
            atual = []
    return out


def escrever_srt(ctx, arq):
    bl = blocos_srt(ctx)
    with open(arq, "w") as f:
        for k, (a, b, txt) in enumerate(bl, 1):
            f.write(f"{k}\n{_tempo_srt(a)} --> {_tempo_srt(b)}\n{txt}\n\n")
    return len(bl)


def nitidez(img):
    g = cv2.cvtColor(cv2.resize(img, (270, 480)), cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(g, cv2.CV_64F).var())


def escolher_quadro(ctx):
    """Segmento e quadro da capa: o pedido em "capa": {"t": s do vídeo final}, ou o mais nítido com rosto na primeira metade."""
    capa = ctx.edl.get("capa", {}) if isinstance(ctx.edl.get("capa"), dict) else {}
    alvo = int(round((capa["t"] - ctx.dur_intro) * FPS)) if "t" in capa else None
    cap = cv2.VideoCapture(ctx.src)
    melhor, acum = None, 0
    for i, s in enumerate(ctx.segs):
        if alvo is not None:
            if acum <= alvo < acum + s["n"]:
                return i, s["ia"] + alvo - acum
            acum += s["n"]
            continue
        if s.get("plano", "rosto") == "motion" or acum > sum(x["n"] for x in ctx.segs) * 0.6:
            acum += s["n"]
            continue
        for frac in (0.3, 0.6):
            fi = s["ia"] + int(s["n"] * frac)
            cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
            ok, f = cap.read()
            if not ok:
                continue
            r = ctx.rosto.em(fi / FPS)
            nota = nitidez(f) * (1.4 if r and r[2] > 0.08 else 1.0)
            if melhor is None or nota > melhor[0]:
                melhor = (nota, i, fi)
        acum += s["n"]
    cap.release()
    return (melhor[1], melhor[2]) if melhor else (0, ctx.segs[0]["ia"])


def gerar_capa(ctx, arq):
    """Quadro limpo (enquadramento, cor e look do vídeo, sem legenda nem elementos) com o título, se o EDL pedir."""
    i, fi = escolher_quadro(ctx)
    tr = Trecho(ctx)
    tr.aquecer(i)
    s = ctx.segs[i]
    for k in range(s["ia"], fi):  # a câmera chega ao quadro escolhido como no vídeo
        tr.camera.passo(s.get("zoom", 1.0), ctx.rosto.em(k / FPS))
    f = tr.ler(fi)
    t_out = (ctx.quadros_antes(i) + fi - s["ia"]) / FPS - ctx.dur_intro
    base = tr.base(s, fi, f, t_out).copy()
    capa = ctx.edl.get("capa", {}) if isinstance(ctx.edl.get("capa"), dict) else {}
    texto = capa.get("texto") or next((e.get("texto") for e in ctx.edl.get("elementos", []) if e.get("tipo") == "titulo"), None)
    if texto:
        img = Cartao(texto, ctx.W * 0.86, "titulo").render(2.0, 9)
        blend(base, img, ctx.W / 2 - img.shape[1] / 2, ctx.H * capa.get("y", 0.16))
    cv2.imwrite(str(arq), base, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return texto


def texto_post(ctx, faixa=None):
    """Rascunho da legenda do post: a frase de abertura (o que já está dito no vídeo), o crédito da música, as hashtags
    da marca ("post": {"hashtags"}) e, por último, o CTA da marca ("post": {"cta"} ou a chamada e o link do "cta").
    É rascunho: o texto final é do Leonardo."""
    ws = [w for w in ctx.an["palavras"] if any(qa <= (w["ini"] + w["fim"]) / 2 < qb for qa, qb in ctx.keep)]
    frase = []
    for w in ws:
        frase.append(w["t"])
        if w["t"][-1:] in ".?!" and len(frase) >= 5:
            break
    post, cta = CFG.get("post", {}), CFG.get("cta", {})
    chamada = post.get("cta") or " ".join(x for x in (cta.get("chamada"), cta.get("url")) if x)
    partes = [" ".join(frase[:40]).strip()]
    if faixa:
        partes.append(faixa["credito"])
    if post.get("hashtags"):
        partes.append(" ".join(post["hashtags"]))
    partes.append(chamada)  # o CTA fecha a legenda (regra do @pontes_brain: termina no link da mentoria)
    return "\n\n".join(p for p in partes if p)


def reel_instagram(final, arq):
    """Cópia do vídeo dentro de 20 MB (o publicador usa jsDelivr, que recusa acima disso)."""
    mb = final.stat().st_size / 1e6
    if mb <= LIMITE_MB * 0.97:
        sh(["ffmpeg", "-y", "-i", str(final), "-c", "copy", "-movflags", "+faststart", str(arq)])
        return mb, False
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(final)],
                               capture_output=True, text=True).stdout or 60)
    kbps = int(min(4800, (LIMITE_MB * 0.92 * 8000) / dur - 192))
    sh(["ffmpeg", "-y", "-i", str(final), "-c:v", "libx264", "-crf", "20", "-maxrate", f"{kbps}k", "-bufsize", f"{2 * kbps}k",
        "-c:a", "copy", "-movflags", "+faststart", str(arq)])
    return arq.stat().st_size / 1e6, True


def entrada_agenda(ctx, quando, legenda, titulo):
    conta, prefixo = CONTAS.get(CFG["id"], (CFG["id"], CFG["id"][:2]))
    dt = datetime.fromisoformat(quando)
    pid = f"{prefixo}-{dt:%m%d-%H%M}"
    pasta = conta.lower()
    return {"id": pid, "conta": conta, "quando": quando, "formato": "reel", "status": "agendado", "titulo": titulo,
            "legenda": legenda, "midia": [f"midia/{pasta}/{pid}.mp4"], "capa": f"midia/{pasta}/{pid}-capa.jpg"}


def cmd_exportar(a):
    edl_p = Path(a.edl).resolve()
    ctx = Contexto(edl_p, falar=True, rapido=True)
    pasta = ctx.pasta
    final = pasta / (ctx.edl.get("saida") or "final.mp4")
    if not final.exists():
        sys.exit(f"Não achei {final.name}: rode `editor.py renderizar {a.edl}` antes de exportar.")
    man = json.load(open(pasta / "manifesto.json")) if (pasta / "manifesto.json").exists() else {}
    if man.get("marca") and man["marca"] != CFG["id"]:
        sys.exit(f"o final.mp4 é da marca {man['marca']}, não de {CFG['id']}")
    n = escrever_srt(ctx, pasta / "legenda.srt")
    print(f"legenda.srt: {n} blocos")
    titulo_capa = gerar_capa(ctx, pasta / "capa.jpg")
    print("capa.jpg" + (f" com o título \"{titulo_capa}\"" if titulo_capa else " (sem título: ponha \"capa\": {\"texto\": …} no EDL)"))
    faixa = man.get("musica")
    legenda = texto_post(ctx, faixa)
    (pasta / "post.txt").write_text(legenda + "\n")
    print("post.txt: rascunho da legenda do post (revise antes de publicar)")
    mb, reenc = reel_instagram(final, pasta / "reel.mp4")
    print(f"reel.mp4: {mb:.1f} MB" + (" (reencodado para caber em 20 MB)" if reenc else ""))
    if a.quando:
        titulo = (titulo_capa or legenda.split("\n")[0])[:70]
        ent = entrada_agenda(ctx, a.quando, legenda, titulo)
        json.dump(ent, open(pasta / "agenda-entrada.json", "w"), ensure_ascii=False, indent=1)
        print(f"agenda-entrada.json: {ent['id']} ({ent['conta']}, {ent['quando']}). Copie reel.mp4 e capa.jpg para "
              f"{ent['midia'][0]} e {ent['capa']} no insta_report e acrescente a entrada no fim de posts, por PR.")
    for fmt in [f.strip() for f in (a.formatos or "").split(",") if f.strip()]:
        print(f"renderizando o formato {fmt}…", flush=True)
        r = subprocess.run([sys.executable, str(RAIZ / "editor.py"), "renderizar", str(edl_p), "--formato", fmt],
                           capture_output=True, text=True)
        print(r.stdout.strip().splitlines()[-1] if r.returncode == 0 and r.stdout.strip() else f"falhou: {r.stderr[-500:]}")
    print(f"Exportado em {pasta}")


