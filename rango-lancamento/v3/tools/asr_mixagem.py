import json,sys,numpy as np,soundfile as sf
sys.argv=[sys.argv[0]]; from asr import rec,norm,wer
import sherpa_onnx
P=json.load(open('/tmp/prod/plan.json')); x,sr=sf.read('/tmp/prod/final_master.wav',dtype='float32'); x=x.mean(1)
res=[]
for cid,c in P['clauses'].items():
    seg=x[int((c['start']-.15)*sr):int((c['end']+.15)*sr)]
    st=rec.create_stream(); st.accept_waveform(sr,seg); rec.decode_stream(st); h=st.result.text
    w=wer(norm(c['text']),norm(h)); res.append(w)
    print(f"{cid} WER={w:.2f} | {h.strip()}")
print('WER médio na mixagem final:',round(float(np.mean(res)),3))
