import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go # Daha şık grafikler için
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Sayfa Ayarları - Geniş ve Premium Görünüm
st.set_page_config(page_title="Yapdoksan Finans | Executive Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- GOOGLE SHEETS BAĞLANTISI ---
edit_url = "https://docs.google.com/spreadsheets/d/1gow0J5IA0GaB-BjViSKGbIxoZije0klFGgvDWYHdcNA/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CUSTOM CSS (Patron Güzellemesi) ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    div[data-testid="stExpander"] { background-color: white; border-radius: 10px; }
    </style>
    """, unsafe_allow_name_with_html=True)

# --- GÜVENLİK (Aynı Mantık) ---
if 'giris_turu' not in st.session_state:
    st.session_state.giris_turu = None

if st.session_state.giris_turu is None:
    st.title("🏛️ Yapdoksan Finans Yönetim Merkezi")
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
    df['Tutar'] = pd.to_numeric(df['Tutar'], errors='coerce').fillna(0)
    df['Vade'] = pd.to_datetime(df['Vade'], errors='coerce')
except:
    st.error("Veri bağlantısı kurulamadı!")
    st.stop()

# --- MUHASEBE PANELİ (Hızlı Giriş Odaklı) ---
if st.session_state.giris_turu == "MUHASEBE":
    st.title("📥 Veri İşleme Merkezi")
    # ... (Buradaki kod öncekiyle aynı, sadece muhasebeci işini yapsın) ...

# --- PATRON PANELİ (Görsel Şölen) ---
elif st.session_state.giris_turu == "PATRON":
    st.markdown(f"# 👑 Finansal Strateji Paneli")
    st.write(f"Hoş geldin Patron. Bugünün özeti ve gelecek risk projeksiyonu aşağıdadır.")

    if not df.empty:
        bugun = pd.to_datetime(datetime.now().date())
        aktif_df = df[df['Vade'] >= bugun].copy()
        aktif_df['Gun'] = (aktif_df['Vade'] - bugun).dt.days

        # Kenar Çubuğu Filtreleri
        st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
        st.sidebar.title("Kontrol Kulesi")
        secili_firma = st.sidebar.selectbox("🎯 Odaklanılacak Cari", ["TÜM PORTFÖY"] + sorted(df['Firma_Adi'].unique().tolist()))
        
        if secili_firma != "TÜM PORTFÖY":
            aktif_df = aktif_df[aktif_df['Firma_Adi'] == secili_firma]

        # --- 1. ÜST METRİKLER (KPI) ---
        toplam_yuk = aktif_df['Tutar'].sum()
        ort_gun = (aktif_df['Tutar'] * aktif_df['Gun']).sum() / toplam_yuk if toplam_yuk > 0 else 0
        en_yakin_odeme = aktif_df['Vade'].min()

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Toplam Borç Yükü", f"{toplam_yuk:,.0f} TL", delta_color="inverse")
        kpi2.metric("Ağırlıklı Vade", f"{int(ort_gun)} Gün")
        kpi3.metric("En Yakın Ödeme", en_yakin_odeme.strftime('%d.%m.%Y') if not aktif_df.empty else "-")
        kpi4.metric("Aktif Evrak", f"{len(aktif_df)} Adet")

        st.markdown("---")

        # --- 2. GÖRSEL ANALİZLER ---
        col_main, col_side = st.columns([2, 1])

        with col_main:
            st.subheader("🚀 Nakit Akış Projeksiyonu (Kümülatif)")
            # Tarihe göre sıralayıp kümülatif toplam alıyoruz
            cum_df = aktif_df.sort_values('Vade').copy()
            cum_df['Kumulatif_Tutar'] = cum_df['Tutar'].cumsum()
            
            fig_area = px.area(cum_df, x='Vade', y='Kumulatif_Tutar', 
                               title="Zaman İçinde Biriken Ödeme Yükü",
                               labels={'Kumulatif_Tutar': 'Toplam Çıkış (TL)'},
                               color_discrete_sequence=['#1f77b4'])
            fig_area.update_layout(hovermode="x unified")
            st.plotly_chart(fig_area, use_container_width=True)

        with col_side:
            st.subheader("🏢 Cari Dağılımı")
            fig_donut = px.pie(aktif_df, values='Tutar', names='Firma_Adi', hole=.5,
                               color_discrete_sequence=px.colors.qualitative.T10)
            fig_donut.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_donut, use_container_width=True)

        # --- 3. BANKA VE VADE ANALİZİ ---
        st.markdown("---")
        c1, c2 = st.columns(2)

        with c1:
            st.subheader("🏦 Banka Pozisyonları")
            banka_data = aktif_df.groupby('Banka')['Tutar'].sum().sort_values(ascending=True)
            fig_banka = px.bar(banka_data, orientation='h', text_auto='.2s',
                               color_discrete_sequence=['#2ecc71'])
            st.plotly_chart(fig_banka, use_container_width=True)

        with c2:
            st.subheader("🗓️ Aylık Ödeme Takvimi")
            aktif_df['Ay'] = aktif_df['Vade'].dt.strftime('%Y-%m')
            aylik_data = aktif_df.groupby('Ay')['Tutar'].sum().reset_index()
            fig_ay = px.bar(aylik_data, x='Ay', y='Tutar', text_auto='.2s',
                            color_discrete_sequence=['#e74c3c'])
            st.plotly_chart(fig_ay, use_container_width=True)

        # --- 4. AKILLI TABLO ---
        with st.expander("🔍 Tüm Evrak Detaylarını İncele"):
            st.dataframe(aktif_df[['Firma_Adi', 'Banka', 'Evrak_Tipi', 'Tutar', 'Vade', 'Aciklama']].sort_values('Vade'), 
                         use_container_width=True)

    else:
        st.balloons()
        st.success("Tebrikler Patron! Gelecek ödemen bulunmuyor. Kasa güvende.")

if st.sidebar.button("🔴 Oturumu Kapat"):
    st.session_state.giris_turu = None
    st.rerun()
