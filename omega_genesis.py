import streamlit as st
import os, gc, random, time, datetime, io, zipfile
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from moviepy.editor import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip, VideoFileClip # dostępne w nowszych wersjach moviepy
import moviepy.config as mpy_config
import imageio_ffmpeg  # zapewni ffmpeg jeśli systemowy nie istnieje

# ==============================================================================
# 0. KONFIGURACJA FFMPEG (jeśli nie znaleziono systemowego, użyj z imageio)
# ==============================================================================
try:
    # próbujemy znaleźć ffmpeg w systemie
    mpy_config.change_settings({"FFMPEG_BINARY": "ffmpeg"})
except:
    # jeśli nie działa, używamy ffmpeg z imageio
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    mpy_config.change_settings({"FFMPEG_BINARY": ffmpeg_path})

# ==============================================================================
# 1. KONFIGURACJA RDZENIA OMEGA V13.0 (ANTY-TIKTOK)
# ==============================================================================

class OmegaCore:
    VERSION = "V13.0 ANTY-TIKTOK (FULL PROTECTION)"
    BASE_RES = (1080, 1920)          # bazowa rozdzielczość
    SAFE_MARGIN = 90
    
    @staticmethod
    def setup_session():
        # Inicjalizacja list (bez pack_size)
        list_keys = ['v_covers', 'v_photos', 'v_music', 'v_results', 'zip_files']
        for key in list_keys:
            if key not in st.session_state:
                st.session_state[key] = []
        
        # Inicjalizacja pack_size osobno (liczba)
        if 'pack_size' not in st.session_state:
            st.session_state.pack_size = 70

    @staticmethod
    def get_magick_path():
        if os.name == 'posix': return "/usr/bin/convert"
        return r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"

# ==============================================================================
# 2. FUNKCJE ANTY-DETEKCYJNE
# ==============================================================================

def apply_antidetection_settings(target_res, fps, bitrate, audio_rate, brightness, gamma):
    """
    Modyfikuje parametry w sposób niezauważalny dla człowieka,
    ale mylący algorytmy detekcji.
    Zwraca krotkę (zmodyfikowana_rozdzielczość, fps, bitrate, audio_rate)
    """
    # 1. Rozdzielczość – zmiana o 2px (parzysta)
    res_mod = (target_res[0] + random.choice([-2, 0, 2]), 
               target_res[1] + random.choice([-2, 0, 2]))
    
    # 2. FPS – ułamkowe (jeśli opcja włączona)
    if fps == 30:
        fps_mod = random.uniform(29.97, 30.03)
    elif fps == 60:
        fps_mod = random.uniform(59.94, 60.06)
    else:
        fps_mod = fps + random.uniform(-0.05, 0.05)
    
    # 3. Bitrate – lekko zmieniony
    if bitrate is not None:
        bitrate_mod = int(bitrate * random.uniform(0.98, 1.02))
    else:
        bitrate_mod = None
    
    # 4. Sample rate audio – do wyboru: 44100 lub 48000 z lekkim offsetem
    if audio_rate == 48000:
        audio_mod = 44100
    else:
        audio_mod = 48000
    
    # 5. Jasność i gamma – zwracamy osobno do zastosowania na klipie
    brightness_mod = brightness * random.uniform(0.99, 1.01)
    gamma_mod = gamma * random.uniform(0.99, 1.01)
    
    return res_mod, fps_mod, bitrate_mod, audio_mod, brightness_mod, gamma_mod

def apply_image_adjustments(img_array, brightness=1.0, gamma=1.0):
    """Modyfikuje jasność i gamma obrazu (tablica numpy)"""
    img = Image.fromarray(img_array)
    if brightness != 1.0:
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness)
    if gamma != 1.0:
        # korekcja gamma przez LUT
        import math
        gamma_corrected = np.array(img).astype(np.float32) / 255.0
        gamma_corrected = np.power(gamma_corrected, gamma)
        gamma_corrected = (gamma_corrected * 255).astype(np.uint8)
        img = Image.fromarray(gamma_corrected)
    return np.array(img)

# ==============================================================================
# 3. SILNIK GRAFICZNY I AUTO-SCALE (bez zmian)
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

def process_image_916(file_obj, target_res=OmegaCore.BASE_RES):
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

def draw_text_pancerny(text, config, res=OmegaCore.BASE_RES):
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
# 4. INTERFEJS I LIVE PREVIEW
# ==============================================================================

OmegaCore.setup_session()
st.set_page_config(page_title="Ω OMEGA V13.0 ANTY-TIKTOK", layout="wide")
mpy_config.change_settings({"IMAGEMAGICK_BINARY": OmegaCore.get_magick_path()})

with st.sidebar:
    st.title("⚙️ KONFIGURACJA")
    
    # ---- PODSTAWOWE USTAWIENIA WYGLĄDU ----
    with st.expander("🖌️ TEKST", expanded=True):
        f_font = st.selectbox("Czcionka", ["League Gothic Regular", "League Gothic Condensed", "Impact"])
        f_size = st.slider("Max Wielkość", 20, 500, 83)
        t_color = st.color_picker("Kolor tekstu", "#FFFFFF")
        s_width = st.slider("Obrys", 0, 20, 3)
        
        st.subheader("🌑 CIEŃ")
        shd_x = st.slider("Cień X", -100, 100, 15)
        shd_y = st.slider("Cień Y", -100, 100, 15)
        shd_alpha = st.slider("Alpha", 0, 255, 200)

    cfg = {
        'font_path': get_font_path(f_font), 'f_size': f_size, 't_color': t_color,
        's_width': s_width, 's_color': "#000000", 'shd_x': shd_x, 'shd_y': shd_y,
        'shd_blur': 8, 'shd_alpha': shd_alpha, 'shd_color': "#000000"
    }

    # ---- PODGLĄD NA ŻYWO ----
    with st.expander("👁️ LIVE PREVIEW"):
        sim_bg = Image.new("RGB", OmegaCore.BASE_RES, (15, 15, 15)) 
        draw_sim = ImageDraw.Draw(sim_bg)
        draw_sim.rectangle([0, 625, 1080, 1295], fill=(0, 255, 0)) 
        t_lay = draw_text_pancerny("LIVE PREVIEW TEST", cfg)
        sim_bg.paste(t_lay, (0, 0), t_lay)
        st.image(sim_bg, caption="Podgląd reaguje na suwaki!", use_container_width=True)
    
    st.divider()
    
    # ---- USTAWIENIA PRODUKCJI ----
    with st.expander("🎬 PRODUKCJA", expanded=True):
        speed_options = st.multiselect(
            "🎞️ Dozwolone szybkości przejść (s)",
            options=[0.1, 0.11, 0.12, 0.15, 0.2, 0.25, 0.3],
            default=[0.1, 0.12, 0.15, 0.2]
        )
        if not speed_options:
            speed_options = [0.1, 0.12, 0.15, 0.2]
        
        pack_size = st.number_input(
            "📦 Filmy na paczkę ZIP",
            min_value=1,
            max_value=100,
            value=int(st.session_state.pack_size),
            step=1
        )
        st.session_state.pack_size = int(pack_size)
    
    # ---- USTAWIENIA ANTY-DETEKCYJNE ----
    with st.expander("🛡️ ANTY-TIKTOK (ochrona przed duplicate detection)", expanded=True):
        enable_anti = st.checkbox("Włącz techniki anty-detekcyjne", value=True)
        
        col1, col2 = st.columns(2)
        with col1:
            res_shift = st.checkbox("🖼️ Zmiana rozdzielczości o 2px", value=True)
            fps_random = st.checkbox("⏱️ Losowy FPS (np. 29.97)", value=True)
            bitrate_random = st.checkbox("📊 Losowy bitrate", value=True)
        with col2:
            audio_switch = st.checkbox("🎵 Przełączanie sample rate", value=True)
            brightness_tweak = st.checkbox("☀️ Modyfikacja jasności (+/-1%)", value=True)
            gamma_tweak = st.checkbox("🎚️ Modyfikacja gamma", value=True)
        
        # Domyślne wartości (będą modyfikowane)
        default_fps = st.selectbox("Bazowe FPS", [24, 30, 60], index=1)
        default_bitrate = st.number_input("Bazowy bitrate (kb/s)", value=5000, step=100)
        default_audio_rate = st.selectbox("Bazowy sample rate audio", [44100, 48000], index=1)
    
    st.divider()
    
    # ---- BAZA TEKSTÓW ----
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
# 5. SEKCJA UPLOAD I GENEROWANIE
# ==============================================================================

st.title(f"Ω OMEGA {OmegaCore.VERSION}")

c1, c2, c3 = st.columns(3)
with c1: u_c = st.file_uploader("Okładki", type=['png','jpg','jpeg'], accept_multiple_files=True)
with c2: u_p = st.file_uploader("Zdjęcia (Bulk)", type=['png','jpg','jpeg'], accept_multiple_files=True)
with c3: u_m = st.file_uploader("Muzyka (MP3)", type=['mp3'], accept_multiple_files=True)

if st.button("🚀 URUCHOM PRODUKCJĘ MASOWĄ (ANTY-TIKTOK)", use_container_width=True):
    if not u_c or not u_p:
        st.error("Wgraj okładki i zdjęcia!")
    else:
        st.session_state.v_results = []
        st.session_state.zip_files = []
        with st.status("🎬 Renderowanie z ochroną anty-TikTok...", expanded=True) as status:
            if not os.path.exists("temp"): os.makedirs("temp")
            
            for idx, cov_file in enumerate(u_c):
                # ---- Losowanie prędkości dla tego filmu ----
                current_speed = random.choice(speed_options)
                
                # ---- Time Guard: długość filmu 8.5-9.8s ----
                target_dur = random.uniform(8.5, 9.8)
                cov_dur = current_speed * 3
                num_photos = int((target_dur - cov_dur) / current_speed)
                
                st.write(f"🎞️ Film {idx+1}/{len(u_c)} | Prędkość: {current_speed}s | Czas: {target_dur:.1f}s | Zdjęć: {num_photos}")
                
                # ---- Przygotowanie parametrów anty-detekcyjnych ----
                if enable_anti:
                    res_mod, fps_mod, bitrate_mod, audio_mod, bright_mod, gamma_mod = apply_antidetection_settings(
                        OmegaCore.BASE_RES,
                        default_fps,
                        default_bitrate if bitrate_random else None,
                        default_audio_rate,
                        1.0,   # bazowa jasność
                        1.0    # bazowa gamma
                    )
                    # Jeśli któraś opcja wyłączona, używamy wartości bazowych
                    if not res_shift:
                        res_mod = OmegaCore.BASE_RES
                    if not fps_random:
                        fps_mod = default_fps
                    if not bitrate_random:
                        bitrate_mod = default_bitrate
                    if not audio_switch:
                        audio_mod = default_audio_rate
                    if not brightness_tweak:
                        bright_mod = 1.0
                    if not gamma_tweak:
                        gamma_mod = 1.0
                else:
                    res_mod = OmegaCore.BASE_RES
                    fps_mod = default_fps
                    bitrate_mod = default_bitrate
                    audio_mod = default_audio_rate
                    bright_mod = 1.0
                    gamma_mod = 1.0
                
                # ---- Tworzenie klipów z modyfikacją jasności/gamma ----
                # Okładka
                cov_arr = process_image_916(cov_file, res_mod)
                cov_arr = apply_image_adjustments(cov_arr, bright_mod, gamma_mod)
                clips = [ImageClip(cov_arr).set_duration(cov_dur)]
                
                # Zdjęcia
                sample = random.sample(u_p, min(num_photos, len(u_p)))
                for p in sample:
                    img_arr = process_image_916(p, res_mod)
                    img_arr = apply_image_adjustments(img_arr, bright_mod, gamma_mod)
                    clips.append(ImageClip(img_arr).set_duration(current_speed))
                
                base = concatenate_videoclips(clips, method="chain")
                
                # ---- Nakładanie tekstu (bez modyfikacji jasności/gamma, bo tekst ma własne kolory) ----
                t_arr = np.array(draw_text_pancerny(random.choice(texts_list), cfg, res=res_mod))
                txt_clip = ImageClip(t_arr).set_duration(base.duration)
                
                final = CompositeVideoClip([base, txt_clip], size=res_mod)
                
                # ---- Audio ----
                if u_m:
                    m_file = random.choice(u_m)
                    tmp_m = f"temp/a_{idx}.mp3"
                    with open(tmp_m, "wb") as f: f.write(m_file.getbuffer())
                    aud = AudioFileClip(tmp_m)
                    # Jeśli sample rate ma być zmieniony, moviepy sam dokona konwersji przy zapisie
                    final = final.set_audio(aud.subclip(0, min(aud.duration, final.duration)))
                
                # ---- Zapis z wybranymi parametrami ----
                out_name = f"OMEGA_VIDEO_{idx+1}.mp4"
                final.write_videofile(
                    out_name,
                    fps=fps_mod,
                    codec="libx264",
                    audio_codec="aac",
                    bitrate=None if bitrate_mod is None else f"{bitrate_mod}k",
                    audio_bitrate=None if audio_mod is None else f"{audio_mod}k",  # moviepy użyje audio_bitrate do konwersji
                    threads=4,
                    logger=None,
                    preset="ultrafast"
                )
                st.session_state.v_results.append(out_name)
                final.close(); base.close(); gc.collect()
            
            # ---- Pakowanie według wybranego rozmiaru ----
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
            
            status.update(label="✅ PRODUKCJA ZAKOŃCZONA! Pliki gotowe do pobrania.", state="complete")

# ==============================================================================
# 6. SEKCJA POBIERANIA
# ==============================================================================
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

