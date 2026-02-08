import streamlit as st
import os
import gc
import random
import time
import zipfile
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip

# --- FUNKCJE POMOCNICZE ---

def crop_to_916(file_path, target_size=(1080, 1920)):
    """Kadruje zdjęcie do formatu 9:16 bez czarnych pasów."""
    try:
        with Image.open(file_path) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            t_w, t_h = target_size
            img_ratio = img.width / img.height
            target_ratio = t_w / t_h
            
            if img_ratio > target_ratio:
                # Zdjęcie zbyt szerokie
                new_w = int(t_h * img_ratio)
                img = img.resize((new_w, t_h), Image.Resampling.LANCZOS)
                left = (new_w - t_w) / 2
                img = img.crop((left, 0, left + t_w, t_h))
            else:
                # Zdjęcie zbyt wąskie
                new_h = int(t_w / img_ratio)
                img = img.resize((t_w, new_h), Image.Resampling.LANCZOS)
                top = (new_h - t_h) / 2
                img = img.crop((0, top, t_w, top + t_h))
            return np.array(img)
    except:
        return np.zeros((1920, 1080, 3), dtype="uint8")

def create_text_overlay(text, cfg, size=(1080, 1920)):
    """Tworzy przezroczystą warstwę z napisem i cieniem."""
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    shadow_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw_shd = ImageDraw.Draw(shadow_layer)
    
    try:
        font = ImageFont.truetype(cfg['font_path'], cfg['f_size'])
    except:
        font = ImageFont.load_default()
        
    # Pozycjonowanie
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size[0] - w) // 2
    y = (size[1] - h) // 2
    
    # Rysowanie cienia
    shd_hex = cfg['shd_color'].lstrip('#')
    shd_rgb = tuple(int(shd_hex[i:i+2], 16) for i in (0, 2, 4))
    draw_shd.text((x + cfg['shd_x'], y + cfg['shd_y']), text, 
                  fill=(*shd_rgb, cfg['shd_alpha']), font=font)
    
    if cfg['shd_blur'] > 0:
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(cfg['shd_blur']))
    
    # Rysowanie tekstu głównego
    draw.text((x, y), text, fill=cfg['t_color'], font=font, 
              stroke_width=cfg['s_width'], stroke_fill=cfg['s_color'])
    
    # Połączenie warstw
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(shadow_layer, (0, 0), shadow_layer)
    out.paste(canvas, (0, 0), canvas)
    return np.array(out)

# --- INTERFEJS STRONY ---

st.set_page_config(page_title="OMEGA V12.70", layout="wide")
st.title("Ω OMEGA V12.70 - REBORN")

with st.sidebar:
    st.header("🎨 STYLIZACJA")
    num_vids = st.number_input("Ilość filmów do wygenerowania", 1, 100, 5)
    slide_speed = st.selectbox("Szybkość zdjęć (sekundy)", [0.1, 0.15, 0.2, 0.3], index=2)
    
    st.divider()
    font_choice = st.selectbox("Czcionka", ["League Gothic Regular", "Impact", "Arial"])
    text_size = st.slider("Wielkość tekstu", 50, 600, 85)
    text_color = st.color_picker("Kolor napisu", "#FFFFFF")
    stroke_w = st.slider("Grubość obramowania", 0, 20, 2)
    stroke_c = st.color_picker("Kolor obramowania", "#000000")
    
    st.subheader("🌑 CIEŃ")
    sx = st.slider("Przesunięcie X", -100, 100, 3)
    sy = st.slider("Przesunięcie Y", -100, 100, 15)
    s_blur = st.slider("Rozmycie cienia", 0, 50, 5)
    s_alpha = st.slider("Przezroczystość cienia", 0, 255, 150)
    s_color = st.color_picker("Kolor cienia", "#000000")
    
    st.divider()
    txt_input = st.text_area("Lista tekstów (jeden na linię)", "Vibe Check")
    all_texts = [line.strip() for line in txt_input.split('\n') if line.strip()]

    # Ścieżki czcionek
    f_map = {"League Gothic Regular": "LeagueGothic-Regular.otf", "Impact": "impact.ttf", "Arial": "arial.ttf"}
    current_cfg = {
        'font_path': f_map.get(font_choice), 'f_size': text_size, 't_color': text_color,
        's_width': stroke_w, 's_color': stroke_c, 'shd_x': sx, 'shd_y': sy,
        'shd_blur': s_blur, 'shd_alpha': s_alpha, 'shd_color': s_color
    }

# --- WGRYWANIE PLIKÓW ---

c1, c2, c3 = st.columns(3)
with c1: u_covers = st.file_uploader("🖼️ OKŁADKI", accept_multiple_files=True)
with c2: u_photos = st.file_uploader("📷 ZDJĘCIA", accept_multiple_files=True)
with c3: u_audio = st.file_uploader("🎵 MUZYKA", accept_multiple_files=True)

# --- PROCES GENEROWANIA ---

if st.button("🚀 URUCHOM RENDERER"):
    if u_covers and u_photos and all_texts:
        with st.status("🎬 Trwa renderowanie... Proszę czekać.") as status:
            session_id = int(time.time())
            
            def save_to_disk(uploaded_list, prefix):
                paths = []
                for i, f in enumerate(uploaded_list):
                    path = f"file_{session_id}_{prefix}_{i}.jpg"
                    with open(path, "wb") as buffer:
                        buffer.write(f.getbuffer())
                    paths.append(path)
                return paths

            p_covers = save_to_disk(u_covers, "cov")
            p_photos = save_to_disk(u_photos, "pho")
            p_music = save_to_disk(u_audio, "mus")

            # Pula okładek (unikalność)
            cover_pool = list(p_covers)
            random.shuffle(cover_pool)
            
            created_files = []

            for v in range(num_vids):
                # Reset puli okładek jeśli się skończą
                if not cover_pool:
                    cover_pool = list(p_covers)
                    random.shuffle(cover_pool)
                
                selected_cover = cover_pool.pop()
                selected_text = random.choice(all_texts)
                
                # Losowanie czasu trwania (8-10s)
                target_duration = random.uniform(8.0, 10.0)
                needed_count = int(target_duration / slide_speed)
                
                # Budowanie puli zdjęć dla filmu
                film_photos = []
                while len(film_photos) < needed_count:
                    temp_p = list(p_photos)
                    random.shuffle(temp_p)
                    film_photos.extend(temp_p)
                film_photos = film_photos[:needed_count]
                
                # Składanie klipów
                all_paths = [selected_cover] + film_photos
                video_clips = [ImageClip(crop_to_916(p)).set_duration(slide_speed) for p in all_paths]
                
                # Łączenie wideo
                base_video = concatenate_videoclips(video_clips, method="chain")
                
                # Nakładanie tekstu
                text_img = create_text_overlay(selected_text, current_cfg)
                overlay_clip = ImageClip(text_img).set_duration(base_video.duration)
                
                final_output = CompositeVideoClip([base_video, overlay_clip], size=(1080, 1920))
                
                # Muzyka
                if p_music:
                    m_file = random.choice(p_music)
                    audio = AudioFileClip(m_file)
                    final_output = final_output.set_audio(audio.subclip(0, min(audio.duration, final_output.duration)))
                
                # Export
                out_name = f"video_{session_id}_{v}.mp4"
                final_output.write_videofile(out_name, fps=24, codec="libx264", audio_codec="aac", logger=None, preset="ultrafast")
                created_files.append(out_name)
                
                # Czyszczenie pamięci
                final_output.close()
                base_video.close()
                gc.collect()

            # Pakowanie do ZIP
            zip_name = f"PACZKA_OMEGA_{session_id}.zip"
            with zipfile.ZipFile(zip_name, 'w') as zipf:
                for f in created_files:
                    zipf.write(f)
                    os.remove(f)
            
            # Usuwanie plików tymczasowych
            for p in p_covers + p_photos + p_music:
                if os.path.exists(p):
                    os.remove(p)
            
            status.update(label="✅ Renderowanie zakończone!", state="complete")
            st.download_button("📥 POBIERZ GOTOWE FILMY", open(zip_name, "rb"), file_name=zip_name)
    else:
        st.warning("⚠️ Brak plików! Wgraj okładki, zdjęcia i dodaj teksty.")
