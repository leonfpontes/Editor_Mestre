# Estilos de referência

Três estilos de edição estudados em Reels de outros criadores (gravações de tela do Instagram, novembro de 2026). Cada
estilo vira uma receita: o que se vê, os números medidos, como montar com o motor de hoje e o que ainda falta construir.
As receitas não carregam a identidade de ninguém: cores, fontes e CTA vêm sempre da marca do vídeo (`marcas/<id>/`).

Como foi medido: cortes por detecção de cena do ffmpeg (`select='gt(scene,0.2)'`), quadros a cada 0,5 s a 2 s,
transcrição com `faster-whisper small` com tempo por palavra, e volume das pausas entre palavras para saber se há trilha.

| | A. Tela em perspectiva | B. Tutorial em passos | C. Vitrine de estilos |
|---|---|---|---|
| Duração | 71 s | 74 s | 44 s (gravação começou no meio) |
| Fala | 241 palavras/min, narração | 267 palavras/min, para a câmera | 221 palavras/min, para a câmera |
| Cortes de plano | 1 (só no fim) | 17 cortes + troca de motion a cada 1 a 3 s | 32 (um a cada 1,4 s) |
| Maior pausa mantida | 0,78 s | 0,44 s | 0,38 s |
| Trilha | Cama baixa (pausas a −35 dB) | Nenhuma (pausas a −40 dB) | Música e efeitos o tempo todo (pausas a −27 dB) |
| Legenda corrida | Não | Sim, 1 ou 2 palavras | Não; a tipografia é cenográfica |
| Serve para | Demonstrar produto, sistema, painel | Ensinar passo a passo | Anúncio, lançamento, mostrar alcance |

## A. Tela em perspectiva

Narração por cima de uma gravação de tela que parece filmada por uma câmera de cinema. O rosto só aparece no fim.

**O que se vê**

- **Gancho (0 a 3 s):** título em duas linhas no canto superior esquerdo, texto preto em sans bold sobre caixas brancas
  justas, uma por linha, com um colchete fino na cor de acento abraçando o canto. Some antes de a tela começar a andar.
- **Tela num plano 3D:** a gravação de tela (interface escura) fica num plano inclinado, com a câmera virtual fazendo
  travelling, inclinação e aproximação. Profundidade de campo rasa: a borda do plano desfoca, o centro fica nítido.
- **Luz quente:** um bokeh laranja grande e fixo à esquerda, como reflexo de luminária no vidro. Dá calor a uma UI fria.
- **Ritmo sem corte:** um único plano por 67 s; o movimento de câmera muda a cada 2 a 4 s (novo enquadramento, novo foco),
  sempre indo para o elemento que a fala cita ("marketing", "vendas", "integrações").
- **Fecho (últimos 3,5 s):** corte seco para o rosto, fala curta com o CTA verbal ("a metodologia está aqui embaixo").
- **Áudio:** voz limpa, cama musical muito baixa. Sem efeitos sonoros perceptíveis.

**Como montar hoje**

- `segmentos`: a narração inteira, pausas acima de 0,3 s cortadas.
- `elementos`: `broll` com a gravação de tela cobrindo do gancho até o fecho; `titulo` no gancho; efeitos `bokeh` e
  `vazamento_luz` (cor `acento` ou `quente`) e `foco` para simular o desfoque de borda.
- `musica` com `volume_db` em torno de −26 e `ducking`.
- `legendas.ativo: false` (a tela já é o assunto).

**O que falta no motor**

1. `broll` em perspectiva: plano 3D com rotação X/Y, trajetória de câmera por pontos-chave ancorados na fala e
   profundidade de campo (desfoque por distância ao centro).
2. Título "caixa justa": cada linha numa caixa do tamanho do texto, com o colchete de canto.

## B. Tutorial em passos

Tutorial falado em quatro passos, com uma folha de estilo explícita (aparece no próprio vídeo). É o estilo mais fácil
de copiar e o mais útil para vender como produto, porque é uma regra simples aplicada com disciplina.

**Três planos, troca em corte seco**

| Plano | Quando | Composição |
|---|---|---|
| Rosto | Opinião, gancho, conversa | Câmera ocupa a tela inteira |
| Dividido | Explicando algo que dá para mostrar | Metade de cima: fundo escuro com motion. Metade de baixo: o rosto |
| Só motion | Quando a imagem explica sozinha | Tela inteira de motion; a voz continua |

A troca entre planos é sempre corte seco, sem transição. Regra do vídeo: **nada parado por mais de três segundos**; dentro
de um plano, o motion muda de estado (ícone entra, pasta abre, linha se desenha) a cada 1 a 2 s.

**Legenda**

- 1 ou 2 palavras por vez, sem caixa e sem contorno pesado, branco quase puro, sans semibold, em caixa normal.
- Posição: na linha que divide os planos (no dividido) ou em torno de 62% da altura (rosto cheio).
- Sem palavra em destaque: o motion faz a ênfase.

**Cabeçalho de passo**

- No topo do motion, sempre visível enquanto o passo dura: `Passo 1.` em serifa itálica + `Monta o ambiente` em sans bold.
- Regra tipográfica: sans no texto do passo, serifa só no número.

**Motion**

- Fundo quase preto e liso, superfície um tom acima. Paleta medida: fundo `#0B0B0C`, superfície `#151517`, texto
  `#F5F5F3`, cinza `#A3A3A8` e um único acento (no vídeo, vermelho).
- **Objeto externo leva a identidade dele:** pasta azul do sistema, ícone colorido do app, janela do app como ela é,
  com sombra e profundidade. O que é da marca fica na cor da marca; o resto, na cor dele.
- Recursos usados: ícone que entra com mola, nome de pasta digitado letra a letra, árvore de pastas que se desenha,
  janela de app (com os três pontos do macOS) mostrando o prompt com trechos marcados em amarelo, cartões de lista,
  storyboard rolando.
- **Recapitulação:** no fim, os quatro passos voltam ao redor do objeto central, ligados por linhas pontilhadas.

**Gancho e CTA**

- Gancho (0 a 10 s): título de duas linhas no topo, sobre o rosto, e três miniaturas de Reels de referência passando como
  carrossel na altura do peito. Promessa forte: "todo mundo faz, ninguém conta como".
- CTA de comentário: o rosto volta e aparece uma barra de comentário com a palavra-chave sendo digitada ("Comenta MOTION").

**Áudio:** só voz, limpa e alta (−17 dB RMS), sem música. Pausas cortadas até sobrar no máximo 0,4 s.

**Como montar hoje**

```jsonc
"legendas": {"ativo": true, "palavras_por_bloco": 2, "posicao_y": 0.62, "maiusculas": false, "enfase": []},
"musica": null,
"audio": {"sfx_transicoes": false},
"segmentos": [ /* transicao: null em todos (corte seco) */ ],
"elementos": [
  {"tipo": "titulo", "texto": "Passo 1. Monta o ambiente", "na": "Primeiro", "ate": "a pasta que você acabou de criar", "y": 0.08},
  {"tipo": "imagem", "arquivo": "<print da janela do app>", "na": "esse prompt", "y": 0.25, "largura": 0.85}
]
```

**O que falta no motor**

1. **Planos** (`"plano": "rosto" | "dividido" | "motion"` por segmento): o dividido põe o rosto na metade de baixo e um
   palco de motion em cima; o motion esconde o rosto e mantém a voz. A legenda acompanha a linha do plano.
2. **Cabeçalho de passo** fixo, com o número em serifa itálica e o texto em sans.
3. **Pacote de motion de interface:** ícone com mola, digitação, árvore que se desenha, janela de app com marca-texto,
   linhas pontilhadas de recapitulação. Todos com a paleta de papéis da marca.
4. **Barra de comentário** para o CTA "comenta a palavra".
5. Regra automática de "nada parado mais de 3 s": a conferência pode medir o tempo máximo sem mudança visual.

## C. Vitrine de estilos

Anúncio de alta produção: cada frase ganha um visual diferente para provar que "dá para fazer de tudo". Funciona como
peça de lançamento; para conteúdo do dia a dia é cansativo.

**O que se vê (um look a cada 1,5 a 3 s)**

- **Palavra atrás da pessoa:** palavras enormes em sans condensada laranja, entrando por partes, com o corpo da pessoa
  recortado por cima. Imagem em preto e branco; só a tipografia tem cor.
- **Anotações de interface:** rótulos pequenos em fonte mono ("+ E NÃO SÃO", "pa·la·vra s.f. unidade de sentido",
  "ELEMENTOS +41"), riscos, cruzes de mira, contador subindo.
- **Chuva de objetos 3D** e cartões de interface (curtidas, gráfico, chat) em volta da cabeça.
- **Título editorial:** "O ESTILO ① *das* PALAVRAS", misturando sans bold amarela e manuscrito itálico, com número circulado.
- **Recorte com contorno:** pessoa recortada em preto e branco, contorno vermelho rabiscado, coroa desenhada à mão,
  bloco mostarda chapado e letras de bilhete de resgate ("COMPLETAMENTE").
- **Look esportivo:** faixa diagonal magenta e texto condensado girado 90°. **Look calmo:** fundo branco com halo
  circular, legenda em serifa itálica fina, tudo dessaturado.
- **Rastreamento facial e corporal como efeito:** malha de pontos no rosto, anéis sobre os óculos, esqueleto laranja
  ligando as articulações, objeto em pixel art preso na ponta do dedo, rótulos mono ("RASTREAMENTO FACIAL", "CORPO 13
  ARTICULAÇÕES").
- **Som visível:** cada efeito sonoro aparece como uma onda laranja com o nome ("WHOOSH", "SWISH", "CATRACA",
  "OBTURADOR", "RISE", "IMPACTO", "PLOP") no exato instante em que toca.
- **Tela do produto** com o rosto numa bolha circular de borda laranja no canto inferior esquerdo.
- **CTA em neon:** "CLICA EM SAIBA MAIS" escrito à mão em neon laranja que acende com tremulação e troca de cor no fim.
- Cenas geradas por IA (escritório com vista, estúdio de mixagem, corrida na orla) intercaladas com a câmera real.

**Áudio:** música o tempo todo, efeito sonoro em quase todo corte e elemento.

**Como montar hoje**

- Cortes curtos com `transicao` alternando `whip`, `flash`, `glitch` e corte seco; som de transição da biblioteca.
- Efeitos `tipografia`, `glitch`, `grao`, `vhs`, `cartao_vidro`, `notificacao`, `reacoes`, `contador` e `objeto3d`.
- `musica` obrigatória com `ducking`; elementos `som` com `riser-curto` chegando na palavra, `impacto-seco` e `pop-limpo`.

**O que falta no motor** (o motor já tem recorte por RVM e detecção de rosto, a base de quase tudo)

1. **Texto atrás da pessoa:** desenhar o texto entre o fundo e o recorte.
2. **Looks por segmento:** `"look": "pb" | "pb_acento" | "editorial" | "esportivo" | "limpo"` com cor, fundo e fonte.
3. **Recorte com contorno e rabisco** (adesivo).
4. **HUD de rastreamento:** malha do rosto, anéis nos olhos, esqueleto do corpo, objeto preso a um ponto do corpo.
5. **Rótulo de som:** onda e nome do efeito sonoro desenhados quando o som toca.
6. **Bolha de rosto** circular sobre `broll` de tela.
7. **Neon manuscrito** para CTA.

## Prioridade sugerida para o produto

1. **Planos do estilo B** (rosto, dividido, motion) e legenda de 1 a 2 palavras sem caixa: maior ganho, menor esforço, e
   já vira um preset vendável ("tutorial em passos").
2. **Texto atrás da pessoa** e **looks por segmento**: usam o recorte que já existe e dão o efeito "uau" do estilo C.
3. **Tela em perspectiva** do estilo A: transforma qualquer gravação de tela em demonstração com cara de produto.
4. HUD de rastreamento, rótulo de som, neon e adesivo: acabamento para peças de lançamento.

## Regras que valem para os três

- O gancho mostra o assunto em texto nos primeiros 2 s e promete algo concreto.
- Corte de pausa agressivo: nenhuma pausa acima de 0,4 s, exceto antes do CTA.
- Cada elemento entra na palavra exata da fala que o justifica e sai quando a ideia termina.
- Uma só cor de acento por vídeo; o resto em tons neutros ou na cor própria do objeto mostrado.
- O CTA é falado e escrito ao mesmo tempo.
