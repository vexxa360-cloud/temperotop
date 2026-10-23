import json,sys,numpy as np,soundfile as sf
from kokoro_onnx import Kokoro
# Roteiro de narração em cláusulas (cada cláusula = 1 legenda). Cena 4 adaptada às telas reais disponíveis.
CL=[
 ("1a","Gerenciar um negócio de alimentação exige organização, controle e agilidade.",None),
 ("1b","E é para facilitar essa rotina que existe a Rango.",None),
 ("2a","Na Rango, você encontra ferramentas para acompanhar a gestão do seu estabelecimento,",None),
 ("2b","em uma plataforma organizada,",None),
 ("2c","com recursos que ajudam a ter mais controle da operação.",None),
 ("3a","Com o controle de CMV e lucro, você acompanha o faturamento,","Com o controle de cê-ême-vê e lucro, você acompanha o faturamento,"),
 ("3b","entende seus custos",None),
 ("3c","e visualiza suas margens, para tomar decisões com mais clareza.",None),
 ("4a","Acompanhe também o estoque,",None),
 ("4b","veja quais produtos precisam de atenção",None),
 ("4c","e registre as compras.",None),
 ("5a","E olha só esse recurso: o cliente pode fazer o pedido por áudio, no WhatsApp.","E olha só esse recurso: o cliente pode fazer o pedido por áudio, no Uótsápi."),
 ("5b","A Rango interpreta a mensagem",None),
 ("5c","e transforma as informações em um pedido organizado no painel,",None),
 ("5d","facilitando o trabalho da equipe.",None),
 ("6a","Seja em um restaurante, em uma hamburgueria ou em uma adega,",None),
 ("6b","a proposta é ajudar você a organizar a operação",None),
 ("6c","e acompanhar melhor o seu negócio.",None),
 ("7a","Rango. Mais controle, mais organização e mais clareza para o seu negócio.",None),
 ("7b","Conheça a Rango.",None),
]
voice=sys.argv[1]; speed=float(sys.argv[2])
k=Kokoro('/tmp/tts/kokoro.onnx','/tmp/tts/voices.bin')
out={}
for cid,t,tt in CL:
    s,sr=k.create(tt or t,voice=voice,speed=speed,lang='pt-br')
    # corta silêncio de borda
    a=np.abs(s); idx=np.where(a>0.01)[0]; s=s[max(idx[0]-int(.03*sr),0):idx[-1]+int(.06*sr)]
    sf.write(f'/tmp/prod/{voice}_{cid}.wav',s,sr); out[cid]={'text':t,'dur':len(s)/sr,'sr':sr}
json.dump(out,open(f'/tmp/prod/{voice}_durs.json','w'),ensure_ascii=False,indent=1)
print(voice,'total fala',round(sum(v['dur'] for v in out.values()),1),'s')
for c,v in out.items(): print(c,round(v['dur'],2))
