import os, subprocess, time, requests, shutil
from threading import Thread, Event
from queue import Queue
from flask import Flask, request, render_template_string, send_file
from gpiozero import OutputDevice, DigitalInputDevice

# ─── KONFİGÜRASYON ────────────────────────────────────────────
API_TOKEN       = "Buraya api token girin"
PIN_IN1, PIN_IN2, PIN_IN3, PIN_IN4 = 18, 23, 24, 25
ADIM_90_DERECE  = 128
MOTOR_HIZI      = 0.0025
LDR_PIN         = 17
LDR_ARABA_VAR   = 1
GECICI_RESIM    = "plaka.jpg"
SON_GECIS_RESIM = "son_gecis.jpg"
PLAKA_DOSYASI   = "plakalar.txt"

# ─── PAYLAŞILAN DURUM (Thread-safe) ───────────────────────────
#   Web → Motor yönünde komut kuyruğu
komut_kuyrugu = Queue()

#   Sinyaller: motor görevini koordine eder
kapi_ac_event    = Event()   # "kapıyı aç" sinyali
kapi_kapat_event = Event()   # "kapıyı kapat" sinyali
kapi_acik_event  = Event()   # motor "şu an açık" durumu

sistem_durumu = {
    "son_plaka": "Henüz geçiş yok",
    "son_zaman": "-",
    "durum":     "Bekleniyor..."
}

# ─── DONANIM BAŞLAT ───────────────────────────────────────────
step_pins = [
    OutputDevice(PIN_IN1), OutputDevice(PIN_IN2),
    OutputDevice(PIN_IN3), OutputDevice(PIN_IN4)
]
step_sequence = [
    [1,0,0,0],[1,1,0,0],[0,1,0,0],[0,1,1,0],
    [0,0,1,0],[0,0,1,1],[0,0,0,1],[1,0,0,1]
]
ldr = DigitalInputDevice(LDR_PIN)

# ─── PLAKA DOSYA FONKSİYONLARI ────────────────────────────────
def plaka_listesini_getir():
    if not os.path.exists(PLAKA_DOSYASI): return []
    with open(PLAKA_DOSYASI) as f:
        return [p.strip() for p in f if p.strip()]

def plaka_ekle(plaka):
    plaka = plaka.upper().replace(" ", "")
    if plaka and plaka not in plaka_listesini_getir():
        with open(PLAKA_DOSYASI, "a") as f:
            f.write(plaka + "\n")

def plaka_sil(plaka):
    plakalar = plaka_listesini_getir()
    if plaka in plakalar:
        plakalar.remove(plaka)
        with open(PLAKA_DOSYASI, "w") as f:
            for p in plakalar: f.write(p + "\n")

if not os.path.exists(PLAKA_DOSYASI):
    plaka_ekle("02ABG585")

# ══════════════════════════════════════════════════════════════
# THREAD 1 — FLASK WEB SUNUCUSU
# ══════════════════════════════════════════════════════════════
app = Flask(__name__)
HTML_SABLON = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Akıllı Bariyer Paneli</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f4f7f6; color: #333; text-align: center; padding: 20px; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); max-width: 500px; margin: 0 auto 20px auto; }
        img { max-width: 100%; border-radius: 8px; border: 2px solid #ddd; }
        .btn { background: #28a745; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; text-decoration: none; display: inline-block;}
        .btn-mavi { background: #007bff; }
        .btn-gri { background: #6c757d; }
        .btn-sil { background: #dc3545; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 14px; }
        input { padding: 10px; width: 60%; border: 1px solid #ccc; border-radius: 5px; }
        ul { list-style: none; padding: 0; }
        li { background: #e9ecef; margin: 5px 0; padding: 10px; border-radius: 5px; display: flex; justify-content: space-between; }
        .durum { font-size: 18px; font-weight: bold; color: #0056b3; }
        .buton-grubu { display: flex; justify-content: space-around; margin-top: 15px; }
    </style>
</head>
<body>
    <h2>Akıllı Bariyer Yönetim Paneli</h2>
    
    <div class="card">
        <h3>Manuel Kapı Kontrolü</h3>
        <div class="buton-grubu">
            <a href="/manuel/ac" class="btn btn-mavi">⬆️ Kapıyı Aç</a>
            <a href="/manuel/kapat" class="btn btn-gri">⬇️ Kapıyı Kapat</a>
        </div>
    </div>

    <div class="card">
        <h3>Son İşlem Gören Araç</h3>
        <p class="durum">{{ sistem_durumu['durum'] }}</p>
        <p><b>Plaka:</b> {{ sistem_durumu['son_plaka'] }} <br> <b>Saat:</b> {{ sistem_durumu['son_zaman'] }}</p>
        <img src="/foto?{{ rand }}" alt="Son Araç Fotoğrafı">
    </div>
    
    <div class="card">
        <h3>İzinli Plakalar Listesi</h3>
        <ul>
            {% for p in plakalar %}
                <li>{{ p }} <a href="/sil/{{ p }}" class="btn-sil">Sil</a></li>
            {% endfor %}
        </ul>
        <form action="/ekle" method="POST" style="margin-top: 15px;">
            <input type="text" name="yeni_plaka" placeholder="Örn: 34ABC123" required>
            <button type="submit" class="btn">Plaka Ekle</button>
        </form>
    </div>
</body>
</html>
"""
@app.route("/test")
def test():
    return "Flask calisiyor"

@app.route("/")
def index():
    try:
        return render_template_string(
            HTML_SABLON,
            plakalar=plaka_listesini_getir(),
            sistem_durumu=sistem_durumu,
            rand=time.time()
        )
    except Exception as e:
        return f"HATA: {str(e)}", 500

@app.route("/foto")
def foto():
    if os.path.exists(SON_GECIS_RESIM):
        return send_file(SON_GECIS_RESIM, mimetype='image/jpeg')
    return "Fotoğraf yok", 404

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
    # Queue üzerinden komut gönder — direkt global değişken YOK
    if islem in ("ac", "kapat"):
        komut_kuyrugu.put(islem.upper())
    return "<script>window.location.href='/';</script>"

def web_thread():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# ══════════════════════════════════════════════════════════════
# THREAD 2 — SENSÖR + PLAKA OKUMA
# ══════════════════════════════════════════════════════════════
def plaka_kontrol_et():
    """Fotoğraf çek, API'ye gönder, yetkili mi kontrol et."""
    if os.path.exists(GECICI_RESIM): os.remove(GECICI_RESIM)
    subprocess.run("pkill rpicam-vid", shell=True)
    time.sleep(0.2)
    subprocess.run(
        f"rpicam-still -n -t 10 --immediate --width 800 --height 600 -o {GECICI_RESIM}",
        shell=True
    )
    subprocess.Popen(
        "DISPLAY=:0 rpicam-vid -t 0 --width 640 --height 480 --inline --preview 0,0,640,480 &",
        shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    if not os.path.exists(GECICI_RESIM): return False

    try:
        with open(GECICI_RESIM, "rb") as fp:
            r = requests.post(
                "https://api.platerecognizer.com/v1/plate-reader/",
                data={"regions": "tr"}, files={"upload": fp},
                headers={"Authorization": f"Token {API_TOKEN}"},
                timeout=10
            )
        if r.status_code in (200, 201):
            results = r.json().get("results", [])
            if results:
                shutil.copy(GECICI_RESIM, SON_GECIS_RESIM)
                plaka = results[0].get("plate", "").upper()
                print(f"[KAMERA] Okunan: {plaka}")
                sistem_durumu.update({
                    "son_plaka": plaka,
                    "son_zaman": time.strftime("%H:%M:%S")
                })
                if plaka in plaka_listesini_getir():
                    sistem_durumu["durum"] = "GİRİŞ ONAYLANDI"
                    return True
                sistem_durumu["durum"] = "REDDEDİLDİ"
    except Exception as e:
        print(f"[HATA] {e}")
    return False

def sensor_ve_plaka_thread():
    """
    Kapı kapalıyken sürekli araç bekle.
    Araç tespit edilirse plaka kontrol et, yetkililiyse aç sinyali ver.
    """
    while True:
        if kapi_acik_event.is_set():
            # Kapı zaten açık — bu thread bekler
            time.sleep(0.5)
            continue

        # Manuel komut var mı? (Kuyruktan bak, blocking değil)
        try:
            komut = komut_kuyrugu.get_nowait()
            if komut == "AC":
                sistem_durumu.update({
                    "son_plaka": "Manuel Giriş",
                    "son_zaman": time.strftime("%H:%M:%S"),
                    "durum":     "WEB PANELİNDEN AÇILDI"
                })
                kapi_ac_event.set()
                continue
            elif komut == "KAPAT":
                kapi_kapat_event.set()
                continue
        except:
            pass  # Kuyruk boşsa devam

        print("\r[SİSTEM] Araç bekleniyor...", end="", flush=True)
        if plaka_kontrol_et():
            kapi_ac_event.set()
        else:
            time.sleep(0.5)

# ══════════════════════════════════════════════════════════════
# THREAD 3 — MOTOR KONTROL
# ══════════════════════════════════════════════════════════════
def motoru_dondur(dongu_sayisi, yon, guvenlik_kontrolu=False):
    atilan = 0
    for _ in range(dongu_sayisi):
        if guvenlik_kontrolu and ldr.value == LDR_ARABA_VAR:
            return atilan
        for step in range(8):
            idx = step if yon == 1 else (7 - step)
            for i in range(4):
                (step_pins[i].on if step_sequence[idx][i] else step_pins[i].off)()
            time.sleep(MOTOR_HIZI)
        atilan += 1
    return True

def kapiyi_ac():
    motoru_dondur(ADIM_90_DERECE, yon=1)

def kapiyi_kapat():
    sonuc = motoru_dondur(ADIM_90_DERECE, yon=-1, guvenlik_kontrolu=True)
    if sonuc is not True:
        print("[ACİL] Araç var! Geri açılıyor!")
        motoru_dondur(sonuc, yon=1)
        return False
    for p in step_pins: p.off()
    return True

def motor_thread():
    while True:
        if not kapi_ac_event.wait(timeout=0.1):
            continue

        kapi_ac_event.clear()
        print("\n[MOTOR] Kapi aciliyor...")
        kapiyi_ac()
        kapi_acik_event.set()

        # 10 saniye bekle veya erken kapat komutu gel
        print("[MOTOR] 10 sn bekleniyor...")
        kapi_kapat_event.wait(timeout=10)
        kapi_kapat_event.clear()

        # Kapanma döngüsü — başarılı kapanana kadar tekrar dener
        while True:
            # Önce lazer hattı temizlenene kadar bekle
            while ldr.value == LDR_ARABA_VAR:
                print("[UYARI] Arac kapida, bekleniyor...")
                time.sleep(1)
                if kapi_kapat_event.is_set():
                    kapi_kapat_event.clear()

            # Lazer temiz — 3 saniye daha bekle, emin ol
            print("[MOTOR] Lazer temiz, 3 sn bekleniyor...")
            time.sleep(3)

            # 3 saniye sonra hala temiz mi?
            if ldr.value == LDR_ARABA_VAR:
                print("[UYARI] Arac tekrar geldi, beklemeye devam...")
                continue  # Başa dön, tekrar bekle

            # Temiz, kapatmayı dene
            print("[MOTOR] Kapatiliyor...")
            if kapiyi_kapat():
                print("[MOTOR] Kapi kapandi.")
                break  # Başarılı, döngüden çık
            else:
                # Kapanma sırasında biri geçti
                # kapiyi_kapat() zaten geri açtı
                print("[MOTOR] Gecis algilandi! 5 sn sonra tekrar denenecek...")
                time.sleep(5)  # 5 saniye bekle, tekrar dene
                # while True döngüsü başa döner

        kapi_acik_event.clear()

# ══════════════════════════════════════════════════════════════
# MAIN — Thread'leri başlat
# ══════════════════════════════════════════════════════════════
def main():
    print("=== Bariyer Sistemi Başlatılıyor ===")
    for p in step_pins: p.off()

    subprocess.Popen(
        "DISPLAY=:0 rpicam-vid -t 0 --width 640 --height 480 --inline --preview 0,0,640,480 &",
        shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(2)

    Thread(target=web_thread,              daemon=True, name="Web").start()
    Thread(target=sensor_ve_plaka_thread,  daemon=True, name="Sensör").start()
    Thread(target=motor_thread,            daemon=True, name="Motor").start()

    print("=== Tüm thread'ler aktif ===")

    try:
        while True:
            time.sleep(1)   # Ana thread sadece hayatta tutar
    except KeyboardInterrupt:
        print("\n[SİSTEM] Kapatılıyor...")
    finally:
        for p in step_pins: p.off()
        subprocess.run("pkill rpicam-vid", shell=True)

if __name__ == "__main__":
    main()