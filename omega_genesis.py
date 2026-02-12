import streamlit as st
import os, gc, random, time, datetime, io
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip
import moviepy.config as mpy_config

# ==============================================================================
# 1. RDZEŃ SYSTEMU OMEGA V12.89 - KONFIGURACJA I SEKCJA STATE
# ==============================================================================

class OmegaCore:
    VERSION = "V12.89 FULL-OPTIMIZED"
    TARGET_RES = (1080, 1920)
    
    @staticmethod
    def setup_session():
        """Inicjalizacja wszystkich magazynów danych sesji."""
        if 'vault_covers' not in st.session_state:
            st.session_state.vault_covers = []
        if 'vault_photos' not in st.session_state:
            st.session_state.vault_photos = []
        if 'vault_music' not in st.session_state:
            st.session_state.vault_music = []
        if 'finished_videos' not in st.session_state:
            st.session_state.finished_videos = []

    @staticmethod
    def get_magick_path():
        """Automatyczna detekcja ImageMagick dla Linux/Windows."""
        if os.name == 'posix': # Serwer Linux
            return "/usr/bin/convert"
        return r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"

# ==============================================================================
# 2. SILNIK GRAFICZNY (ZACHOWANE WSZYSTKIE EFEKTY)
# ==============================================================================

def get_font_path(font_selection):
    font_files = {
        "League Gothic Regular": "LeagueGothic-Regular.otf",
        "League Gothic Condensed": "LeagueGothic-CondensedRegular.otf",
        "Impact": "impact.ttf"
    }
    target = font_files.get(font_selection)
    if target and os.path.exists(target):
        return os.path.abspath(target)
    return "arial.ttf"

def process_image_916(img_source, target_res=OmegaCore.TARGET_RES):
    """Logika Side-Touch z obsługą błędów i zamykaniem plików."""
    try:
        # Obsługa zarówno obiektów UploadedFile jak i ścieżek lokalnych
        with Image.open(img_source) as img:
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
    except Exception:
        return np.zeros((target_res[1], target_res[0], 3), dtype="uint8")

def draw_text_on_canvas(text, config, res=OmegaCore.TARGET_RES, is_preview=False):
    """Pełny render tekstu: Cień, Blur, Obramowanie (Alpha fix)."""
    txt_layer = Image.new("RGBA", res, (0, 0, 0, 0))
    shd_layer = Image.new("RGBA", res, (0, 0, 0, 0))
    draw_txt = ImageDraw.Draw(txt_layer)
    draw_shd = ImageDraw.Draw(shd_layer)

    try:
        font = ImageFont.truetype(config['font_path'], config['f_size'])
    except:
        font = ImageFont.load_default()

    bbox = draw_txt.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    base_pos = ((res[0] - tw) // 2, (res[1] - th) // 2)
    shd_pos = (base_pos[0] + config['shd_x'], base_pos[1] + config['shd_y'])

    # Warstwa cienia (Pełna kontrola Alpha i Blur)
    c_shd = config['shd_color'].lstrip('#')
    rgb_shd = tuple(int(c_shd[i:i+2], 16) for i in (0, 2, 4))
    draw_shd.text(shd_pos, text, fill=(*rgb_shd, config['shd_alpha']), font=font)
    if config['shd_blur'] > 0:
        shd_layer = shd_layer.filter(ImageFilter.GaussianBlur(config['shd_blur']))

    # Warstwa główna (Obramowanie i Tekst)
    draw_txt.text(base_pos, text, fill=config['t_color'], font=font,
                  stroke_width=config['s_width'], stroke_fill=config['s_color'])

    combined = Image.new("RGBA", res, (0, 0, 0, 0))
    combined.paste(shd_layer, (0, 0), shd_layer)
    combined.paste(txt_layer, (0, 0), txt_layer)

    if is_preview:
        bg = Image.new("RGB", res, (20, 40, 20))
        bg.paste(combined, (0, 0), combined)
        return bg
    return np.array(combined)

# ==============================================================================
# 3. UI - SIDEBAR (WSZYSTKIE TWOJE OPCJE)
# ==============================================================================

OmegaCore.setup_session()
st.set_page_config(page_title="OMEGA V12.89", layout="wide")
mpy_config.change_settings({"IMAGEMAGICK_BINARY": OmegaCore.get_magick_path()})

st.title(f"Ω OMEGA {OmegaCore.VERSION}")

with st.sidebar:
    st.header("⚙️ SYSTEM CONFIG")
    speed = st.selectbox("Szybkość (s)", [0.1, 0.15, 0.2, 0.25], index=1)
    
    st.divider()
    st.header("🎨 TYPOGRAFIA")
    f_font = st.selectbox("Czcionka", ["League Gothic Regular", "League Gothic Condensed", "Impact"])
    f_size = st.slider("Wielkość", 20, 500, 82)
    t_color = st.color_picker("Tekst", "#FFFFFF")
    s_width = st.slider("Obramowanie", 0, 20, 2)
    s_color = st.color_picker("Kolor Obrysu", "#000000")
    
    st.divider()
    st.header("🌑 CIEŃ")
    shd_x = st.slider("Cień X", -100, 100, 2)
    shd_y = st.slider("Cień Y", -100, 100, 19)
    shd_blur = st.slider("Cień Blur", 0, 50, 5)
    shd_alpha = st.slider("Cień Alpha", 0, 255, 146)
    shd_color = st.color_picker("Kolor Cienia", "#000000")
    
    st.divider()
    raw_texts = st.text_area("Teksty", "ig brands aint safe")
    texts_list = [t.strip() for t in raw_texts.split('\n') if t.strip()]
    
    config_dict = {
        'font_path': get_font_path(f_font), 'f_size': f_size, 't_color': t_color,
        's_width': s_width, 's_color': s_color, 'shd_x': shd_x, 'shd_y': shd_y,
        'shd_blur': shd_blur, 'shd_alpha': shd_alpha, 'shd_color': shd_color
    }

    if texts_list:
        st.subheader("👁️ PODGLĄD")
        p_img = draw_text_on_canvas(texts_list[0], config_dict, is_preview=True)
        st.image(p_img.resize((300, 533)))

# ==============================================================================
# 4. SKARBIEC I GENEROWANIE
# ==============================================================================

st.subheader("📥 SKARBIEC MEDIÓW")
c1, c2, c3 = st.columns(3)
with c1:
    u_c = st.file_uploader("Dodaj Okładki", type=['png','jpg','jpeg','webp'], accept_multiple_files=True)
    if u_c: st.session_state.vault_covers = u_c
with c2:
    u_p = st.file_uploader("Dodaj Zdjęcia", type=['png','jpg','jpeg','webp'], accept_multiple_files=True)
    if u_p: st.session_state.vault_photos = u_p
with c3:
    u_m = st.file_uploader("Dodaj Muzykę", type=['mp3'], accept_multiple_files=True)
    if u_m: st.session_state.vault_music = u_m

if st.button("🚀 URUCHOM SILNIK OMEGA", use_container_width=True):
    if not st.session_state.vault_covers or not st.session_state.vault_photos:
        st.error("Skarbiec jest pusty!")
    else:
        st.session_state.finished_videos = []
        with st.status("🎬 Produkcja w toku...", expanded=True) as status:
            # Zabezpieczenie przed brakiem folderu temp
            if not os.path.exists("temp"): os.makedirs("temp")
            
            for i, cov_file in enumerate(st.session_state.vault_covers):
                st.write(f"Renderowanie {i+1}/{len(st.session_state.vault_covers)}...")
                
                # Dynamiczna długość filmu
                dur = random.uniform(8.0, 10.0)
                num_p = int(dur / speed)
                batch = random.sample(st.session_state.vault_photos, min(num_p, len(st.session_state.vault_photos)))
                
                # Konwersja obrazów na klipy (używamy with dla oszczędności RAM)
                clips = [ImageClip(process_image_916(cov_file)).set_duration(speed * 2)]
                clips += [ImageClip(process_image_916(p)).set_duration(speed) for p in batch]
                
                base = concatenate_videoclips(clips, method="chain")
                
                # Nakładka tekstowa (z Twoimi wszystkimi ustawieniami)
                txt_arr = draw_text_on_canvas(random.choice(texts_list) if texts_list else "OMEGA", config_dict)
                txt_clip = ImageClip(txt_arr).set_duration(base.duration)
                
                final = CompositeVideoClip([base, txt_clip], size=OmegaCore.TARGET_RES)
                
                # Dodanie audio jeśli istnieje
                if st.session_state.vault_music:
                    m_file = random.choice(st.session_state.vault_music)
                    audio_path = f"temp/audio_{i}.mp3"
                    with open(audio_path, "wb") as f: f.write(m_file.getbuffer())
                    aud = AudioFileClip(audio_path)
                    final = final.set_audio(aud.subclip(0, min(aud.duration, final.duration)))
                
                out_n = f"OMEGA_EXPORT_{i+1}.mp4"
                final.write_videofile(out_n, fps=24, codec="libx264", audio_codec="aac", threads=4, logger=None, preset="ultrafast")
                
                st.session_state.finished_videos.append(out_n)
                
                # Zamykanie procesów i czyszczenie RAM
                final.close(); base.close(); gc.collect()
                
            status.update(label="✅ GOTOWE!", state="complete")

# SEKCJA POBIERANIA
if st.session_state.finished_videos:
    st.divider()
    cols = st.columns(4)
    for idx, vid in enumerate(st.session_state.finished_videos):
        if os.path.exists(vid):
            with open(vid, "rb") as f:
                cols[idx % 4].download_button(f"🎥 Film {idx+1}", f, file_name=vid, key=f"d_{idx}")
