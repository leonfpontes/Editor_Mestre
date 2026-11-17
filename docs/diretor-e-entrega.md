# Diretor, prévia, conferência e entrega

O caminho de um vídeo, do bruto ao post agendado:

```bash
.venv/bin/python editor.py analisar VIDEO --marca <marca> [--estilo tutorial_passos]   # rascunho já dirigido
.venv/bin/python editor.py renderizar P/edl.json --previa --de 0 --ate 8               # revisar um trecho em segundos
.venv/bin/python editor.py renderizar P/edl.json                                       # final + conferência visual
.venv/bin/python editor.py linha-do-tempo P/edl.json                                   # página para revisar a edição
.venv/bin/python editor.py exportar P/edl.json --quando 2026-11-20T19:00:00-03:00      # SRT, capa, post, reel, agenda
```

## Diretor automático (`analisar`)

Depois de transcrever, o `analisar` dirige o rascunho. Tudo é proposta: o agente lê `diretor.json` e o resumo no fim da
`transcricao.txt` antes de renderizar. O diretor nunca inventa fala: só corta o que foi dito a mais e marca o que já está
no vídeo. `--sem-diretor` volta ao rascunho cru.

| O que faz | Como |
|---|---|
| **Vícios** | Corta "ãh", "hum", "éé", "né" no fim de frase, "tipo," de muleta e palavra gaguejada ("eu eu"). "Um", "é" e "ah" ficam: são palavras de verdade |
| **Tomadas repetidas** | Quando a frase seguinte (ou a próxima depois de um "não, peraí") recomeça igual, fica só a última tomada |
| **Ênfases** | `legendas.enfase` com as palavras mais fortes: voz acima da vizinhança, números, palavras como "nunca" e "segredo"; uma a cada 2,5 s no máximo |
| **Zoom nos cortes** | Em jump cut no mesmo plano, alterna o enquadramento (1.0 ↔ 1.08) com `"salto": true` (a câmera troca no corte, sem deslizar). Marcas com enquadramento contínuo desligam no `marca.json` com `"diretor": {"alternar_zoom": false}` (@pontes_brain e GiraHub) |
| **Punch** | `zooms` com tranco nas 1 a 3 ênfases mais fortes |
| **Gancho** | Nota de 0 a 10 para os primeiros 3 s (saudação e ritmo lento descontam; pergunta, número e "você" somam) e a frase mais forte do vídeo, quando ela é bem melhor que a abertura. Para abrir com ela, copie o trecho para o início com `"gancho": true` |
| **Elementos** | Contador em "40%", `passo` (no estilo `tutorial_passos`) ou `destaque` em "primeiro passo", `check` em "certo", `xis` em "errado", todos ancorados na fala |
| **Termos de b-roll** | As palavras de conteúdo que mais aparecem, para `editor.py broll` |

## Prévia rápida (`renderizar --previa`)

`--previa` desenha 10 quadros por segundo e só a janela de `--de` a `--ate` (segundos do vídeo final), com o áudio de
verdade, em `previa.mp4`. Serve para conferir um ajuste do EDL em segundos. Não é o vídeo final.

## Velocidade

- O render divide o vídeo em trechos e usa um processo por núcleo (até 8). `--processos 1` desliga.
- Cada trecho aquece a câmera e o recorte com o fim do trecho anterior, então o resultado é igual ao do render corrido.
- O recorte da pessoa (a parte mais cara) fica em cache em `P/_cache/`: o segundo render do mesmo vídeo é várias vezes
  mais rápido. Para desligar, use `"cache_recorte": false`. Apague `_cache` para liberar espaço.
- Os looks e a correção de cor são LUTs (uma passada no quadro). A tela em perspectiva desfoca em resolução reduzida.

## Conferência visual

Todo render (menos `--so-audio` e `--sem-conferencia`) confere um quadro a cada 5 e grava `conferencia.json`:

- elemento ou legenda fora da área segura do Reels: 5–95% na largura, 9–80% na altura e longe dos botões à direita;
- elemento cobrindo o rosto (no plano `rosto`);
- legenda em cima do rosto ou brigando com um elemento;
- legenda `limpa` sobre fundo claro (sem contraste);
- loudness fora de −17,5 a −14,5 LUFS ou pico acima de −1 dBFS;
- vídeo com mais de 90 s;
- gancho com nota abaixo de 6 sem segmento `gancho`.

"Confere" no terminal é a meta. Cada aviso traz o trecho e o que mudar.

## Linha do tempo (`linha-do-tempo`)

Gera `P/linha_do_tempo.html`, com o vídeo (`final.mp4` ou `previa.mp4`) e as trilhas:

- cortes, planos e looks
- b-roll e elementos
- zooms, legenda e sons
- avisos da conferência

Clicar num bloco leva o vídeo ao instante e mostra os detalhes. Abra no navegador, na pasta do vídeo.

## Entrega (`exportar`)

| Arquivo | O que é |
|---|---|
| `legenda.srt` | Legendas no tempo do vídeo final, quebradas por pausa, pontuação e tamanho |
| `capa.jpg` | Quadro limpo e nítido (sem legenda), com o título de `"capa": {"texto": "…", "t": 4.2, "y": 0.16}` ou do primeiro `titulo` |
| `post.txt` | Rascunho da legenda do post. Leva a frase de abertura, o crédito da música e as hashtags da marca (`"post": {"hashtags": […]}`), e termina no CTA da marca |
| `reel.mp4` | O vídeo dentro de 20 MB, o limite do publicador |
| `agenda-entrada.json` | Com `--quando`: o post no formato da agenda do insta_report |
| `final_<formato>.mp4` | Com `--formatos feed,horizontal`: o mesmo EDL em outro formato |

Com `--insta-report <clone>`, o `exportar` também prepara o post no insta_report:

- copia o reel e a capa para `instagram/midia/…`;
- acrescenta o post no fim de `posts`, com sufixo se o id repetir.

Não faz commit: o resto segue o fluxo do insta_report (branch, PR, ok do Leonardo, merge). Nada aqui publica.

## B-roll de banco (`broll`)

```bash
export PEXELS_API_KEY=…   # grátis em pexels.com/api; nunca vai para o repositório nem para o EDL
.venv/bin/python editor.py broll "reunião de equipe" P/edl.json             # lista opções verticais
.venv/bin/python editor.py broll "reunião de equipe" P/edl.json --baixar 2  # baixa para P/broll/ e mostra o elemento
```

A licença do Pexels permite uso comercial sem crédito. A origem de cada vídeo fica em `P/broll/pexels-<id>.json`.

## Cor

| Campo de `cor` | O que faz |
|---|---|
| `lut` | LUT 3D `.cube` (caminho, ou id em `biblioteca/luts/<id>.cube`). Aplicada depois da correção básica |
| `lut_intensidade` | 0 a 1 (padrão 1): mistura a LUT com a imagem |
| `proteger_pele` | `true` (padrão): nos looks `quente`, `frio`, `noite` e `limpo`, a pele fica perto do tom original |
| `igualar_clipes` | `true` (padrão): com vários clipes, o `analisar` mede a cor de cada um e o render deixa todos iguais |
