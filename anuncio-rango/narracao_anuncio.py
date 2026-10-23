"""Narracao do comercial (pt-BR, Kokoro ONNX, voz pf_dora). Uso: python narracao_anuncio.py <kokoro.onnx> <voices.bin>"""
import json, sys
import soundfile as sf
from kokoro_onnx import Kokoro

FALAS = [  # (arquivo, texto) — exatamente o roteiro aprovado
 ('cena1', "Seu bar ou restaurante ainda é controlado no improviso?"),
 ('cena2', "Com o Rango, você coloca sua operação inteira sob controle, em um só sistema."),
 ('cena3', "Registre suas vendas, acompanhe o faturamento e saiba exatamente o que está acontecendo no seu negócio."),
 ('cena4', "Controle seu estoque, veja o que está acabando e registre perdas e consumo."),
 ('cena5', "Organize seus pedidos e tenha mais agilidade na operação, do atendimento à entrega."),
 ('cena6', "E acompanhe seus resultados para tomar decisões melhores, sem depender de planilhas."),
 ('cena7', "Rango. Sistema de gestão para bares e restaurantes."),
 ('cena8', "Quer mais controle, organização e praticidade para o seu negócio? Conheça o Rango."),
]
if __name__ == '__main__':
    k = Kokoro(sys.argv[1], sys.argv[2]); dur = {}
    for nome, txt in FALAS:
        s, sr = k.create(txt, voice='pf_dora', speed=0.98, lang='pt-br')
        sf.write(f'audio/{nome}.wav', s, sr); dur[nome] = len(s)/sr; print(nome, round(dur[nome], 2))
    json.dump(dur, open('audio/duracoes.json', 'w'), indent=1)
