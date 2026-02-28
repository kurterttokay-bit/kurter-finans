import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
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
    if st.button("Sistemi Aç"):
        if sifre == "patron125": st.session_state.giris_turu = "PATRON"
        elif sifre == "muhasebe007": st.session_state.giris_turu = "MUHASEBE"
        else: st.error("Hatalı Şifre!")
        st.rerun()
    st.stop()

# --- VERİ ÇEKME (Sütun Korumalı & Hata Önleyici) ---
@st.cache_data(ttl=0)
def get_clean_data():
    try:
        # Sadece ilk 6 sütunu al (A'dan F'ye) - Sheets'teki sağa saçılan çöpleri görmezden gel
        data = conn.read(spreadsheet=edit_url, ttl=0, usecols=[0,1,2,3,4,5])
        data.columns = ["Firma Adı", "Evrak Tipi", "Banka", "Tutar", "Vade", "Açıklama"]
        
        if not data.empty:
            # Tarih temizliği
            data['Vade_Hesap'] = pd.to_datetime(data['Vade'], errors='coerce').dt.date
            data['Tutar'] = pd.to_numeric(data['Tutar'], errors='coerce').fillna(0)
            data['Firma Adı'] = data['Firma Adı'].str.strip().str.upper()
        return data
    except:
        return pd.DataFrame(columns=["Firma Adı", "Evrak Tipi", "Banka", "Tutar", "Vade", "Açıklama"])

df = get_clean_data()
bugun = datetime.now().date()

# --- ORTAK SIDEBAR ---
with st.sidebar:
    st.write(f"Hoş geldin: **{st.session_state.giris_turu}**")
    if st.button("🔴 Oturumu Kapat", use_container_width=True):
        st.session_state.giris_turu = None
        st.rerun()
    st.divider()

# --- PATRON PANELİ ---
if st.session_state.giris_turu == "PATRON":
    st.title("👑 Yönetim Paneli")
    
    if not df.empty:
        # 🚨 ALERT SİSTEMİ
        yaklasanlar = df[(df['Vade_Hesap'] >= bugun) & (df['Vade_Hesap'] <= bugun + timedelta(days=7))].copy()
        for _, row in yaklasanlar.iterrows():
            kalan = (row['Vade_Hesap'] - bugun).days
            tr_tarih = row['Vade_Hesap'].strftime('%d.%m.%Y')
            if kalan <= 3:
                st.error(f"🚨 **KRİTİK:** {row['Firma Adı']} | Vade: {tr_tarih} | {row['Tutar']:,.2f} TL")
            else:
                st.warning(f"⚠️ **Yaklaşan:** {row['Firma Adı']} | {kalan} gün kaldı ({tr_tarih})")

        # FİLTRE VE ANALİZ
        firmalar = ["TÜMÜ"] + sorted(df['Firma Adı'].dropna().unique().tolist())
        secili = st.sidebar.selectbox("🎯 Cari Seç", firmalar)
        
        f_df = df if secili == "TÜMÜ" else df[df['Firma Adı'] == secili]
        aktif_df = f_df[f_df['Vade_Hesap'] >= bugun].copy()

        if not aktif_df.empty:
            # Metrikler
            c1, c2, c3 = st.columns(3)
            total_borc = aktif_df['Tutar'].sum()
            c1.metric("Toplam Yük", f"{total_borc:,.2f} TL")
            c2.metric("Evrak Sayısı", len(aktif_df))
            
            # 📊 GRAFİK (Görsellik Geri Geldi)
            st.divider()
            fig = px.area(aktif_df.sort_values('Vade_Hesap'), x='Vade_Hesap', y='Tutar', 
                          title="Ödeme Projeksiyonu", markers=True)
            st.plotly_chart(fig, use_container_width=True)

            # 📋 TABLO (HATA VEREN KISIM DÜZELTİLDİ)
            # Önce sıralıyoruz, sonra sadece istediğimiz sütunları gösteriyoruz
            aktif_df['Vade_TR'] = pd.to_datetime(aktif_df['Vade_Hesap']).dt.strftime('%d.%m.%Y')
            display_df = aktif_df.sort_values('Vade_Hesap')[["Firma Adı", "Evrak Tipi", "Banka", "Tutar", "Vade_TR", "Açıklama"]]
            display_df.columns = ["Firma Adı", "Evrak Tipi", "Banka", "Tutar", "Vade", "Açıklama"]
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("Gelecek vadeli kayıt bulunamadı.")

# --- MUHASEBE PANELİ ---
elif st.session_state.giris_turu == "MUHASEBE":
    st.title("📝 Veri Girişi")
    
    mevcut_firmalar = sorted(df['Firma Adı'].dropna().unique().tolist()) if not df.empty else []
    
    with st.form("kayit_formu", clear_on_submit=True):
        f_liste = st.selectbox("Eski Firmalar", [""] + mevcut_firmalar)
        f_yeni = st.text_input("Yeni Firma (Listede yoksa yazın)")
        final_f = f_yeni.upper().strip() if f_yeni else f_liste
        
        c1, c2 = st.columns(2)
        b_adi = c1.text_input("Banka").upper()
        e_tipi = c1.selectbox("Evrak Tipi", ["Çek", "Senet", "Fatura", "Kart"])
        tutar = c2.number_input("Tutar", min_value=0.0)
        vade = c2.date_input("Vade Tarihi")
        not_ = st.text_input("Not")
        
        if st.form_submit_button("Kaydet"):
            if final_f and tutar > 0:
                # SADECE 6 SÜTUN (A-F) OLACAK ŞEKİLDE KAYDET
                new_row = pd.DataFrame([[final_f, e_tipi, b_adi, tutar, vade.isoformat(), not_]], 
                                       columns=["Firma Adı", "Evrak Tipi", "Banka", "Tutar", "Vade", "Açıklama"])
                updated = pd.concat([df[["Firma Adı", "Evrak Tipi", "Banka", "Tutar", "Vade", "Açıklama"]], new_row], ignore_index=True)
                conn.update(spreadsheet=edit_url, data=updated)
                st.success("Kayıt Başarılı!")
                st.rerun()
