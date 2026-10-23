"""Gera a narracao (pt-BR) com Kokoro ONNX. Uso: python narracao.py <kokoro.onnx> <voices.bin>
Saidas: narracao/<chave>.wav e narracao/duracoes.json"""
import json, os, sys
import soundfile as sf
from kokoro_onnx import Kokoro

CUES = {
 'intro': "Esta é a plataforma Rango, vista no celular. Vamos percorrer o menu lateral, seção por seção. O item selecionado agora é o Dashboard.",
 'dash1': "O Dashboard mostra o Painel do Bar dos últimos trinta dias: faturamento de quinhentos e oitenta e dois reais e quarenta e cinco centavos, em sete vendas; custo, o CMV, de quatrocentos e setenta e um reais e sessenta e seis centavos, oitenta e um por cento; lucro bruto de cento e dez reais e setenta e nove centavos; e ticket médio de oitenta e três reais e vinte e um centavos.",
 'dash2': "Rolando a página, aparecem as perdas e o consumo, que não entram no faturamento, o estoque crítico, com dois produtos, e o ranking de faturamento.",
 'nav_lanc': "Abro o menu e escolho Lançar Venda.",
 'lanc1': "Aqui eu busco o produto e filtro por categoria: bebidas, doses, pratos ou conveniência. Cada cerveja pode ser vendida por unidade ou por caixa.",
 'lanc2': "Na venda rápida, o carrinho mostra o X-Burguer, a vinte e um reais e vinte centavos. Escolho a forma de pagamento, dinheiro, e toco em Lançar venda.",
 'lanc3': "A venda número oito foi registrada: total de vinte e um reais e vinte centavos, lucro de doze reais e setenta e dois centavos, com CMV de quarenta por cento e margem de sessenta por cento. Toco em Nova venda para voltar à lista.",
 'nav_ped': "Agora, Pedidos e Delivery.",
 'ped2': "Chega um aviso de novo pedido: pedido número três, da Maria, de vinte e um reais e vinte centavos, com cartão na entrega. Toco em Ver pedido.",
 'ped3': "Nos detalhes, vejo o cliente, o endereço, o item e o total, com as opções de confirmar o pagamento, confirmar ou cancelar o pedido. Vou confirmar o pedido.",
 'ped4': "De volta à lista, os cartões mostram os pedidos abertos, em separação, em entrega e finalizados, com filtros por status.",
 'ped5': "Rolando, o pedido confirmado aparece com o botão Iniciar preparo, junto dos anteriores, um finalizado e outro cancelado.",
 'nav_hist': "Em seguida, Histórico de Vendas.",
 'hist1': "Nos últimos trinta dias, o faturamento é de seiscentos e vinte e quatro reais e oitenta e cinco centavos, em nove vendas, com lucro de cento e trinta e seis reais e vinte e três centavos e ticket médio de sessenta e nove reais e quarenta e três centavos. Nenhuma venda foi cancelada.",
 'hist2': "Trocando o filtro para Hoje, o painel mostra quarenta e dois reais e quarenta centavos, em duas vendas, com margem de sessenta por cento.",
 'nav_rec': "Agora, Receitas.",
 'rec1': "Aqui ficam as fichas técnicas. O X-Burguer custa oito reais e quarenta e oito centavos, com três ingredientes, é vendido a vinte e um reais e vinte centavos e tem lucro de doze reais e setenta e dois centavos, com CMV de quarenta por cento.",
 'rec2': "Ao tocar em Criar receita, abre o formulário de nova receita, com nome, tipo, categoria, rendimento, tempo de preparo, modo de preparo e foto do produto.",
 'nav_prod': "Abro o menu, rolo a lista até o fim e escolho Produtos e Estoque.",
 'prod1': "A tela mostra nove produtos ativos, dois com estoque baixo e seis categorias, com busca, filtros e a lista de produtos com o estoque de cada um.",
 'nav_func': "Agora, Funcionários.",
 'func1': "Esta é a equipe: três funcionários ativos, nenhum inativo, e o plano permite sete, com quatro vagas disponíveis. A lista traz o nome e o e-mail de cada pessoa.",
 'nav_rel': "Seguindo, Relatórios.",
 'rel1': "Nos últimos trinta dias, o faturamento é de seiscentos e vinte e quatro reais e oitenta e cinco centavos, em nove vendas. O ticket médio é de sessenta e nove reais e quarenta e três centavos, o custo é de quatrocentos e oitenta e oito reais e sessenta e dois centavos, com CMV de setenta e oito vírgula dois por cento, e o lucro bruto é de cento e trinta e seis reais e vinte e três centavos.",
 'rel2': "Rolando, aparecem a evolução do faturamento ao longo dos dias e os produtos mais vendidos, que podem ser ordenados por quantidade, faturamento, lucro ou margem.",
 'nav_cmv': "Agora, CMV e Lucro.",
 'cmv1': "O mês mostra faturamento de seiscentos e vinte e quatro reais e oitenta e cinco centavos, custo de quatrocentos e oitenta e oito reais e sessenta e dois centavos, lucro de cento e trinta e seis reais e vinte e três centavos e CMV geral de setenta e oito vírgula dois por cento, com a divisão por tipo.",
 'nav_perd': "Por fim, Perdas e Consumo.",
 'perd1': "O total do período é de cento e trinta e oito reais e trinta e oito centavos, sendo oito reais e quarenta e oito centavos de consumo do proprietário e cento e vinte e nove reais e noventa centavos de quebra. Esses valores não entram no faturamento. Essa foi a navegação completa pela plataforma Rango.",
}

if __name__ == '__main__':
    k = Kokoro(sys.argv[1], sys.argv[2])
    os.makedirs('narracao', exist_ok=True); dur = {}
    for key, txt in CUES.items():
        s, sr = k.create(txt, voice='pf_dora', speed=1.0, lang='pt-br')
        sf.write(f'narracao/{key}.wav', s, sr); dur[key] = len(s)/sr; print(key, round(dur[key], 1))
    json.dump(dur, open('narracao/duracoes.json', 'w'))
