import streamlit as st
import os, gc, random, time, zipfile
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip

# --- 1. FUNKCJA KADROWANIA ---
def process_image_916(img_file, target_res=(1080, 1920)):
    try:
        with Image.open(img_file) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            target_ratio = target_res[0] / target_res[1]
            img_ratio = img.width / img.height
            if img_ratio > target_ratio:
                new_width = int(target_res[1] * img_ratio)
                img = img.resize((new_width, target_res[1]), Image.Resampling.LANCZOS)
                left = (new_width - target_res[0]) / 2
                img = img.crop((left, 0, left + target_res[0], target_res[1]))
            else:
                new_height = int(target_res[0] / img_ratio)
                img = img.resize((target_res[0], new_height), Image.Resampling.LANCZOS)
                top = (new_height - target_res[1]) / 2
                img = img.crop((0, top, target_res[0], top + target_res[1]))
            return np.array(img)
    except:
        return np.zeros((1920, 1080, 3), dtype="uint8")

# --- 2. SILNIK RYSOWANIA ---
def draw_text_on_canvas(text, config, res=(1080, 1920), is_preview=False):
    txt_layer = Image.new("RGBA", res, (0, 0, 0, 0))
    shd_layer = Image.new("RGBA", res, (0, 0, 0, 0))
    draw_txt = ImageDraw.Draw(txt_layer)
    draw_shd = ImageDraw.Draw(shd_layer)
    try:
        font = ImageFont.truetype(config['font_path'], config['f_size']) if config['font_path'] else ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    bbox = draw_txt.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    base_pos = ((res[0]-tw)//2, (res[1]-th)//2)
    shd_pos = (base_pos[0] + config['shd_x'], base_pos[1] + config['shd_y'])
    c_shd = config['shd_color'].lstrip('#')
    rgb_shd = tuple(int(c_shd[i:i+2], 16) for i in (0, 2, 4))
    draw_shd.text(shd_pos, text, fill=(*rgb_shd, config['shd_alpha']), font=font)
    if config['shd_blur'] > 0:
        shd_layer = shd_layer.filter(ImageFilter.GaussianBlur(config['shd_blur']))
    draw_txt.text(base_pos, text, fill=config['t_color'], font=font, stroke_width=config['s_width'], stroke_fill=config['s_color'])
    combined = Image.new("RGBA", res, (0, 0, 0, 0))
    combined.paste(shd_layer, (0,0), shd_layer)
    combined.paste(txt_layer, (0,0), txt_layer)
    if is_preview:
        bg = Image.new("RGB", res, (0, 255, 0))
        bg.paste(combined, (0,0), combined)
        return bg
    return np.array(combined)

# --- 3. INTERFEJS ---
st.set_page_config(page_title="OMEGA V12.54", layout="wide")
st.title("Ω OMEGA V12.54 - MOBILE MULTI-UPLOAD FIX")

with st.sidebar:
    st.header("⚙️ USTAWIENIA")
    v_count = st.number_input("Ile filmów?", 1, 100, 5)
    speed = st.selectbox("Szybkość", [0.1, 0.15, 0.2, 0.3], index=2)
    font_choice = st.selectbox("Czcionka", ["League Gothic Regular", "League Gothic Condensed", "Impact"])
    f_size = st.slider("Wielkość", 10, 800, 82)
    t_color = st.color_picker("Kolor tekstu", "#FFFFFF")
    s_width = st.slider("Obramowanie", 0, 30, 2)
    s_color = st.color_picker("Kolor obramowania", "#000000")
    st.subheader("🌑 CIEŃ")
    shd_x = st.slider("X", -150, 150, 2)
    shd_y = st.slider("Y", -150, 150, 19)
    shd_blur = st.slider("Blur", 0, 100, 5)
    shd_alpha = st.slider("Alpha", 0, 255, 146)
    shd_color = st.color_picker("Kolor cienia", "#000000")
    raw_texts = st.text_area("Teksty", "ig brands aint safe")
    texts_list = [t.strip() for t in raw_texts.split('\n') if t.strip()]
    font_paths = {"League Gothic Regular": "LeagueGothic-Regular.otf", "League Gothic Condensed": "LeagueGothic-CondensedRegular.otf", "Impact": "impact.ttf"}
    config_dict = {'font_path': font_paths.get(font_choice), 'f_size': f_size, 't_color': t_color, 's_width': s_width, 's_color': s_color, 'shd_x': shd_x, 'shd_y': shd_y, 'shd_blur': shd_blur, 'shd_alpha': shd_alpha, 'shd_color': shd_color}
    if texts_list:
        st.image(draw_text_on_canvas(texts_list[0], config_dict, is_preview=True), use_container_width=True)

# --- 4. WRZUCANIE PLIKÓW (ZWIĘKSZONA TOLERANCJA) ---
# Używamy key z timestampem, aby wymusić świeżość uploadera
col1, col2, col3 = st.columns(3)

with col1:
    u_cov = st.file_uploader("🖼️ OKŁADKI (Wybierz 5-20 plików)", accept_multiple_files=True, key="cov_fix")
with col2:
    u_pho = st.file_uploader("📷 ZDJĘCIA", accept_multiple_files=True, key="pho_fix")
with col3:
    u_mus = st.file_uploader("🎵 MUZYKA", accept_multiple_files=True, key="mus_fix")

# --- 5. RENDERER ---
if st.button("🚀 GENERUJ FILMY"):
    if u_cov and u_pho and texts_list:
        with st.status("🎬 Przetwarzanie wielu plików...") as status:
            sid = int(time.time())
            
            # Naprawiony zapis plików z Pinteresta
            def save_uploaded(uploaded, prefix):
                paths = []
                for i, f in enumerate(uploaded):
                    try:
                        ext = f.name.split('.')[-1] if '.' in f.name else "jpg"
                        p = f"{prefix}_{sid}_{i}.{ext}"
                        with open(p, "wb") as b:
                            b.write(f.getvalue()) # getvalue() jest stabilniejsze na mobile
                        paths.append(p)
                    except:
                        continue
                return paths

            c_paths = save_uploaded(u_cov, "c")
            p_paths = save_uploaded(u_pho, "p")
            m_paths = save_uploaded(u_mus, "m")

            if not c_paths or not p_paths:
                st.error("Błąd zapisu plików. Spróbuj wybrać mniej zdjęć naraz.")
                st.stop()

            pool_covers = list(c_paths)
            random.shuffle(pool_covers)
            final_files = []
            
            for i in range(v_count):
                if not pool_covers:
                    pool_covers = list(c_paths); random.shuffle(pool_covers)
                
                curr_cov = pool_covers.pop()
                curr_txt = random.choice(texts_list)
                needed = int(9.0 / speed)
                batch = []
                while len(batch) < needed:
                    temp = list(p_paths); random.shuffle(temp); batch.extend(temp)
                batch = batch[:needed]
                
                v_clips = [ImageClip(process_image_916(p)).set_duration(speed) for p in [curr_cov] + batch]
                base = concatenate_videoclips(v_clips, method="chain")
                txt_arr = draw_text_on_canvas(curr_txt, config_dict)
                txt_clip = ImageClip(txt_arr).set_duration(base.duration)
                final_v = CompositeVideoClip([base, txt_clip], size=(1080, 1920))
                
                if m_paths:
                    aud = AudioFileClip(random.choice(m_paths))
                    final_video_dur = final_v.duration
                    final_v = final_v.set_audio(aud.subclip(0, min(aud.duration, final_video_dur)))
                
                out = f"v_{sid}_{i}.mp4"
                final_v.write_videofile(out, fps=24, codec="libx264", audio_codec="aac", threads=1, logger=None, preset="ultrafast")
                final_files.append(out)
                final_v.close(); base.close(); gc.collect()

            zip_n = f"OMEGA_{sid}.zip"
            with zipfile.ZipFile(zip_n, 'w') as z:
                for f in final_files: z.write(f); os.remove(f)
            for p in c_paths + p_paths + m_paths:
                if os.path.exists(p): os.remove(p)
            status.update(label="✅ Gotowe!", state="complete")
            st.download_button("📥 POBIERZ ZIP", open(zip_n, "rb"), file_name=zip_n)
    else:
        st.warning("Upewnij się, że wgrałeś pliki i wpisałeś tekst.")
