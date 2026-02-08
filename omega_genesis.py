import streamlit as st
import os
import gc
import random
import time
import zipfile
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

# --- 2. SILNIK RYSOWANIA TEKSTU ---
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
    
    # Cień
    shd_pos = (base_pos[0] + config['shd_x'], base_pos[1] + config['shd_y'])
    c_shd = config['shd_color'].lstrip('#')
    rgb_shd = tuple(int(c_shd[i:i+2], 16) for i in (0, 2, 4))
    draw_shd.text(shd_pos, text, fill=(*rgb_shd, config['shd_alpha']), font=font)
    if config['shd_blur'] > 0:
        shd_layer = shd_layer.filter(ImageFilter.GaussianBlur(config['shd_blur']))
    
    # Tekst główny
    draw_txt.text(base_pos, text, fill=config['t_color'], font=font, stroke_width=config['s_width'], stroke_fill=config['s_color'])
    
    combined = Image.new("RGBA", res, (0, 0, 0, 0))
    combined.paste(shd_layer, (0,0), shd_layer)
    combined.paste(txt_layer, (0,0), txt_layer)
    if is_preview:
        bg = Image.new("RGB", res, (0, 255, 0))
        bg.paste(combined, (0,0), combined)
        return bg
    return np.array(combined)

# --- 3. INTERFEJS UŻYTKOWNIKA ---
st.set_page_config(page_title="OMEGA V12.63", layout="wide")
st.title("Ω OMEGA V12.63 - FINAL FIX")

with st.sidebar:
    st.header("⚙️ USTAWIENIA FILMU")
    v_count = st.number_input("Ilość filmów", 1, 100, 5)
    speed = st.selectbox("Szybkość zmiany zdjęć (s)", [0.1, 0.15, 0.2, 0.3], index=2)
    
    st.divider()
    f_font = st.selectbox("Czcionka", ["League Gothic Regular", "League Gothic Condensed", "Impact"])
    f_size = st.slider("Wielkość tekstu", 10, 800, 82)
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

    font_paths = {"League Gothic Regular": "LeagueGothic-Regular.otf", "League Gothic Condensed": "LeagueGothic-CondensedRegular.otf", "Impact": "impact.ttf"}
    config_dict = {'font_path': font_paths.get(f_font), 'f_size': f_size, 't_color': t_color, 's_width': s_width, 's_color': s_color, 'shd_x': shd_x, 'shd_y': shd_y, 'shd_blur': shd_blur, 'shd_alpha': shd_alpha, 'shd_color': shd_color}
    
    if texts_list:
        st.write("🖼️ Podgląd:")
        st.image(draw_text_on_canvas(texts_list[0], config_dict, is_preview=True), use_container_width=True)

# --- 4. WRZUCANIE PLIKÓW ---
col1, col2, col3 = st.columns(3)
with col1: u_cov = st.file_uploader("🖼️ OKŁADKI (PNG/JPG)", accept_multiple_files=True)
with col2: u_pho = st.file_uploader("📷 ZDJĘCIA", accept_multiple_files=True)
with col3: u_mus = st.file_uploader("🎵 MUZYKA", accept_multiple_files=True)

# --- 5. RENDERER ---
if st.button("🚀 GENERUJ FILMY"):
    if u_cov and u_pho and texts_list:
        with st.status("🎬 Przetwarzanie...") as status:
            sid = int(time.time())
            
            def save_files(uploaded, prefix):
                paths = []
                for i, f in enumerate(uploaded):
                    p = f"{prefix}_{sid}_{i}.jpg"
                    with open(p, "wb") as b:
                        b.write(f.getbuffer())
                    paths.append(p)
                return paths

            c_p = save_files(u_cov, "c")
            p_p = save_files(u_pho, "p")
            m_p = save_files(u_mus, "m")

            # Logika unikalnych okładek
            avail_covers = list(c_p)
            random.shuffle(avail_covers)
            final_vids = []

            for i in range(v_count):
                # Jeśli okładki się skończyły, odśwież pulę
                if not avail_covers:
                    avail_covers = list(c_p)
                    random.shuffle(avail_covers)
                
                chosen_cov = avail_covers.pop() # Pobiera unikalną okładkę
                txt = random.choice(texts_list)
                
                # LOSOWANIE CZASU 8.0 - 10.0 sekundy
                target_dur = random.uniform(8.0, 10.0)
                req_photos = int(target_dur / speed)
                
                p_pool = []
                while len(p_pool) < req_photos:
                    temp = list(p_p)
                    random.shuffle(temp)
                    p_pool.extend(temp)
                p_pool = p_pool[:req_photos]
                
                # Budowa klipu
                clips = [ImageClip(process_image_916(p)).set_duration(speed) for p in [chosen_cov] + p_pool]
                base = concatenate_videoclips(clips, method="chain")
                
                t_arr = draw_text_on_canvas(txt, config_dict)
                t_clip = ImageClip(t_arr).set_duration(base.duration)
                final_v = CompositeVideoClip([base, t_clip], size=(1080, 1920))
                
                if m_p:
                    aud = AudioFileClip(random.choice(m_p))
                    final_v = final_v.set_audio(aud.subclip(0, min(aud.duration, final_v.duration)))
                
                out_n = f"v_{sid}_{i}.mp4"
                final_v.write_videofile(out_n, fps=24, codec="libx264", audio_codec="aac", threads=1, logger=None, preset="ultrafast")
                final_vids.append(out_n)
                
                final_v.close()
                base.close()
                gc.collect()

            zip_n = f"OMEGA_{sid}.zip"
            with zipfile.ZipFile(zip_n, 'w') as z:
                for f in final_vids:
                    z.write(f)
                    os.remove(f)
            
            for p in c_p + p_p + m_p:
                if os.path.exists(p):
                    os.remove(p)
                
            status.update(label="✅ Gotowe!", state="complete")
            st.download_button("📥 POBIERZ PACZKĘ ZIP", open(zip_n, "rb"), file_name=zip_n)
    else:
        st.error("Wgraj okładki, zdjęcia i podaj teksty!")
