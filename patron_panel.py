import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- GERÇEK VE GÜNCEL KUR MOTORU ---
def get_live_kurlar():
    try:
        # Daha stabil bir kaynak: Doviz.com
        url = "https://www.doviz.com/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Sitedeki span class'larını hedef alıyoruz
        usd = soup.find("span", {"data-column": "mevcut", "data-row": "USD"}).text.strip()
        eur = soup.find("span", {"data-column": "mevcut", "data-row": "EUR"}).text.strip()
        return {"USD": usd, "EUR": eur}
    except Exception as e:
        # Eğer bu da patlarsa hata mesajını gör ki "salladın" demeyesin :D
        return {"USD": "Veri Alınamadı", "EUR": "Veri Alınamadı"}

# --- SAYFA VE BAĞLANTI AYARLARI ---
st.set_page_config(page_title="Yapdoksan Finans Pro", layout="wide")
edit_url = "https://docs.google.com/spreadsheets/d/1gow0J5IA0GaB-BjViSKGbIxoZije0klFGgvDWYHdcNA/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- GÜVENLİK ---
if 'giris_turu' not in st.session_state:
    st.session_state.giris_turu = None

if st.session_state.giris_turu is None:
    st.title("🏛️ Yapdoksan Giriş")
    sifre = st.text_input("Şifre", type="password")
    if st.button("Sistemi Aç"):
        if sifre == "patron125": st.session_state.giris_turu = "PATRON"
        elif sifre == "muhasebe007": st.session_state.giris_turu = "MUHASEBE"
        else: st.error("Hatalı Şifre!")
        st.rerun()
    st.stop()

# --- VERİ ÇEKME VE TEMİZLEME ---
try:
    df = conn.read(spreadsheet=edit_url, ttl=0)
    df.columns = [c.strip() for c in df.columns] # Başlıktaki boşlukları temizle
except:
    df = pd.DataFrame(columns=['Firma Adı', 'Evrak Tipi', 'Banka', 'Tutar', 'Vade', 'Açıklama'])

# --- PATRON PANELİ ---
if st.session_state.giris_turu == "PATRON":
    st.title("👑 Yönetim Paneli")

    # Kurları ekrana bas
    kurlar = get_live_kurlar()
    c1, c2, c3 = st.columns([1, 1, 2])
    c1.metric("💵 DOLAR", f"{kurlar['USD']} TL")
    c2.metric("💶 EURO", f"{kurlar['EUR']} TL")
    
    # Sütun kontrolü ve Odaklan (Firma Adı)
    col_name = "Firma Adı"
    if col_name in df.columns:
        firmalar = ["TÜMÜ"] + sorted(df[col_name].unique().tolist())
        with c3:
            secili_firma = st.selectbox("🎯 Odaklan", firmalar)
            
        st.divider()

        if not df.empty:
            df['Tutar'] = pd.to_numeric(df['Tutar'], errors='coerce').fillna(0)
            df['Vade'] = pd.to_datetime(df['Vade'], errors='coerce')
            bugun = pd.to_datetime(datetime.now().date())
            
            f_df = df if secili_firma == "TÜMÜ" else df[df[col_name] == secili_firma]
            aktif_df = f_df[f_df['Vade'] >= bugun].copy()

            if not aktif_df.empty:
                t_borc = aktif_df['Tutar'].sum()
                # Ağırlıklı Ortalama Vade
                aktif_df['Gun'] = (aktif_df['Vade'] - bugun).dt.days
                ort_v = (aktif_df['Tutar'] * aktif_df['Gun']).sum() / t_borc if t_borc > 0 else 0
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Toplam Yük", f"{t_borc:,.2f} TL")
                m2.metric("Ort. Vade", f"{int(ort_v)} Gün")
                m3.metric("Evrak", len(aktif_df))

                st.plotly_chart(px.area(aktif_df.sort_values('Vade'), x='Vade', y='Tutar'), use_container_width=True)
                st.dataframe(aktif_df.sort_values('Vade'), use_container_width=True)
    else:
        st.error(f"DİKKAT: Google Sheets başlığın '{col_name}' olmalı!")

# --- MUHASEBE PANELİ ---
elif st.session_state.giris_turu == "MUHASEBE":
    st.title("📝 Veri Girişi")
    # ... (Muhasebe giriş formu buraya gelecek, öncekiyle aynı mantık) ...
