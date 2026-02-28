import streamlit as st
import pandas as pd
import plotly.express as px # Grafik için ekledik
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Sayfa Ayarları
st.set_page_config(page_title="Yapdoksan Finans & Cari Analiz", layout="wide")

# --- GOOGLE SHEETS BAĞLANTISI ---
edit_url = "https://docs.google.com/spreadsheets/d/1gow0J5IA0GaB-BjViSKGbIxoZije0klFGgvDWYHdcNA/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- GÜVENLİK ---
if 'giris_turu' not in st.session_state:
    st.session_state.giris_turu = None

if st.session_state.giris_turu is None:
    st.title("🔒 Yapdoksan Finans Yönetimi")
    sifre = st.text_input("Şifre", type="password")
    if st.button("Giriş"):
        if sifre == "patron125": st.session_state.giris_turu = "PATRON"
        elif sifre == "muhasebe007": st.session_state.giris_turu = "MUHASEBE"
        else: st.error("Hatalı Şifre!")
        st.rerun()
    st.stop()

# --- VERİ ÇEKME ---
try:
    df = conn.read(spreadsheet=edit_url, ttl=0)
    # Eksik sütunları otomatik tamamla
    cols = ['Firma_Adi', 'Evrak_Tipi', 'Banka', 'Tutar', 'Vade', 'Aciklama']
    for c in cols:
        if c not in df.columns: df[c] = ""
except:
    df = pd.DataFrame(columns=['Firma_Adi', 'Evrak_Tipi', 'Banka', 'Tutar', 'Vade', 'Aciklama'])

# --- MUHASEBE PANELİ ---
if st.session_state.giris_turu == "MUHASEBE":
    st.title("📝 Veri Giriş Ekranı")
    with st.form("kayit_formu"):
        c1, c2, c3 = st.columns(3)
        firma = c1.text_input("Firma Adı").upper()
        evrak = c1.selectbox("Tip", ["Çek", "Senet", "Fatura"])
        tutar = c2.number_input("Tutar (TL)", step=5000.0)
        vade = c2.date_input("Vade")
        banka = c3.text_input("Banka")
        not_ = c3.text_input("Açıklama")
        
        if st.form_submit_button("Kaydet"):
            new_row = pd.DataFrame([{"Firma_Adi": firma, "Evrak_Tipi": evrak, "Banka": banka.upper(), "Tutar": tutar, "Vade": str(vade), "Aciklama": not_}])
            df = pd.concat([df, new_row], ignore_index=True)
            conn.update(spreadsheet=edit_url, data=df)
            st.success("Kayıt Başarılı!")
            st.rerun()

# --- PATRON PANELİ ---
elif st.session_state.giris_turu == "PATRON":
    st.title("📊 Finansal Durum & Banka Analizi")
    
    if not df.empty:
        df['Vade'] = pd.to_datetime(df['Vade'])
        df['Tutar'] = pd.to_numeric(df['Tutar'])
        bugun = pd.to_datetime(datetime.now().date())
        aktif_df = df[df['Vade'] >= bugun].copy()
        
        # Filtre Paneli
        secili_firma = st.sidebar.selectbox("Cari Filtresi", ["TÜMÜ"] + sorted(df['Firma_Adi'].unique().tolist()))
        if secili_firma != "TÜMÜ":
            aktif_df = aktif_df[aktif_df['Firma_Adi'] == secili_firma]

        if not aktif_df.empty:
            # --- 1. METRİKLER ---
            toplam_tutar = aktif_df['Tutar'].sum()
            aktif_df['Gun'] = (aktif_df['Vade'] - bugun).dt.days
            ort_gun = (aktif_df['Tutar'] * aktif_df['Gun']).sum() / toplam_tutar
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Toplam Yük", f"{toplam_tutar:,.2f} TL")
            m2.metric("Ağ. Ortalama Vade", f"{int(ort_gun)} Gün")
            m3.metric("Evrak Sayısı", len(aktif_df))

            st.divider()

            # --- 2. BANKA DAĞILIMI (PASTA GRAFİK) ---
            col_left, col_right = st.columns(2)
            
            with col_left:
                st.subheader("🏦 Banka Bazlı Dağılım")
                banka_df = aktif_df.groupby('Banka')['Tutar'].sum().reset_index()
                fig_banka = px.pie(banka_df, values='Tutar', names='Banka', hole=0.4, 
                                   color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_banka, use_container_width=True)

            with col_right:
                st.subheader("📅 Vade Dilimleri (Risk Analizi)")
                # Vade gruplama
                bins = [0, 30, 60, 90, 180, 360, 1000]
                labels = ['0-30 Gün', '31-60 Gün', '61-90 Gün', '91-180 Gün', '181-360 Gün', '360+ Gün']
                aktif_df['Vade_Grubu'] = pd.cut(aktif_df['Gun'], bins=bins, labels=labels)
                vade_grafik = aktif_df.groupby('Vade_Grubu', observed=True)['Tutar'].sum().reset_index()
                fig_vade = px.bar(vade_grafik, x='Vade_Grubu', y='Tutar', color='Vade_Grubu', text_auto='.2s')
                st.plotly_chart(fig_vade, use_container_width=True)

            st.divider()
            
            # --- 3. DETAYLI LİSTE ---
            st.subheader("📑 Aktif Evrak Listesi")
            st.dataframe(aktif_df[['Firma_Adi', 'Banka', 'Evrak_Tipi', 'Tutar', 'Vade', 'Aciklama']].sort_values('Vade'), use_container_width=True)

    else:
        st.info("Henüz veri girilmemiş.")

if st.sidebar.button("Güvenli Çıkış"):
    st.session_state.giris_turu = None
    st.rerun()
