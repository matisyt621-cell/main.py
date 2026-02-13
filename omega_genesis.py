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
    VERSION = "V12.89 UNLIMITED + SPREADSHEET EDITION"
    TARGET_RES = (1080, 1920)
    
    @staticmethod
    def setup_session():
        keys = ['v_covers', 'v_photos', 'v_music', 'v_results']
        for key in keys:
            if key not in st.session_state:
                st.session_state[key] = []

    @staticmethod
    def get_magick_path():
        if os.name == 'posix': return "/usr/bin/convert"
        return r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"

# ==============================================================================
# 2. SILNIK GRAFICZNY I PANNCERNY RENDER TEKSTU
# ==============================================================================

def get_font_path(font_selection):
    font_files = {
        "League Gothic Regular": "LeagueGothic-Regular.otf",
        "League Gothic Condensed": "LeagueGothic-CondensedRegular.otf",
        "Impact": "impact.ttf"
    }
    target = font_files.get(font_selection)
    if target and os.path.exists(target): return os.path.abspath(target)
    return "arial.ttf"

def process_image_916(file_obj, target_res=OmegaCore.TARGET_RES):
    try:
        file_bytes = file_obj.getvalue()
        with Image.open(io.BytesIO(file_bytes)) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            t_w, t_h = target_res
            img_w, img_h = img.size
            scale = t_w / img_w
            new_size = (t_w, int(img_h * scale))
            img_resized = img.resize(new_size, Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", target_res, (0, 0, 0))
            y_off = (t_h - img_resized.height) // 2
            if y_off < 0:
                img_resized = img_resized.crop((0, abs(y_off), t_w, abs(y_off) + t_h))
                y_off = 0
            canvas.paste(img_resized, (0, y_off))
            return np.array(canvas)
    except:
        return np.zeros((target_res[1], target_res[0], 3), dtype="uint8")

def draw_text_pancerny(text, config, res=OmegaCore.TARGET_RES):
    combined = Image.new("RGBA", res, (0, 0, 0, 0))
    shd_layer = Image.new("RGBA", res, (0, 0, 0, 0))
    txt_layer = Image.new("RGBA", res, (0, 0, 0, 0))
    
    try:
        font = ImageFont.truetype(config['font_path'], config['f_size'])
    except:
        font = ImageFont.load_default()

    draw_txt = ImageDraw.Draw(txt_layer)
    draw_shd = ImageDraw.Draw(shd_layer)
    bbox = draw_txt.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pos = ((res[0] - tw) // 2, (res[1] - th) // 2)

    c_shd = config['shd_color'].lstrip('#')
    rgb_shd = tuple(int(c_shd[i:i+2], 16) for i in (0, 2, 4))
    shd_pos = (pos[0] + config['shd_x'], pos[1] + config['shd_y'])
    draw_shd.text(shd_pos, text, fill=(*rgb_shd, config['shd_alpha']), font=font)
    if config['shd_blur'] > 0:
        shd_layer = shd_layer.filter(ImageFilter.GaussianBlur(config['shd_blur']))

    draw_txt.text(pos, text, fill=config['t_color'], font=font,
                  stroke_width=config['s_width'], stroke_fill=config['s_color'])

    combined = Image.alpha_composite(combined, shd_layer)
    combined = Image.alpha_composite(combined, txt_layer)
    return combined

# ==============================================================================
# 3. INTERFEJS I KONFIGURACJA
# ==============================================================================

OmegaCore.setup_session()
st.set_page_config(page_title="Ω OMEGA UNLIMITED", layout="wide")
mpy_config.change_settings({"IMAGEMAGICK_BINARY": OmegaCore.get_magick_path()})

with st.sidebar:
    st.title("⚙️ CONFIGURATION")
    speed = st.selectbox("Szybkość przejść (s)", [0.1, 0.15, 0.2, 0.25], index=1)
    
    st.divider()
    st.header("🎨 TYPOGRAFIA")
    f_font = st.selectbox("Czcionka", ["League Gothic Regular", "League Gothic Condensed", "Impact"])
    # ZMIANA: Startowa wielkość ustawiona na 83
    f_size = st.slider("Wielkość", 20, 500, 83)
    t_color = st.color_picker("Kolor tekstu", "#FFFFFF")
    s_width = st.slider("Obramowanie", 0, 20, 3)
    s_color = st.color_picker("Kolor Obrysu", "#000000")
    
    st.header("🌑 CIEŃ")
    shd_x = st.slider("Cień X", -100, 100, 15)
    shd_y = st.slider("Cień Y", -100, 100, 15)
    shd_blur = st.slider("Cień Blur", 0, 50, 8)
    shd_alpha = st.slider("Cień Alpha", 0, 255, 200)
    shd_color = st.color_picker("Kolor Cienia", "#000000")
    
    st.divider()
    # ZMIANA: Nowa lista tekstów
    default_texts = (
        "Most unique spreadsheet rn\n"
        "Ig brands ain't safe\n"
        "POV: You created best ig brands spreadsheet\n"
        "Best archive spreadsheet rn\n"
        "Archive fashion ain't safe\n"
        "Best ig brands spreadsheet oat.\n"
        "Best archive fashion spreadsheet rn.\n"
        "Even ig brands ain't safe\n"
        "POV: you have best spreadsheet on tiktok\n"
        "pov: you found best spreadsheet\n"
        "Swagest spreadsheet ever\n"
        "Swagest spreadsheet in 2026\n"
        "Coldest spreadsheet rn.\n"
        "No more gatekeeping this spreadsheet\n"
        "Ultimate archive clothing vault\n"
        "Only fashion sheet needed\n"
        "Best fashion sheet oat\n"
        "IG brands ain't safe\n"
        "I found the holy grail of spreadsheets\n"
        "Took me 3 months to create best spreadsheet\n"
        "I’m actually done gatekeeping this\n"
        "Why did nobody tell me about this sheet earlier?\n"
        "Honestly, best finds i’ve ever seen\n"
        "pov: you’re not gatekeeping your sources anymore\n"
        "pov: your fits are about to get 10x better\n"
        "pov: you found the spreadsheet everyone was looking for\n"
        "me after finding this archive sheet:\n"
        "This spreadsheet is actually crazy\n"
        "archive pieces you actually need\n"
        "Spreadsheet just drooped"
    )
    raw_texts = st.text_area("Baza Tekstów", default_texts, height=300)
    texts_list = [t.strip() for t in raw_texts.split('\n') if t.strip()]
    
    cfg = {
        'font_path': get_font_path(f_font), 'f_size': f_size, 't_color': t_color,
        's_width': s_width, 's_color': s_color, 'shd_x': shd_x, 'shd_y': shd_y,
        'shd_blur': shd_blur, 'shd_alpha': shd_alpha, 'shd_color': shd_color
    }

    st.divider()
    st.header("👁️ LIVE PREVIEW")
    if texts_list:
        p_bg = Image.new("RGB", OmegaCore.TARGET_RES, (0, 255, 0))
        t_lay = draw_text_pancerny(texts_list[0], cfg)
        p_bg.paste(t_lay, (0, 0), t_lay)
        st.image(p_bg, caption="Kontrast: Green Screen", use_container_width=True)

# ==============================================================================
# 4. SKARBIEC I MASOWA PRODUKCJA
# ==============================================================================

st.title(f"Ω OMEGA {OmegaCore.VERSION}")
st.info("🚀 Tryb Unlimited Aktywny. Twoja nowa baza tekstów została załadowana.")

c1, c2, c3 = st.columns(3)
with c1:
    u_c = st.file_uploader("Okładki", type=['png','jpg','jpeg'], accept_multiple_files=True)
    if u_c: st.session_state.v_covers = u_c
with c2:
    u_p = st.file_uploader("Zdjęcia (Bulk)", type=['png','jpg','jpeg'], accept_multiple_files=True)
    if u_p: st.session_state.v_photos = u_p
with c3:
    u_m = st.file_uploader("Muzyka (MP3)", type=['mp3'], accept_multiple_files=True)
    if u_m: st.session_state.v_music = u_m

if st.button("🔥 URUCHOM SILNIK OMEGA", use_container_width=True):
    if not st.session_state.v_covers or not st.session_state.v_photos:
        st.error("Skarbiec jest pusty!")
    else:
        st.session_state.v_results = []
        with st.status("🎬 Renderowanie...", expanded=True) as status:
            if not os.path.exists("temp"): os.makedirs("temp")
            
            for idx, cov_file in enumerate(st.session_state.v_covers):
                st.write(f"🎞️ Film {idx+1}/{len(st.session_state.v_covers)}...")
                sample = random.sample(st.session_state.v_photos, min(45, len(st.session_state.v_photos)))
                clips = [ImageClip(process_image_916(cov_file)).set_duration(speed*3)]
                clips += [ImageClip(process_image_916(p)).set_duration(speed) for p in sample]
                base = concatenate_videoclips(clips, method="chain")
                t_arr = np.array(draw_text_pancerny(random.choice(texts_list) if texts_list else "OMEGA", cfg))
                txt_clip = ImageClip(t_arr).set_duration(base.duration)
                final = CompositeVideoClip([base, txt_clip], size=OmegaCore.TARGET_RES)
                
                if st.session_state.v_music:
                    m_file = random.choice(st.session_state.v_music)
                    tmp_m = f"temp/aud_{idx}.mp3"
                    with open(tmp_m, "wb") as f: f.write(m_file.getbuffer())
                    aud = AudioFileClip(tmp_m)
                    final = final.set_audio(aud.subclip(0, min(aud.duration, final.duration)))

                out_name = f"OMEGA_{idx+1}.mp4"
                final.write_videofile(out_name, fps=24, codec="libx264", audio_codec="aac", threads=4, logger=None, preset="ultrafast")
                st.session_state.v_results.append(out_name)
                final.close(); base.close(); gc.collect()
            
            status.update(label="✅ GOTOWE!", state="complete")

if st.session_state.v_results:
    st.divider()
    st.header("📥 POBIERALNIA")
    cols = st.columns(4)
    for i, vid in enumerate(st.session_state.v_results):
        if os.path.exists(vid):
            with open(vid, "rb") as f:
                cols[i % 4].download_button(f"🎥 Film {i+1}", f, file_name=vid)
