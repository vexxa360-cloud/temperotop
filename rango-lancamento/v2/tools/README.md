# Exportação do MP4

Requer Node + `playwright-core` + Chromium e `ffmpeg`.

1. `for k in 0 1 2; do node render-frames.js $k 3 & done; wait`  → 900 quadros JPEG (30 FPS) em /tmp/pw/frames
2. `node render-audio.js`  → áudio sintetizado (PCM) em /tmp/pw/audio.pcm
3. `ffmpeg -f s16le -ar 44100 -ac 2 -i audio.pcm -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 48000 audio.wav`
4. `ffmpeg -framerate 30 -i frames/f%04d.jpg -i audio.wav -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart -shortest rango-lancamento-30s.mp4`

O HTML (`index.html`) também toca ao vivo no navegador.
