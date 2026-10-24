# Rango Loader

Animação de carregamento do Rango em JavaScript puro + CSS, sem dependências. Controlada **somente por estado real** (promessas e `AbortSignal` do próprio app).

> **Situação do projeto.** O repositório em que este trabalho foi feito **não contém a aplicação Rango** (apenas uma landing page de outra marca, que não foi usada). Por isso não foi possível mapear framework, rotas, autenticação, menu, tema nem os componentes de loading existentes, e **o componente não está integrado ao sistema real**. Ele foi entregue como módulo autônomo, com demo, testes e guia de integração. As telas usadas na demo e no vídeo são prints reais do Rango; os módulos representados vêm do menu real (Pedidos, Entregas/Motoboys, WhatsApp, Produtos e Estoque, Relatórios).

## Arquivos
| Caminho | Finalidade |
|---|---|
| `src/rango-loader.js` | Componente (`createRangoLoader`), 4 modos, eventos, `whenReady`, `track`, `cancel`, `destroy`. |
| `src/rango-loader.css` | Estilos e animações (somente `transform`/`opacity`); movimento reduzido; temas claro/escuro. |
| `src/rango-loader.d.ts` | Tipos TypeScript. |
| `assets/logo_rango.png` | Logo oficial (branca, transparente). Usada como máscara: branca no escuro, azul `#1560E5` no claro; o desenho não é alterado. |
| `demo/index.html` | Demo interativa com as telas reais (cenários: início rápido/lento, falha, sessão expirada, auth, página, local, tema). |
| `demo/intro.html` | Abertura de vídeo: voo sobre telas reais dentro de aparelhos iPhone (usada só no vídeo de exemplo). |
| `assets/iphone_frame.png`, `assets/referencia_iphone.webp` | Moldura do iPhone 17 Pro Max (extraída da imagem de referência) para a demo `?phone=1`. |
| `tests/loader.test.cjs` | 20 testes em Chromium real. |
| `tools/render-video.cjs`, `tools/shot.cjs`, `tools/intro-frames.cjs` | Geração do vídeo de exemplo e capturas. |
| `rango_loader_exemplo.mp4` | Vídeo de exemplo (1080×1920, 30 fps, sem áudio). |

## Uso
```js
import { createRangoLoader } from './rango-loader.js';
import './rango-loader.css';

// 1) Inicialização — versão completa, enquanto os requisitos ESSENCIAIS carregam
const boot = createRangoLoader({ mode: 'initial', theme: () => appTheme() /* seu provedor de tema */ });
boot.on('error', (e) => app.showError(e.detail.error));   // o erro continua sendo tratado pelo app
boot.start();
boot.whenReady([session.restore(), config.load()], { signal: abortController.signal });
// libera quando TODAS resolverem; falha rápido se alguma rejeitar; cancela se o signal abortar

// 2) Autenticação — versão simplificada (sem cards)
createRangoLoader({ mode: 'auth' }).start();

// 3) Navegação entre módulos — barra fina, sem bloquear; só aparece se demorar (appearAfter=120 ms)
const page = createRangoLoader({ mode: 'page' });
router.beforeEach((to) => page.track(loadRoute(to), { signal }));   // devolve a mesma promessa

// 4) Operação local — indicador inline + aria-busy
const local = createRangoLoader({ mode: 'local', target: buttonEl });
local.track(save());
```
Ao desmontar a tela use `loader.cancel()` (troca de rota) ou `loader.destroy()` (remoção imediata).

### Regras que o componente garante
- Sem duração mínima, sem progresso/porcentagem falsa, sem pedidos ou dados fictícios na animação.
- Nenhuma requisição é criada: só observa as promessas fornecidas; não altera resultados nem engole erros.
- Só passe em `whenReady` o que é essencial à tela; requisições secundárias não devem ser passadas.
- Os únicos temporizadores: `appearAfter` (evita piscar) e a limpeza do DOM após a saída (600 ms de segurança).
- `prefers-reduced-motion`: composição estática, sem animações, saída imediata. Estado também em texto (`role="status"`, `aria-live="polite"`), não só por cor/movimento.
- Overlay do modo `initial`/`auth` bloqueia cliques **apenas enquanto carrega**; ao concluir, recebe `pointer-events: none` e é removido.

## Como integrar no Rango (checklist)
1. Descobrir o ponto de boot (ex.: `main.tsx`/`App`), a leitura de sessão e o provedor de tema.
2. Listar os requisitos essenciais por tela (sessão, permissões, dados do estabelecimento) e passá-los a `whenReady`.
3. Ligar o modo `page` ao roteador (`track` por navegação); ligar `local` a botões/ações demoradas.
4. Mapear o tema real (claro/escuro) em `theme`. Se o Rango não tiver modo escuro, use `theme: 'light'` ou `'dark'` fixo.
5. Sem React/Vue: o módulo funciona direto; em React, crie o loader num `useEffect` e chame `destroy()` no cleanup.

## Modo contido (dentro de um aparelho/painel)
Passe `container: elemento` (com `position: relative/absolute`) e o loader passa a ocupar só esse elemento, usando unidades de container. Na demo: `demo/index.html?phone=1`. Para a barra de página, defina `--rl-inset-top` no container para ficar abaixo de uma barra de status.

## Testes
```bash
python3 -m http.server 8765 --bind 127.0.0.1   # na pasta rango-loader
NODE_PATH=<caminho do node_modules com playwright-core> node tests/loader.test.cjs
```
Cobrem (inclui o modo contido dentro do aparelho): início rápido/lento, requisito secundário, falha de rede, sessão expirada, cancelamento, `AbortSignal`, desmontagem, interface liberada após o loading, barra de página (sem piscar, vários requests), local/aria-busy, acessibilidade, movimento reduzido, temas, responsividade (320×568 a 1920×1080) e não alteração de resultado/erros das promessas.

## Limitações conhecidas
- Não integrado ao Rango (código-fonte indisponível); permissões, perfis, rotas e fluxos de pedidos/delivery/WhatsApp/estoque/pagamentos **não foram testados** por não existirem aqui.
- Não há versão da logo em azul-marinho sobre branco; no tema claro usamos a logo oficial recolorida para o azul `#1560E5` (por máscara).
- Cores: azul `#1560E5` e azul-marinho `#021323` vêm dos prints; não havia guia de marca oficial.
- A abertura em voo (`intro.html`) é para vídeo; o loader de produção usa só `transform`/`opacity` e não faz desfoque.
- Não testado em Safari/Firefox (somente Chromium).
- A barra de status do aparelho na demo (9:41, bateria) é decorativa e não faz parte do Rango.
