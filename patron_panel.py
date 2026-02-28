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
        # Sadece A-F arası 6 sütunu oku, Sheets'teki o sağa saçılan çöpleri görmezden gel
        data = conn.read(spreadsheet=edit_url, ttl=0, usecols=[0,1,2,3,4,5])
        data.columns = ["Firma Adı", "Evrak Tipi", "Banka", "Tutar", "Vade", "Açıklama"]
        
        if not data.empty:
            data['Vade_Hesap'] = pd.to_datetime(data['Vade'], errors='coerce').dt.date
            data['Tutar'] = pd.to_numeric(data['Tutar'], errors='coerce').fillna(0)
            data['Firma Adı'] = data['Firma Adı'].str.strip().str.upper() # Boşlukları temizle ve büyüt
        return data
    except:
        return pd.DataFrame(columns=["Firma Adı", "Evrak Tipi", "Banka", "Tutar", "Vade", "Açıklama"])

df = get_clean_data()
bugun = datetime.now().date()

# --- PATRON PANELİ ---
if st.session_state.giris_turu == "PATRON":
    st.title("👑 Yönetim Paneli")
    
    # ALERT (3 Gün Kırmızı, 7 Gün Sarı)
    if not df.empty:
        yaklasanlar = df[(df['Vade_Hesap'] >= bugun) & (df['Vade_Hesap'] <= bugun + timedelta(days=7))].copy()
        for _, row in yaklasanlar.iterrows():
            kalan = (row['Vade_Hesap'] - bugun).days
            tr_tarih = row['Vade_Hesap'].strftime('%d.%m.%Y')
            if kalan <= 3:
                st.error(f"🚨 **KRİTİK:** {row['Firma Adı']} | Vade: {tr_tarih} | Tutar: {row['Tutar']:,.2f} TL")
            else:
                st.warning(f"⚠️ **Yaklaşan:** {row['Firma Adı']} | {kalan} gün kaldı ({tr_tarih})")

    # CARİ FİLTRE
    firmalar = ["TÜMÜ"] + sorted(df['Firma Adı'].dropna().unique().tolist())
    secili = st.sidebar.selectbox("🎯 Cari Seç", firmalar)
    
    f_df = df if secili == "TÜMÜ" else df[df['Firma Adı'] == secili]
    f_df['Vade Gösterim'] = pd.to_datetime(f_df['Vade_Hesap']).dt.strftime('%d.%m.%Y')
    
    st.dataframe(f_df[["Firma Adı", "Evrak Tipi", "Banka", "Tutar", "Vade Gösterim", "Açıklama"]].sort_values('Firma Adı'), use_container_width=True)

# --- MUHASEBE PANELİ (OTOMATİK ÖNERİLİ) ---
elif st.session_state.giris_turu == "MUHASEBE":
    st.title("📝 Veri Girişi")
    
    # Mevcut firma listesini hazırla
    mevcut_firmalar = sorted(df['Firma Adı'].dropna().unique().tolist()) if not df.empty else []
    
    with st.form("yeni_kayit", clear_on_submit=True):
        st.subheader("Evrak Detayları")
        
        # OTOMATİK TAMAMLAMA ÖZELLİĞİ: 
        # Streamlit'te text_input yerine selectbox'ın 'editable' benzeri bir mantığını kullanıyoruz.
        # En pratik ve hatasız yol: listeye "YENİ FİRMA EKLE" seçeneği koymak veya datalist mantığı.
        # Senin için en temizi: Firma adını bir 'selectbox' içine alıp, en üste boşluk bırakmak.
        
        f_adi = st.selectbox("Firma Adı (Listeden seçin veya listede yoksa aşağıya yazın)", [""] + mevcut_firmalar)
        f_yeni = st.text_input("Yeni Firma (Eğer listede yoksa buraya yazın)")
        
        # Hangi ismi kullanacağımıza karar verelim
        final_firma = f_yeni.upper().strip() if f_yeni else f_adi
        
        c1, c2 = st.columns(2)
        b_adi = c1.text_input("Banka").upper()
        e_tipi = c1.selectbox("Evrak Tipi", ["Çek", "Senet", "Fatura"])
        tutar = c2.number_input("Tutar", min_value=0.0, step=100.0)
        vade = c2.date_input("Vade Tarihi")
        not_ = st.text_input("Açıklama")
        
        if st.form_submit_button("Sisteme Kaydet"):
            if not final_firma or tutar <= 0:
                st.error("Lütfen Firma Adı ve Tutar alanlarını doldurun!")
            else:
                new_row = pd.DataFrame([[final_firma, e_tipi, b_adi, tutar, vade.isoformat(), not_]], 
                                       columns=["Firma Adı", "Evrak Tipi", "Banka", "Tutar", "Vade", "Açıklama"])
                
                # Temiz veri setine ekle ve güncelle
                updated = pd.concat([df[["Firma Adı", "Evrak Tipi", "Banka", "Tutar", "Vade", "Açıklama"]], new_row], ignore_index=True)
                conn.update(spreadsheet=edit_url, data=updated)
                st.success(f"{final_firma} kaydı başarıyla eklendi!")
                st.rerun()
