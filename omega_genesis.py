import streamlit as st
import os, gc, random, time, zipfile
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip
import moviepy.config as mpy_config

# --- 1. KONFIGURACJA ŚRODOWISKA ---
def setup_imagemagick(path):
    if os.path.exists(path):
        mpy_config.change_settings({"IMAGEMAGICK_BINARY": path})
        return True
    return False

# --- 2. LOGIKA GRAFICZNA (Side-Touch + Pinterest Fix) ---
def process_image_916(img_file, target_res=(1080, 1920)):
    try:
        with Image.open(img_file) as img:
            # Fix dla Pinterest/WebP/PNG (wymuszone RGB)
            img = ImageOps.exif_transpose(img).convert("RGB")
            t_w, t_h = target_res
            img_w, img_h = img.size
            
            # Skalowanie do szerokości (Side-Touch)
            scale = t_w / img_w
            new_size = (t_w, int(img_h * scale))
            img_resized = img.resize(new_size, Image.Resampling.LANCZOS)
            
            canvas = Image.new("RGB", target_res, (0, 0, 0))
            y_offset = (t_h - img_resized.height) // 2
            
            # Jeśli zdjęcie za wysokie - dotnij, jeśli za niskie - wycentruj (czarne pasy góra/dół)
            if y_offset < 0:
                top_crop = abs(y_offset)
                img_resized = img_resized.crop((0, top_crop, t_w, top_crop + t_h))
                y_offset = 0
                
            canvas.paste(img_resized, (0, y_offset))
            return np.array(canvas)
    except Exception:
        return np.zeros((1920, 1080, 3), dtype="uint8")

# --- 3. CZCIONKI I TEKST ---
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

def draw_text_on_canvas(text, config, res=(1080, 1920), is_preview=False):
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

    c_shd = config['shd_color'].lstrip('#')
    rgb_shd = tuple(int(c_shd[i:i + 2], 16) for i in (0, 2, 4))
    draw_shd.text(shd_pos, text, fill=(*rgb_shd, config['shd_alpha']), font=font)

    if config['shd_blur'] > 0:
        shd_layer = shd_layer.filter(ImageFilter.GaussianBlur(config['shd_blur']))

    draw_txt.text(base_pos, text, fill=config['t_color'], font=font,
                  stroke_width=config['s_width'], stroke_fill=config['s_color'])

    combined = Image.new("RGBA", res, (0, 0, 0, 0))
    combined.paste(shd_layer, (0, 0), shd_layer)
    combined.paste(txt_layer, (0, 0), txt_layer)

    if is_preview:
        bg = Image.new("RGB", res, (34, 139, 34))
        bg.paste(combined, (0, 0), combined)
        return bg
    return np.array(combined)

# --- 4. INTERFEJS STREAMLIT ---
st.set_page_config(page_title="OMEGA V12.89", layout="wide")
st.title("Ω OMEGA V12.89 - FULL SYSTEM")

with st.sidebar:
    st.header("⚙️ SYSTEM")
    m_path = st.text_input("ImageMagick", r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe")
    setup_imagemagick(m_path)
    v_count = st.number_input("Ilość filmów", 1, 100, 5)
    speed = st.selectbox("Szybkość (s)", [0.1, 0.15, 0.2], index=1)
    
    st.divider()
    f_font = st.selectbox("Czcionka", ["League Gothic Regular", "League Gothic Condensed", "Impact"])
    f_size = st.slider("Wielkość", 10, 500, 82)
    t_color = st.color_picker("Tekst", "#FFFFFF")
    s_width = st.slider("Obramowanie", 0, 20, 2)
    s_color = st.color_picker("Kolor Obramowania", "#000000")
    
    st.divider()
    shd_x = st.slider("Cień X", -100, 100, 2); shd_y = st.slider("Cień Y", -100, 100, 19)
    shd_blur = st.slider("Cień Blur", 0, 50, 5); shd_alpha = st.slider("Cień Alpha", 0, 255, 146)
    shd_color = st.color_picker("Kolor Cienia", "#000000")
    
    st.divider()
    raw_texts = st.text_area("Teksty", "ig brands aint safe")
    texts_list = [t.strip() for t in raw_texts.split('\n') if t.strip()]
    
    config_dict = {
        'font_path': get_font_path(f_font), 'f_size': f_size, 't_color': t_color,
        's_width': s_width, 's_color': s_color, 'shd_x': shd_x, 'shd_y': shd_y,
        'shd_blur': shd_blur, 'shd_alpha': shd_alpha, 'shd_color': shd_color
    }

    # POWRÓT PREVIEW W SIDEBARZE
    if texts_list:
        st.subheader("👁️ PODGLĄD")
        p_img = draw_text_on_canvas(texts_list[0], config_dict, is_preview=True)
        st.image(p_img.resize((300, 533)))

# --- 5. WRZUCANIE PLIKÓW (Tylko zdjęcia, brak video) ---
st.info("💡 Wskazówka: Jeśli połączenie przerywa, wrzucaj zdjęcia partiami (np. po 10 sztuk).")
c1, c2, c3 = st.columns(3)
with c1: u_cov = st.file_uploader("Okładki", type=['png','jpg','jpeg','webp'], accept_multiple_files=True)
with c2: u_pho = st.file_uploader("Zdjęcia", type=['png','jpg','jpeg','webp'], accept_multiple_files=True)
with c3: u_mus = st.file_uploader("Muzyka", type=['mp3','wav'], accept_multiple_files=True)

# --- 6. PROCES GENEROWANIA ---
if st.button("🚀 URUCHOM"):
    if u_cov and u_pho and texts_list:
        if len(u_cov) < v_count:
            st.error(f"⚠️ Masz tylko {len(u_cov)} okładek. Potrzebujesz {v_count}!")
        else:
            with st.status("🎬 Generowanie...") as status:
                sid = int(time.time())
                
                # Zapisywanie bezpieczne
                def save_safe(files, prefix):
                    paths = []
                    for i, f in enumerate(files):
                        p = f"t_{prefix}_{sid}_{i}.jpg"
                        with open(p, "wb") as b: b.write(f.getvalue())
                        paths.append(p)
                    return paths

                c_paths = save_safe(u_cov, "c")
                p_paths = save_safe(u_pho, "p")
                m_paths = [f"m_{sid}_{i}.mp3" for i in range(len(u_mus))]
                for p, f in zip(m_paths, u_mus):
                    with open(p, "wb") as b: b.write(f.getvalue())

                # Unikalność
                avail_covers = list(c_paths)
                random.shuffle(avail_covers)
                master_photo_pool = list(p_paths)

                final_vids = []
                for i in range(v_count):
                    st.write(f"Tworzenie filmu {i+1}...")
                    curr_cover = avail_covers.pop()
                    txt = random.choice(texts_list)
                    
                    # Losowy czas 8-10s
                    target_dur = random.uniform(8.0, 10.0)
                    num_p = int(target_dur / speed)
                    
                    # Unikalne zdjęcia wewnątrz filmu
                    if len(master_photo_pool) < num_p:
                        master_photo_pool = list(p_paths)
                    random.shuffle(master_photo_pool)
                    batch = [master_photo_pool.pop() for _ in range(num_p)]
                    
                    full_list = [curr_cover] + batch
                    clips = [ImageClip(process_image_916(p)).set_duration(speed) for p in full_list]
                    base = concatenate_videoclips(clips, method="chain")
                    
                    txt_arr = draw_text_on_canvas(txt, config_dict)
                    txt_clip = ImageClip(txt_arr).set_duration(base.duration)
                    
                    final_v = CompositeVideoClip([base, txt_clip], size=(1080, 1920))

                    if m_paths:
                        aud = AudioFileClip(random.choice(m_paths))
                        final_v = final_v.set_audio(aud.subclip(0, min(aud.duration, final_v.duration)))

                    out_n = f"OMEGA_{sid}_{i}.mp4"
                    final_v.write_videofile(out_n, fps=24, codec="libx264", audio_codec="aac", threads=1, logger=None, preset="ultrafast")
                    final_vids.append(out_n)
                    final_v.close(); base.close(); gc.collect()

                z_name = f"OMEGA_EXPORT_{sid}.zip"
                with zipfile.ZipFile(z_name, 'w') as z:
                    for f in final_vids: z.write(f); os.remove(f)
                for p in c_paths + p_paths + m_paths:
                    if os.path.exists(p): os.remove(p)
                
                status.update(label="✅ Gotowe!", state="complete")
                st.download_button("📥 POBIERZ PACZKĘ", open(z_name, "rb"), file_name=z_name)
