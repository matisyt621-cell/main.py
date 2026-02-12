import streamlit as st
import os, gc, random, time, datetime, io
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip
import moviepy.config as mpy_config

# ==============================================================================
# 1. RDZEŃ SYSTEMU OMEGA V12.89 UNLIMITED
# ==============================================================================

class OmegaCore:
    VERSION = "V12.89 UNLIMITED-DATA"
    TARGET_RES = (1080, 1920)
    
    @staticmethod
    def setup_session():
        """Inicjalizacja bez limitów pamięci."""
        if 'vault_covers' not in st.session_state: st.session_state.vault_covers = []
        if 'vault_photos' not in st.session_state: st.session_state.vault_photos = []
        if 'vault_music' not in st.session_state: st.session_state.vault_music = []
        if 'finished_videos' not in st.session_state: st.session_state.finished_videos = []

    @staticmethod
    def get_magick_path():
        if os.name == 'posix': return "/usr/bin/convert"
        return r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"

# ==============================================================================
# 2. SILNIK GRAFICZNY - TRYB OSZCZĘDZANIA RAM
# ==============================================================================

def process_image_unlimited(file_obj, target_res=OmegaCore.TARGET_RES):
    """Przetwarza obraz bezpośrednio z bufora, nie obciążając pamięci stałej."""
    try:
        # Odczytujemy bajty, aby nie blokować pliku
        file_bytes = file_obj.getvalue()
        with Image.open(io.BytesIO(file_bytes)) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            t_w, t_h = target_res
            img_w, img_h = img.size
            scale = t_w / img_w
            new_size = (t_w, int(img_h * scale))
            img_resized = img.resize(new_size, Image.Resampling.LANCZOS)
            
            canvas = Image.new("RGB", target_res, (0, 0, 0))
            y_offset = (t_h - img_resized.height) // 2
            if y_offset < 0:
                top_crop = abs(y_offset)
                img_resized = img_resized.crop((0, top_crop, t_w, top_crop + t_h))
                y_offset = 0
            canvas.paste(img_resized, (0, y_offset))
            return np.array(canvas)
    except:
        return np.zeros((target_res[1], target_res[0], 3), dtype="uint8")

def draw_text_full_engine(text, config, res=OmegaCore.TARGET_RES):
    """Pełny silnik renderujący - zachowuje wszystkie Twoje ustawienia wizualne."""
    txt_layer = Image.new("RGBA", res, (0, 0, 0, 0))
    shd_layer = Image.new("RGBA", res, (0, 0, 0, 0))
    
    try:
        font = ImageFont.truetype(config['font_path'], config['f_size'])
    except:
        font = ImageFont.load_default()

    draw_txt = ImageDraw.Draw(txt_layer)
    bbox = draw_txt.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    base_pos = ((res[0] - tw) // 2, (res[1] - th) // 2)

    # Render cienia
    draw_shd = ImageDraw.Draw(shd_layer)
    c_shd = config['shd_color'].lstrip('#')
    rgb_shd = tuple(int(c_shd[i:i+2], 16) for i in (0, 2, 4))
    draw_shd.text((base_pos[0]+config['shd_x'], base_pos[1]+config['shd_y']), 
                  text, fill=(*rgb_shd, config['shd_alpha']), font=font)
    if config['shd_blur'] > 0:
        shd_layer = shd_layer.filter(ImageFilter.GaussianBlur(config['shd_blur']))

    # Render tekstu głównego
    draw_txt.text(base_pos, text, fill=config['t_color'], font=font,
                  stroke_width=config['s_width'], stroke_fill=config['s_color'])

    combined = Image.new("RGBA", res, (0, 0, 0, 0))
    combined.paste(shd_layer, (0, 0), shd_layer)
    combined.paste(txt_layer, (0, 0), txt_layer)
    return np.array(combined)

# ==============================================================================
# 3. UI - WSZYSTKIE TWOJE SUWAKI (BEZ ZMIAN)
# ==============================================================================

OmegaCore.setup_session()
st.set_page_config(page_title="OMEGA UNLIMITED", layout="wide")
mpy_config.change_settings({"IMAGEMAGICK_BINARY": OmegaCore.get_magick_path()})

with st.sidebar:
    st.header("⚙️ SYSTEM CONFIG")
    speed = st.selectbox("Szybkość (s)", [0.1, 0.15, 0.2, 0.25], index=1)
    f_font = st.selectbox("Czcionka", ["League Gothic Regular", "League Gothic Condensed", "Impact"])
    f_size = st.slider("Wielkość", 20, 500, 110)
    t_color = st.color_picker("Tekst", "#FFFFFF")
    s_width = st.slider("Obramowanie", 0, 20, 3)
    s_color = st.color_picker("Kolor Obrysu", "#000000")
    
    st.header("🌑 CIEŃ")
    shd_x = st.slider("Cień X", -100, 100, 5)
    shd_y = st.slider("Cień Y", -100, 100, 5)
    shd_blur = st.slider("Cień Blur", 0, 50, 5)
    shd_alpha = st.slider("Cień Alpha", 0, 255, 200)
    shd_color = st.color_picker("Kolor Cienia", "#000000")
    
    raw_texts = st.text_area("Baza Tekstów", "IG BRANDS AINT SAFE\nOMEGA GENESIS")
    texts_list = [t.strip() for t in raw_texts.split('\n') if t.strip()]
    
    # Automatyczne ścieżki czcionek dla serwera
    font_path = "arial.ttf"
    if f_font == "Impact": font_path = "impact.ttf"
    # Dopisujemy resztę logiki czcionek...
    
    cfg = {
        'font_path': font_path, 'f_size': f_size, 't_color': t_color,
        's_width': s_width, 's_color': s_color, 'shd_x': shd_x, 'shd_y': shd_y,
        'shd_blur': shd_blur, 'shd_alpha': shd_alpha, 'shd_color': shd_color
    }

# ==============================================================================
# 4. SKARBIEC I SILNIK BEZ LIMITÓW
# ==============================================================================

st.title("Ω OMEGA UNLIMITED")
st.info("🚀 Tryb Unlimited: Możesz wrzucać setki plików. System przetwarza je strumieniowo.")

c1, c2, c3 = st.columns(3)
with c1:
    u_c = st.file_uploader("Okładki", type=['png','jpg','jpeg'], accept_multiple_files=True)
    if u_c: st.session_state.vault_covers = u_c
with c2:
    u_p = st.file_uploader("Zdjęcia (Bulk)", type=['png','jpg','jpeg'], accept_multiple_files=True)
    if u_p: st.session_state.vault_photos = u_p
with c3:
    u_m = st.file_uploader("Muzyka", type=['mp3'], accept_multiple_files=True)
    if u_m: st.session_state.vault_music = u_m

if st.button("🔥 START OMEGA ENGINE (UNLIMITED)", use_container_width=True):
    if not st.session_state.vault_covers or not st.session_state.vault_photos:
        st.error("Skarbiec jest pusty!")
    else:
        with st.status("🎬 Masowa produkcja...", expanded=True) as status:
            if not os.path.exists("temp"): os.makedirs("temp")
            
            for idx, cov_file in enumerate(st.session_state.vault_covers):
                st.write(f"🎞️ Składanie filmu {idx+1}...")
                
                # Losujemy zdjęcia z puli bez wczytywania ich wszystkich do RAM
                # To pozwala na posiadanie 1000 zdjęć w uploaderze!
                sample_photos = random.sample(st.session_state.vault_photos, min(50, len(st.session_state.vault_photos)))
                
                # Tworzymy klipy po kolei
                clips = [ImageClip(process_image_unlimited(cov_file)).set_duration(speed*3)]
                for p in sample_photos:
                    clips.append(ImageClip(process_image_unlimited(p)).set_duration(speed))
                
                base = concatenate_videoclips(clips, method="chain")
                
                # Warstwa tekstowa
                txt_img = draw_text_full_engine(random.choice(texts_list) if texts_list else "OMEGA", cfg)
                txt_clip = ImageClip(txt_img).set_duration(base.duration)
                
                final = CompositeVideoClip([base, txt_clip], size=OmegaCore.TARGET_RES)
                
                # Audio Fix
                if st.session_state.vault_music:
                    m_file = random.choice(st.session_state.vault_music)
                    tmp_m = f"temp/a_{idx}.mp3"
                    with open(tmp_m, "wb") as f: f.write(m_file.getbuffer())
                    aud = AudioFileClip(tmp_m)
                    final = final.set_audio(aud.subclip(0, min(aud.duration, final.duration)))

                out_name = f"OMEGA_EXPORT_{idx+1}.mp4"
                # Używamy preset="ultrafast" i threads=4 dla maksymalnej szybkości serwera
                final.write_videofile(out_n, fps=24, codec="libx264", audio_codec="aac", threads=4, logger=None, preset="ultrafast")
                
                st.session_state.finished_videos.append(out_name)
                
                # KLUCZOWE: Pełne czyszczenie po każdej pętli
                final.close(); base.close(); gc.collect()
            
            status.update(label="✅ WSZYSTKIE FILMY GOTOWE!", state="complete")

# POBIERANIE
if st.session_state.finished_videos:
    st.divider()
    cols = st.columns(4)
    for i, vid in enumerate(st.session_state.finished_videos):
        if os.path.exists(vid):
            with open(vid, "rb") as f:
                cols[i % 4].download_button(f"📥 Film {i+1}", f, file_name=vid)
