import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Görsellik kütüphanesini kontrol et (Patlamayı önler)
try:
    import plotly.express as px
    import plotly.graph_objects as go
    has_plotly = True
except ImportError:
    has_plotly = False

# Sayfa Ayarları
st.set_page_config(page_title="Yapdoksan Finans | Yönetim", layout="wide")

# --- BAĞLANTI ---
edit_url = "https://docs.google.com/spreadsheets/d/1gow0J5IA0GaB-BjViSKGbIxoZije0klFGgvDWYHdcNA/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- GÜVENLİK ---
if 'giris_turu' not in st.session_state:
    st.session_state.giris_turu = None

if st.session_state.giris_turu is None:
    st.title("🏛️ Yapdoksan Finans Yönetimi")
    sifre = st.text_input("Giriş Anahtarı", type="password")
    if st.button("Sistemi Aç"):
        if sifre == "patron125": st.session_state.giris_turu = "PATRON"
        elif sifre == "muhasebe007": st.session_state.giris_turu = "MUHASEBE"
        else: st.error("Erişim Reddedildi!")
        st.rerun()
    st.stop()

# --- VERİ ÇEKME ---
try:
    df = conn.read(spreadsheet=edit_url, ttl=0)
    # Sütunları sayısal ve tarihsel formata zorla
    df['Tutar'] = pd.to_numeric(df['Tutar'], errors='coerce').fillna(0)
    df['Vade'] = pd.to_datetime(df['Vade'], errors='coerce')
except:
    df = pd.DataFrame(columns=['Firma_Adi', 'Evrak_Tipi', 'Banka', 'Tutar', 'Vade', 'Aciklama'])

# --- MUHASEBE PANELİ ---
if st.session_state.giris_turu == "MUHASEBE":
    st.title("📥 Muhasebe Veri Girişi")
    with st.form("kayit"):
        c1, c2 = st.columns(2)
        firma = c1.text_input("Firma/Cari Adı").upper()
        banka = c1.text_input("Banka")
        tutar = c2.number_input("Tutar (TL)", min_value=0.0)
        vade = c2.date_input("Vade")
        evrak = st.selectbox("Evrak Tipi", ["Çek", "Senet", "Fatura"])
        not_ = st.text_input("Açıklama")
        if st.form_submit_button("Sisteme İşle"):
            new_row = pd.DataFrame([{"Firma_Adi": firma, "Evrak_Tipi": evrak, "Banka": banka, "Tutar": tutar, "Vade": str(vade), "Aciklama": not_}])
            df = pd.concat([df, new_row], ignore_index=True)
            conn.update(spreadsheet=edit_url, data=df)
            st.success("Kayıt Alındı.")
            st.cache_data.clear()
            st.rerun()

# --- PATRON PANELİ (GÜZELLEŞTİRİLMİŞ) ---
elif st.session_state.giris_turu == "PATRON":
    st.title("👑 Yönetim Paneli")
    
    if not df.empty and 'Vade' in df.columns:
        bugun = pd.to_datetime(datetime.now().date())
        aktif_df = df[df['Vade'] >= bugun].copy()
        
        # Filtreleme
        secili_firma = st.sidebar.selectbox("🎯 Odaklan", ["TÜMÜ"] + sorted(df['Firma_Adi'].unique().tolist()))
        if secili_firma != "TÜMÜ":
            aktif_df = aktif_df[aktif_df['Firma_Adi'] == secili_firma]

        if not aktif_df.empty:
            # Üst Metrikler
            total = aktif_df['Tutar'].sum()
            aktif_df['Gun'] = (aktif_df['Vade'] - bugun).dt.days
            ort_vade = (aktif_df['Tutar'] * aktif_df['Gun']).sum() / total if total > 0 else 0
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Toplam Yük", f"{total:,.0f} TL")
            k2.metric("Ağırlıklı Vade", f"{int(ort_vade)} Gün")
            k3.metric("Kayıt Sayısı", len(aktif_df))

            st.divider()

            if has_plotly:
                c_left, c_right = st.columns(2)
                # Kümülatif Nakit Akışı (Patronun en sevdiği)
                cum_df = aktif_df.sort_values('Vade').copy()
                cum_df['Kumulatif'] = cum_df['Tutar'].cumsum()
                fig_area = px.area(cum_df, x='Vade', y='Kumulatif', title="Gelecek Nakit Çıkış Grafiği")
                c_left.plotly_chart(fig_area, use_container_width=True)
                
                # Banka Dağılımı
                fig_pie = px.pie(aktif_df, values='Tutar', names='Banka', hole=.4, title="Banka Risk Dağılımı")
                c_right.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.warning("Görsel grafikler için lütfen requirements.txt dosyasına 'plotly' ekleyin.")
                st.bar_chart(aktif_df.set_index('Vade')['Tutar'])
            
            st.subheader("📋 Ödeme Listesi")
            st.dataframe(aktif_df[['Firma_Adi', 'Banka', 'Tutar', 'Vade', 'Aciklama']].sort_values('Vade'), use_container_width=True)
        else:
            st.info("Gelecek ödemeniz bulunmuyor.")

if st.sidebar.button("Güvenli Çıkış"):
    st.session_state.giris_turu = None
    st.rerun()
