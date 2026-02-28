import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# Sayfa Ayarları
st.set_page_config(page_title="Yapdoksan Finans Pro", layout="wide")

# --- BAĞLANTI ---
edit_url = "https://docs.google.com/spreadsheets/d/1gow0J5IA0GaB-BjViSKGbIxoZije0klFGgvDWYHdcNA/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- GÜVENLİK ---
if 'giris_turu' not in st.session_state:
    st.session_state.giris_turu = None

if st.session_state.giris_turu is None:
    st.title("🔒 Yapdoksan Giriş")
    sifre = st.text_input("Şifre", type="password")
    if st.button("Giriş Yap"):
        if sifre == "patron125": st.session_state.giris_turu = "PATRON"
        elif sifre == "muhasebe007": st.session_state.giris_turu = "MUHASEBE"
        else: st.error("Hatalı Şifre!")
        st.rerun()
    st.stop()

# --- VERİ ÇEKME ---
try:
    df = conn.read(spreadsheet=edit_url, ttl=0)
    df.columns = [c.strip() for c in df.columns]
except:
    df = pd.DataFrame(columns=['Firma Adı', 'Evrak Tipi', 'Banka', 'Tutar', 'Vade', 'Açıklama'])

# --- PATRON PANELİ ---
if st.session_state.giris_turu == "PATRON":
    st.title("👑 Yönetim Paneli")
    
    col_name = "Firma Adı"
    if col_name in df.columns:
        # --- SIDEBAR DİZİLİMİ ---
        with st.sidebar:
            st.header("⚙️ Kontrol Paneli")
            firmalar = ["TÜMÜ"] + sorted(df[col_name].unique().tolist())
            secili_firma = st.selectbox("🎯 Cari Seç", firmalar)
            
            st.divider() # Görsel ayrım
            
            if st.button("🔴 Oturumu Kapat", use_container_width=True):
                st.session_state.giris_turu = None
                st.rerun()
        
        if not df.empty:
            df['Tutar'] = pd.to_numeric(df['Tutar'], errors='coerce').fillna(0)
            df['Vade'] = pd.to_datetime(df['Vade'], errors='coerce')
            bugun = pd.to_datetime(datetime.now().date())
            
            f_df = df if secili_firma == "TÜMÜ" else df[df[col_name] == secili_firma]
            aktif_df = f_df[f_df['Vade'] >= bugun].copy()

            # Üst Metrikler
            t_borc = aktif_df['Tutar'].sum()
            m1, m2, m3 = st.columns(3)
            m1.metric("Toplam Yük", f"{t_borc:,.2f} TL")
            m2.metric("Evrak Sayısı", len(aktif_df))
            
            if t_borc > 0:
                aktif_df['Gun'] = (aktif_df['Vade'] - bugun).dt.days
                ort_v = (aktif_df['Tutar'] * aktif_df['Gun']).sum() / t_borc
                m3.metric("Ort. Vade", f"{int(ort_v)} Gün")

            st.divider()
            
            # Grafik
            st.plotly_chart(px.area(aktif_df.sort_values('Vade'), x='Vade', y='Tutar', title="Ödeme Takvimi"), use_container_width=True)
            
            # Tablo
            st.dataframe(aktif_df.sort_values('Vade'), use_container_width=True)
    else:
        st.error(f"DİKKAT: Excel başlığın '{col_name}' olmalı!")

# --- MUHASEBE PANELİ ---
elif st.session_state.giris_turu == "MUHASEBE":
    st.title("📝 Veri Girişi")
    
    with st.sidebar:
        st.header("⚙️ Muhasebe Menü")
        if st.button("🔴 Oturumu Kapat", use_container_width=True):
            st.session_state.giris_turu = None
            st.rerun()

    with st.form("muhasebe_form"):
        f_adi = st.text_input("Firma Adı").upper()
        e_tipi = st.selectbox("Evrak Tipi", ["Çek", "Senet", "Fatura"])
        b_adi = st.text_input("Banka").upper()
        tutar = st.number_input("Tutar", min_value=0.0)
        vade = st.date_input("Vade Tarihi")
        not_ = st.text_input("Not")
        
        if st.form_submit_button("Kaydet"):
            yeni_satir = pd.DataFrame([{"Firma Adı": f_adi, "Evrak Tipi": e_tipi, "Banka": b_adi, "Tutar": tutar, "Vade": str(vade), "Açıklama": not_}])
            yeni_df = pd.concat([df, yeni_satir], ignore_index=True)
            conn.update(spreadsheet=edit_url, data=yeni_df)
            st.success("Kaydedildi!")
            st.rerun()
