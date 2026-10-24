# Filme de produto Rango — navegação realista pelo menu lateral

`rango_filme.mp4` — 1080×1920 (9:16), 30 fps, H.264, **sem áudio**. Gerado por `python3 -I filme.py` (PIL + numpy + ffmpeg).

## Direção
Um percurso contínuo, como uma pessoa usando o sistema: um cursor de seta com movimento humano (trajetória em arco suave, sai e chega devagar, pausa antes do clique, clique discreto com anel fino) abre o menu lateral, escolhe o item, o destaque azul-claro migra para ele, o menu se fecha e a próxima tela já está sob o aparelho. A câmera acompanha de forma controlada: aproxima-se do botão do menu, enquadra a lista aberta, estabiliza para a leitura de cada módulo e recua no final. Nenhum efeito de câmera fica ativo durante a leitura.

## Roteiro (≈ 64 s)
1. Abertura da marca (logo oficial, linhas de conexão discretas) → o aparelho entra com o Dashboard.
2. Dashboard: enquadramento estável e aproximação nos cartões.
3. Cursor → botão do menu → menu abre → **Lançar Venda** (rolagem real até o carrinho).
4. Menu → **Pedidos / Delivery** (lista, rolagem até o pedido confirmado).
5. Menu → **Histórico de Vendas** (troca do filtro para "Hoje").
6. Menu → **Receitas** (abre e fecha o formulário de nova receita).
7. Menu (rolado) → **Produtos e Estoque**.
8. Câmera recua, o aparelho sai e a logo assina: "Rango. Sua operação, conectada." (frase sugerida; ajuste ao posicionamento oficial).

## Fidelidade e limites
- A interface é composta dos **prints reais** do Rango (não foi recriada); o menu, o destaque azul-claro (solicitado) e as rolagens vêm de `../anuncio-rango/rango_ui.py`, que recorta e recompõe trechos dos próprios prints.
- Só foram navegados módulos cujo item **aparece no menu real** dos prints. Entregas/Motoboys, WhatsApp e Visão Geral estão no menu, mas não há tela deles; Funcionários, Relatórios, CMV e Perdas e Consumo existem como telas, mas nenhum print do menu mostra esses itens (não inventei a posição deles). Não há demonstração de cozinha, pagamentos nem áudio.
- Não foi possível analisar a aplicação (código, rotas, tema, bibliotecas): ela não está neste repositório. Não há integração com o sistema; este é um filme gerado a partir de prints.
- Os valores que aparecem são os dos prints (dados já existentes do estabelecimento de teste), sem alterações. A barra de status 9:41 é do molde do iPhone.
- Zoom da câmera é digital sobre prints de ~746 px de largura; em aproximações maiores a imagem fica levemente suave.
