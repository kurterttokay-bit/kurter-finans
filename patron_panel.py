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

# --- VERİ ÇEKME (Sütun Korumalı) ---
@st.cache_data(ttl=0)
def get_clean_data():
    try:
        # Sadece A-F sütunlarını oku, Sheets'i kirletme
        data = conn.read(spreadsheet=edit_url, ttl=0, usecols=[0,1,2,3,4,5])
        data.columns = ["Firma Adı", "Evrak Tipi", "Banka", "Tutar", "Vade", "Açıklama"]
        
        if not data.empty:
            data['Vade_Hesap'] = pd.to_datetime(data['Vade'], errors='coerce').dt.date
            data['Tutar'] = pd.to_numeric(data['Tutar'], errors='coerce').fillna(0)
            data['Firma Adı'] = data['Firma Adı'].str.strip().str.upper()
        return data
    except:
        return pd.DataFrame(columns=["Firma Adı", "Evrak Tipi", "Banka", "Tutar", "Vade", "Açıklama"])

df = get_clean_data()
bugun = datetime.now().date()

# --- ORTAK SIDEBAR (ÇIKIŞ BUTONU) ---
with st.sidebar:
    st.write(f"Hoş geldin, **{st.session_state.giris_turu}**")
    if st.button("🔴 Oturumu Kapat", use_container_width=True):
        st.session_state.giris_turu = None
        st.rerun()
    st.divider()

# --- PATRON PANELİ ---
if st.session_state.giris_turu == "PATRON":
    st.title("👑 Yönetim Paneli")
    
    # ALERT SİSTEMİ
    if not df.empty:
        yaklasanlar = df[(df['Vade_Hesap'] >= bugun) & (df['Vade_Hesap'] <= bugun + timedelta(days=7))].copy()
        for _, row in yaklasanlar.iterrows():
            kalan = (row['Vade_Hesap'] - bugun).days
            tr_vade = row['Vade_Hesap'].strftime('%d.%m.%Y')
            if kalan <= 3:
                st.error(f"🚨 **KRİTİK:** {row['Firma Adı']} | Vade: {tr_vade} | {row['Tutar']:,.2f} TL")
            else:
                st.warning(f"⚠️ **Yaklaşan:** {row['Firma Adı']} | {kalan} gün kaldı ({tr_vade})")

    # CARİ FİLTRE (Sidebar'da Cari Seç'in altına çıkış butonunu zaten yukarıda koyduk)
    firmalar = ["TÜMÜ"] + sorted(df['Firma Adı'].dropna().unique().tolist())
    secili = st.sidebar.selectbox("🎯 Cari Seç", firmalar)
    
    # Veri Analizi
    f_df = df if secili == "TÜMÜ" else df[df['Firma Adı'] == secili]
    aktif_df = f_df[f_df['Vade_Hesap'] >= bugun].copy()

    if not aktif_df.empty:
        # Metrikler
        m1, m2, m3 = st.columns(3)
        total = aktif_df['Tutar'].sum()
        m1.metric("Toplam Borç", f"{total:,.2f} TL")
        m2.metric("Evrak Sayısı", len(aktif_df))
        
        # Grafik (Geri Geldi!)
        st.divider()
        st.subheader("📊 Ödeme Takvimi")
        fig = px.area(aktif_df.sort_values('Vade_Hesap'), x='Vade_Hesap', y='Tutar', 
                      markers=True, title=f"{secili} Nakit Akışı")
        st.plotly_chart(fig, use_container_width=True)
        
        # Tablo (Türkiye Formatlı)
        aktif_df['Vade'] = pd.to_datetime(aktif_df['Vade_Hesap']).dt.strftime('%d.%m.%Y')
        st.dataframe(aktif_df[["Firma Adı", "Evrak Tipi", "Banka", "Tutar", "Vade", "Açıklama"]].sort_values('Vade_Hesap'), use_container_width=True)
    else:
        st.info("Gelecek vadeli ödeme bulunamadı.")

# --- MUHASEBE PANELİ ---
elif st.session_state.giris_turu == "MUHASEBE":
    st.title("📝 Veri Girişi")
    
    # Öneri Listesi
    mevcut_firmalar = sorted(df['Firma Adı'].dropna().unique().tolist()) if not df.empty else []
    
    with st.form("yeni_kayit", clear_on_submit=True):
        st.subheader("Evrak Detayları")
        
        # Akıllı Firma Girişi
        f_adi = st.selectbox("Eski Firmalardan Seç (Veya aşağıya yeni yazın)", [""] + mevcut_firmalar)
        f_yeni = st.text_input("Yeni Firma Adı (Listede yoksa doldurun)")
        final_f = f_yeni.upper().strip() if f_yeni else f_adi
        
        c1, c2 = st.columns(2)
        b_adi = c1.text_input("Banka").upper()
        e_tipi = c1.selectbox("Evrak Tipi", ["Çek", "Senet", "Fatura", "Kart"])
        tutar = c2.number_input("Tutar (TL)", min_value=0.0)
        vade = c2.date_input("Vade Tarihi")
        not_ = st.text_input("Not / Açıklama")
        
        if st.form_submit_button("Sisteme İşle"):
            if not final_f or tutar <= 0:
                st.error("Firma ve Tutar boş geçilemez!")
            else:
                new_data = pd.DataFrame([[final_f, e_tipi, b_adi, tutar, vade.isoformat(), not_]], 
                                       columns=["Firma Adı", "Evrak Tipi", "Banka", "Tutar", "Vade", "Açıklama"])
                updated = pd.concat([df[["Firma Adı", "Evrak Tipi", "Banka", "Tutar", "Vade", "Açıklama"]], new_data], ignore_index=True)
                conn.update(spreadsheet=edit_url, data=updated)
                st.success(f"{final_f} için kayıt eklendi!")
                st.rerun()
