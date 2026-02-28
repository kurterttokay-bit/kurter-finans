import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Sayfa Ayarları
st.set_page_config(page_title="Yapdoksan Finans Pro", layout="wide")

# --- GOOGLE SHEETS BAĞLANTISI ---
edit_url = "https://docs.google.com/spreadsheets/d/1gow0J5IA0GaB-BjViSKGbIxoZije0klFGgvDWYHdcNA/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- GÜVENLİK ---
if 'giris_turu' not in st.session_state:
    st.session_state.giris_turu = None

if st.session_state.giris_turu is None:
    st.title("🔒 Yapdoksan Finans Giriş")
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
    # Sütunları kontrol et, yoksa oluştur (Geriye dönük uyumluluk için)
    beklenen_sutunlar = ['Firma_Adi', 'Evrak_Tipi', 'Banka', 'Tutar', 'Vade', 'Aciklama']
    for col in beklenen_sutunlar:
        if col not in df.columns:
            df[col] = ""
except:
    df = pd.DataFrame(columns=['Firma_Adi', 'Evrak_Tipi', 'Banka', 'Tutar', 'Vade', 'Aciklama'])

# --- MUHASEBE PANELİ ---
if st.session_state.giris_turu == "MUHASEBE":
    st.title("📝 Cari & Evrak Veri Girişi")
    
    with st.form("yeni_kayit_formu"):
        col1, col2 = st.columns(2)
        with col1:
            firma = st.text_input("Firma Adı (Cari)").upper()
            evrak = st.selectbox("Evrak Tipi", ["Çek", "Senet", "Diğer"])
            banka = st.text_input("Banka Adı")
        with col2:
            tutar = st.number_input("Meblağ (TL)", min_value=0.0, step=1000.0)
            vade = st.date_input("Vade Tarihi")
            aciklama = st.text_input("Not/Açıklama")
            
        submit = st.form_submit_button("Sisteme İşle")
        
        if submit:
            new_row = pd.DataFrame([{
                "Firma_Adi": firma,
                "Evrak_Tipi": evrak,
                "Banka": banka,
                "Tutar": tutar,
                "Vade": str(vade),
                "Aciklama": aciklama
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(spreadsheet=edit_url, data=updated_df)
            st.success(f"{firma} carisine evrak işlendi!")
            st.cache_data.clear()
            st.rerun()

    # Kayıtları Listeleme
    if not df.empty:
        with st.expander("Son Kayıtları İncele / Sil"):
            st.dataframe(df.tail(10)) # Son 10 kaydı göster
            sil_idx = st.number_input("Silinecek Satır No", min_value=0, max_value=len(df)-1, step=1)
            if st.button("Seçili Kaydı Sil"):
                df = df.drop(sil_idx)
                conn.update(spreadsheet=edit_url, data=df)
                st.rerun()

# --- PATRON PANELİ ---
elif st.session_state.giris_turu == "PATRON":
    st.title("📈 Cari Bazlı Analiz & Vade Takvimi")
    
    if not df.empty:
        df['Vade'] = pd.to_datetime(df['Vade'])
        bugun = pd.to_datetime(datetime.now().date())
        
        # Filtreleme Seçenekleri
        st.sidebar.header("Filtreler")
        secili_firma = st.sidebar.selectbox("Cari Seçin", ["TÜMÜ"] + sorted(df['Firma_Adi'].unique().tolist()))
        
        # Veriyi Filtrele
        if secili_firma != "TÜMÜ":
            f_df = df[df['Firma_Adi'] == secili_firma].copy()
        else:
            f_df = df.copy()
            
        aktif_df = f_df[f_df['Vade'] >= bugun].copy()
        
        if not aktif_df.empty:
            # --- HESAPLAMALAR ---
            toplam_yuk = aktif_df['Tutar'].sum()
            aktif_df['Gun'] = (aktif_df['Vade'] - bugun).dt.days
            # Ağırlıklı Ortalama Vade Formülü: Sum(Tutar * Gün) / Sum(Tutar)
            ort_gun = (aktif_df['Tutar'] * aktif_df['Gun']).sum() / toplam_yuk
            ort_vade_tarihi = bugun + pd.to_timedelta(round(ort_gun), unit='D')
            
            # --- METRİKLER ---
            m1, m2, m3 = st.columns(3)
            m1.metric(f"{secili_firma} Toplam", f"{toplam_yuk:,.2f} TL")
            m2.metric("Ort. Vade (Gün)", f"{round(ort_gun)} Gün")
            m3.metric("Ort. Vade Tarihi", ort_vade_tarihi.strftime('%d.%m.%Y'))
            
            # --- GRAFİKLER ---
            st.subheader("Vade Dağılımı")
            chart_data = aktif_df.groupby('Vade')['Tutar'].sum()
            st.bar_chart(chart_data)
            
            # --- DETAYLI TABLO ---
            st.subheader("Evrak Detayları")
            st.table(aktif_df[['Firma_Adi', 'Banka', 'Evrak_Tipi', 'Tutar', 'Vade', 'Aciklama']].sort_values('Vade'))
            
        else:
            st.info("Bu kriterlere uygun gelecek ödemesi bulunamadı.")
    else:
        st.warning("Veritabanı boş.")

if st.button("Çıkış Yap"):
    st.session_state.giris_turu = None
    st.rerun()
