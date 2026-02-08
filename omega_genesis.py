import streamlit as st
import os
import gc
import random
import time
import zipfile
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip

# ==========================================================
# 1. FUNKCJA KADROWANIA (FULL SCREEN 9:16)
# ==========================================================
def process_image_916(img_file, target_res=(1080, 1920)):
    """
    Automatycznie docina zdjęcie do formatu 9:16 bez czarnych pasów.
    """
    try:
        with Image.open(img_file) as img:
            # Naprawa orientacji zdjęcia z telefonu (EXIF)
            img = ImageOps.exif_transpose(img).convert("RGB")
            
            target_ratio = target_res[0] / target_res[1]
            img_ratio = img.width / img.height
            
            if img_ratio > target_ratio:
                # Zdjęcie jest za szerokie - dopasuj do wysokości i przytnij boki
                new_width = int(target_res[1] * img_ratio)
                img = img.resize((new_width, target_res[1]), Image.Resampling.LANCZOS)
                left = (new_width - target_res[0]) / 2
                img = img.crop((left, 0, left + target_res[0], target_res[1]))
            else:
                # Zdjęcie jest za wysokie - dopasuj do szerokości i przytnij góra/dół
                new_height = int(target_res[0] / img_ratio)
                img = img.resize((target_res[0], new_height), Image.Resampling.LANCZOS)
                top = (new_height - target_res[1]) / 2
                img = img.crop((0, top, target_res[0], top + target_res[1]))
                
            return np.array(img)
    except Exception as e:
        # W razie błędu zwróć czarne tło
        return np.zeros((1920, 1080, 3), dtype="uint8")

# ==========================================================
# 2. SILNIK RYSOWANIA TEKSTU (Z CIEŃ + BLUR + ALPHA)
# ==========================================================
def draw_text_on_canvas(text, config, res=(1080, 1920), is_preview=False):
    """
    Tworzy warstwę tekstu z obramowaniem i rozmytym cieniem.
    """
    # Tworzenie warstw
    txt_layer = Image.new("RGBA", res, (0, 0, 0, 0))
    shd_layer = Image.new("RGBA", res, (0, 0, 0, 0))
    
    draw_txt = ImageDraw.Draw(txt_layer)
    draw_shd = ImageDraw.Draw(shd_layer)
    
    # Ładowanie czcionki
    try:
        if config['font_path'] and os.path.exists(config['font_path']):
            font = ImageFont.truetype(config['font_path'], config['f_size'])
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
        
    # Obliczanie pozycji (środek)
    bbox = draw_txt.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    base_pos = ((res[0] - tw) // 2, (res[1] - th) // 2)
    
    # 1. Rysowanie cienia
    shd_pos = (base_pos[0] + config['shd_x'], base_pos[1] + config['shd_y'])
    c_shd = config['shd_color'].lstrip('#')
    rgb_shd = tuple(int(c_shd[i:i+2], 16) for i in (0, 2, 4))
    
    draw_shd.text(shd_pos, text, fill=(*rgb_shd, config['shd_alpha']), font=font)
    
    # Nakładanie rozmycia na cień
    if config['shd_blur'] > 0:
        shd_layer = shd_layer.filter(ImageFilter.GaussianBlur(config['shd_blur']))
        
    # 2. Rysowanie tekstu głównego z obramowaniem
    draw_txt.text(
        base_pos, 
        text, 
        fill=config['t_color'], 
        font=font, 
        stroke_width=config['s_width'], 
        stroke_fill=config['s_color']
    )
    
    # Łączenie warstw
    combined = Image.new("RGBA", res, (0, 0, 0, 0))
    combined.paste(shd_layer, (0, 0), shd_layer)
    combined.paste(txt_layer, (0, 0), txt_layer)
    
    if is_preview:
        # Tło Green Screen dla podglądu w aplikacji
        bg = Image.new("RGB", res, (0, 255, 0))
        bg.paste(combined, (0, 0), combined)
        return bg
        
    return np.array(combined)

# ==========================================================
# 3. INTERFEJS UŻYTKOWNIKA (SIDEBAR)
# ==========================================================
st.set_page_config(page_title="OMEGA V12.51", layout="wide")
st.title("Ω OMEGA V12.51 - THE ULTIMATE VERSION")

with st.sidebar:
    st.header("⚙️ USTAWIENIA")
    
    v_count = st.number_input("Ile filmów wygenerować?", 1, 100, 5)
    speed = st.selectbox("Szybkość zdjęć (sekundy)", [0.1, 0.15, 0.2, 0.3], index=2)
    
    st.divider()
    
    st.subheader("🅰️ STYL TEKSTU")
    font_choice = st.selectbox("Czcionka", ["League Gothic Regular", "League Gothic Condensed", "Impact"])
    f_size = st.slider("Wielkość napisu", 10, 800, 82)
    t_color = st.color_picker("Kolor tekstu", "#FFFFFF")
    s_width = st.slider("Grubość obramowania", 0, 30, 2)
    s_color = st.color_picker("Kolor obramowania", "#000000")
    
    st.subheader("🌑 USTAWIENIA CIENIA")
    shd_x = st.slider("Przesunięcie X", -150, 150, 2)
    shd_y = st.slider("Przesunięcie Y", -150, 150, 19)
    shd_blur = st.slider("Rozmycie (Blur)", 0, 100, 5)
    shd_alpha = st.slider("Przezroczystość (Alpha)", 0, 255, 146)
    shd_color = st.color_picker("Kolor cienia", "#000000")
    
    st.divider()
    
    raw_texts = st.text_area("Lista tekstów (jeden pod drugim)", "ig brands aint safe")
    texts_list = [t.strip() for t in raw_texts.split('\n') if t.strip()]

    # Mapowanie ścieżek czcionek
    font_paths = {
        "League Gothic Regular": "LeagueGothic-Regular.otf",
        "League Gothic Condensed": "LeagueGothic-CondensedRegular.otf",
        "Impact": "impact.ttf"
    }
    
    config_dict = {
        'font_path': font_paths.get(font_choice),
        'f_size': f_size,
        't_color': t_color,
        's_width': s_width,
        's_color': s_color,
        'shd_x': shd_x,
        'shd_y': shd_y,
        'shd_blur': shd_blur,
        'shd_alpha': shd_alpha,
        'shd_color': shd_color
    }
    
    # PRZYWRÓCONY PODGLĄD (PREVIEW)
    if texts_list:
        st.write("### 👀 Podgląd na żywo:")
        preview_img = draw_text_on_canvas(texts_list[0], config_dict, is_preview=True)
        st.image(preview_img, use_container_width=True)

# ==========================================================
# 4. WRZUCANIE PLIKÓW (FIX NA TELEFON)
# ==========================================================
col1, col2, col3 = st.columns(3)

with col1:
    # Dodano 'type' i 'key' dla lepszej obsługi galerii w telefonie
    u_cov = st.file_uploader("🖼️ OKŁADKI (Wiele)", accept_multiple_files=True, type=["jpg", "png", "jpeg"], key="c_mob")
with col2:
    u_pho = st.file_uploader("📷 ZDJĘCIA (Wiele)", accept_multiple_files=True, type=["jpg", "png", "jpeg"], key="p_mob")
with col3:
    u_mus = st.file_uploader("🎵 MUZYKA", accept_multiple_files=True, type=["mp3", "wav"], key="m_mob")

# ==========================================================
# 5. GŁÓWNY PROCES RENDEROWANIA
# ==========================================================
if st.button("🚀 URUCHOM GENEROWANIE FILMU"):
    if u_cov and u_pho and texts_list:
        with st.status("🎬 Trwa tworzenie Twoich filmów...") as status:
            sid = int(time.time())
            
            # Zapisywanie okładek
            c_paths = []
            for i, f in enumerate(u_cov):
                path = f"cover_{sid}_{i}.jpg"
                with open(path, "wb") as b:
                    b.write(f.getbuffer())
                c_paths.append(path)
                
            # Zapisywanie zdjęć
            p_paths = []
            for i, f in enumerate(u_pho):
                path = f"photo_{sid}_{i}.jpg"
                with open(path, "wb") as b:
                    b.write(f.getbuffer())
                p_paths.append(path)
                
            # Zapisywanie muzyki
            m_paths = []
            for i, f in enumerate(u_mus):
                path = f"music_{sid}_{i}.mp3"
                with open(path, "wb") as b:
                    b.write(f.getbuffer())
                m_paths.append(path)

            # --- LOGIKA UNIKALNYCH OKŁADEK ---
            pool_covers = list(c_paths)
            random.shuffle(pool_covers)
            
            final_files = []
            
            for i in range(v_count):
                # Jeśli wykorzystano wszystkie unikalne okładki, odśwież pulę
                if not pool_covers:
                    pool_covers = list(c_paths)
                    random.shuffle(pool_covers)
                
                # Wybór unikalnej okładki
                current_cover = pool_covers.pop()
                current_text = random.choice(texts_list)
                
                # Budowanie sekwencji 9 sekund
                needed = int(9.0 / speed)
                batch = []
                while len(batch) < needed:
                    temp_p = list(p_paths)
                    random.shuffle(temp_p)
                    batch.extend(temp_p)
                batch = batch[:needed]
                
                # Tworzenie klipów MoviePy
                video_clips = []
                # 1. Dodaj okładkę na początek
                video_clips.append(ImageClip(process_image_916(current_cover)).set_duration(speed))
                # 2. Dodaj resztę zdjęć
                for p in batch:
                    video_clips.append(ImageClip(process_image_916(p)).set_duration(speed))
                
                # Łączenie wideo
                base_video = concatenate_videoclips(video_clips, method="chain")
                
                # Nakładanie tekstu
                txt_img = draw_text_on_canvas(current_text, config_dict)
                txt_clip = ImageClip(txt_img).set_duration(base_video.duration)
                
                final_video = CompositeVideoClip([base_video, txt_clip], size=(1080, 1920))
                
                # Dodawanie muzyki
                if m_paths:
                    audio = AudioFileClip(random.choice(m_paths))
                    final_video = final_video.set_audio(audio.subclip(0, min(audio.duration, final_video.duration)))
                
                # Eksport pliku
                out_name = f"video_result_{sid}_{i}.mp4"
                final_video.write_videofile(
                    out_name, 
                    fps=24, 
                    codec="libx264", 
                    audio_codec="aac", 
                    threads=1, 
                    logger=None, 
                    preset="ultrafast"
                )
                final_files.append(out_name)
                
                # Czyszczenie pamięci po każdym filmie
                final_video.close()
                base_video.close()
                gc.collect()

            # Pakowanie do ZIP
            zip_name = f"OMEGA_EXPORT_{sid}.zip"
            with zipfile.ZipFile(zip_name, 'w') as z:
                for f in final_files:
                    z.write(f)
                    os.remove(f)
            
            # Usuwanie plików tymczasowych
            for p in c_paths + p_paths + m_paths:
                if os.path.exists(p):
                    os.remove(p)
                    
            status.update(label="✅ Gotowe! Pobierz paczkę poniżej.", state="complete")
            st.download_button("📥 POBIERZ PACZKĘ ZIP", open(zip_name, "rb"), file_name=zip_name)
    else:
        st.error("Wgraj okładki, zdjęcia i wpisz tekst!")
