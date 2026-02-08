import streamlit as st
import os, gc, random, time, zipfile
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip

# --- 1. SILNIK GRAFICZNY (FULL SCREEN 9:16 CROP) ---
def process_image_916(img_file, target_res=(1080, 1920)):
    try:
        with Image.open(img_file) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            # Obliczanie proporcji dla wypełnienia całego ekranu (Crop)
            target_ratio = target_res[0] / target_res[1]
            img_ratio = img.width / img.height
            
            if img_ratio > target_ratio:
                # Zdjęcie jest za szerokie - dopasuj do wysokości i utnij boki
                new_width = int(target_res[1] * img_ratio)
                img = img.resize((new_width, target_res[1]), Image.Resampling.LANCZOS)
                left = (new_width - target_res[0]) / 2
                img = img.crop((left, 0, left + target_res[0], target_res[1]))
            else:
                # Zdjęcie jest za wąskie - dopasuj do szerokości i utnij górę/dół
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
    return target if target and os.path.exists(target) else None

# --- 3. SILNIK RYSOWANIA ---
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
        
    draw_txt.text(base_pos, text, fill=config['t_color'], font=font, 
                  stroke_width=config['s_width'], stroke_fill=config['s_color'])
    
    combined = Image.new("RGBA", res, (0, 0, 0, 0))
    combined.paste(shd_layer, (0,0), shd_layer)
    combined.paste(txt_layer, (0,0), txt_layer)
    
    if is_preview:
        bg = Image.new("RGB", res, (0, 255, 0)) 
        bg.paste(combined, (0,0), combined)
        return bg
    return np.array(combined)

# --- 4. INTERFEJS ---
st.set_page_config(page_title="OMEGA FIXED", layout="wide")
st.title("Ω OMEGA V12.45 - FULLSCREEN & DURATION FIXED")

with st.sidebar:
    st.header("🎨 USTAWIENIA")
    v_count = st.number_input("Ilość filmów", 1, 50, 5)
    speed = st.selectbox("Szybkość (s)", [0.1, 0.15, 0.2], index=2) # Domyślnie 0.2 dla płynności
    
    f_font = st.selectbox("Czcionka", ["League Gothic Regular", "League Gothic Condensed", "Impact"])
    f_size = st.slider("Wielkość", 10, 500, 82)
    t_color = st.color_picker("Kolor Tekstu", "#FFFFFF")
    s_width = st.slider("Obramowanie", 0, 20, 2)
    s_color = st.color_picker("Kolor Obramowania", "#000000")
    
    st.divider()
    shd_x = st.slider("X", -100, 100, 2)
    shd_y = st.slider("Y", -100, 100, 19)
    shd_blur = st.slider("Blur", 0, 50, 5)
    shd_alpha = st.slider("Alpha", 0, 255, 146)
    shd_color = st.color_picker("Cień", "#000000")
    
    raw_texts = st.text_area("Teksty", "ig brands aint safe")
    texts_list = [t.strip() for t in raw_texts.split('\n') if t.strip()]

    config_dict = {
        'font_path': get_font_path(f_font), 'f_size': f_size, 't_color': t_color,
        's_width': s_width, 's_color': s_color, 'shd_x': shd_x, 'shd_y': shd_y,
        'shd_blur': shd_blur, 'shd_alpha': shd_alpha, 'shd_color': shd_color
    }

# --- 5. RENDER ---
u_cov = st.file_uploader("Okładki", accept_multiple_files=True)
u_pho = st.file_uploader("Zdjęcia", accept_multiple_files=True)
u_mus = st.file_uploader("Muzyka", accept_multiple_files=True)

if st.button("🚀 GENERUJ FILMY (8-10s)"):
    if u_cov and u_pho and texts_list:
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

            final_vids = []
            for i in range(v_count):
                txt = random.choice(texts_list)
                
                # --- LOGIKA CZASU TRWANIA ---
                # Aby uzyskać 9 sekund przy speed 0.2s, potrzebujemy 45 zdjęć.
                required_photos = int(9.0 / speed) 
                
                # Wybieramy losowe zdjęcia, a jeśli jest ich za mało - powtarzamy je
                current_batch_photos = []
                while len(current_batch_photos) < required_photos:
                    random.shuffle(p_p)
                    current_batch_photos.extend(p_p)
                current_batch_photos = current_batch_photos[:required_photos]
                
                # Składamy: 1 okładka + reszta zdjęć
                batch = [random.choice(c_p)] + current_batch_photos
                
                base = concatenate_videoclips([ImageClip(process_image_916(p)).set_duration(speed) for p in batch], method="chain")
                
                txt_arr = draw_text_on_canvas(txt, config_dict)
                txt_clip = ImageClip(txt_arr).set_duration(base.duration)
                
                final_v = CompositeVideoClip([base, txt_clip], size=(1080, 1920))
                
                if m_p:
                    aud = AudioFileClip(random.choice(m_p))
                    # Zapętlamy dźwięk jeśli jest krótszy niż film
                    if aud.duration < final_v.duration:
                        # W tym prostym modelu bierzemy tylko tyle ile jest, 
                        # ale ustawiamy muzykę na długość filmu
                        final_v = final_v.set_audio(aud.subclip(0, min(aud.duration, final_v.duration)))
                    else:
                        final_v = final_v.set_audio(aud.subclip(0, final_v.duration))
                
                out = f"v_{sid}_{i}.mp4"
                final_v.write_videofile(out, fps=24, codec="libx264", audio_codec="aac", threads=1, logger=None, preset="ultrafast")
                final_vids.append(out)
                final_v.close(); base.close(); gc.collect()

            zip_n = f"OMEGA_EXPORT_{sid}.zip"
            with zipfile.ZipFile(zip_n, 'w') as z:
                for f in final_vids: z.write(f); os.remove(f)
            for p in c_p + p_p + m_p: 
                if os.path.exists(p): os.remove(p)
            status.update(label="✅ Gotowe!", state="complete")
            st.download_button("📥 POBIERZ PACZKĘ", open(zip_n, "rb"), file_name=zip_n)
