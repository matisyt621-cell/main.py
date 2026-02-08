import streamlit as st
import os, gc, random, time, zipfile
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip

# --- 1. SILNIK GRAFICZNY: FULL SCREEN CROP ---
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

# --- 2. SYSTEM CZCIONEK ---
def get_font_path(font_selection):
    font_files = {
        "League Gothic Regular": "LeagueGothic-Regular.otf",
        "League Gothic Condensed": "LeagueGothic-CondensedRegular.otf",
        "Impact": "impact.ttf"
    }
    target = font_files.get(font_selection)
    if target and os.path.exists(target):
        return target
    return None

# --- 3. SILNIK RYSOWANIA Z PODGLĄDEM ---
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

# --- 4. INTERFEJS UŻYTKOWNIKA ---
st.set_page_config(page_title="OMEGA V12.49", layout="wide")
st.title("Ω OMEGA V12.49 - FULL & STABLE")

with st.sidebar:
    st.header("🎨 KONFIGURACJA")
    v_count = st.number_input("Ilość filmów", 1, 100, 5)
    speed = st.selectbox("Szybkość (s)", [0.1, 0.15, 0.2, 0.3], index=2)
    
    f_font = st.selectbox("Czcionka", ["League Gothic Regular", "League Gothic Condensed", "Impact"])
    f_size = st.slider("Wielkość", 10, 800, 82)
    t_color = st.color_picker("Tekst", "#FFFFFF")
    s_width = st.slider("Obramowanie", 0, 30, 2)
    s_color = st.color_picker("Kolor Obramowania", "#000000")
    
    st.subheader("🌑 Cień")
    shd_x = st.slider("X", -150, 150, 2)
    shd_y = st.slider("Y", -150, 150, 19)
    shd_blur = st.slider("Blur", 0, 100, 5)
    shd_alpha = st.slider("Alpha", 0, 255, 146)
    shd_color = st.color_picker("Kolor cienia", "#000000")
    
    raw_texts = st.text_area("Teksty", "ig brands aint safe")
    texts_list = [t.strip() for t in raw_texts.split('\n') if t.strip()]
    
    config_dict = {
        'font_path': get_font_path(f_font),
        'f_size': f_size,
        't_color': t_color,
        's_width': s_width,
        's_color': s_color,
        'shd_x': shd_x,
        'shd_y': shd_y,
        'shd_blur': shd_blur,
        'shd_alpha': shd_alpha,
        'shd_color': shd_color
    }
    
    if texts_list:
        st.write("👀 Podgląd:")
        pre_img = draw_text_on_canvas(texts_list[0], config_dict, is_preview=True)
        st.image(pre_img, use_container_width=True)

# --- 5. RENDERER Z UNIKALNYMI OKŁADKAMI ---
u_cov = st.file_uploader("Okładki", accept_multiple_files=True)
u_pho = st.file_uploader("Zdjęcia", accept_multiple_files=True)
u_mus = st.file_uploader("Muzyka", accept_multiple_files=True)

if st.button("🚀 GENERUJ FILMY"):
    if u_cov and u_pho and texts_list:
        with st.status("🎬 Przetwarzanie...") as status:
            sid = int(time.time())
            
            # Bezpieczne zapisywanie plików (rozbite linie)
            c_p = []
            for i, f in enumerate(u_cov):
                path = f"c_{sid}_{i}.jpg"
                with open(path, "wb") as b:
                    b.write(f.getbuffer())
                c_p.append(path)
                
            p_p = []
            for i, f in enumerate(u_pho):
                path = f"p_{sid}_{i}.jpg"
                with open(path, "wb") as b:
                    b.write(f.getbuffer())
                p_p.append(path)
                
            m_p = []
            for i, f in enumerate(u_mus):
                path = f"m_{sid}_{i}.mp3"
                with open(path, "wb") as b:
                    b.write(f.getbuffer())
                m_p.append(path)

            # Logika unikalnych okładek
            available_covers = list(c_p)
            random.shuffle(available_covers)
            
            final_vids = []
            for i in range(v_count):
                if not available_covers:
                    available_covers = list(c_p)
                    random.shuffle(available_covers)
                
                chosen_cover = available_covers.pop()
                txt = random.choice(texts_list)
                
                # Długość 9 sekund
                req_photos = int(9.0 / speed)
                batch_p = []
                while len(batch_p) < req_photos:
                    pool = list(p_p)
                    random.shuffle(pool)
                    batch_p.extend(pool)
                batch_p = batch_p[:req_photos]
                
                # Budowa klipu
                clips = []
                # Najpierw okładka
                clips.append(ImageClip(process_image_916(chosen_cover)).set_duration(speed))
                # Potem zdjęcia
                for p in batch_p:
                    clips.append(ImageClip(process_image_916(p)).set_duration(speed))
                
                base = concatenate_videoclips(clips, method="chain")
                
                txt_arr = draw_text_on_canvas(txt, config_dict)
                txt_clip = ImageClip(txt_arr).set_duration(base.duration)
                final_v = CompositeVideoClip([base, txt_clip], size=(1080, 1920))
                
                if m_p:
                    aud = AudioFileClip(random.choice(m_p))
                    final_v = final_v.set_audio(aud.subclip(0, min(aud.duration, final_v.duration)))
                
                out_name = f"v_{sid}_{i}.mp4"
                final_v.write_videofile(out_name, fps=24, codec="libx264", audio_codec="aac", threads=1, logger=None, preset="ultrafast")
                final_vids.append(out_name)
                
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
            st.download_button("📥 POBIERZ PACZKĘ", open(zip_n, "rb"), file_name=zip_n)
