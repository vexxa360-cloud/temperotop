# Mascote flutuante Greenfinity Universe — como instalar no Wix

## A limitação real (leia primeiro)
Um código dentro do "Elemento HTML" do Wix roda em um iframe. Ele **não enxerga** o scroll da página principal
e `position:fixed` dentro dele só fixa o gorila dentro da caixa do iframe. Por isso há dois caminhos que funcionam de verdade:

| | Caminho A — Elemento HTML + "Fixar na tela" | Caminho B — Custom Code (recomendado) |
|---|---|---|
| Como acompanha o scroll | o próprio Wix fixa a caixa do iframe na tela | `position:fixed` real na página, sem iframe |
| Exige plano Premium + domínio | Não | Sim |
| Tamanho no mobile | ajustado à mão no Editor Mobile | automático (media queries no código) |
| Arquivo | `mascote-wix-elemento-html.html` | `mascote-wix-custom-code.html` |

Velo **não é necessário** para o mascote ficar fixo. (Velo só serviria para mostrar/esconder o elemento por página.)

## Imagem
O código já traz o gorila **embutido** (PNG/WebP com fundo transparente verdadeiro, recortado, 331×520 px), então funciona sem hospedar nada.
Para usar uma URL sua (opcional):
1. Wix > Mídia (Gerenciador de mídia) > envie `gorila-greenfinity.png`.
2. Clique no arquivo > copie o endereço (`https://static.wixstatic.com/media/....png`).
3. No código, substitua o valor de `src` (Caminho A) ou da variável `SRC` (Caminho B) por essa URL.

## Caminho A — Elemento HTML (sem Premium)
1. Editor do Wix > Adicionar (+) > Incorporar código > **Incorporar HTML** > "Código".
2. Cole todo o conteúdo de `mascote-wix-elemento-html.html` > Atualizar.
3. Tamanho: **Desktop 120 × 170 px** · **Mobile 70 × 100 px** (Editor Mobile, ajuste separado).
4. Posição: arraste para o canto inferior direito, ~20 px das bordas (mobile ~12 px).
5. Com o elemento selecionado: botão direito (ou ícone de alfinete) > **Fixar na tela** > âncora **inferior direita**.
6. Camada: deixe acima do conteúdo (Ordenar > Trazer para frente) e longe de WhatsApp/cookies (suba ~80 px se houver).
7. Desative "Mostrar em todas as páginas" só se quiser limitar; para todas as páginas, coloque no **cabeçalho** do site.
8. Publique e teste: o iframe tem fundo transparente e sem barras de rolagem.

Observação: a caixa do iframe bloqueia cliques na área dela (100×150 px). Mantenha-a pequena.

## Caminho B — Custom Code (fixo de verdade)
1. Painel do site > Configurações > **Custom Code** (Código personalizado) > Adicionar código.
2. Cole `mascote-wix-custom-code.html` inteiro.
3. Aplicar a: **Todas as páginas** · Carregar uma vez · Colocar em: **Body – final**.
4. Salvar e publicar. Não aparece no Editor, apenas no site publicado.
5. Tamanho/posição: altura 130 px (desktop), 100 px (tablet), 78 px (celular), canto inferior direito. Ajuste `height`, `right`, `bottom` no CSS.

## Tornar clicável no futuro
Caminho B: preencha `var LINK="https://..."`. Caminho A: envolva o `<img>` em `<a href="..." target="_top">`. Por padrão não há link nem clique.
