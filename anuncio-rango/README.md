# Comercial Rango — 80 s, vertical 9:16

**Entrega:** `rango_anuncio_80s.mp4` (1080×1920, 30 fps, H.264 + AAC, 80,0 s) e `legendas.srt` (pt-BR, sincronizadas com a narração; também gravadas no vídeo).

## Como foi feito
- **Interface:** prints reais do Rango em `../rango-video/prints/` (sem telas inventadas). O menu lateral e o destaque azul claro são recortes dos prints reais (`rango_ui.py`). Telas com números levam o aviso "Dados de demonstração"; a cena 1 leva "Ilustração" (papéis desenhados, sem texto, não são do produto).
- **Logo:** `assets/logo_rango_original.png` (arquivo enviado). `assets/logo_rango.png` é a mesma logo recortada no contorno, com transparência preservada; só foram zerados pixels com alpha ≤ 2 (franja magenta invisível). Nada foi redesenhado nem deformado. Aparece só na abertura (cena 1) e no final (cenas 7 e 8).
- **Cores:** somente azuis e branco, conforme pedido.
- **Narração:** `narracao_anuncio.py` (Kokoro ONNX, voz `pf_dora`, pt-BR) com as 8 falas do roteiro, sem alterações. `audio/` guarda os WAVs.
- **Música e efeitos:** trilha instrumental original sintetizada em `../rango-video/music.py` (sem amostras de terceiros), com ganho crescente, abaixa sob a voz e destaca o CTA; efeitos discretos de transição, toque e texto.
- **Montagem:** `anuncio.py` compõe os quadros (PIL/numpy), grava com ffmpeg e mistura o áudio.

## Cronograma
| Cena | Tempo | Conteúdo |
|---|---|---|
| 1 | 0–7 s | Abertura da logo (azul profundo) → gancho "Chega de improvisar na gestão." |
| 2 | 7–15 s | Dashboard e menu lateral — "Seu negócio. Mais organizado." |
| 3 | 15–27 s | Lançar Venda, venda #8 e Histórico de Vendas |
| 4 | 27–39 s | Produtos e Estoque, estoque crítico, Perdas e Consumo |
| 5 | 39–51 s | Aviso de novo pedido, detalhe, confirmação e lista de Pedidos |
| 6 | 51–63 s | Dashboard, ranking e Relatórios |
| 7 | 63–70 s | Posicionamento da marca |
| 8 | 70–80 s | CTA final |

## Reproduzir
```bash
# 1) voz (venv com kokoro-onnx e soundfile; modelo e vozes: github.com/thewh1teagle/kokoro-onnx, release model-files-v1.0)
python narracao_anuncio.py kokoro-v1.0.onnx voices-v1.0.bin
# 2) vídeo + áudio + legendas (precisa de ffmpeg, numpy e Pillow)
python3 -I anuncio.py rango_anuncio_80s.mp4
```
Para ver quadros isolados: `python3 -I anuncio.py x.mp4 frames 12 40 75` (gera `_dbg_*.png`).

## Limitações
- Não há endereço, telefone ou canal oficial do Rango no projeto; por isso o CTA diz apenas "CONHEÇA O RANGO". Quando houver um canal confirmado, é só incluí-lo na cena 8 (`scene8`).
- Não havia filmagem de um estabelecimento; a cena 1 usa uma ilustração em motion graphics.
- O repositório só contém a landing page TemperoTop (outra marca); nada dela foi usado.
