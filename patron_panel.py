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
    df['Tutar'] = pd.to_numeric(df['Tutar'], errors='coerce').fillna(0)
    df['Vade'] = pd.to_datetime(df['Vade'], errors='coerce')
    bugun = pd.to_datetime(datetime.now().date())
except:
    df = pd.DataFrame(columns=['Firma Adı', 'Evrak Tipi', 'Banka', 'Tutar', 'Vade', 'Açıklama'])

# --- PATRON PANELİ ---
if st.session_state.giris_turu == "PATRON":
    st.title("👑 Yönetim Paneli")
    
    # --- ALERT SİSTEMİ (EN ÜSTTE) ---
    if not df.empty:
        # Vadesi yaklaşanları filtrele (Bugünden itibaren 7 gün içi)
        yaklasanlar = df[(df['Vade'] >= bugun) & (df['Vade'] <= bugun + timedelta(days=7))].copy()
        
        if not yaklasanlar.empty:
            for _, row in yaklasanlar.iterrows():
                kalan_gun = (row['Vade'] - bugun).days
                
                if kalan_gun == 3:
                    st.error(f"🚨 **KRİTİK ÖDEME UYARISI:** {row['Firma Adı']} ödemesine son **3 GÜN**! | Tutar: {row['Tutar']:,.2f} TL")
                elif kalan_gun <= 7:
                    st.warning(f"⚠️ **Yaklaşan Ödeme:** {row['Firma Adı']} vadesine **{kalan_gun} gün** kaldı. | Tutar: {row['Tutar']:,.2f} TL")
    
    # --- SIDEBAR & FİLTRE ---
    with st.sidebar:
        st.header("⚙️ Kontrol Paneli")
        firmalar = ["TÜMÜ"] + sorted(df['Firma Adı'].unique().tolist()) if 'Firma Adı' in df.columns else ["TÜMÜ"]
        secili_firma = st.selectbox("🎯 Cari Seç", firmalar)
        st.divider()
        if st.button("🔴 Oturumu Kapat", use_container_width=True):
            st.session_state.giris_turu = None
            st.rerun()

    # --- ANALİZ VE GRAFİKLER ---
    if not df.empty and 'Firma Adı' in df.columns:
        f_df = df if secili_firma == "TÜMÜ" else df[df['Firma Adı'] == secili_firma]
        aktif_df = f_df[f_df['Vade'] >= bugun].copy()

        if not aktif_df.empty:
            t_borc = aktif_df['Tutar'].sum()
            m1, m2, m3 = st.columns(3)
            m1.metric("Toplam Yük", f"{t_borc:,.2f} TL")
            m2.metric("Evrak Sayısı", len(aktif_df))
            
            if t_borc > 0:
                aktif_df['Gun'] = (aktif_df['Vade'] - bugun).dt.days
                ort_v = (aktif_df['Tutar'] * aktif_df['Gun']).sum() / t_borc
                m3.metric("Ort. Vade", f"{int(ort_v)} Gün")

            st.divider()
            st.plotly_chart(px.area(aktif_df.sort_values('Vade'), x='Vade', y='Tutar', title="Nakit Akış Projeksiyonu"), use_container_width=True)
            st.dataframe(aktif_df.sort_values('Vade'), use_container_width=True)
        else:
            st.info("Gelecek vadesi olan kayıt bulunamadı.")
    else:
        st.warning("Henüz veri girilmemiş veya başlıklar hatalı.")

# --- MUHASEBE PANELİ (Öncekiyle aynı) ---
elif st.session_state.giris_turu == "MUHASEBE":
    st.title("📝 Veri Girişi")
    # ... (Muhasebe formu buraya gelecek)
