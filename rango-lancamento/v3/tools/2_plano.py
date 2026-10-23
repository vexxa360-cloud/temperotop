import json,sys
voice=sys.argv[1]
D=json.load(open(f'/tmp/prod/{voice}_durs.json'))
d=lambda c:D[c]['dur']
P={'clauses':{},'scenes':{}}
t=0.0
def scene(n,lead,ids,gaps,minL,tail):
    global t
    t0=t; c=t0+lead
    for i,cid in enumerate(ids):
        P['clauses'][cid]={'start':round(c,3),'end':round(c+d(cid),3),'text':D[cid]['text']}
        c+=d(cid)+(gaps[i] if i<len(gaps) else 0)
    end=P['clauses'][ids[-1]]['end']
    L=max(end+tail-t0,minL); P['scenes'][n]={'t0':round(t0,3),'L':round(L,3)}; t=t0+L
scene(1,.6,['1a','1b'],[.35],0,1.1)
scene(2,.9,['2a','2b','2c'],[.2,.18],10.0,.8)
scene(3,.6,['3a','3b','3c'],[.2,.25],9.5,.8)
scene(4,.5,['4a','4b','4c'],[.22,.22],7.5,.7)
scene(5,.9,['5a','5b','5c','5d'],[.4,.15,.2],14.8,1.4)
scene(6,.4,['6a','6b','6c'],[.22,.22],8.5,.8)
scene(7,2.5,['7a','7b'],[.5],0,3.4)
P['total']=round(t,3); P['voice']=voice
json.dump(P,open('/tmp/prod/plan.json','w'),ensure_ascii=False,indent=1)
print(P['total'],{k:(v['t0'],v['L']) for k,v in P['scenes'].items()})
