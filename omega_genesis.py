import streamlit as st
import os, gc, random, time, datetime, io, subprocess
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip
import moviepy.config as mpy_config

# ==============================================================================
# 1. RDZEŃ SYSTEMU OMEGA V12.89 - ZOPTYMALIZOWANY
# ==============================================================================

class OmegaCore:
    VERSION = "V12.89 OPTIMIZED"
    TARGET_RES = (1080, 1920)
    
    @staticmethod
    def setup_session():
        """Inicjalizacja magazynów danych bez przeładowywania RAMu."""
        for key in ['v_covers', 'v_photos', 'v_music', 'v_results']:
            if key not in st.session_state:
                st.session_state[key] = []

    @staticmethod
    def get_magick_path():
        """Automatyczna detekcja ImageMagick dla Linux/Windows."""
        if os.name == 'posix': # Linux
            return "/usr/bin/convert"
        return r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"

# ==============================================================================
# 2. SILNIK GRAFICZNY (CACHE'OWANY)
# ==============================================================================

@st.cache_data(show_spinner=False)
def process_frame(img_bytes, target_res=OmegaCore.TARGET_RES):
    """Szybkie skalowanie Side-Touch z wykorzystaniem Cache Streamlit."""
    try:
        with Image.open(io.BytesIO(img_bytes)) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            t_w, t_h = target_res
            img_w, img_h = img.size
            scale = t_w / img_w
            img_resized = img.resize((t_w, int(img_h * scale)), Image.Resampling.LANCZOS)
            
            canvas = Image.new("RGB", target_res, (0, 0, 0))
            y_off = (t_h - img_resized.height) // 2
            if y_off < 0:
                img_resized = img_resized.crop((0, abs(y_off), t_w, abs(y_off) + t_h))
                y_off = 0
            canvas.paste(img_resized, (0, y_off))
            return np.array(canvas)
    except:
        return np.zeros((target_res[1], target_res[0], 3), dtype="uint8")

def render_text_layer(text, cfg):
    """Renderowanie warstwy tekstowej z optymalizacją warstw."""
    res = OmegaCore.TARGET_RES
    layer = Image.new("RGBA", res, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    
    try:
        font = ImageFont.truetype(cfg['font_path'], cfg['f_size'])
    except:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    pos = ((res[0] - (bbox[2]-bbox[0])) // 2, (res[1] - (bbox[3]-bbox[1])) // 2)

    # Render cienia z blurem (tylko jeśli alpha > 0)
    if cfg['shd_alpha'] > 0:
        shadow = Image.new("RGBA", res, (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow)
        s_color = tuple(int(cfg['shd_color'].lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        s_draw.text((pos[0]+cfg['shd_x'], pos[1]+cfg['shd_y']), text, fill=(*s_color, cfg['shd_alpha']), font=font)
        if cfg['shd_blur'] > 0:
            shadow = shadow.filter(ImageFilter.GaussianBlur(cfg['shd_blur']))
        layer.paste(shadow, (0,0), shadow)

    # Tekst główny
    draw.text(pos, text, fill=cfg['t_color'], font=font, 
              stroke_width=cfg['s_width'], stroke_fill=cfg['s_color'])
    return np.array(layer)

# ==============================================================================
# 3. INTERFEJS I KONFIGURACJA
# ==============================================================================

OmegaCore.setup_session()
st.set_page_config(page_title="Ω OMEGA V12.89", layout="wide")
mpy_config.change_settings({"IMAGEMAGICK_BINARY": OmegaCore.get_magick_path()})

with st.sidebar:
    st.title("Ω SETTINGS")
    speed = st.slider("Szybkość przejść (s)", 0.05, 0.5, 0.15)
    f_size = st.slider("Wielkość tekstu", 50, 300, 110)
    t_color = st.color_picker("Kolor tekstu", "#FFFFFF")
    
    raw_txt = st.text_area("Baza tekstów (jeden na linię)", "IG BRANDS AINT SAFE\nOMEGA GENERATION")
    texts = [t.strip() for t in raw_txt.split('\n') if t.strip()]

    cfg = {
        'font_path': "arial.ttf", 'f_size': f_size, 't_color': t_color,
        's_width': 3, 's_color': "#000000", 'shd_x': 5, 'shd_y': 5,
        'shd_blur': 5, 'shd_alpha': 180, 'shd_color': "#000000"
    }

# ==============================================================================
# 4. SILNIK PRODUKCYJNY (STABILNY)
# ==============================================================================

st.header("📥 SKARBIEC")
col1, col2, col3 = st.columns(3)

with col1:
    u_covers = st.file_uploader("Okładki", type=['jpg', 'png'], accept_multiple_files=True)
    if u_covers: st.session_state.v_covers = u_covers

with col2:
    u_photos = st.file_uploader("Zdjęcia (Bulk)", type=['jpg', 'png'], accept_multiple_files=True)
    if u_photos: st.session_state.v_photos = u_photos

with col3:
    u_music = st.file_uploader("Muzyka (MP3)", type=['mp3'], accept_multiple_files=True)
    if u_music: st.session_state.v_music = u_music

if st.button("🚀 GENERUJ FILMY", use_container_width=True):
    if not st.session_state.v_covers or not st.session_state.v_photos:
        st.error("Brak materiałów w skarbcu!")
    else:
        results = []
        progress = st.progress(0)
        
        for idx, cov_file in enumerate(st.session_state.v_covers):
            try:
                # Przygotowanie klipów
                cov_bytes = cov_file.read()
                photo_pool = [f.read() for f in random.sample(st.session_state.v_photos, min(40, len(st.session_state.v_photos)))]
                
                # Budowa sekwencji
                clips = [ImageClip(process_frame(cov_bytes)).set_duration(speed * 3)] # Okładka dłużej
                clips += [ImageClip(process_frame(p)).set_duration(speed) for p in photo_pool]
                
                video = concatenate_videoclips(clips, method="chain")
                
                # Dodanie tekstu
                txt_img = render_text_layer(random.choice(texts) if texts else "OMEGA", cfg)
                txt_clip = ImageClip(txt_img).set_duration(video.duration)
                
                final = CompositeVideoClip([video, txt_clip], size=OmegaCore.TARGET_RES)
                
                # Audio
                if st.session_state.v_music:
                    m_file = random.choice(st.session_state.v_music)
                    with open("tmp_audio.mp3", "wb") as f: f.write(m_file.getvalue())
                    audio = AudioFileClip("tmp_audio.mp3").set_duration(final.duration)
                    final = final.set_audio(audio)

                out_name = f"OMEGA_EXPORT_{idx}.mp4"
                final.write_videofile(out_name, fps=24, codec="libx264", audio_codec="aac", threads=4, logger=None, preset="ultrafast")
                
                results.append(out_name)
                
                # Sprzątanie pamięci po każdym filmie
                final.close(); video.close(); gc.collect()
                progress.progress((idx + 1) / len(st.session_state.v_covers))
                
            except Exception as e:
                st.error(f"Błąd przy filmie {idx}: {e}")

        st.session_state.v_results = results
        st.success("Produkcja zakończona!")

# SEKCJA POBIERANIA
if st.session_state.v_results:
    st.divider()
    cols = st.columns(4)
    for i, res in enumerate(st.session_state.v_results):
        with open(res, "rb") as f:
            cols[i % 4].download_button(f"📥 Pobierz {i+1}", f, file_name=res)
