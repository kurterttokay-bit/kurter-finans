# MUHASEBE KAYDETME KISMINI BU ŞEKİLDE GÜNCELLE
if st.form_submit_button("Sisteme Kaydet"):
    # 1. Önce sayfadaki EN GÜNCEL halini bir çekelim (Boşsa bile)
    try:
        # Clear cache yaparak en taze veriyi çekiyoruz
        current_df = conn.read(spreadsheet=edit_url, ttl=0) 
    except:
        current_df = pd.DataFrame(columns=['Tanim', 'Tutar', 'Vade'])

    # 2. Yeni satırı hazırla
    new_row = pd.DataFrame([{"Tanim": t, "Tutar": m, "Vade": str(v)}])

    # 3. Mevcut verinin altına yapıştır (Üzerine yazma hatasını burası çözer)
    updated_df = pd.concat([current_df, new_row], ignore_index=True)

    # 4. Hepsini birden geri gönder
    try:
        conn.update(spreadsheet=edit_url, data=updated_df)
        st.success("Veri başarıyla eklendi!")
        st.cache_data.clear() # Cache temizle ki patron anında görsün
        st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")
