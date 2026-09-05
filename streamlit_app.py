from __future__ import annotations
import urllib.parse
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from siter_engine import DataLab, TerritorialAnalytics, MODEL_REGISTRY, normalize_base, sha256_obj, run_model

APP_VERSION="7.3-MOBILE-READY"
BASE_MODEL=Path(__file__).parent/"netlogo"/"territorial_lab_mobile.nlogo"
PARAM_META={
 "beta_voter":(.1,3.,1.,"Sensibilidad de actualización"),"epsilon":(.01,1.,.40,"Umbral de atracción"),
 "mu":(.01,1.,.30,"Fuerza de ajuste"),"epsilon_repulsion":(.01,2.,.80,"Umbral de repulsión"),
 "mu_rep":(.01,1.,.15,"Fuerza de repulsión"),"coupling_saf":(0.,1.,.50,"Acoplamiento estructural"),
 "field_pressure":(-1.,1.,0.,"Presión de campo"),"shock":(0.,1.,0.,"Perturbación exógena"),
 "steps":(5,200,30,"Iteraciones"),"seed":(0,9999,42,"Semilla reproducible")}
st.set_page_config(page_title=f"SITER-CAE {APP_VERSION}",page_icon="🧬",layout="centered")
st.markdown("<style>.block-container{max-width:980px;padding:1rem 1rem 2rem}.mobile-card{padding:.8rem 1rem;border:1px solid rgba(128,128,128,.25);border-radius:12px;margin:.4rem 0 1rem}iframe{border-radius:12px}</style>",unsafe_allow_html=True)

def get_secret(name):
    try:return str(st.secrets.get(name,"")).strip()
    except Exception:return ""

def make_model_bytes(df):
    text=BASE_MODEL.read_text(encoding="utf-8")
    start=text.index("  let rows (list"); end=text.index("\n  )\n  foreach rows",start)+len("\n  )")
    rows=[]
    for _,r in df.iterrows():
        vals=[r.get("territorial_unit_id",""),r.get("alcaldia",""),r.get("poblacion",1000),r.get("opinion_continua",0),r.get("temperatura",.5),r.get("capital_social",.5),r.get("acceso_informacion",.5),r.get("influencia_liderazgo",.5),r.get("arraigo",.5),r.get("nivel_movilizacion",.5),r.get("desconfianza",.5),r.get("exposicion_problema",.5),r.get("influencia_liderazgo",.5),r.get("influencia_liderazgo",.5),r.get("resistencia_institucional",.5),r.get("prioridad_problema",.5),r.get("lat",0),r.get("lon",0)]
        parts=[f'"{str(v).replace(chr(34),chr(39))}"' if isinstance(v,str) else f"{float(v):.8g}" for v in vals]
        rows.append("      ["+" ".join(parts)+"]")
    block="  let rows (list\n"+"\n".join(rows)+"\n  )"
    return (text[:start]+block+text[end:]).encode()

st.title("SITER-CAE v7.3-MOBILE")
st.caption("Consultoría territorial · Streamlit Cloud + NetLogo Web · phone-first")
with st.expander("Flujo de trabajo",expanded=True):
    st.write("**Matriz del consultor → análisis Python → escenario ABM → interpretación.**")
    st.info("Los resultados de simulación son escenarios analíticos; no equivalen a observaciones empíricas ni predicciones garantizadas.")

st.subheader("1 · Caso territorial")
source=st.radio("Fuente",["DUMMY 80","DUMMY 48","CSV propio"],horizontal=True)
if source=="DUMMY 80": df=DataLab.synthetic(80,42)
elif source=="DUMMY 48": df=DataLab.synthetic(48,42)
else:
    up=st.file_uploader("Sube CSV territorial",type=["csv"])
    df=DataLab.synthetic(80,42) if up is None else pd.read_csv(up)
df=normalize_base(df)
G=TerritorialAnalytics.network(df)
a,b,c=st.columns(3); a.metric("Unidades",len(df)); b.metric("Aristas",G.number_of_edges()); c.metric("Hash",sha256_obj(df.to_dict(orient="records"))[:10])
with st.expander("Tabla territorial"): st.dataframe(df,use_container_width=True,height=280)
with st.expander("Resumen por alcaldía"): st.dataframe(TerritorialAnalytics.table(df),use_container_width=True)

st.subheader("2 · Matriz del consultor")
params={}; cols=st.columns(2)
for i,(name,(lo,hi,default,help_text)) in enumerate(PARAM_META.items()):
    with cols[i%2]:
        if name in ("steps","seed"): params[name]=int(st.number_input(name,int(lo),int(hi),int(default),help=help_text))
        else: params[name]=float(st.number_input(name,float(lo),float(hi),float(default),step=.01,help=help_text))

st.subheader("3 · Simulación Python")
model_name=st.selectbox("Modelo sociofísico",list(MODEL_REGISTRY.keys()))
if st.button("Ejecutar escenario",type="primary",use_container_width=True):
    rng=np.random.default_rng(params["seed"]); n=len(df); A=(rng.random((n,n))<.12).astype(float); A=np.triu(A,1); A=A+A.T; np.fill_diagonal(A,0)
    x=((df["opinion_continua"].to_numpy(float)+1)/2).clip(0,1)
    try:
        hist=run_model(model_name,x,A,params,seed=params["seed"])
        if hist.ndim==2: st.line_chart(pd.DataFrame({"media":np.mean(hist,axis=1),"dispersion":np.std(hist,axis=1)}))
        else: st.line_chart(pd.DataFrame({"serie":hist}))
        final=np.asarray(hist[-1]); st.metric("Estado final medio",f"{float(np.mean(final)):.3f}")
        st.write("**Lectura del consultor:** el cambio observado corresponde al escenario parametrizado y a la red sintética/territorial utilizada; debe contrastarse con evidencia de campo.")
    except Exception as exc: st.error(f"No fue posible ejecutar el modelo: {exc}")

st.subheader("4 · NetLogo Web")
model_url=get_secret("NETLOGO_MODEL_URL") or st.text_input("URL pública del modelo NetLogo",placeholder="https://raw.githubusercontent.com/USUARIO/REPO/main/netlogo/territorial_lab_mobile.nlogo")
if model_url:
    web_url="https://netlogoweb.org/web?url="+urllib.parse.quote(model_url,safe="")+"&speed=0.2"
    st.link_button("Abrir NetLogo Web",web_url,use_container_width=True)
    with st.expander("Simulador dentro de SITER",expanded=False): components.iframe(web_url,height=680,scrolling=True)
else: st.info("Publica el .nlogo y configura NETLOGO_MODEL_URL en Streamlit Cloud cuando quieras el ABM remoto.")

st.subheader("5 · Caso personalizado para NetLogo")
st.download_button("⬇️ Descargar .nlogo con el caso actual",make_model_bytes(df),"territorial_lab_mobile.nlogo","text/plain",use_container_width=True)
with st.expander("Arquitectura móvil"):
    st.markdown("**Streamlit Cloud:** cálculo, matriz, datos e interpretación.  \n**NetLogo Web:** ABM visual en navegador.  \n**GitHub:** código y modelo.  \n**No requerido para operar:** Python local, NetLogo Desktop o una PC.")
st.divider(); st.caption(f"SITER-CAE {APP_VERSION} · {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
