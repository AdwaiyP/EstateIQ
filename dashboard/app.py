from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="EstateIQ | India Housing Intelligence", page_icon="🏙️", layout="wide")
BASE = Path(__file__).resolve().parent
st.markdown('''<style>
.stApp {background:#F7F9FC;color:#172B4D}
.block-container {padding-top:2rem;max-width:1450px}
h1,h2,h3 {color:#172B4D!important}
[data-testid="stMetric"] {background:#fff;border:1px solid #E2E8F0;border-radius:14px;padding:18px}
[data-testid="stMetricLabel"] {color:#64748B}
</style>''', unsafe_allow_html=True)

@st.cache_data
def load_csv(filename):
    path = BASE / 'data' / filename
    if not path.exists():
        st.error(f"Missing file: {path}. Export the PostgreSQL view to this location.")
        st.stop()
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower()
    required = {'city','observation_date','house_price_index'}
    missing = required - set(df.columns)
    if missing:
        st.error(f"{filename} is missing columns: {', '.join(sorted(missing))}. Found: {', '.join(df.columns)}")
        st.stop()
    df['city'] = df['city'].astype(str).str.strip()
    df['observation_date'] = pd.to_datetime(df['observation_date'], errors='coerce')
    for col in ['house_price_index','qoq_growth_pct','yoy_growth_pct']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        else:
            df[col] = float('nan')
    return df.dropna(subset=['observation_date','city'])

nhb = load_csv('nhb.csv')
rbi = load_csv('rbi.csv')


def fmt_hpi(x):
    return f"{x:,.2f}" if pd.notna(x) else "N/A"

def fmt_pct(x):
    return f"{x:+.2f}%" if pd.notna(x) else "N/A"

def latest_per_city(df):
    latest = df.groupby('city')['observation_date'].transform('max')
    return df.loc[df['observation_date'].eq(latest)].copy()

def line_plot(df, title):
    if df.empty:
        st.info('No observations available for this selection.')
        return
    series = df.groupby('observation_date',as_index=False)['house_price_index'].mean().sort_values('observation_date')
    fig = px.line(series, x='observation_date', y='house_price_index', markers=True,
                  labels={'observation_date':'Reporting quarter','house_price_index':'HPI (index points)'})
    fig.update_traces(line_color='#2563EB', marker_color='#2563EB')
    fig.update_layout(title=title,template='plotly_white',height=400,margin=dict(l=20,r=20,t=65,b=20))
    st.plotly_chart(fig, use_container_width=True)

def bar_plot(df, metric, title, n=10):
    valid = df.dropna(subset=[metric])
    if valid.empty:
        st.info('No reported values for this metric and reporting quarter. Missing values are not treated as zero.')
        return
    values = valid.groupby('city',as_index=False)[metric].mean().nlargest(n,metric).sort_values(metric)
    fig = px.bar(values, x=metric, y='city', orientation='h',
                 labels={'city':'City',metric:'Growth (%)' if 'growth' in metric else 'HPI (index points)'})
    fig.update_traces(marker_color='#2563EB')
    fig.update_layout(title=title,template='plotly_white',height=440,margin=dict(l=20,r=20,t=65,b=20))
    st.plotly_chart(fig,use_container_width=True)

st.markdown('### ESTATEIQ  /  INDIA HOUSING INTELLIGENCE')
st.title('Housing Market Analytics')
st.caption('RBI House Price Index & NHB RESIDEX | Index values are not property prices in rupees')
page = st.sidebar.radio('Explore', ['NHB Market Overview','RBI Historical Intelligence','Market Momentum'])

if page == 'NHB Market Overview':
    st.header('NHB Market Overview')
    c1,c2 = st.columns(2)
    city = c1.selectbox('Select city',sorted(nhb['city'].unique()))
    quarters = sorted(nhb['observation_date'].unique(),reverse=True)
    quarter = c2.selectbox('Reporting quarter',quarters,format_func=lambda d: pd.Timestamp(d).strftime('%d %b %Y'))
    chosen = nhb[(nhb.city==city)&(nhb.observation_date==quarter)]
    city_history = nhb[nhb.city==city]
    k1,k2,k3,k4 = st.columns(4)
    k1.metric('Cities covered',nhb.city.nunique())
    k2.metric('HPI for selected quarter',fmt_hpi(chosen.house_price_index.mean()))
    k3.metric('QoQ growth',fmt_pct(chosen.qoq_growth_pct.mean()))
    k4.metric('YoY growth',fmt_pct(chosen.yoy_growth_pct.mean()))
    left,right=st.columns(2)
    with left: line_plot(city_history,f'{city} — HPI history')
    with right: bar_plot(nhb[nhb.observation_date==quarter],'house_price_index','Top 10 cities by HPI')

elif page == 'RBI Historical Intelligence':
    st.header('RBI Historical Intelligence')
    city=st.selectbox('Select city',sorted(rbi.city.unique()))
    history=rbi[rbi.city==city]
    most_recent=history[history.observation_date==history.observation_date.max()]
    k1,k2,k3=st.columns(3)
    k1.metric('Latest RBI HPI',fmt_hpi(most_recent.house_price_index.mean()))
    k2.metric('Latest QoQ growth',fmt_pct(most_recent.qoq_growth_pct.mean()))
    k3.metric('Latest YoY growth',fmt_pct(most_recent.yoy_growth_pct.mean()))
    line_plot(history,f'{city} — historical RBI HPI')
    st.subheader('Latest HPI by city')
    comparable=latest_per_city(rbi)
    comparable=comparable[comparable.city.str.casefold()!='all india']
    bar_plot(comparable,'house_price_index','Latest available RBI HPI by city',n=20)
    st.caption('RBI city index levels are compared within the RBI series only; cities may have different latest dates.')

else:
    st.header('Market Momentum')
    quarters=sorted(nhb.observation_date.unique(),reverse=True)
    quarter=st.selectbox('Reporting quarter',quarters,format_func=lambda d:pd.Timestamp(d).strftime('%d %b %Y'))
    selected=nhb[nhb.observation_date==quarter]
    st.metric('Cities with reported YoY growth',selected.dropna(subset=['yoy_growth_pct']).city.nunique())
    left,right=st.columns(2)
    with left: bar_plot(selected,'yoy_growth_pct','Top 10 cities — annual growth')
    with right: bar_plot(selected,'qoq_growth_pct','Top 10 cities — quarterly growth')
    st.caption('Unavailable growth observations are intentionally left blank; they are not zero.')

st.divider()
st.caption('Source: RBI HPI and NHB RESIDEX exported analytical snapshots. The two indices are not directly interchangeable. Data is a static export, not live market prices.')
