import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- FONKSİYON: CANLI KUR ÇEKME (Altin.in üzerinden en sağlamı) ---
def get_live_kurlar():
    try:
        url = "https://www.altin.in/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        kurlar = {}
        kurlar['USD'] = soup.find("li", {"id": "dolar"}).find("dfn").text.strip()
        kurlar['EUR'] = soup.find("li", {"id": "euro"}).find("dfn").text.strip()
        return kurlar
    except:
        return {"USD": "Hata", "EUR": "Hata"}

# Sayfa Ayarları
st.set_page_config(page_title="Yapdoksan Finans Pro", layout="wide")

# --- BAĞLANTI ---
edit_url = "https://docs.google.com/spreadsheets/d/1gow0J5IA0GaB-BjViSKGbIxoZije0klFGgvDWYHdcNA/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- GÜVENLİK ---
if 'giris_turu' not in st.session_state:
    st.session_state.giris_turu = None

if st.session_state.giris_turu is None:
    st.title("🏛️ Yapdoksan Finans Giriş")
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
    # Sütun isimlerini ve formatları düzelt
    df['Tutar'] = pd.to_numeric(df['Tutar'], errors='coerce').fillna(0)
    df['Vade'] = pd.to_datetime(df['Vade'], errors='coerce')
except:
    df = pd.DataFrame(columns=['Firma_Adi', 'Evrak_Tipi', 'Banka', 'Tutar', 'Vade', 'Aciklama'])

# --- MUHASEBE PANELİ ---
if st.session_state.giris_turu == "MUHASEBE":
    st.title("📝 Muhasebe Veri Girişi")
    with st.form("yeni_kayit"):
        c1, c2 = st.columns(2)
        firma = c1.text_input("Firma Adı").upper()
        banka = c1.text_input("Banka").upper()
        tutar = c2.number_input("Tutar (TL)", min_value=0.0)
        vade = c2.date_input("Vade Tarihi")
        evrak = st.selectbox("Evrak Tipi", ["Çek", "Senet", "Fatura"])
        not_ = st.text_input("Açıklama")
        
        if st.form_submit_button("Sisteme Kaydet"):
            new_data = pd.DataFrame([{"Firma_Adi": firma, "Evrak_Tipi": evrak, "Banka": banka, "Tutar": tutar, "Vade": str(vade), "Aciklama": not_}])
            updated_df = pd.concat([df, new_data], ignore_index=True)
            conn.update(spreadsheet=edit_url, data=updated_df)
            st.success("Veri başarıyla işlendi!")
            st.rerun()

# --- PATRON PANELİ ---
elif st.session_state.giris_turu == "PATRON":
    st.title("👑 Patron Yönetim Paneli")

    # --- Üst Bölüm: Kurlar ve Filtre ---
    kurlar = get_live_kurlar()
    c1, c2, c3 = st.columns([1, 1, 2])
    c1.metric("💵 USD/TL", f"{kurlar['USD']} TL")
    c2.metric("💶 EUR/TL", f"{kurlar['EUR']} TL")
    
    with c3:
        firmalar = ["TÜMÜ"] + sorted(df['Firma_Adi'].unique().tolist()) if not df.empty else ["TÜMÜ"]
        secili_firma = st.selectbox("🎯 Odaklan (Cari Seç)", firmalar)

    st.divider()

    if not df.empty:
        bugun = pd.to_datetime(datetime.now().date())
        # Filtreleme
        f_df = df if secili_firma == "TÜMÜ" else df[df['Firma_Adi'] == secili_firma]
        aktif_df = f_df[f_df['Vade'] >= bugun].copy()

        if not aktif_df.empty:
            # Metrikler
            toplam_borc = aktif_df['Tutar'].sum()
            aktif_df['Gun'] = (aktif_df['Vade'] - bugun).dt.days
            ort_vade = (aktif_df['Tutar'] * aktif_df['Gun']).sum() / toplam_borc
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Toplam Ödeme", f"{toplam_borc:,.2f} TL")
            m2.metric("Ağırlıklı Vade", f"{int(ort_vade)} Gün")
            m3.metric("Evrak Sayısı", len(aktif_df))

            # Grafikler
            st.subheader("📉 Ödeme Projeksiyonu")
            fig = px.area(aktif_df.sort_values('Vade'), x='Vade', y='Tutar', hover_data=['Firma_Adi', 'Banka'])
            st.plotly_chart(fig, use_container_width=True)

            # Liste
            st.subheader("📑 Detaylı Liste")
            st.dataframe(aktif_df.sort_values('Vade')[['Firma_Adi', 'Banka', 'Evrak_Tipi', 'Tutar', 'Vade', 'Aciklama']], use_container_width=True)
        else:
            st.info("Gelecek ödemeniz bulunmuyor.")
    else:
        st.warning("Henüz veri girilmemiş.")

if st.sidebar.button("Güvenli Çıkış"):
    st.session_state.giris_turu = None
    st.rerun()
