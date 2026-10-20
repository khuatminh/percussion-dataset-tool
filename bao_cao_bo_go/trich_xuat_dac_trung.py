#!/usr/bin/env python3
"""Extract three reproducible audio feature sets; no audio files are modified."""
import csv, hashlib, json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import scipy
from scipy.fft import dct
from scipy.spatial.distance import pdist,cdist
from scipy.signal import windows
import soundfile as sf

HERE=Path(__file__).resolve().parent
OUT=HERE/'features'
TEMP=['log1p_active_s','log1p_energy90_s','crest_db','active_fraction','peak_position']
SPEC=['centroid_hz','bandwidth_hz','rolloff85_hz','flatness','entropy','zcr','low500_ratio','flux']
A_NAMES=TEMP+[n+'_'+stat for n in SPEC for stat in ['mean','std']]
B_NAMES=[f'mfcc{i:02d}_{stat}' for stat in ['mean','std','delta_std'] for i in range(1,14)]
F=np.fft.rfftfreq(512,1/16000)
MEL_POINTS=700*(10**(np.linspace(2595*np.log10(1+20/700),2595*np.log10(1+8000/700),42)/2595)-1)
MEL=np.array([np.maximum(0,np.minimum((F-a)/(b-a),(c-F)/(c-b))) for a,b,c in zip(MEL_POINTS[:-2],MEL_POINTS[1:-1],MEL_POINTS[2:])])
MEL/=MEL.sum(axis=1,keepdims=True)

def extract(y):
    y=y.astype(np.float64);y=y-y.mean();peak=np.max(np.abs(y))
    if peak<1e-12:raise ValueError('Silent signal')
    y=y/peak;n=len(y)
    blocks=[y[i:i+160] for i in range(0,n,160)]
    env=np.array([np.sqrt(np.mean(t*t)) for t in blocks]);active10=env>.01
    smask=np.repeat(active10,160)[:n]
    if not smask.any():raise ValueError('No active samples')
    active_s=smask.sum()/16000
    first,last=np.flatnonzero(smask)[[0,-1]]
    total_energy=np.cumsum(y*y)
    e05,e95=[np.searchsorted(total_energy,q*total_energy[-1]) for q in [.05,.95]]
    d90=(e95-e05)/16000
    crest=20*np.log10(1/np.sqrt(np.mean(y[smask]**2)))
    span=(last-first+1)/16000
    peak_position=np.clip((np.argmax(env)*160-first)/max(last-first,1),0,1)
    temporal=[np.log1p(active_s),np.log1p(d90),crest,active_s/span,peak_position]
    count=max(1,int(np.ceil((n-400)/160))+1)
    padded=np.pad(y,(0,(count-1)*160+400-n))
    frames=np.lib.stride_tricks.sliding_window_view(padded,400)[::160]
    valid=np.sqrt(np.mean(frames**2,axis=1))>.01
    if not valid.any():valid[np.argmax(np.mean(frames**2,axis=1))]=True
    P=np.abs(np.fft.rfft(frames*windows.hann(400,sym=False),n=512,axis=1))**2
    q=P/np.maximum(P.sum(axis=1,keepdims=True),1e-30)
    cent=q@F
    bw=np.sqrt(np.sum(q*(F[None,:]-cent[:,None])**2,axis=1))
    roll=F[np.argmax(np.cumsum(q,axis=1)>=.85,axis=1)]
    safe=np.maximum(P,1e-12*np.maximum(P.max(axis=1,keepdims=True),1e-30))
    flat=np.exp(np.mean(np.log(safe),axis=1))/safe.mean(axis=1)
    entropy=-np.sum(q*np.log(np.maximum(q,1e-30)),axis=1)/np.log(len(F))
    zcr=np.mean(np.signbit(frames[:,1:])!=np.signbit(frames[:,:-1]),axis=1)
    low=q[:,F<500].sum(axis=1)
    mag=np.sqrt(q)
    flux=np.linalg.norm(np.maximum(mag[1:]-mag[:-1],0),axis=1)
    flux=flux[valid[1:]&valid[:-1]]
    arrays=[cent[valid],bw[valid],roll[valid],flat[valid],entropy[valid],zcr[valid],low[valid],flux if len(flux) else np.array([0.])]
    aa=np.array(temporal+[v for arr in arrays for v in [arr.mean(),arr.std(ddof=0)]])
    # HTK mel scale, row-sum normalized triangular filters; natural log; c0 omitted.
    mel=P@MEL.T
    cep=dct(np.log(np.maximum(mel,1e-10)),type=2,norm='ortho',axis=1)[:,1:14]
    edges=np.pad(cep,((2,2),(0,0)),mode='edge')
    delta=(edges[3:-1]-edges[1:-3]+2*(edges[4:]-edges[:-4]))/10
    vm=np.pad(valid,(2,2),mode='edge')
    delta_valid=np.lib.stride_tricks.sliding_window_view(vm,5).all(axis=1)
    ds=delta[delta_valid].std(axis=0,ddof=0) if delta_valid.any() else np.zeros(13)
    bb=np.r_[cep[valid].mean(axis=0),cep[valid].std(axis=0,ddof=0),ds]
    assert aa.shape==(21,) and bb.shape==(39,) and np.isfinite(np.r_[aa,bb]).all()
    return aa,bb,dict(active_frames=int(valid.sum()),delta_valid_frames=int(delta_valid.sum()),frame_count=count)

def write_csv(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)

def main(dataset_root=None):
    OUT.mkdir(exist_ok=True)
    inventory=list(csv.DictReader((HERE/'evidence/inventory.csv').open(encoding='utf-8-sig')))
    audit=json.loads((HERE/'evidence/audit_summary.json').read_text())
    root=Path(dataset_root).resolve() if dataset_root is not None else Path(audit['root'])
    actual={p.relative_to(root).as_posix() for p in (root/'accepted').rglob('*') if p.is_file() and p.suffix.lower()=='.wav'}
    assert actual=={r['relative_path'] for r in inventory},'Dataset membership changed'
    A=[];B=[];rowsA=[];rowsB=[];qc=[]
    for r in inventory:
        p=root/r['relative_path']
        assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],'Audio changed: '+r['relative_path']
        y,sr=sf.read(p,dtype='float64');assert sr==16000 and y.ndim==1
        a,b,meta=extract(y);A.append(a);B.append(b)
        ids=dict(sample_id=r['index'],label=r['label'])
        rowsA.append(ids|dict(zip(A_NAMES,a.tolist())));rowsB.append(ids|dict(zip(B_NAMES,b.tolist())))
        qc.append(ids|meta)
    A=np.array(A);B=np.array(B)
    scalers={};Z={}
    for name,X in [('A',A),('B',B)]:
        mu=X.mean(axis=0);sd=X.std(axis=0);sd[sd<1e-12]=1
        Z[name]=(X-mu)/sd
        scalers[name]={'mean':mu.tolist(),'std':sd.tolist()}
    vectors={'A':Z['A']/np.sqrt(21),'B':Z['B']/np.sqrt(39),
             'C':np.c_[Z['A']/np.sqrt(42),Z['B']/np.sqrt(78)]}
    labels=np.array([r['label'] for r in inventory]);classes=sorted(set(labels));idx={c:np.flatnonzero(labels==c) for c in classes}
    summaries=[];pairs=[]
    for name,X in vectors.items():
        within=[pdist(X[idx[c]]).mean() for c in classes]
        between=[]
        for i,c in enumerate(classes):
            for d in classes[i+1:]:
                avg=float(cdist(X[idx[c]],X[idx[d]]).mean());between.append(avg)
                pairs.append(dict(feature_set=name,class_1=c,class_2=d,mean_pair_distance=avg,
                                  centroid_distance=float(np.linalg.norm(X[idx[c]].mean(axis=0)-X[idx[d]].mean(axis=0)))))
        summaries.append(dict(feature_set=name,dimensions=X.shape[1],within_macro=float(np.mean(within)),between_macro=float(np.mean(between)),
                              ratio=float(np.mean(between)/np.mean(within))))
    ranks=[]
    for name,X,features in [('A',A,A_NAMES),('B',B,B_NAMES)]:
        means=np.array([X[idx[c]].mean(axis=0) for c in classes]);var=np.array([X[idx[c]].var(axis=0) for c in classes])
        score=means.var(axis=0)/np.maximum(var.mean(axis=0),1e-12)
        for j,f in enumerate(features):ranks.append(dict(feature_set=name,feature=f,between_within_ratio=float(score[j])))
    rank_sorted=sorted(ranks,key=lambda r:r['between_within_ratio'],reverse=True)
    class_stats=[]
    for c in classes:
        row={'label':c,'count':len(idx[c])}
        for feature in ['centroid_hz_mean','flatness_mean','entropy_mean','low500_ratio_mean','flux_mean']:
            row[feature+'_median']=float(np.median(A[idx[c],A_NAMES.index(feature)]))
        class_stats.append(row)
    # Simple implementation checks: gain invariance; low-band energy of a low pure tone vs white noise.
    t=np.arange(16000)/16000;sig=np.sin(2*np.pi*220*t)*np.exp(-3*t)
    a1,b1,_=extract(sig);a2,b2,_=extract(sig*.02)
    assert np.allclose(a1,a2,rtol=1e-8,atol=1e-8) and np.allclose(b1,b2,rtol=1e-8,atol=1e-8)
    noise=np.random.default_rng(42).normal(size=16000);an,bn,_=extract(noise)
    assert a1[A_NAMES.index('low500_ratio_mean')]>an[A_NAMES.index('low500_ratio_mean')]
    assert a1[A_NAMES.index('flatness_mean')]<an[A_NAMES.index('flatness_mean')]
    write_csv(OUT/'features_A.csv',rowsA);write_csv(OUT/'features_B.csv',rowsB)
    write_csv(OUT/'features_C_standardized.csv',[dict(sample_id=r['index'],label=r['label'])|dict(zip(A_NAMES+B_NAMES,v.tolist())) for r,v in zip(inventory,vectors['C'])])
    write_csv(OUT/'quality.csv',qc);write_csv(OUT/'set_comparison.csv',summaries)
    write_csv(OUT/'class_pair_distances.csv',pairs);write_csv(OUT/'feature_ranking.csv',rank_sorted);write_csv(OUT/'class_feature_medians.csv',class_stats)
    (OUT/'scaling.json').write_text(json.dumps(scalers,indent=2))
    result={'created':datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat(),'files':len(inventory),'classes':len(classes),'dimensions':{'A':21,'B':39,'C':60},
            'finite':True,'input_hashes_match':True,'checks':'gain invariance, tone/noise low-band and flatness passed',
            'one_active_frame_files':sum(q['active_frames']==1 for q in qc),'no_delta_valid_frame_files':sum(q['delta_valid_frames']==0 for q in qc),
            'versions':{'numpy':np.__version__,'scipy':scipy.__version__,'soundfile':sf.__version__},'summaries':summaries,'top_features':rank_sorted[:12]}
    (OUT/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
