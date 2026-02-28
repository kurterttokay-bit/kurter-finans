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

# --- GÜVENLİK VE OTURUM ---
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
    # Sayısal ve tarihsel dönüşümler
    if not df.empty:
        df['Tutar'] = pd.to_numeric(df['Tutar'], errors='coerce').fillna(0)
        df['Vade'] = pd.to_datetime(df['Vade'], errors='coerce')
    bugun = pd.to_datetime(datetime.now().date())
except:
    df = pd.DataFrame(columns=['Firma Adı', 'Evrak Tipi', 'Banka', 'Tutar', 'Vade', 'Açıklama'])
    bugun = pd.to_datetime(datetime.now().date())

# --- ORTAK SIDEBAR (ÇIKIŞ BUTONU) ---
with st.sidebar:
    st.write(f"Yetki: **{st.session_state.giris_turu}**")
    if st.button("🔴 Oturumu Kapat", use_container_width=True):
        st.session_state.giris_turu = None
        st.rerun()
    st.divider()

# --- PATRON PANELİ ---
if st.session_state.giris_turu == "PATRON":
    st.title("👑 Yönetim Paneli")
    
    # ALERT SİSTEMİ
    if not df.empty:
        yaklasanlar = df[(df['Vade'] >= bugun) & (df['Vade'] <= bugun + timedelta(days=7))].copy()
        if not yaklasanlar.empty:
            for _, row in yaklasanlar.iterrows():
                kalan_gun = (row['Vade'] - bugun).days
                if kalan_gun == 3:
                    st.error(f"🚨 **KRİTİK UYARI:** {row['Firma Adı']} ödemesine son **3 GÜN**! | Tutar: {row['Tutar']:,.2f} TL")
                elif kalan_gun <= 7:
                    st.warning(f"⚠️ **Yaklaşan:** {row['Firma Adı']} - **{kalan_gun} gün** kaldı.")

    # Filtre ve Analiz
    col_name = "Firma Adı"
    if col_name in df.columns:
        firmalar = ["TÜMÜ"] + sorted(df[col_name].unique().tolist())
        secili_firma = st.sidebar.selectbox("🎯 Cari Seç", firmalar)
        
        f_df = df if secili_firma == "TÜMÜ" else df[df[col_name] == secili_firma]
        aktif_df = f_df[f_df['Vade'] >= bugun].copy()

        if not aktif_df.empty:
            t_borc = aktif_df['Tutar'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Toplam Yük", f"{t_borc:,.2f} TL")
            c2.metric("Evrak", len(aktif_df))
            st.divider()
            st.plotly_chart(px.area(aktif_df.sort_values('Vade'), x='Vade', y='Tutar'), use_container_width=True)
            st.dataframe(aktif_df.sort_values('Vade'), use_container_width=True)
    else:
        st.warning("Veritabanı başlıklarını kontrol edin.")

# --- MUHASEBE PANELİ (TAMİR EDİLEN KISIM) ---
elif st.session_state.giris_turu == "MUHASEBE":
    st.title("📝 Veri Giriş Ekranı")
    
    # Mevcut Verileri Görme (Muhasebeci ne girdiğini bilsin)
    with st.expander("Kayıtlı Verileri Görüntüle"):
        st.dataframe(df.sort_values('Vade', ascending=False) if not df.empty else df)

    st.subheader("Yeni Evrak Ekle")
    with st.form("yeni_evrak_formu", clear_on_submit=True):
        c1, c2 = st.columns(2)
        f_adi = c1.text_input("Firma Adı").upper()
        b_adi = c1.text_input("Banka").upper()
        e_tipi = c2.selectbox("Evrak Tipi", ["Çek", "Senet", "Fatura", "Diğer"])
        tutar = c2.number_input("Tutar (TL)", min_value=0.0, step=100.0)
        vade = st.date_input("Vade Tarihi")
        not_ = st.text_area("Açıklama / Not")
        
        gonder = st.form_submit_button("Sisteme İşle")
        
        if gonder:
            if f_adi and tutar > 0:
                yeni_veri = pd.DataFrame([{
                    "Firma Adı": f_adi,
                    "Evrak Tipi": e_tipi,
                    "Banka": b_adi,
                    "Tutar": tutar,
                    "Vade": str(vade),
                    "Açıklama": not_
                }])
                
                # Mevcut veriye ekle ve güncelle
                updated_df = pd.concat([df, yeni_veri], ignore_index=True)
                conn.update(spreadsheet=edit_url, data=updated_df)
                st.success(f"{f_adi} için {tutar} TL tutarlı kayıt başarıyla eklendi!")
                st.rerun()
            else:
                st.warning("Lütfen en azından Firma Adı ve Tutar giriniz.")
