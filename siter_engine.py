from __future__ import annotations
import hashlib, json, math, re
from typing import Any
import numpy as np
import pandas as pd
import networkx as nx

ALCALDIAS = [
    "ALVARO OBREGON","AZCAPOTZALCO","BENITO JUAREZ","COYOACAN",
    "CUAJIMALPA DE MORELOS","CUAUHTEMOC","GUSTAVO A MADERO","IZTACALCO",
    "IZTAPALAPA","LA MAGDALENA CONTRERAS","MIGUEL HIDALGO","MILPA ALTA",
    "TLAHUAC","TLALPAN","VENUSTIANO CARRANZA","XOCHIMILCO",
]
ALCALDIA_COORDS = {
    "CUAUHTEMOC": (19.4326,-99.1332), "BENITO JUAREZ": (19.3984,-99.1576),
    "MIGUEL HIDALGO": (19.4285,-99.2000), "COYOACAN": (19.3467,-99.1617),
    "IZTAPALAPA": (19.3550,-99.0620), "GUSTAVO A MADERO": (19.49,-99.11),
    "ALVARO OBREGON": (19.358,-99.227), "TLALPAN": (19.288,-99.167),
    "XOCHIMILCO": (19.263,-99.104), "VENUSTIANO CARRANZA": (19.42,-99.10),
    "AZCAPOTZALCO": (19.487,-99.186), "IZTACALCO": (19.395,-99.098),
    "CUAJIMALPA DE MORELOS": (19.357,-99.29), "LA MAGDALENA CONTRERAS": (19.32,-99.24),
    "TLAHUAC": (19.27,-99.005), "MILPA ALTA": (19.192,-99.023),
}

def norm_col(x):
    s = str(x).strip().lower()
    s = re.sub(r"[^a-z0-9_]+", "_", s)
    return s.strip("_")

def clean_alcaldia(x):
    s = str(x).strip().upper()
    return s.translate(str.maketrans("ÁÉÍÓÚÜÑ", "AEIOUUN"))

def sha256_obj(obj):
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()

def gini(values):
    x = np.asarray(values, float)
    x = np.abs(x[np.isfinite(x)])
    if len(x) == 0 or np.allclose(x.sum(), 0): return 0.0
    x = np.sort(x); n = len(x)
    return float((2*np.sum(np.arange(1,n+1)*x)/(n*x.sum()))-(n+1)/n)

def entropy_from_counts(counts):
    vals = np.asarray(list(counts), float); vals = vals[vals > 0]
    if len(vals) == 0: return 0.0
    p = vals/vals.sum(); return float(-np.sum(p*np.log(p)))

def field_state(simpat, indec, stability, polarization):
    if stability >= .70 and max(simpat, 1-simpat-indec) >= .50: return "CONSOLIDACION"
    if indec >= .35 or polarization >= .55 or stability < .45: return "DISPUTA_ABIERTA"
    return "CONTENCION"

def ensure_lat_lon(df, seed=42):
    out = df.copy(); rng = np.random.default_rng(seed)
    if "alcaldia" not in out: out["alcaldia"] = rng.choice(ALCALDIAS, len(out))
    out["alcaldia"] = out["alcaldia"].map(clean_alcaldia)
    lats, lons = [], []
    for a in out["alcaldia"]:
        lat, lon = ALCALDIA_COORDS.get(a, (19.35,-99.15))
        lats.append(lat+rng.normal(0,.007)); lons.append(lon+rng.normal(0,.007))
    if "lat" not in out: out["lat"] = lats
    else: out["lat"] = pd.to_numeric(out["lat"], errors="coerce").fillna(pd.Series(lats,index=out.index))
    if "lon" not in out: out["lon"] = lons
    else: out["lon"] = pd.to_numeric(out["lon"], errors="coerce").fillna(pd.Series(lons,index=out.index))
    return out

def normalize_base(df, seed=42):
    out = df.copy(); out.columns = [norm_col(c) for c in out.columns]
    aliases = {"seccion_electoral":"seccion","seccion_id":"seccion","territory_id":"territorial_unit_id","id_territorial":"territorial_unit_id","id":"territorial_unit_id"}
    for a,b in aliases.items():
        if a in out.columns and b not in out.columns: out[b] = out[a]
    if "territorial_unit_id" not in out: out["territorial_unit_id"] = [f"CDMX-SEC-{i+1:05d}" for i in range(len(out))]
    if "seccion" not in out: out["seccion"] = out["territorial_unit_id"].astype(str)
    if "utm" not in out: out["utm"] = ""
    if "manzana" not in out: out["manzana"] = ""
    if "alcaldia" not in out: out["alcaldia"] = "NO_ESPECIFICADA"
    out["alcaldia"] = out["alcaldia"].map(clean_alcaldia)
    defaults = {"opinion_continua":0.0,"capital_social":.5,"acceso_informacion":.5,"influencia_liderazgo":.5,"arraigo":.5,"nivel_movilizacion":.5,"desconfianza":.5,"exposicion_problema":.5,"temperatura":.5,"resistencia_institucional":.5,"prioridad_problema":.5,"poblacion":1000.0}
    for c,v in defaults.items():
        if c not in out: out[c] = v
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(v)
    out["opinion_continua"] = out["opinion_continua"].clip(-1,1)
    out = ensure_lat_lon(out, seed)
    out["intencion"] = out["opinion_continua"].apply(lambda x: "SIMPATIZANTE" if x>.33 else ("OPOSITOR" if x<-.33 else "INDECISO"))
    out["opinion"] = out["opinion_continua"]
    return out.reset_index(drop=True)

class DataLab:
    @staticmethod
    def synthetic(n=80, seed=42):
        rng=np.random.default_rng(seed); rows=[]
        for i in range(n):
            alc=ALCALDIAS[i%len(ALCALDIAS)]
            rows.append({"territorial_unit_id":f"SYN-{i+1:04d}","alcaldia":alc,"seccion":str(1000+i),
                "opinion_continua":float(np.clip(rng.normal(0,.5),-1,1)),"capital_social":float(rng.random()),
                "acceso_informacion":float(rng.random()),"influencia_liderazgo":float(rng.random()),"arraigo":float(rng.random()),
                "nivel_movilizacion":float(rng.random()),"desconfianza":float(rng.random()*.6),"exposicion_problema":float(rng.random()),
                "temperatura":float(rng.random()),"resistencia_institucional":float(rng.random()),"prioridad_problema":float(rng.random()),
                "poblacion":float(800+rng.random()*400),"lat":ALCALDIA_COORDS[alc][0]+rng.normal(0,.007),"lon":ALCALDIA_COORDS[alc][1]+rng.normal(0,.007)})
        return normalize_base(pd.DataFrame(rows), seed)

class TerritorialAnalytics:
    @staticmethod
    def network(df, geo_threshold_km=8.0, k_neighbors=6, seed=42):
        rng=np.random.default_rng(seed); G=nx.Graph()
        for _,r in df.iterrows(): G.add_node(r["territorial_unit_id"],alcaldia=r["alcaldia"],lat=r["lat"],lon=r["lon"])
        def hav(a,b,c,d):
            R=6371.; p1,p2=math.radians(a),math.radians(c); dp=math.radians(c-a); dl=math.radians(d-b)
            q=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
            return 2*R*math.asin(min(1,math.sqrt(q)))
        nodes=list(G.nodes(data=True))
        for i in range(len(nodes)):
            for j in range(i+1,len(nodes)):
                u,a=nodes[i]; v,b=nodes[j]; d=hav(a["lat"],a["lon"],b["lat"],b["lon"])
                if d<=geo_threshold_km or rng.random()<.05: G.add_edge(u,v,weight=.5,distance_km=d)
        return G
    @staticmethod
    def table(df):
        rows=[]
        for alc,sub in df.groupby("alcaldia",dropna=False):
            sim=float((sub.opinion_continua>.33).mean()); opo=float((sub.opinion_continua<-.33).mean()); ind=1-sim-opo
            ent=entropy_from_counts([sim,opo,ind]); stab=1-ent/math.log(3) if ent else 1.; pol=float(sub.opinion_continua.std()) if len(sub)>1 else 0
            rows.append({"alcaldia":alc,"n":len(sub),"simpat":sim,"opos":opo,"indec":ind,"entropia":ent,"estabilidad":stab,"polarizacion":pol,"campo":field_state(sim,ind,stab,pol),"resistencia":float(sub.resistencia_institucional.mean()),"prioridad":float(sub.prioridad_problema.mean())})
        return pd.DataFrame(rows)

class OpinionModels:
    @staticmethod
    def voter(x,A,beta=1.,steps=30,seed=42):
        rng=np.random.default_rng(seed); x=np.asarray(x,float).copy(); G=nx.from_numpy_array(np.asarray(A)); hist=[x.copy()]
        for _ in range(steps):
            y=x.copy()
            for i in range(len(x)):
                nb=list(G.neighbors(i))
                if nb: y[i]=x[rng.choice(nb)]
            x=(1-.5/beta)*x+(.5/beta)*y if beta>=.5 else y; hist.append(x.copy())
        return np.asarray(hist)
    @staticmethod
    def deffuant(x,A,epsilon=.4,mu=.3,repulsion=.8,mu_rep=.15,steps=30,seed=42):
        rng=np.random.default_rng(seed); x=np.asarray(x,float).copy(); edges=np.argwhere(np.asarray(A)>0); hist=[x.copy()]
        for _ in range(steps):
            y=x.copy(); rng.shuffle(edges)
            for i,j in edges:
                if i>=j: continue
                d=x[i]-x[j]
                if abs(d)<=epsilon: y[i]-=mu*d; y[j]+=mu*d
                elif abs(d)>=repulsion: y[i]+=mu_rep*d*.5; y[j]-=mu_rep*d*.5
            x=np.clip(y,0,1); hist.append(x.copy())
        return np.asarray(hist)
    @staticmethod
    def ising(x,A,coupling=.5,field=None,temperature=.2,steps=30,seed=42):
        rng=np.random.default_rng(seed); s=np.where(np.asarray(x)>=.5,1,-1).astype(int); A=np.asarray(A); h=np.zeros(len(s)) if field is None else np.asarray(field); hist=[s.copy()]
        for _ in range(steps):
            for i in rng.permutation(len(s)):
                H=coupling*np.dot(A[i],s)+h[i]; p=1/(1+np.exp(-2*H/max(temperature,1e-6))); s[i]=1 if rng.random()<p else -1
            hist.append(s.copy())
        return np.asarray(hist)
    @staticmethod
    def hk(x,A,epsilon=.2,steps=30):
        x=np.asarray(x,float).copy(); A=np.asarray(A); hist=[x.copy()]
        for _ in range(steps):
            y=x.copy()
            for i in range(len(x)):
                nb=np.where((A[i]>0)&(np.abs(x-x[i])<=epsilon))[0]
                if len(nb): y[i]=np.mean(x[nb])
            x=np.clip(y,0,1); hist.append(x.copy())
        return np.asarray(hist)
    @staticmethod
    def degroot(x,A,steps=30):
        x=np.asarray(x,float).copy(); W=np.asarray(A,float); W=W/np.maximum(W.sum(1,keepdims=True),1e-12); hist=[x.copy()]
        for _ in range(steps): x=W@x; hist.append(x.copy())
        return np.asarray(hist)
    @staticmethod
    def friedkin_johnsen(x,A,lam=.7,steps=30):
        x=np.asarray(x,float).copy(); x0=x.copy(); W=np.asarray(A,float); W=W/np.maximum(W.sum(1,keepdims=True),1e-12); hist=[x.copy()]
        for _ in range(steps): x=lam*(W@x)+(1-lam)*x0; hist.append(x.copy())
        return np.asarray(hist)
    @staticmethod
    def watts_threshold(x,A,theta=.5,steps=30):
        s=np.asarray(x,float)>=.5; A=np.asarray(A); hist=[s.astype(int).copy()]
        for _ in range(steps):
            y=s.copy()
            for i in range(len(s)):
                nb=np.where(A[i]>0)[0]
                if len(nb): y[i]=np.mean(s[nb])>=theta
            s=y; hist.append(s.astype(int).copy())
        return np.asarray(hist)
    @staticmethod
    def complex_contagion(x,A,threshold=2,steps=30):
        s=np.asarray(x,float)>=.5; A=np.asarray(A); hist=[s.astype(int).copy()]
        for _ in range(steps):
            y=s.copy()
            for i in range(len(s)):
                nb=np.where(A[i]>0)[0]
                if len(nb) and np.sum(s[nb])>=threshold: y[i]=True
            s=y; hist.append(s.astype(int).copy())
        return np.asarray(hist)
    @staticmethod
    def majority(x,A,steps=30):
        x=np.asarray(x,float).copy(); A=np.asarray(A); hist=[x.copy()]
        for _ in range(steps):
            y=x.copy()
            for i in range(len(x)):
                nb=np.where(A[i]>0)[0]
                if len(nb): y[i]=float(np.mean(x[nb])>=.5)
            x=y; hist.append(x.copy())
        return np.asarray(hist)
    @staticmethod
    def q_voter(x,A,q=3,epsilon=.5,steps=30,seed=42):
        rng=np.random.default_rng(seed); x=np.asarray(x,float).copy(); A=np.asarray(A); hist=[x.copy()]
        for _ in range(steps):
            y=x.copy()
            for i in rng.permutation(len(x)):
                nb=np.where(A[i]>0)[0]
                if len(nb)>=q:
                    s=rng.choice(nb,q,replace=False); signs=x[s]>=.5
                    if np.all(signs) or not np.any(signs): y[i]=float(np.mean(signs))
                    elif rng.random()<epsilon: y[i]=float(rng.random()>.5)
            x=y; hist.append(x.copy())
        return np.asarray(hist)
    @staticmethod
    def sznajd(x,A,steps=30,seed=42):
        rng=np.random.default_rng(seed); s=np.asarray(x,float)>=.5; A=np.asarray(A); hist=[s.astype(int).copy()]
        for _ in range(steps):
            for i in rng.permutation(len(s)):
                nb=np.where(A[i]>0)[0]
                if len(nb):
                    j=int(rng.choice(nb)); common=np.where((A[i]>0)&(A[j]>0))[0]
                    if s[i]==s[j] and len(common): s[common]=s[i]
            hist.append(s.astype(int).copy())
        return np.asarray(hist)
    @staticmethod
    def zealot(x,A,zealots=None,steps=30):
        x=np.asarray(x,float).copy(); A=np.asarray(A); z=set(zealots or []); hist=[x.copy()]
        for _ in range(steps):
            y=x.copy()
            for i in range(len(x)):
                if i in z: continue
                nb=np.where(A[i]>0)[0]
                if len(nb): y[i]=np.mean(x[nb])
            x=y; hist.append(x.copy())
        return np.asarray(hist)
    @staticmethod
    def rfim(x,A,field,coupling=.5,disorder=.2,steps=30,seed=42):
        rng=np.random.default_rng(seed); s=np.where(np.asarray(x)>=.5,1,-1).astype(int); A=np.asarray(A); h=np.asarray(field,float)+rng.normal(0,disorder,len(s)); hist=[s.copy()]
        for _ in range(steps):
            for i in rng.permutation(len(s)):
                s[i]=1 if coupling*np.dot(A[i],s)+h[i]>=0 else -1
            hist.append(s.copy())
        return np.asarray(hist)

MODEL_REGISTRY = {
    "Voter": OpinionModels.voter, "Deffuant": OpinionModels.deffuant, "Ising": OpinionModels.ising,
    "Hegselmann-Krause": OpinionModels.hk, "DeGroot": OpinionModels.degroot,
    "Friedkin-Johnsen": OpinionModels.friedkin_johnsen, "Watts Threshold": OpinionModels.watts_threshold,
    "Contagio complejo": OpinionModels.complex_contagion, "Mayoría": OpinionModels.majority,
    "q-Voter": OpinionModels.q_voter, "Sznajd": OpinionModels.sznajd, "Zealot": OpinionModels.zealot,
    "RFIM": OpinionModels.rfim,
}

def run_model(name, x, A, params, seed=42):
    fn=MODEL_REGISTRY[name]
    common={"steps":int(params.get("steps",30))}
    if name=="Voter": common.update(beta=float(params["beta_voter"]),seed=seed)
    elif name=="Deffuant": common.update(epsilon=float(params["epsilon"]),mu=float(params["mu"]),repulsion=float(params["epsilon_repulsion"]),mu_rep=float(params["mu_rep"]),seed=seed)
    elif name=="Ising": common.update(coupling=float(params["coupling_saf"]),temperature=max(.05,float(params.get("temperature",.2))),seed=seed)
    elif name=="Hegselmann-Krause": common.update(epsilon=float(params["epsilon"]))
    elif name=="Friedkin-Johnsen": common.update(lam=float(params["coupling_saf"]))
    elif name=="Watts Threshold": common.update(theta=float(params["epsilon"]))
    elif name=="Contagio complejo": common.update(threshold=max(1,int(round(1+4*float(params["epsilon"])))) )
    elif name=="q-Voter": common.update(q=3,epsilon=float(params["epsilon"]),seed=seed)
    elif name=="Sznajd": common.update(seed=seed)
    elif name=="RFIM":
        field=np.full(len(x),float(params["field_pressure"]))
        common.update(field=field,coupling=float(params["coupling_saf"]),disorder=float(params.get("disorder",.2)),seed=seed)
    return fn(x,A,**common)
