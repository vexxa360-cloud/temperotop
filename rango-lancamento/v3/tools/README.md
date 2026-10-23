# Pipeline do vídeo comercial (v3)

Requisitos: Python 3 (`numpy scipy soundfile kokoro-onnx sherpa-onnx`), Node + `playwright-core` + Chromium, `ffmpeg`.
Modelos de voz (Kokoro v1.0) e de teste (Whisper small, sherpa-onnx) são baixados dos releases do GitHub.

1. `1_narracao.py pm_alex 1.1`  → fala por cláusula (voz neural PT-BR, Kokoro). Texto exibido ≠ texto falado só onde há ajuste de pronúncia.
2. `2_plano.py pm_alex`          → `plan.json`: início/fim de cada fala e de cada cena (a timeline do HTML é ancorada nesses tempos).
3. HTML `index.html` (build injeta `plan.json`) → `export-cues.js` grava `cues.json` (efeitos sonoros sincronizados com a animação).
4. `3_mixagem.py pm_alex out.wav` → trilha ORIGINAL sintetizada + efeitos + narração, com ducking; depois `loudnorm` do ffmpeg (-16 LUFS, pico -1,5 dB).
5. `render-frames.js k 3` (k=0,1,2) → quadros 1920×1080 a 30 FPS; ffmpeg monta H.264 + AAC.
6. `asr_mixagem.py` → transcreve cada fala NA MIXAGEM FINAL (com música/efeitos) e calcula o erro de palavras.
