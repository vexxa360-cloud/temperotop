"""Gera a narracao (pt-BR) com Kokoro ONNX. Uso: python narracao.py <kokoro.onnx> <voices.bin>
Saidas: narracao/<chave>.wav e narracao/duracoes.json"""
import json, os, sys
import soundfile as sf
from kokoro_onnx import Kokoro

CUES = {
 'intro': "Conheça o Rango: a gestão do seu bar e do seu delivery, direto no celular.",
 'dash': "No Dashboard, você vê faturamento, custo e lucro do período, além do estoque crítico e do ranking de vendas.",
 'lanc': "Em Lançar Venda, escolha os produtos, por unidade ou por caixa, e registre a venda em segundos, já com o lucro.",
 'ped': "Em Pedidos e Delivery, chegou pedido novo? É só confirmar o pagamento e acompanhar cada etapa.",
 'hist': "No menu, também estão Entregas e Motoboys e o WhatsApp. E no Histórico de Vendas, você confere todas as vendas, com filtro por período.",
 'rec': "Em Receitas, as fichas técnicas já calculam custo e margem automaticamente.",
 'prod': "Produtos e Estoque, com saldo, categorias e alerta de estoque baixo. E logo abaixo, a Visão Geral.",
 'func': "Em Funcionários, você cadastra a sua equipe, dentro do limite do seu plano.",
 'rel': "Relatórios traz faturamento, ticket médio, lucro e os produtos mais vendidos.",
 'cmv': "Em CMV e Lucro, você sabe quanto realmente sobra de cada venda.",
 'perd': "E Perdas e Consumo registra quebras e consumo próprio, separados do faturamento. Rango: controle total, na palma da mão.",
}

if __name__ == '__main__':
    k = Kokoro(sys.argv[1], sys.argv[2])
    os.makedirs('narracao', exist_ok=True); dur = {}
    for key, txt in CUES.items():
        s, sr = k.create(txt, voice='pf_dora', speed=1.05, lang='pt-br')
        sf.write(f'narracao/{key}.wav', s, sr); dur[key] = len(s)/sr; print(key, round(dur[key], 1))
    json.dump(dur, open('narracao/duracoes.json', 'w'))
