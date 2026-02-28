import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- CANLI KUR ÇEKME (Kuveyt Türk) ---
def get_live_kurlar():
    try:
        url = "https://finans.kuveytturk.com.tr/finans-portali"
        res = requests.get(url, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        kurlar = {}
        # Basit bir eşleşme ile USD ve EUR satış fiyatlarını alıyoruz
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) > 2:
                birim = cells[0].text.strip()
                if "USD" in birim: kurlar['USD'] = cells[2].text.strip()
                if "EUR" in birim: kurlar['EUR'] = cells[2].text.strip()
        return kurlar
    except: return None

# Sayfa Ayarları
st.set_page_config(page_title="Yapdoksan Mobil", layout="wide")

# --- BAĞLANTI ---
edit_url = "https://docs.google.com/spreadsheets/d/1gow0J5IA0GaB-BjViSKGbIxoZije0klFGgvDWYHdcNA/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- GÜVENLİK ---
if 'giris_turu' not in st.session_state:
    st.session_state.giris_turu = None

if st.session_state.giris_turu is None:
    st.title("🏛️ Yapdoksan Giriş")
    sifre = st.text_input("Giriş Anahtarı", type="password")
    if st.button("Sistemi Aç"):
        if sifre == "patron125": st.session_state.giris_turu = "PATRON"
        elif sifre == "muhasebe007": st.session_state.giris_turu = "MUHASEBE"
        else: st.error("Erişim Reddedildi!")
        st.rerun()
    st.stop()

# Veri Çekme
try:
    df = conn.read(spreadsheet=edit_url, ttl=0)
except:
    df = pd.DataFrame(columns=['Firma_Adi', 'Tutar', 'Vade', 'Banka'])

# --- PATRON PANELİ ---
if st.session_state.giris_turu == "PATRON":
    st.markdown("## 👑 Yönetim & Canlı Kur")
    
    # KURLAR VE ODAKLAN (MOBİL UYUMLU)
    live_k = get_live_kurlar()
    c1, c2, c3 = st.columns([1,1,2])
    if live_k:
        c1.metric("💵 USD", f"{live_k.get('USD', '0')} TL")
        c2.metric("💶 EUR", f"{live_k.get('EUR', '0')} TL")
    
    with c3:
        secili_firma = st.selectbox("🎯 Odaklan", ["TÜMÜ"] + sorted(df['Firma_Adi'].unique().tolist() if not df.empty else []))

    st.divider()

    if not df.empty:
        df['Vade'] = pd.to_datetime(df['Vade'])
        df['Tutar'] = pd.to_numeric(df['Tutar'], errors='coerce').fillna(0)
        # Filtreleme
        aktif_df = df if secili_firma == "TÜMÜ" else df[df['Firma_Adi'] == secili_firma]
        
        # Grafik
        fig = px.area(aktif_df.sort_values('Vade'), x='Vade', y='Tutar', title="Ödeme Projeksiyonu")
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(aktif_df.sort_values('Vade'), use_container_width=True)
    else:
        st.info("Veritabanı henüz boş.")

# (Muhasebe paneli önceki kodun aynısı olarak devam edebilir...)
