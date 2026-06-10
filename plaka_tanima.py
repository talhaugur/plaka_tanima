import os
import subprocess
import time
import requests
import shutil
from threading import Thread, Event
from queue import Queue, Empty
from flask import Flask, request, render_template_string, send_file
from gpiozero import OutputDevice, DigitalInputDevice

# --- KONFIGÜRASYON ---
API_TOKEN       = "e8dbc6b3a35577a8af907c118920c24ae404d3bb"
PIN_IN1         = 18
PIN_IN2         = 23
PIN_IN3         = 24
PIN_IN4         = 25
ADIM_90_DERECE  = 128
MOTOR_HIZI      = 0.0025
LDR_PIN         = 17
LDR_ARABA_VAR   = 1
GECICI_RESIM    = "plaka.jpg"
SON_GECIS_RESIM = "son_gecis.jpg"
PLAKA_DOSYASI   = "plakalar.txt"

# --- PAYLAŞILAN DURUM (Thread-safe Event ve Queue) ---
komut_kuyrugu   = Queue()
kapi_ac_event   = Event()   # Sensör/web → motor: "kapıyı aç"
kapi_kapat_event = Event()  # Web → motor: "hemen kapat"
kapi_acik_event  = Event()  # Motor → sensör: "kapı şu an açık"

sistem_durumu = {
    "son_plaka": "Henüz gecis yok",
    "son_zaman": "-",
    "durum":     "Bekleniyor..."
}

# --- DONANIM BAŞLAT ---
step_pins = [
    OutputDevice(PIN_IN1),
    OutputDevice(PIN_IN2),
    OutputDevice(PIN_IN3),
    OutputDevice(PIN_IN4),
]
step_sequence = [
    [1, 0, 0, 0],
    [1, 1, 0, 0],
    [0, 1, 0, 0],
    [0, 1, 1, 0],
    [0, 0, 1, 0],
    [0, 0, 1, 1],
    [0, 0, 0, 1],
    [1, 0, 0, 1],
]
ldr = DigitalInputDevice(LDR_PIN)

# --- PLAKA DOSYA FONKSİYONLARI ---
def plaka_listesini_getir():
    if not os.path.exists(PLAKA_DOSYASI):
        return []
    with open(PLAKA_DOSYASI, "r") as f:
        return [p.strip() for p in f.readlines() if p.strip()]

def plaka_ekle(plaka):
    plakalar = plaka_listesini_getir()
    plaka = plaka.upper().replace(" ", "")
    if plaka and plaka not in plakalar:
        with open(PLAKA_DOSYASI, "a") as f:
            f.write(plaka + "\n")

def plaka_sil(plaka):
    plakalar = plaka_listesini_getir()
    if plaka in plakalar:
        plakalar.remove(plaka)
        with open(PLAKA_DOSYASI, "w") as f:
            for p in plakalar:
                f.write(p + "\n")

if not os.path.exists(PLAKA_DOSYASI):
    plaka_ekle("02ABG585")

# ======================================================
# THREAD 1 — FLASK WEB SUNUCUSU
# ======================================================
app = Flask(__name__)

HTML_SABLON = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Akilli Bariyer Paneli</title>
    <style>
        body {
            font-family: 'Segoe UI', sans-serif;
            background: #f4f7f6;
            color: #333;
            text-align: center;
            padding: 20px;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            max-width: 500px;
            margin: 0 auto 20px auto;
        }
        img {
            max-width: 100%;
            border-radius: 8px;
            border: 2px solid #ddd;
        }
        .btn {
            background: #28a745;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            text-decoration: none;
            display: inline-block;
        }
        .btn-mavi { background: #007bff; }
        .btn-gri  { background: #6c757d; }
        .btn-sil  {
            background: #dc3545;
            color: white;
            padding: 5px 10px;
            text-decoration: none;
            border-radius: 3px;
            font-size: 14px;
        }
        input {
            padding: 10px;
            width: 60%;
            border: 1px solid #ccc;
            border-radius: 5px;
        }
        ul { list-style: none; padding: 0; }
        li {
            background: #e9ecef;
            margin: 5px 0;
            padding: 10px;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
        }
        .durum {
            font-size: 18px;
            font-weight: bold;
            color: #0056b3;
        }
        .buton-grubu {
            display: flex;
            justify-content: space-around;
            margin-top: 15px;
        }
    </style>
</head>
<body>
    <h2>Akilli Bariyer Yonetim Paneli</h2>

    <div class="card">
        <h3>Manuel Kapi Kontrolu</h3>
        <div class="buton-grubu">
            <a href="/manuel/ac"    class="btn btn-mavi">Kapiyi Ac</a>
            <a href="/manuel/kapat" class="btn btn-gri">Kapiyi Kapat</a>
        </div>
    </div>

    <div class="card">
        <h3>Son Islem Goren Arac</h3>
        <p class="durum">{{ sistem_durumu['durum'] }}</p>
        <p>
            <b>Plaka:</b> {{ sistem_durumu['son_plaka'] }}<br>
            <b>Saat:</b>  {{ sistem_durumu['son_zaman'] }}
        </p>
        <img src="/foto?{{ rand }}" alt="Son Arac Fotografi">
    </div>

    <div class="card">
        <h3>Izinli Plakalar Listesi</h3>
        <ul>
            {% for p in plakalar %}
            <li>
                {{ p }}
                <a href="/sil/{{ p }}" class="btn-sil">Sil</a>
            </li>
            {% endfor %}
        </ul>
        <form action="/ekle" method="POST" style="margin-top: 15px;">
            <input type="text" name="yeni_plaka" placeholder="Orn: 34ABC123" required>
            <button type="submit" class="btn">Plaka Ekle</button>
        </form>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(
        HTML_SABLON,
        plakalar=plaka_listesini_getir(),
        sistem_durumu=sistem_durumu,
        rand=time.time()
    )

@app.route("/foto")
def foto():
    if os.path.exists(SON_GECIS_RESIM):
        return send_file(SON_GECIS_RESIM, mimetype="image/jpeg")
    return "Fotograf yok", 404

@app.route("/ekle", methods=["POST"])
def ekle():
    plaka_ekle(request.form.get("yeni_plaka", ""))
    return "<script>window.location.href='/';</script>"

@app.route("/sil/<plaka>")
def sil(plaka):
    plaka_sil(plaka)
    return "<script>window.location.href='/';</script>"

@app.route("/manuel/<islem>")
def manuel(islem):
    if islem in ("ac", "kapat"):
        komut_kuyrugu.put(islem.upper())
    return "<script>window.location.href='/';</script>"

def web_thread():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

# ======================================================
# THREAD 2 — SENSÖR + PLAKA OKUMA
# ======================================================
def plaka_kontrol_et():
    """Fotograf cek, API'ye gonder, yetkili mi kontrol et."""
    if os.path.exists(GECICI_RESIM):
        os.remove(GECICI_RESIM)

    subprocess.run("pkill rpicam-vid", shell=True)
    time.sleep(0.2)

    subprocess.run(
        f"rpicam-still -n -t 10 --immediate --width 800 --height 600 -o {GECICI_RESIM}",
        shell=True
    )

    subprocess.Popen(
        "DISPLAY=:0 rpicam-vid -t 0 --width 640 --height 480 "
        "--inline --preview 0,0,640,480 &",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    if not os.path.exists(GECICI_RESIM):
        return False

    try:
        with open(GECICI_RESIM, "rb") as fp:
            response = requests.post(
                "https://api.platerecognizer.com/v1/plate-reader/",
                data={"regions": "tr"},
                files={"upload": fp},
                headers={"Authorization": f"Token {API_TOKEN}"},
                timeout=10
            )

        if response.status_code in (200, 201):
            results = response.json().get("results", [])
            if results:
                shutil.copy(GECICI_RESIM, SON_GECIS_RESIM)
                okunan_plaka = results[0].get("plate", "").upper()
                print(f"\n[KAMERA] Okunan: {okunan_plaka}")

                sistem_durumu["son_plaka"] = okunan_plaka
                sistem_durumu["son_zaman"] = time.strftime("%H:%M:%S")

                if okunan_plaka in plaka_listesini_getir():
                    sistem_durumu["durum"] = "GIRIS ONAYLANDI"
                    return True
                else:
                    sistem_durumu["durum"] = "REDDEDILDI (Kayitsiz Plaka)"

    except Exception as e:
        print(f"[HATA] Baglanti veya API Hatasi: {e}")

    return False


def sensor_ve_plaka_thread():
    """
    Kapi kapali iken surekli arac bekle.
    Manuel komut veya yetkili plaka → kapi_ac_event'i set et.
    """
    while True:
        # Kapi zaten aciksa bu thread bekler
        if kapi_acik_event.is_set():
            time.sleep(0.5)
            continue

        # Kuyrukta manuel komut var mi? (non-blocking)
        try:
            komut = komut_kuyrugu.get_nowait()
            if komut == "AC":
                sistem_durumu["son_plaka"] = "Manuel Giris"
                sistem_durumu["son_zaman"] = time.strftime("%H:%M:%S")
                sistem_durumu["durum"]     = "WEB PANELINDEN ACILDI"
                kapi_ac_event.set()
                continue
            elif komut == "KAPAT":
                kapi_kapat_event.set()
                continue
        except Empty:
            pass

        print("\r[SISTEM] Arac bekleniyor...", end="", flush=True)

        if plaka_kontrol_et():
            kapi_ac_event.set()
        else:
            time.sleep(0.5)

# ======================================================
# THREAD 3 — MOTOR KONTROL
# ======================================================
def motoru_dondur(dongu_sayisi, yon, guvenlik_kontrolu=False):
    """
    Motoru dondur.
    guvenlik_kontrolu=True ise LDR'de arac varsa durur ve
    kac dongu atildigini dondurur (geri acmak icin).
    """
    atilan_dongu = 0
    for _ in range(dongu_sayisi):
        if guvenlik_kontrolu and ldr.value == LDR_ARABA_VAR:
            return atilan_dongu  # Kac adim atildi?

        for step in range(8):
            seq_index = step if yon == 1 else (7 - step)
            for pin_num in range(4):
                if step_sequence[seq_index][pin_num] == 1:
                    step_pins[pin_num].on()
                else:
                    step_pins[pin_num].off()
            time.sleep(MOTOR_HIZI)

        atilan_dongu += 1

    return True  # Tamamlandi


def kapiyi_ac():
    motoru_dondur(ADIM_90_DERECE, yon=1)


def kapiyi_kapat():
    print("[MOTOR] Kapi kapatiliyor...")
    sonuc = motoru_dondur(ADIM_90_DERECE, yon=-1, guvenlik_kontrolu=True)

    if sonuc is not True:
        print(f"\n[ACIL DURUM] Arac algilandi! {sonuc} adim geri aciliyor!")
        motoru_dondur(sonuc, yon=1)
        return False

    for pin in step_pins:
        pin.off()
    return True


def motor_thread():
    """
    Sadece event'leri dinler ve motoru surer.
    Diger thread'lerden tamamen bagimsiz calisir.
    """
    while True:
        # Acma sinyali gelene kadar bekle (100ms timeout ile polling)
        if not kapi_ac_event.wait(timeout=0.1):
            continue

        kapi_ac_event.clear()
        print("\n[MOTOR] Kapi aciliyor...")
        kapiyi_ac()
        kapi_acik_event.set()   # "Kapi su an acik" bayragi

        # 10 saniye bekle ya da erken kapat komutu gel
        print("[MOTOR] 10 sn otomatik bekleme basliyor...")
        kapi_kapat_event.wait(timeout=10)
        kapi_kapat_event.clear()

        # Arac gecene kadar bekle (guvenlik)
        while ldr.value == LDR_ARABA_VAR:
            print("[UYARI] Arac hala kapinin altinda, bekleniyor...")
            time.sleep(2)
            # Web'den zorla kapat gelirse bile arac varken kapat
            if kapi_kapat_event.is_set():
                print("[WEB] Guvenlik ihlali: Arac varken manuel kapanamaz!")
                kapi_kapat_event.clear()

        print("[MOTOR] Lazer hatti temiz. Kapatiliyor...")
        if kapiyi_kapat():
            print("[MOTOR] Kapi basariyla kapandi.")
        else:
            print("[MOTOR] Guvenlik ihlali! Yeniden acik beklenecek...")
            # kapi_acik_event set kalmaya devam eder,
            # sensor_thread tekrar ac sinyali gonderene kadar bekler

        kapi_acik_event.clear()

# ======================================================
# MAIN — Thread'leri baslat
# ======================================================
def main():
    print("=" * 50)
    print("=== Bariyer Sistemi Baslatiliyor ===")
    print("=" * 50)

    # Tum pinleri sifirla
    for pin in step_pins:
        pin.off()

    # Canli kamera onizlemesini baslat
    subprocess.Popen(
        "DISPLAY=:0 rpicam-vid -t 0 --width 640 --height 480 "
        "--inline --preview 0,0,640,480 &",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)

    # Thread'leri olustur ve baslat
    threads = [
        Thread(target=web_thread,             daemon=True, name="Web-Flask"),
        Thread(target=sensor_ve_plaka_thread, daemon=True, name="Sensor-Plaka"),
        Thread(target=motor_thread,           daemon=True, name="Motor-Kontrol"),
    ]

    for t in threads:
        t.start()
        print(f"[BASLATILDI] Thread: {t.name}")

    print("=" * 50)
    print("=== Tum thread'ler aktif. Ctrl+C ile cikis. ===")
    print("=" * 50)

    try:
        # Ana thread sadece sistemi ayakta tutar
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SISTEM] Kapatiliyor...")
    finally:
        for pin in step_pins:
            pin.off()
        subprocess.run("pkill rpicam-vid", shell=True)
        print("[SISTEM] Pinler sifirlanmadi, program sona erdi.")


if __name__ == "__main__":
    main()