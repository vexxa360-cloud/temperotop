import sys,json,re,unicodedata,numpy as np,soundfile as sf,sherpa_onnx
M='/tmp/prod/sherpa-onnx-whisper-small/'
rec=sherpa_onnx.OfflineRecognizer.from_whisper(encoder=M+'small-encoder.int8.onnx',decoder=M+'small-decoder.int8.onnx',tokens=M+'small-tokens.txt',language='pt',task='transcribe',num_threads=4)
def norm(t): t=unicodedata.normalize('NFD',t.lower()); t=''.join(c for c in t if unicodedata.category(c)!='Mn'); return re.sub(r'[^a-z0-9 ]',' ',t).split()
def wer(r,h):
    d=list(range(len(h)+1))
    for i in range(1,len(r)+1):
        p=d[:]; d[0]=i
        for j in range(1,len(h)+1): d[j]=min(p[j]+1,d[j-1]+1,p[j-1]+(r[i-1]!=h[j-1]))
    return d[-1]/max(len(r),1)
def trans(path):
    s,sr=sf.read(path,dtype='float32'); 
    if s.ndim>1: s=s.mean(1)
    st=rec.create_stream(); st.accept_waveform(sr,s); rec.decode_stream(st); return st.result.text
if __name__=='__main__':
    for v in sys.argv[1:]:
        d=json.load(open(f'/tmp/prod/{v}_durs.json')); tot=[];
        for c,x in d.items():
            h=trans(f'/tmp/prod/{v}_{c}.wav'); w=wer(norm(x['text']),norm(h)); tot.append(w)
            if w>.25: print('  ',c,round(w,2),'|',h)
        print(v,'WER médio',round(float(np.mean(tot)),3))
