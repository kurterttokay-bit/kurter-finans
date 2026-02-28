import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
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

# --- VERİ ÇEKME VE TEMİZLEME ---
@st.cache_data(ttl=0)
def get_clean_data():
    try:
        # Sadece A'dan F'ye kadar olan ana sütunları oku (Diğer çöpleri görme!)
        data = conn.read(spreadsheet=edit_url, ttl=0, usecols=[0,1,2,3,4,5])
        # Başlıkları senin istediğin gibi "Firma Adı" formatına zorla
        data.columns = ["Firma Adı", "Evrak Tipi", "Banka", "Tutar", "Vade", "Açıklama"]
        
        if not data.empty:
            # Tarihi saatsiz temizle
            data['Vade_Hesap'] = pd.to_datetime(data['Vade'], errors='coerce').dt.date
            data['Tutar'] = pd.to_numeric(data['Tutar'], errors='coerce').fillna(0)
        return data
    except Exception as e:
        return pd.DataFrame(columns=["Firma Adı", "Evrak Tipi", "Banka", "Tutar", "Vade", "Açıklama"])

df = get_clean_data()
bugun = datetime.now().date()

# --- ORTAK SIDEBAR ---
with st.sidebar:
    if st.button("🔴 Oturumu Kapat", use_container_width=True):
        st.session_state.giris_turu = None
        st.rerun()
    st.divider()

# --- PATRON PANELİ ---
if st.session_state.giris_turu == "PATRON":
    st.title("👑 Yönetim Paneli")
    
    # ALERT (GG.AA.YYYY Formatında Görünüm)
    if not df.empty:
        yaklasanlar = df[(df['Vade_Hesap'] >= bugun) & (df['Vade_Hesap'] <= bugun + timedelta(days=7))].copy()
        for _, row in yaklasanlar.iterrows():
            kalan = (row['Vade_Hesap'] - bugun).days
            tr_tarih = row['Vade_Hesap'].strftime('%d.%m.%Y')
            if kalan == 3:
                st.error(f"🚨 **KRİTİK:** {row['Firma Adı']} | Vade: {tr_tarih} | Tutar: {row['Tutar']:,.2f} TL")
            else:
                st.warning(f"⚠️ **Yaklaşan:** {row['Firma Adı']} | {kalan} gün kaldı ({tr_tarih})")

    # CARİ FİLTRE VE TABLO
    firmalar = ["TÜMÜ"] + sorted(df['Firma Adı'].dropna().unique().tolist())
    secili = st.sidebar.selectbox("🎯 Cari Seç", firmalar)
    
    f_df = df if secili == "TÜMÜ" else df[df['Firma Adı'] == secili]
    # Sadece GG.AA.YYYY formatında tablo gösterimi
    f_df['Vade'] = pd.to_datetime(f_df['Vade_Hesap']).dt.strftime('%d.%m.%Y')
    st.dataframe(f_df[["Firma Adı", "Evrak Tipi", "Banka", "Tutar", "Vade", "Açıklama"]], use_container_width=True)

# --- MUHASEBE PANELİ ---
elif st.session_state.giris_turu == "MUHASEBE":
    st.title("📝 Veri Girişi")
    with st.form("yeni_kayit", clear_on_submit=True):
        c1, c2 = st.columns(2)
        f = c1.text_input("Firma Adı").upper()
        b = c1.text_input("Banka").upper()
        e = c2.selectbox("Evrak Tipi", ["Çek", "Senet", "Fatura"])
        t = c2.number_input("Tutar", min_value=0.0)
        v = st.date_input("Vade")
        
        if st.form_submit_button("Kaydet"):
            # SADECE İLK 6 SÜTUNA YAZ (Sheets'i kirletme!)
            new_row = pd.DataFrame([[f, e, b, t, v.isoformat(), ""]], 
                                   columns=["Firma Adı", "Evrak Tipi", "Banka", "Tutar", "Vade", "Açıklama"])
            updated = pd.concat([df[["Firma Adı", "Evrak Tipi", "Banka", "Tutar", "Vade", "Açıklama"]], new_row], ignore_index=True)
            conn.update(spreadsheet=edit_url, data=updated)
            st.success("Kaydedildi!")
            st.rerun()
