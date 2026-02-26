import streamlit as st
import os, gc, random, time, datetime, io, zipfile
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from moviepy.editor import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip, VideoFileClip
import moviepy.config as mpy_config
import subprocess

# ==============================================================================
# 1. KONFIGURACJA RDZENIA OMEGA V12.99
# ==============================================================================

class OmegaCore:
    VERSION = "V12.99 ANTY-TIKTOK EDITION"
    TARGET_RES = (1080, 1920)
    SAFE_MARGIN = 90  # Margines boczny dla tekstu (Auto-Scale)
    
    @staticmethod
    def setup_session():
        keys = ['v_covers', 'v_photos', 'v_music', 'v_results', 'zip_files']
        for key in keys:
            if key not in st.session_state:
                st.session_state[key] = []
        if 'pack_size' not in st.session_state:
            st.session_state.pack_size = 70  # Domyślnie 70 filmów na paczkę

    @staticmethod
    def get_magick_path():
        if os.name == 'posix': return "/usr/bin/convert"
        return r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"

# ==============================================================================
# 2. SILNIK GRAFICZNY I AUTO-SCALE
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
    """Silnik Auto-Scale: Zmniejsza czcionkę, aby tekst nie wystawał poza marginesy."""
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
# 3. FUNKCJE ANTY-WYKRYWAWCZE (TIKTOK)
# ==============================================================================

def apply_anti_fingerprint_modifications(input_path, output_path, fps, bitrate, sample_rate, brightness, gamma):
    """
    Zastosuje serię modyfikacji do pliku wideo, aby utrudnić algorytmom wykrycie podobieństw.
    Używa ffmpeg bezpośrednio.
    """
    # 1. Zmiana rozdzielczości o 2 piksele (parzysta zmiana)
    # Losowo odejmij 2 od szerokości lub wysokości (lub obu) – ale zachowaj proporcje? 
    # Lepiej zmienić rozmiar o 2px w obie strony, ale żeby nie zniekształcić obrazu, użyjemy skalowania i przycięcia.
    # Ustalmy nowy rozmiar: szerokość = 1080 - 2 = 1078, wysokość = 1920 - 2 = 1918
    # Ale to zmieni proporcje. Możemy przeskalować do 1078x1918, a potem dodać czarne paski? 
    # Prościej: użyjemy filtra scale, który rozciągnie obraz do nowego rozmiaru (minimalne zniekształcenie).
    new_w = 1078
    new_h = 1918

    # 2. Zmiana fps na ułamkową (np. 29.97 zamiast 30)
    # 3. Bitrate – ustawiamy zadany
    # 4. Sample rate audio – zadany
    # 5. Jasność i gamma – przez filtry eq

    # Komenda ffmpeg
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-vf', f'scale={new_w}:{new_h},eq=brightness={brightness}:gamma={gamma}',
        '-r', str(fps),
        '-b:v', bitrate,
        '-b:a', f'{sample_rate}k',  # zakładając, że sample_rate to liczba w kHz? Tu chcemy w bitach, więc lepiej użyć sample_rate jako liczby Hz.
        '-ar', str(sample_rate),
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-c:a', 'aac',
        output_path
    ]
    subprocess.run(cmd, check=True)

# ==============================================================================
# 4. INTERFEJS I LIVE PREVIEW
# ==============================================================================

OmegaCore.setup_session()
st.set_page_config(page_title="Ω OMEGA ANTY-TIKTOK", layout="wide")
mpy_config.change_settings({"IMAGEMAGICK_BINARY": OmegaCore.get_magick_path()})

with st.sidebar:
    st.title("⚙️ CONFIGURATION")

    f_font = st.selectbox("Czcionka", ["League Gothic Regular", "League Gothic Condensed", "Impact"])
    f_size = st.slider("Max Wielkość", 20, 500, 83)
    t_color = st.color_picker("Kolor tekstu", "#FFFFFF")
    s_width = st.slider("Obrys", 0, 20, 3)
    
    st.header("🌑 CIEŃ")
    shd_x = st.slider("Cień X", -100, 100, 15)
    shd_y = st.slider("Cień Y", -100, 100, 15)
    shd_alpha = st.slider("Alpha", 0, 255, 200)

    cfg = {
        'font_path': get_font_path(f_font), 'f_size': f_size, 't_color': t_color,
        's_width': s_width, 's_color': "#000000", 'shd_x': shd_x, 'shd_y': shd_y,
        'shd_blur': 8, 'shd_alpha': shd_alpha, 'shd_color': "#000000"
    }

    st.header("👁️ LIVE PREVIEW")
    sim_bg = Image.new("RGB", OmegaCore.TARGET_RES, (15, 15, 15)) 
    draw_sim = ImageDraw.Draw(sim_bg)
    draw_sim.rectangle([0, 625, 1080, 1295], fill=(0, 255, 0)) 
    
    t_lay = draw_text_pancerny("LIVE PREVIEW TEST", cfg)
    sim_bg.paste(t_lay, (0, 0), t_lay)
    st.image(sim_bg, caption="Podgląd reaguje na suwaki!", use_container_width=True)
    
    st.divider()
    
    # Wybór dozwolonych prędkości (multiselect)
    speed_options = st.multiselect(
        "🎞️ Dozwolone szybkości przejść (s)",
        options=[0.1, 0.11, 0.12, 0.15, 0.2, 0.25, 0.3],
        default=[0.1, 0.12, 0.15, 0.2]
    )
    if not speed_options:
        speed_options = [0.1, 0.12, 0.15, 0.2]  # zabezpieczenie
    
    # Rozmiar paczki ZIP – z konwersją na int
    pack_size = st.number_input(
        "📦 Filmy na paczkę ZIP",
        min_value=1,
        max_value=100,
        value=int(st.session_state.pack_size),
        step=1
    )
    st.session_state.pack_size = int(pack_size)
    
    st.divider()
    
    # Opcje anty-wykrywawcze
    st.header("🕵️ ANTY-TIKTOK")
    enable_anti = st.checkbox("Włącz modyfikacje anty-wykrywawcze", value=True)
    if enable_anti:
        fps_options = st.selectbox("FPS (ułamkowe)", [29.97, 30.0, 30.01, 59.94, 60.0], index=0)
        bitrate_options = st.selectbox("Bitrate", ["4000k", "4500k", "4850k", "5000k"], index=2)
        sample_rate_options = st.selectbox("Sample rate audio", [44100, 48000], index=0)
        brightness_adj = st.slider("Korekta jasności (np. 0.01)", -0.05, 0.05, 0.01, step=0.01)
        gamma_adj = st.slider("Korekta gamma (np. 0.99)", 0.95, 1.05, 0.99, step=0.01)
    else:
        fps_options = 30.0
        bitrate_options = "5000k"
        sample_rate_options = 48000
        brightness_adj = 0.0
        gamma_adj = 1.0
    
    st.divider()
    
    default_txts = (
        "Most unique spreadsheet rn\nIg brands ain't safe\nPOV: You created best ig brands spreadsheet\n"
        "Best archive spreadsheet rn\nArchive fashion ain't safe\nBest ig brands spreadsheet oat.\n"
        "Best archive fashion spreadsheet rn.\nEven ig brands ain't safe\nPOV: you have best spreadsheet on tiktok\n"
        "pov: you found best spreadsheet\nSwagest spreadsheet ever\nSwagest spreadsheet in 2026\n"
        "Coldest spreadsheet rn.\nNo more gatekeeping this spreadsheet\nUltimate archive clothing vault\n"
        "Only fashion sheet needed\nBest fashion sheet oat\nIG brands ain't safe\n"
        "I found the holy grail of spreadsheets\nTook me 3 months to create best spreadsheet\n"
        "I’m actually done gatekeeping this\nWhy did nobody tell me about this sheet earlier?\n"
        "Honestly, best finds i’ve ever seen\npov: you’re not gatekeeping your sources anymore\n"
        "pov: your fits are about to get 10x better\npov: you found the spreadsheet everyone was looking for\n"
        "me after finding this archive sheet:\nThis spreadsheet is actually crazy\n"
        "archive pieces you actually need\nSpreadsheet just drooped"
    )
    raw_texts = st.text_area("Baza Tekstów", default_txts, height=150)
    texts_list = [t.strip() for t in raw_texts.split('\n') if t.strip()]

# ==============================================================================
# 5. SILNIK PRODUKCJI (MULTI-ZIP Z KONFIGUROWALNYM ROZMIAREM PACZKI)
# ==============================================================================

st.title(f"Ω OMEGA {OmegaCore.VERSION}")

c1, c2, c3 = st.columns(3)
with c1: u_c = st.file_uploader("Okładki", type=['png','jpg','jpeg'], accept_multiple_files=True)
with c2: u_p = st.file_uploader("Zdjęcia (Bulk)", type=['png','jpg','jpeg'], accept_multiple_files=True)
with c3: u_m = st.file_uploader("Muzyka (MP3)", type=['mp3'], accept_multiple_files=True)

if st.button("🚀 URUCHOM PRODUKCJĘ MASOWĄ", use_container_width=True):
    if not u_c or not u_p:
        st.error("Wgraj okładki i zdjęcia!")
    else:
        st.session_state.v_results = []
        st.session_state.zip_files = []
        with st.status("🎬 Renderowanie...", expanded=True) as status:
            if not os.path.exists("temp"): os.makedirs("temp")
            
            for idx, cov_file in enumerate(u_c):
                # Losowanie prędkości dla tego filmu
                current_speed = random.choice(speed_options)
                
                # Time Guard: długość filmu 8.5-9.8s
                target_dur = random.uniform(8.5, 9.8)
                cov_dur = current_speed * 3
                num_photos = int((target_dur - cov_dur) / current_speed)
                
                st.write(f"🎞️ Film {idx+1}/{len(u_c)} | Prędkość: {current_speed}s | Czas: {target_dur:.1f}s | Zdjęć: {num_photos}")
                
                # Dobór zdjęć
                sample = random.sample(u_p, min(num_photos, len(u_p)))
                clips = [ImageClip(process_image_916(cov_file)).set_duration(cov_dur)]
                clips += [ImageClip(process_image_916(p)).set_duration(current_speed) for p in sample]
                
                base = concatenate_videoclips(clips, method="chain")
                
                # Nakładanie tekstu
                t_arr = np.array(draw_text_pancerny(random.choice(texts_list), cfg))
                txt_clip = ImageClip(t_arr).set_duration(base.duration)
                
                final = CompositeVideoClip([base, txt_clip], size=OmegaCore.TARGET_RES)
                
                # Tymczasowy plik przed modyfikacjami
                temp_raw = f"temp/raw_{idx}.mp4"
                final.write_videofile(temp_raw, fps=24, codec="libx264", audio_codec="aac", threads=4, logger=None, preset="ultrafast")
                final.close(); base.close(); gc.collect()
                
                # Jeśli włączone anty-fingerprint, zastosuj modyfikacje
                if enable_anti:
                    out_name = f"OMEGA_VIDEO_{idx+1}.mp4"
                    apply_anti_fingerprint_modifications(
                        temp_raw, out_name,
                        fps=fps_options,
                        bitrate=bitrate_options,
                        sample_rate=sample_rate_options,
                        brightness=brightness_adj,
                        gamma=gamma_adj
                    )
                    os.remove(temp_raw)  # usuń surowy plik
                else:
                    out_name = temp_raw  # po prostu zmień nazwę
                
                st.session_state.v_results.append(out_name)

            # --- PAKOWANIE WEDŁUG USTAWIONEGO ROZMIARU PACZKI ---
            st.write(f"📦 Dzielenie na paczki po {st.session_state.pack_size} filmów...")
            chunk_size = st.session_state.pack_size
            for i in range(0, len(st.session_state.v_results), chunk_size):
                chunk = st.session_state.v_results[i:i + chunk_size]
                part_num = (i // chunk_size) + 1
                zip_n = f"OMEGA_PART_{part_num}.zip"
                
                with zipfile.ZipFile(zip_n, 'w', compression=zipfile.ZIP_STORED) as z:
                    for f in chunk:
                        if os.path.exists(f): z.write(f)
                st.session_state.zip_files.append(zip_n)
            
            status.update(label="✅ PRODUKCJA I PAKOWANIE ZAKOŃCZONE!", state="complete")

# SEKCJA POBIERANIA
if st.session_state.zip_files:
    st.divider()
    st.subheader("📥 Gotowe paczki:")
    cols = st.columns(len(st.session_state.zip_files))
    for idx, zip_path in enumerate(st.session_state.zip_files):
        with open(zip_path, "rb") as f:
            cols[idx].download_button(
                label=f"📂 Pobierz PART {idx+1}",
                data=f,
                file_name=zip_path,
                use_container_width=True
            )

    if st.button("🗑️ WYCZYŚĆ SERWER (Usuń pliki)"):
        for f in st.session_state.v_results + st.session_state.zip_files:
            if os.path.exists(f): os.remove(f)
        st.session_state.v_results = []
        st.session_state.zip_files = []
        st.rerun()
