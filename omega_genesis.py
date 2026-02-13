import streamlit as st
import os, gc, random, time, datetime, io, zipfile
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip
import moviepy.config as mpy_config

# ==============================================================================
# 1. KONFIGURACJA RDZENIA OMEGA V12.96
# ==============================================================================

class OmegaCore:
    VERSION = "V12.96 LIVE-FIX"
    TARGET_RES = (1080, 1920)
    SAFE_MARGIN = 90
    
    @staticmethod
    def setup_session():
        keys = ['v_covers', 'v_photos', 'v_music', 'v_results', 'zip_ready']
        for key in keys:
            if key not in st.session_state:
                st.session_state[key] = [] if key != 'zip_ready' else None

    @staticmethod
    def get_magick_path():
        if os.name == 'posix': return "/usr/bin/convert"
        return r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"

# ==============================================================================
# 2. SILNIK GRAFICZNY
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
    current_f_size = config['f_size']
    max_w = res[0] - (OmegaCore.SAFE_MARGIN * 2)
    
    while current_f_size > 15:
        try:
            font = ImageFont.truetype(config['font_path'], current_f_size)
        except:
            font = ImageFont.load_default()
        
        test_img = Image.new("RGBA", (1, 1))
        test_draw = ImageDraw.Draw(test_img)
        bbox = test_draw.textbbox((0, 0), text, font=font)
        if (bbox[2] - bbox[0]) <= max_w:
            break
        current_f_size -= 4

    combined = Image.new("RGBA", res, (0, 0, 0, 0))
    shd_layer = Image.new("RGBA", res, (0, 0, 0, 0))
    txt_layer = Image.new("RGBA", res, (0, 0, 0, 0))
    
    draw_txt = ImageDraw.Draw(txt_layer)
    draw_shd = ImageDraw.Draw(shd_layer)
    
    final_bbox = draw_txt.textbbox((0, 0), text, font=font)
    tw, th = final_bbox[2] - final_bbox[0], final_bbox[3] - final_bbox[1]
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
# 3. INTERFEJS I LIVE PREVIEW (FIXED)
# ==============================================================================

OmegaCore.setup_session()
st.set_page_config(page_title="Ω OMEGA V12.96", layout="wide")
mpy_config.change_settings({"IMAGEMAGICK_BINARY": OmegaCore.get_magick_path()})

with st.sidebar:
    st.title("⚙️ CONFIG")

    # 1. Najpierw pobieramy wszystkie parametry z suwaków
    f_font = st.selectbox("Czcionka", ["League Gothic Regular", "League Gothic Condensed", "Impact"])
    f_size = st.slider("Max Wielkość", 20, 500, 83)
    t_color = st.color_picker("Kolor tekstu", "#FFFFFF")
    s_width = st.slider("Obrys", 0, 20, 3)
    s_color = st.color_picker("Kolor Obrysu", "#000000")
    
    st.header("🌑 CIEŃ")
    shd_x = st.slider("Cień X", -100, 100, 15)
    shd_y = st.slider("Cień Y", -100, 100, 15)
    shd_blur = st.slider("Blur", 0, 50, 8)
    shd_alpha = st.slider("Alpha", 0, 255, 200)
    shd_color = st.color_picker("Kolor Cienia", "#000000")

    # 2. Tworzymy obiekt konfiguracji, który będzie użyty i w podglądzie, i w filmie
    cfg = {
        'font_path': get_font_path(f_font), 'f_size': f_size, 't_color': t_color,
        's_width': s_width, 's_color': s_color, 'shd_x': shd_x, 'shd_y': shd_y,
        'shd_blur': shd_blur, 'shd_alpha': shd_alpha, 'shd_color': shd_color
    }

    # 3. Wyświetlamy podgląd na górze, który TERAZ reaguje na suwaki powyżej
    st.header("👁️ LIVE PREVIEW")
    sim_bg = Image.new("RGB", OmegaCore.TARGET_RES, (15, 15, 15)) 
    draw_sim = ImageDraw.Draw(sim_bg)
    draw_sim.rectangle([0, 625, 1080, 1295], fill=(0, 255, 0)) 
    
    # Renderujemy tekst podglądu z aktualnym cfg
    t_lay = draw_text_pancerny("LIVE PREVIEW TEST", cfg)
    sim_bg.paste(t_lay, (0, 0), t_lay)
    st.image(sim_bg, caption="Podgląd reaguje na suwaki!", use_container_width=True)
    
    st.divider()
    speed = st.selectbox("Szybkość (s)", [0.1, 0.12, 0.15, 0.2], index=2)
    
    default_txts = "Most unique spreadsheet rn\nIg brands ain't safe\nPOV: You created best ig brands spreadsheet\nBest archive spreadsheet rn\nArchive fashion ain't safe\nBest ig brands spreadsheet oat.\nBest archive fashion spreadsheet rn.\nEven ig brands ain't safe\nPOV: you have best spreadsheet on tiktok\npov: you found best spreadsheet\nSwagest spreadsheet ever\nSwagest spreadsheet in 2026\nColdest spreadsheet rn.\nNo more gatekeeping this spreadsheet\nUltimate archive clothing vault\nOnly fashion sheet needed\nBest fashion sheet oat\nIG brands ain't safe\nI found the holy grail of spreadsheets\nTook me 3 months to create best spreadsheet\nI’m actually done gatekeeping this\nWhy did nobody tell me about this sheet earlier?\nHonestly, best finds i’ve ever seen\npov: you’re not gatekeeping your sources anymore\npov: your fits are about to get 10x better\npov: you found the spreadsheet everyone was looking for\nme after finding this archive sheet:\nThis spreadsheet is actually crazy\narchive pieces you actually need\nSpreadsheet just drooped"
    raw_texts = st.text_area("Baza Tekstów", default_txts, height=150)
    texts_list = [t.strip() for t in raw_texts.split('\n') if t.strip()]

# ==============================================================================
# 4. PRODUKCJA (IDENTYCZNA Z PODGLĄDEM)
# ==============================================================================

st.title(f"Ω OMEGA {OmegaCore.VERSION}")

c1, c2, c3 = st.columns(3)
with c1: u_c = st.file_uploader("Okładki", type=['png','jpg','jpeg'], accept_multiple_files=True)
with c2: u_p = st.file_uploader("Zdjęcia (Bulk)", type=['png','jpg','jpeg'], accept_multiple_files=True)
with c3: u_m = st.file_uploader("Muzyka", type=['mp3'], accept_multiple_files=True)

if st.button("🚀 URUCHOM PRODUKCJĘ MASOWĄ", use_container_width=True):
    if not u_c or not u_p:
        st.error("Wgraj okładki i zdjęcia!")
    else:
        st.session_state.v_results = []
        with st.status("🎬 Renderowanie...", expanded=True) as status:
            if not os.path.exists("temp"): os.makedirs("temp")
            for idx, cov_file in enumerate(u_c):
                target_dur = random.uniform(8.5, 9.8)
                cov_dur = speed * 3
                num_p = int((target_dur - cov_dur) / speed)
                st.write(f"🎞️ Film {idx+1}/{len(u_c)} | Czas: {target_dur:.1f}s")
                sample = random.sample(u_p, min(num_p, len(u_p)))
                clips = [ImageClip(process_image_916(cov_file)).set_duration(cov_dur)]
                clips += [ImageClip(process_image_916(p)).set_duration(speed) for p in sample]
                base = concatenate_videoclips(clips, method="chain")
                t_arr = np.array(draw_text_pancerny(random.choice(texts_list), cfg))
                txt_clip = ImageClip(t_arr).set_duration(base.duration)
                final = CompositeVideoClip([base, txt_clip], size=OmegaCore.TARGET_RES)
                if u_m:
                    m_file = random.choice(u_m)
                    tmp_m = f"temp/a_{idx}.mp3"; f_aud = open(tmp_m, "wb"); f_aud.write(m_file.getbuffer()); f_aud.close()
                    aud = AudioFileClip(tmp_m)
                    final = final.set_audio(aud.subclip(0, min(aud.duration, final.duration)))
                out_name = f"OMEGA_{idx+1}.mp4"
                final.write_videofile(out_name, fps=24, codec="libx264", audio_codec="aac", threads=4, logger=None, preset="ultrafast")
                st.session_state.v_results.append(out_name)
                final.close(); base.close(); gc.collect()
            zip_n = "OMEGA_EXPORT.zip"
            with zipfile.ZipFile(zip_n, 'w') as z:
                for f in st.session_state.v_results: z.write(f)
            st.session_state.zip_ready = zip_n
            status.update(label="✅ GOTOWE!", state="complete")

if st.session_state.zip_ready:
    st.divider()
    with open(st.session_state.zip_ready, "rb") as f:
        st.download_button("📥 POBIERZ ZIP", f, file_name=st.session_state.zip_ready, use_container_width=True)
