# Changelog

## Não lançado

### Novo

- **Peças fixas no Pencil**: capa de Reel do @pontes_brain em `marcas/pontes_brain/pencil/capa-reel.pen` (fonte) e
  `capa-reel.png` (1080×1920); convenção documentada em `docs/marcas.md`.
- **Estilos de edição** (`"estilo"` no EDL, `analisar --estilo`, `editor.py estilos`): `tutorial_passos`,
  `tela_perspectiva` e `vitrine`, presets que ajustam legenda, sons, corte de pausas e o aviso de ritmo.
- **Planos por segmento** (`"plano"`): `rosto`, `dividido` (palco de motion em cima, rosto embaixo) e `motion`; a
  legenda acompanha a linha do plano. `motor/planos.py`.
- **Looks por segmento** (`"look"`): `pb`, `pb_acento`, `duotom`, `quente`, `frio`, `limpo`, `noite` e `adesivo`
  (pessoa recortada com contorno sobre fundo chapado).
- **Legenda `limpa`**: 1 ou 2 palavras, branco, sem caixa nem contorno, sombra macia.
- **Motion de estilo** (`motor/motion.py`): `passo`, `digitacao`, `janela`, `arvore`, `mapa`, `comentario`, `icone`,
  `carrossel`, `titulo_caixa`, `titulo_editorial`, `bilhete`, `anotacao`, `neon`, `texto_atras` (atrás da pessoa, com
  recorte automático) e `hud_rosto` (segue o rosto). `som` com `rotulo` mostra o som na tela.
- **Tela em perspectiva** (`broll` com `perspectiva`): plano 3D com câmera por pontos-chave, profundidade de campo e
  luz quente. **Bolha de rosto** (`broll` com `bolha`).
- **Aviso de ritmo**: com `parado_max`, o render mede o maior trecho sem mudança visual.
- **Fontes de estilo** (OFL): DM Serif Display, Anton, Space Mono e Caveat, com licenças em `biblioteca/fontes/LICENCAS.md`.
- **Estilos de referência** em `docs/estilos-de-referencia.md`: três estilos de Reels estudados (tela em perspectiva,
  tutorial em passos, vitrine de estilos), com números medidos, receita para o motor atual e lista do que falta construir.

## 2.1.0 (2026-10-29)

Assets em alta para Reels (pesquisa de tendências de outubro de 2026), pensados para o @pontes_brain e servindo a todas as marcas.

### Novo

- **Biblioteca de sons** (`biblioteca/sons/`): 38 efeitos sonoros (whooshes, risers, impactos, interface, papel, lápis,
  teclado, notificação, moedas), gravações CC0 do OpenGameArt e efeitos próprios desenhados em `ferramentas/montar_sons.py`,
  nivelados e com o instante do pico (`ataque`) para alinhar ao corte ou à palavra. `editor.py biblioteca listar sons`.
- **Sons no EDL**: `"som"` em segmentos e elementos (id ou `false`) e o elemento `{"tipo": "som"}`. Marcas com
  `"sons": {"modo": "biblioteca"}` tocam um som por tipo de transição, de elemento e de efeito, alternando variações.
- **4 transições**: `giro` (giro 3D), `rasgo` (papel rasgado), `vidro` (vidro líquido) e `luz` (queima de luz).
- **8 efeitos**: `cartao_vidro`, `notificacao`, `carregando`, `checklist`, `tipografia` (cinética), `marca_texto`,
  `reacoes`, `reflexo` e o painel de vidro líquido reutilizável (`painel_vidro`).
- **48 objetos 3D** (Fluent Emoji, MIT) para gestão de produto: semáforo, zumbi, caracol, tesoura, extintor, boia,
  balança, porta, ciclo, correntes, régua, telescópio, microscópio, cadeado aberto, coroa, "você"…
- **3D do @pontes_brain**: placas `g1` a `g4` dos gates e o ciclo `pdca` (`ferramentas/gerar_3d_pontes_brain.py`).

### Mudou

- O @pontes_brain passa a usar a biblioteca de sons (vinheta, transições, elementos e CTA). GiraHub e @leopontesrp não mudam.
- Efeitos ganham `som` no catálogo; `biblioteca verificar` confere os sons.


## 2.0.0 (2026-10-29)

Repositório profissionalizado, com bibliotecas compartilhadas e isolamento entre marcas.

### Novo

- **Isolamento entre marcas**: `--marca` obrigatório (sem padrão), pasta por marca com sandbox de arquivos, vinhetas,
  fundos e Leo com dono, termos exclusivos por marca, guarda do EDL (`motor/guarda.py`), auditoria dos arquivos abertos,
  selo da marca nos metadados do vídeo e `editor.py conferir`.
- **Biblioteca 3D**: 167 objetos (119 renders do Fluent Emoji 3D, 48 logos extrudados do Simple Icons), com busca.
- **Biblioteca de músicas**: 35 faixas reais CC BY 4.0, com clima, energia, BPM, gênero, instrumentos e crédito;
  download conferido por sha256 e `creditos.txt` no render.
- **Biblioteca de efeitos**: 20 layers procedurais na paleta da marca (luz, textura, impacto, celebração, anotação,
  informação), ancorados na fala.
- `editor.py marcas`, `editor.py biblioteca listar|baixar|verificar|previa|catalogo`.
- `manifesto.json` em todo render.
- Testes de unidade (pytest), CI no GitHub Actions, Makefile, `pyproject.toml`.
- README vitrine, CLAUDE.md, AGENTS.md, CONTRIBUTING.md e docs/.

### Mudou

- `editor.py` virou o pacote `motor/` (mesmo visual, regressão com diferença 0,00 em todas as marcas).
- `marcas/<id>.json` → `marcas/<id>/marca.json`, com os arquivos da marca ao lado.
- `assets/` dividido entre `marcas/<id>/` (identidade) e `biblioteca/` (compartilhado).
- Skills em `skills/<skill>/SKILL.md`.
- Música no EDL por `"faixa"` (id do catálogo); `"arquivo"` antigo continua funcionando.
- `musica_obrigatoria` → `"musica": {"politica": "proibida" | "opcional" | "obrigatoria"}`. O @pontes_brain passa a
  recusar música no vídeo (o Leonardo põe a música no Instagram).

### Removido

- `PROMPT-MESTRE.md` e `PROMPT-instagram-pessoal.md` (duplicavam as skills).
- `assets/musicas/` (as faixas agora vêm da biblioteca).

## 1.x

Editor de arquivo único para @pontes_brain, depois GiraHub e @leopontesrp.
