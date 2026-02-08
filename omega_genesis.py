import streamlit as st
import os, gc, random, time, zipfile
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.compositing.concatenate import concatenate_videoclips
from moviepy.audio.io.AudioFileClip import AudioFileClip
import moviepy.config as mpy_config

# --- 1. KONFIGURACJA ŚRODOWISKA (ImageMagick) ---
def setup_imagemagick(path):
    if os.path.exists(path):
        mpy_config.change_settings({"IMAGEMAGICK_BINARY": path})
        return True
    return False


# --- 2. LOGIKA GRAFICZNA (Przetwarzanie obrazu do 9:16) ---
def process_image_916(img_file, target_res=(1080, 1920)):
    try:
        with Image.open(img_file) as img:
            # Korekcja obrotu EXIF i konwersja do RGB
            img = ImageOps.exif_transpose(img).convert("RGB")

            # Tworzenie czarnego płótna
            canvas = Image.new("RGB", target_res, (0, 0, 0))

            # Dopasowanie zdjęcia (thumbnail zachowuje proporcje)
            img.thumbnail(target_res, Image.Resampling.LANCZOS)

            # Centrowanie zdjęcia na płótnie
            offset = ((target_res[0] - img.width) // 2, (target_res[1] - img.height) // 2)
            canvas.paste(img, offset)

            return np.array(canvas)
    except Exception as e:
        print(f"Błąd procesowania obrazu: {e}")
        return np.zeros((1920, 1080, 3), dtype="uint8")


# --- 3. DYNAMICZNY SYSTEM CZCIONEK ---
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


# --- 4. GŁÓWNY SILNIK RYSOWANIA TEKSTU (Pillow Engine) ---
def draw_text_on_canvas(text, config, res=(1080, 1920), is_preview=False):
    # Inicjalizacja warstw przezroczystych (RGBA)
    txt_layer = Image.new("RGBA", res, (0, 0, 0, 0))
    shd_layer = Image.new("RGBA", res, (0, 0, 0, 0))

    draw_txt = ImageDraw.Draw(txt_layer)
    draw_shd = ImageDraw.Draw(shd_layer)

    try:
        font = ImageFont.truetype(config['font_path'], config['f_size'])
    except Exception:
        font = ImageFont.load_default()

    # Obliczanie wymiarów tekstu do centrowania
    bbox = draw_txt.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # Pozycjonowanie (Środek ekranu)
    base_pos = ((res[0] - tw) // 2, (res[1] - th) // 2)
    shd_pos = (base_pos[0] + config['shd_x'], base_pos[1] + config['shd_y'])

    # Renderowanie warstwy cienia
    c_shd = config['shd_color'].lstrip('#')
    rgb_shd = tuple(int(c_shd[i:i + 2], 16) for i in (0, 2, 4))

    draw_shd.text(shd_pos, text, fill=(*rgb_shd, config['shd_alpha']), font=font)

    # Nakładanie rozmycia Gaussa na cień
    if config['shd_blur'] > 0:
        shd_layer = shd_layer.filter(ImageFilter.GaussianBlur(config['shd_blur']))

    # Renderowanie warstwy głównej tekstu (z obramowaniem)
    draw_txt.text(base_pos, text, fill=config['t_color'], font=font,
                  stroke_width=config['s_width'], stroke_fill=config['s_color'])

    # Kompozycja końcowa napisu
    combined = Image.new("RGBA", res, (0, 0, 0, 0))
    combined.paste(shd_layer, (0, 0), shd_layer)
    combined.paste(txt_layer, (0, 0), txt_layer)

    # Specjalne tło dla podglądu (Green Screen)
    if is_preview:
        bg = Image.new("RGB", res, (0, 255, 0))
        bg.paste(combined, (0, 0), combined)
        return bg

    return np.array(combined)


# --- 5. INTERFEJS UŻYTKOWNIKA (Streamlit) ---
st.set_page_config(page_title="OMEGA V12.40 FULL", layout="wide")
st.title("Ω OMEGA V12.40 - PEŁNA STRUKTURA")

with st.sidebar:
    st.header("⚙️ USTAWIENIA SYSTEMOWE")
    m_path = st.text_input("Ścieżka ImageMagick", r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe")
    setup_imagemagick(m_path)

    v_count = st.number_input("Ilość filmów", 1, 100, 5)
    speed = st.selectbox("Szybkość zmiany zdjęć (s)", [0.1, 0.15, 0.2], index=1)

    st.divider()
    st.header("🎨 WYGLĄD NAPISU")
    f_font = st.selectbox("Wybierz Czcionkę", ["League Gothic Regular", "League Gothic Condensed", "Impact"])
    f_size = st.slider("Wielkość Czcionki", 10, 500, 82)
    t_color = st.color_picker("Kolor Tekstu", "#FFFFFF")
    s_width = st.slider("Grubość Obramowania", 0, 20, 2)
    s_color = st.color_picker("Kolor Obramowania", "#000000")

    st.divider()
    st.header("☁️ PARAMETRY CIENIA")
    shd_x = st.slider("Przesunięcie X", -100, 100, 2)
    shd_y = st.slider("Przesunięcie Y", -100, 100, 19)
    shd_blur = st.slider("Rozmycie (Blur)", 0, 50, 5)
    shd_alpha = st.slider("Przezroczystość", 0, 255, 146)
    shd_color = st.color_picker("Kolor Cienia", "#000000")

    st.divider()
    raw_texts = st.text_area("Lista Tekstów", "ig brands aint safe")
    texts_list = [t.strip() for t in raw_texts.split('\n') if t.strip()]

    # Przygotowanie konfiguracji dla silnika rysowania
    config_dict = {
        'font_path': get_font_path(f_font), 'f_size': f_size, 't_color': t_color,
        's_width': s_width, 's_color': s_color, 'shd_x': shd_x, 'shd_y': shd_y,
        'shd_blur': shd_blur, 'shd_alpha': shd_alpha, 'shd_color': shd_color
    }

    # Wyświetlanie podglądu na żywo
    if texts_list:
        preview_img = draw_text_on_canvas(texts_list[0], config_dict, is_preview=True)
        st.image(preview_img.resize((350, 622)), caption="PODGLĄD GREEN SCREEN")

# --- 6. PROCES RENDEROWANIA ---
c1, c2, c3 = st.columns(3)
with c1: u_cov = st.file_uploader("Wgraj Okładki", accept_multiple_files=True)
with c2: u_pho = st.file_uploader("Wgraj Zdjęcia", accept_multiple_files=True)
with c3: u_mus = st.file_uploader("Wgraj Muzykę", accept_multiple_files=True)

if st.button("🚀 URUCHOM GENEROWANIE"):
    if u_cov and u_pho and texts_list:
        with st.status("🎬 Trwa renderowanie filmów...") as status:
            sid = int(time.time())

            # 1. Zapis plików tymczasowych na dysku
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

            # 2. Główna pętla generowania filmów
            for i in range(v_count):
                st.write(f"Przetwarzanie filmu {i + 1} z {v_count}...")

                txt = random.choice(texts_list)
                # Losowanie zestawu zdjęć (35 sztuk)
                batch = [random.choice(c_p)] + random.sample(p_p, min(len(p_p), 35))

                # Tworzenie sekwencji obrazów
                base = concatenate_videoclips([ImageClip(process_image_916(p)).set_duration(speed) for p in batch],
                                              method="chain")

                # Generowanie warstwy napisu z Pillow
                txt_arr = draw_text_on_canvas(txt, config_dict)
                txt_clip = ImageClip(txt_arr).set_duration(base.duration)

                # Składanie warstw
                final_video = CompositeVideoClip([base, txt_clip], size=(1080, 1920))

                # Dodawanie dźwięku
                if m_p:
                    audio_clip = AudioFileClip(random.choice(m_p))
                    final_video = final_video.set_audio(
                        audio_clip.subclip(0, min(audio_clip.duration, final_video.duration)))

                # Eksport pliku
                out_name = f"final_{sid}_{i}.mp4"
                final_video.write_videofile(out_name, fps=24, codec="libx264", audio_codec="aac", threads=1,
                                            logger=None, preset="ultrafast")
                final_vids.append(out_name)

                # Czyszczenie pamięci podręcznej po każdym filmie
                final_video.close();
                base.close();
                gc.collect()

            # 3. Pakowanie wyników i sprzątanie plików tymczasowych
            zip_final = f"OMEGA_EXPORT_{sid}.zip"
            with zipfile.ZipFile(zip_final, 'w') as z:
                for f in final_vids:
                    z.write(f)
                    os.remove(f)

            for p in c_p + p_p + m_p:
                if os.path.exists(p): os.remove(p)

            status.update(label="✅ Renderowanie zakończone!", state="complete")

            st.download_button("📥 POBIERZ PACZKĘ MP4", open(zip_final, "rb"), file_name=zip_final)

