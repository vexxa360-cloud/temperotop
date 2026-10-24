# Post Rango (Instagram 4:5, 1080×1350)

`post_rango_1080x1350.png` — arte final. Cores do Rango (azul, claro-azulado, branco), logo oficial (`assets/logo_rango_original.png`, sem alteração).

- `cofrinho_blender.py`: cofrinho de cerâmica rosa-salmão esmaltada + moeda de R$ 1, renderizado em Blender/Cycles (bpy). Saída: `cofrinho_render.png` (PNG com transparência e sombra de contato).
- `post_rango.py`: composição 2D (fundo azul com curva orgânica, logo, manchete em Anton, pincelada branca em "TAXAS", dois blocos de texto).
- Reproduzir: `python cofrinho_blender.py cofrinho_render.png 1300 160` (Python 3.11 + `bpy`, `numpy`, `scikit-image`) e depois `python3 -I post_rango.py`.

Adaptações em relação ao prompt: laranja/bege viraram o azul e o azul-claro do Rango (pedido do cliente); o logo e o nome no texto são "Rango" (o prompt citava "zesto" como exemplo da referência); a moeda é uma representação da moeda de R$ 1, sem o desenho oficial.
