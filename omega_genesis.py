import streamlit as st
import os, gc, random, time, zipfile
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip

# --- 1. SILNIK GRAFICZNY ---
def process_image_916(img_file, target_res=(1080, 1920)):
    try:
        with Image.open(img_file) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            t_ratio = target_res[0] / target_res[1]
            i_ratio = img.width / img.height
            if i_ratio > t_ratio:
                nw = int(target_res[1] * i_ratio)
                img = img.resize((nw, target_res[1]), Image.Resampling.LANCZOS)
                left = (nw - target_res[0]) / 2
                img = img.crop((left, 0, left + target_res[0], target_res[1]))
            else:
                nh = int(target_res[0] / i_ratio)
                img = img.resize((target_res[0], nh), Image.Resampling.LANCZOS)
                top = (nh - target_res[1]) / 2
                img = img.crop((0, top, target_res[0], top + target_res[1]))
            return np.array(img)
    except Exception:
        return np.zeros((1920, 1080, 3), dtype="uint8")

# --- 2. SILNIK TEKSTU ---
def draw_text_on_canvas(text, config, res=(1080, 1920), is_preview=False):
    txt_l = Image.new("RGBA", res, (0, 0, 0, 0))
    shd_l = Image.new("RGBA", res, (0, 0, 0, 0))
    d_t = ImageDraw.Draw(txt_l)
    d_s = ImageDraw.Draw(shd_l)
    try:
        font = ImageFont.truetype(config['font_path'], config['f_size'])
    except:
        font = ImageFont.load_default()
    
    bbox = d_t.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    pos = ((res[0]-tw)//2, (res[1]-th)//2)
    s_pos = (pos[0] + config['shd_x'], pos[1] + config['shd_y'])
    
    c_s = config['shd_color'].lstrip('#')
    rgb_s = tuple(int(c_s[i:i+2], 16) for i in (0, 2, 4))
    d_s.text(s_pos, text, fill=(*rgb_s, config['shd_alpha']), font=font)
    if config['shd_blur'] > 0:
        shd_l = shd_l.filter(ImageFilter.GaussianBlur(config['shd_blur']))
    
    d_t.text(pos, text, fill=config['t_color'], font=font, stroke_width=config['s_width'], stroke_fill=config['s_color'])
    combined = Image.new("RGBA", res, (0, 0, 0, 0))
    combined.paste(shd_l, (0,0), shd_l)
    combined.paste(txt_l, (0,0), txt_l)
    return np.array(combined.convert("RGB") if is_preview else combined)

# --- 3. INTERFEJS ---
st.set_page_config(page_title="OMEGA V12.64", layout="wide")
st.title("Ω OMEGA V12.64 - OPTIMUS")

with st.sidebar:
    st.header("⚙️ OPCJE")
    v_count = st.number_input("Ile filmów?", 1, 50, 5) # Zmniejszyłem max do 50 dla stabilności
    speed = st.selectbox("Szybkość (s)", [0.1, 0.15, 0.2, 0.3], index=2)
    f_font = st.selectbox("Czcionka", ["League Gothic Regular", "Impact"])
    f_size = st.slider("Wielkość", 50, 500, 82)
    t_color = st.color_picker("Tekst", "#FFFFFF")
    s_width = st.slider("Stroke", 0, 20, 2)
    s_color = st.color_picker("Stroke Kolor", "#000000")
    st.subheader("🌑 CIEŃ")
    shd_x = st.slider("X", -100, 100, 2); shd_y = st.slider("Y", -100, 100, 15)
    shd_blur = st.slider("Blur", 0, 50, 5); shd_alpha = st.slider("Alpha", 0, 255, 150)
    shd_color = st.color_picker("Cień Kolor", "#000000")
    raw_texts = st.text_area("Teksty", "example text")
    texts_list = [t.strip() for t in raw_texts.split('\n') if t.strip()]

    f_paths = {"League Gothic Regular": "LeagueGothic-Regular.otf", "Impact": "impact.ttf"}
    conf = {'font_path': f_paths.get(f_font), 'f_size': f_size, 't_color': t_color, 's_width': s_width, 's_color': s_color, 'shd_x': shd_x, 'shd_y': shd_y, 'shd_blur': shd_blur, 'shd_alpha': shd_alpha, 'shd_color': shd_color}

# --- 4. PLIKI ---
c1, c2, c3 = st.columns(3)
with c1: u_cov = st.file_uploader("OKŁADKI", accept_multiple_files=True)
with c2: u_pho = st.file_uploader("ZDJĘCIA", accept_multiple_files=True)
with c3: u_mus = st.file_uploader("MUZYKA", accept_multiple_files=True)

# --- 5. RENDERER ---
if st.button("🚀 START"):
    if u_cov and u_pho and texts_list:
        status = st.empty()
        sid = int(time.time())
        
        def save_tmp(upl, pref):
            ps = []
            for i, f in enumerate(upl):
                p = f"tmp_{sid}_{pref}_{i}.jpg"
                with open(p, "wb") as b: b.write(f.getbuffer())
                ps.append(p)
            return ps

        c_p = save_tmp(u_cov, "c"); p_p = save_tmp(u_pho, "p"); m_p = save_tmp(u_mus, "m")
        a_covs = list(c_p); random.shuffle(a_covs)
        vids = []

        try:
            for i in range(v_count):
                status.write(f"⏳ Renderowanie filmu {i+1}/{v_count}...")
                if not a_covs: a_covs = list(c_p); random.shuffle(a_covs)
                
                c_img = a_covs.pop()
                dur = random.uniform(8.0, 10.0)
                n_p = int(dur / speed)
                
                pool = []
                while len(pool) < n_p:
                    batch = list(p_p); random.shuffle(batch); pool.extend(batch)
                pool = pool[:n_p]
                
                all_img_paths = [c_img] + pool
                clips = [ImageClip(process_image_916(p)).set_duration(speed) for p in all_img_paths]
                
                video = concatenate_videoclips(clips, method="chain")
                t_img = draw_text_on_canvas(random.choice(texts_list), conf)
                t_clip = ImageClip(t_img).set_duration(video.duration)
                
                final = CompositeVideoClip([video, t_clip], size=(1080, 1920))
                if m_p:
                    a = AudioFileClip(random.choice(m_p))
                    final = final.set_audio(a.subclip(0, min(a.duration, final.duration)))
                
                out = f"fin_{sid}_{i}.mp4"
                final.write_videofile(out, fps=24, codec="libx264", audio_codec="aac", logger=None, preset="ultrafast")
                vids.append(out)
                
                # Czyścimy pamięć natychmiast
                final.close(); video.close(); gc.collect()

            z_n = f"OMEGA_{sid}.zip"
            with zipfile.ZipFile(z_n, 'w') as z:
                for v in vids: z.write(v); os.remove(v)
            for p in c_p + p_p + m_p: 
                if os.path.exists(p): os.remove(p)
            
            status.success("✅ Gotowe!")
            st.download_button("📥 POBIERZ ZIP", open(z_n, "rb"), file_name=z_n)
        except Exception as e:
            st.error(f"Błąd: {e}")
