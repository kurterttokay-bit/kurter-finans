import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- FONKSİYON: CANLI KUR ÇEKME ---
def get_live_kurlar():
    try:
        url = "https://www.altin.in/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        kurlar = {}
        kurlar['USD'] = soup.find("li", {"id": "dolar"}).find("dfn").text.strip()
        kurlar['EUR'] = soup.find("li", {"id": "euro"}).find("dfn").text.strip()
        return kurlar
    except:
        return {"USD": "35,60", "EUR": "38,30"} # Bağlantı koparsa yedek

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
    sifre = st.text_input("Giriş Anahtarı", type="password")
    if st.button("Sistemi Aç"):
        if sifre == "patron125": st.session_state.giris_turu = "PATRON"
        elif sifre == "muhasebe007": st.session_state.giris_turu = "MUHASEBE"
        else: st.error("Hatalı Giriş!")
        st.rerun()
    st.stop()

# --- VERİ ÇEKME ---
try:
    df = conn.read(spreadsheet=edit_url, ttl=0)
    # Sütun isimlerini temizle (Başındaki sonundaki boşlukları siler)
    df.columns = [c.strip() for c in df.columns]
except:
    df = pd.DataFrame(columns=['Firma Adı', 'Evrak Tipi', 'Banka', 'Tutar', 'Vade', 'Açıklama'])

# --- MUHASEBE PANELİ ---
if st.session_state.giris_turu == "MUHASEBE":
    st.title("📝 Veri Giriş Ekranı")
    with st.form("kayit"):
        c1, c2 = st.columns(2)
        firma = c1.text_input("Firma Adı").upper()
        banka = c1.text_input("Banka").upper()
        tutar = c2.number_input("Tutar (TL)", min_value=0.0)
        vade = c2.date_input("Vade")
        evrak = st.selectbox("Evrak Tipi", ["Çek", "Senet", "Fatura"])
        not_ = st.text_input("Açıklama")
        
        if st.form_submit_button("Kaydet"):
            new_row = pd.DataFrame([{"Firma Adı": firma, "Evrak Tipi": evrak, "Banka": banka, "Tutar": tutar, "Vade": str(vade), "Açıklama": not_}])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(spreadsheet=edit_url, data=updated_df)
            st.success("Başarıyla eklendi!")
            st.rerun()

# --- PATRON PANELİ ---
elif st.session_state.giris_turu == "PATRON":
    st.title("👑 Yönetici Özeti")

    # Kurlar
    kurlar = get_live_kurlar()
    c1, c2, c3 = st.columns([1, 1, 2])
    c1.metric("💵 USD/TL", f"{kurlar['USD']} TL")
    c2.metric("💶 EUR/TL", f"{kurlar['EUR']} TL")
    
    # Filtreleme (Senin istediğin "Firma Adı" burada)
    col_name = "Firma Adı"
    if col_name in df.columns:
        firmalar = ["TÜMÜ"] + sorted(df[col_name].unique().tolist())
    else:
        firmalar = ["TÜMÜ"]
        st.error(f"DİKKAT: Excel'de '{col_name}' başlığı bulunamadı!")

    with c3:
        secili_firma = st.selectbox("🎯 Odaklan", firmalar)

    st.divider()

    if not df.empty and 'Tutar' in df.columns:
        # Veri Formatlama
        df['Tutar'] = pd.to_numeric(df['Tutar'], errors='coerce').fillna(0)
        df['Vade'] = pd.to_datetime(df['Vade'], errors='coerce')
        bugun = pd.to_datetime(datetime.now().date())
        
        # Filtrele
        f_df = df if secili_firma == "TÜMÜ" else df[df[col_name] == secili_firma]
        aktif_df = f_df[f_df['Vade'] >= bugun].copy()

        if not aktif_df.empty:
            total = aktif_df['Tutar'].sum()
            aktif_df['Gun'] = (aktif_df['Vade'] - bugun).dt.days
            ort_vade = (aktif_df['Tutar'] * aktif_df['Gun']).sum() / total if total > 0 else 0
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Toplam Yük", f"{total:,.2f} TL")
            m2.metric("Ort. Vade", f"{int(ort_vade)} Gün")
            m3.metric("Evrak Sayısı", len(aktif_df))

            st.subheader("📊 Ödeme Takvimi")
            fig = px.area(aktif_df.sort_values('Vade'), x='Vade', y='Tutar', 
                          labels={'Tutar':'Ödeme (TL)', 'Vade':'Tarih'})
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(aktif_df.sort_values('Vade'), use_container_width=True)
        else:
            st.info("Gelecek vadesi olan ödemeniz bulunmuyor.")

if st.sidebar.button("🔴 Oturumu Kapat"):
    st.session_state.giris_turu = None
    st.rerun()
