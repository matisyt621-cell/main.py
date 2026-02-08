import streamlit as st
import os, gc, random, time, zipfile
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip
import moviepy.config as mpy_config

# --- 1. KONFIGURACJA ---
def setup_imagemagick(path):
    if os.path.exists(path):
        mpy_config.change_settings({"IMAGEMAGICK_BINARY": path})
        return True
    return False

# --- 2. INTELIGENTNE SKALOWANIE (Bez deformacji, dotyka ramek) ---
def process_image_916(img_file, target_res=(1080, 1920)):
    try:
        with Image.open(img_file) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            
            t_w, t_h = target_res
            img_w, img_h = img.size
            
            # Obliczamy skalę potrzebną do wypełnienia szerokości i wysokości
            scale_w = t_w / img_w
            scale_h = t_h / img_h
            
            # Wybieramy większą skalę, aby zdjęcie "dotknęło" wszystkich ramek (Fill)
            scale = max(scale_w, scale_h)
            
            new_size = (int(img_w * scale), int(img_h * scale))
            img_resized = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Wycinamy środek, aby idealnie pasował do 1080x1920
            left = (img_resized.width - t_w) / 2
            top = (img_resized.height - t_h) / 2
            right = left + t_w
            bottom = top + t_h
            
            img_final = img_resized.crop((left, top, right, bottom))
            
            return np.array(img_final)
    except Exception:
        return np.zeros((1920, 1080, 3), dtype="uint8")

# --- 3. SYSTEM CZCIONEK ---
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

# --- 4. RYSOWANIE TEKSTU ---
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
        bg = Image.new("RGB", res, (0, 255, 0))
        bg.paste(combined, (0, 0), combined)
        return bg
    return np.array(combined)

# --- 5. INTERFEJS ---
st.set_page_config(page_title="OMEGA V12.84", layout="wide")
st.title("Ω OMEGA V12.84 - AUTO FILL FRAME")

with st.sidebar:
    st.header("⚙️ SYSTEM")
    m_path = st.text_input("ImageMagick", r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe")
    setup_imagemagick(m_path)
    v_count = st.number_input("Ilość filmów", 1, 100, 5)
    speed = st.selectbox("Szybkość zdjęcia (s)", [0.1, 0.15, 0.2], index=1)

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

c1, c2, c3 = st.columns(3)
with c1: u_cov = st.file_uploader("Okładki", accept_multiple_files=True)
with c2: u_pho = st.file_uploader("Zdjęcia", accept_multiple_files=True)
with c3: u_mus = st.file_uploader("Muzyka", accept_multiple_files=True)

if st.button("🚀 GENERUJ"):
    if u_cov and u_pho and texts_list:
        if len(u_cov) < v_count:
            st.error(f"⚠️ Potrzebujesz {v_count} okładek dla unikalności!")
        else:
            with st.status("🎬 Renderowanie...") as status:
                sid = int(time.time())
                c_p = [f"c_{sid}_{i}.jpg" for i in range(len(u_cov))]
                for p, f in zip(c_p, u_cov):
                    with open(p, "wb") as b: b.write(f.getbuffer())
                
                p_p = [f"p_{sid}_{i}.jpg" for i in range(len(u_pho))]
                for p, f in zip(p_p, u_pho):
                    with open(p, "wb") as b: b.write(f.getbuffer())

                m_p = [f"m_{sid}_{i}.mp3" for i in range(len(u_mus))] if u_mus else []
                for p, f in zip(m_p, u_mus):
                    with open(p, "wb") as b: b.write(f.getbuffer())

                available_covers = list(c_p)
                random.shuffle(available_covers)
                
                final_vids = []
                for i in range(v_count):
                    current_cover = available_covers.pop()
                    txt = random.choice(texts_list)
                    
                    target_duration = random.uniform(8.0, 10.0)
                    num_photos = int(target_duration / speed)
                    
                    batch_photos = [random.choice(p_p) for _ in range(num_photos)]
                    full_batch = [current_cover] + batch_photos
                    
                    base = concatenate_videoclips([ImageClip(process_image_916(p)).set_duration(speed) for p in full_batch], method="chain")

                    txt_arr = draw_text_on_canvas(txt, config_dict)
                    txt_clip = ImageClip(txt_arr).set_duration(base.duration)
                    final_video = CompositeVideoClip([base, txt_clip], size=(1080, 1920))

                    if m_p:
                        audio_clip = AudioFileClip(random.choice(m_p))
                        final_video = final_video.set_audio(audio_clip.subclip(0, min(audio_clip.duration, final_video.duration)))

                    out_name = f"final_{sid}_{i}.mp4"
                    final_video.write_videofile(out_name, fps=24, codec="libx264", audio_codec="aac", threads=1, logger=None, preset="ultrafast")
                    final_vids.append(out_name)
                    final_video.close(); base.close(); gc.collect()

                zip_final = f"OMEGA_{sid}.zip"
                with zipfile.ZipFile(zip_final, 'w') as z:
                    for f in final_vids: z.write(f); os.remove(f)
                for p in c_p + p_p + m_p:
                    if os.path.exists(p): os.remove(p)

                status.update(label="✅ Gotowe!", state="complete")
                st.download_button("📥 POBIERZ PACZKĘ", open(zip_final, "rb"), file_name=zip_final)
