import os
import subprocess
import time
import requests
import shutil
import os
from threading import Thread
from flask import Flask, request, render_template_string, send_file
from gpiozero import OutputDevice, DigitalInputDevice

# --- API AYARLARI ---
API_TOKEN = "e8dbc6b3a35577a8af907c118920c24ae404d3bb" 

# --- STEP MOTOR AYARLARI ---
PIN_IN1 = 18
PIN_IN2 = 23
PIN_IN3 = 24
PIN_IN4 = 25

step_pins = [OutputDevice(PIN_IN1), OutputDevice(PIN_IN2), OutputDevice(PIN_IN3), OutputDevice(PIN_IN4)]
step_sequence = [[1,0,0,0], [1,1,0,0], [0,1,0,0], [0,1,1,0], [0,0,1,0], [0,0,1,1], [0,0,0,1], [1,0,0,1]]

ADIM_90_DERECE = 128 
MOTOR_HIZI = 0.0025 

# --- SENSÖR (LDR) AYARLARI ---
LDR_PIN = 17
ldr = DigitalInputDevice(LDR_PIN)
LDR_ARABA_VAR = 1  

# --- SİSTEM VE DOSYA AYARLARI ---
GECICI_RESIM = "plaka.jpg"
SON_GECIS_RESIM = "son_gecis.jpg" 
PLAKA_DOSYASI = "plakalar.txt"

# Web panelinden gelen manuel komutları yakalamak için global değişken
global_komut = None

sistem_durumu = {
    "son_plaka": "Henüz geçiş yok",
    "son_zaman": "-",
    "durum": "Bekleniyor..."
}

def plaka_listesini_getir():
    if not os.path.exists(PLAKA_DOSYASI): return []
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
            for p in plakalar: f.write(p + "\n")

if not os.path.exists(PLAKA_DOSYASI):
    plaka_ekle("02ABG585")

# --- WEB SUNUCUSU (FLASK) ---
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

@app.route("/")
def index():
    return render_template_string(HTML_SABLON, plakalar=plaka_listesini_getir(), sistem_durumu=sistem_durumu, rand=time.time())

@app.route("/foto")
def foto():
    if os.path.exists(SON_GECIS_RESIM): return send_file(SON_GECIS_RESIM, mimetype='image/jpeg')
    return "Fotoğraf yok", 404

@app.route("/ekle", methods=["POST"])
def ekle():
    plaka_ekle(request.form.get("yeni_plaka"))
    return "<script>window.location.href='/';</script>"

@app.route("/sil/<plaka>")
def sil(plaka):
    plaka_sil(plaka)
    return "<script>window.location.href='/';</script>"

@app.route("/manuel/<islem>")
def manuel(islem):
    global global_komut
    if islem == "ac":
        global_komut = "AC"
    elif islem == "kapat":
        global_komut = "KAPAT"
    return "<script>window.location.href='/';</script>"

def web_sunucusunu_baslat():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# --- DONANIM FONKSİYONLARI ---
def motoru_dondur(dongu_sayisi, yon, guvenlik_kontrolu=False):
    atilan_dongu = 0
    for _ in range(dongu_sayisi):
        if guvenlik_kontrolu and ldr.value == LDR_ARABA_VAR:
            return atilan_dongu 

        for step in range(8):
            seq_index = step if yon == 1 else (7 - step)
            for pin_num in range(4):
                if step_sequence[seq_index][pin_num] == 1:
                    step_pins[pin_num].on()
                else:
                    step_pins[pin_num].off()
            time.sleep(MOTOR_HIZI)
        atilan_dongu += 1
        
    return True 

def kapiyi_ac():
    motoru_dondur(ADIM_90_DERECE, yon=1)

def kapiyi_kapat():
    print("[SİSTEM] Kapı kapatılıyor...")
    sonuc = motoru_dondur(ADIM_90_DERECE, yon=-1, guvenlik_kontrolu=True)
    
    if sonuc is not True:
        print("\n[ACİL DURUM] Araç algılandı! Kapı GERİ AÇILIYOR!")
        motoru_dondur(sonuc, yon=1) 
        return False 
    
    for pin in step_pins:
        pin.off()
    return True 

def plaka_kontrol_et():
    if os.path.exists(GECICI_RESIM): os.remove(GECICI_RESIM)

    subprocess.run("pkill rpicam-vid", shell=True)
    time.sleep(0.2) 
    
    cmd_capture = f"rpicam-still -n -t 10 --immediate --width 800 --height 600 -o {GECICI_RESIM}"
    subprocess.run(cmd_capture, shell=True) 
    
    subprocess.Popen("DISPLAY=:0 rpicam-vid -t 0 --width 640 --height 480 --inline --preview 0,0,640,480 &", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not os.path.exists(GECICI_RESIM): return False

    with open(GECICI_RESIM, "rb") as fp:
        try:
            response = requests.post(
                "https://api.platerecognizer.com/v1/plate-reader/",
                data={"regions": "tr"}, files={"upload": fp}, 
                headers={"Authorization": f"Token {API_TOKEN}"},
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                results = response.json().get("results", [])
                
                # DÜZELTME: Sadece gerçekten plaka bulunduğunda fotoğrafı kopyala ve paneli güncelle
                if results:
                    shutil.copy(GECICI_RESIM, SON_GECIS_RESIM)
                    
                    okunan_plaka = results[0].get("plate", "").upper()
                    print(f"\n[KAMERA GÖRDÜ] Okunan Plaka: {okunan_plaka}")
                    
                    sistem_durumu["son_plaka"] = okunan_plaka
                    sistem_durumu["son_zaman"] = time.strftime("%H:%M:%S")
                    
                    if okunan_plaka in plaka_listesini_getir():
                        sistem_durumu["durum"] = "GİRİŞ ONAYLANDI"
                        return True
                    else:
                        sistem_durumu["durum"] = "REDDEDİLDİ (Kayıtsız Plaka)"
                        
                # Eğer fotoda plaka yoksa, pas geç. Site boşu boşuna güncellenmez.
        except Exception as e:
            print(f"[HATA] Bağlantı veya API Hatası: {e}")
            
    return False

def main():
global global_komut
    
    # --- RTOS ÖNCELİKLENDİRME (SCHED_FIFO) ---
    try:
        # Mevcut sürecin (PID 0) önceliğini gerçek zamanlı (SCHED_FIFO) ve en yüksek (99) seviyeye çekiyoruz.
        param = os.sched_param(99)
        os.sched_setscheduler(0, os.SCHED_FIFO, param)
        print("[RTOS] Sistem SCHED_FIFO gerçek zamanlı görev (Real-Time Task) önceliğine alındı.")
    except Exception as e:
        print(f"[UYARI] RTOS önceliği reddedildi (Sudo ile çalıştırın!): {e}")
    # ----------------------------------------

    print("==================================================")
    print("=== Turbo Hızlandırılmış Bariyer Sistemi Aktif ===")
    print("==================================================")

    Thread(target=web_sunucusunu_baslat, daemon=True).start()
    for pin in step_pins: pin.off()
    
    subprocess.Popen("DISPLAY=:0 rpicam-vid -t 0 --width 640 --height 480 --inline --preview 0,0,640,480 &", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)

    try:
        while True:
            manuel_acildi = False
            
            if global_komut == "AC":
                manuel_acildi = True
                global_komut = None
                print("\n[WEB] Manuel AÇMA komutu tetiklendi!")
                sistem_durumu["son_plaka"] = "Manuel Giriş"
                sistem_durumu["son_zaman"] = time.strftime("%H:%M:%S")
                sistem_durumu["durum"] = "WEB PANELİNDEN AÇILDI"
            else:
                print("\r[SİSTEM] Yeni araç bekleniyor...", end="", flush=True)
                if not plaka_kontrol_et():
                    time.sleep(0.5) 
                    continue

            if not manuel_acildi:
                print("\n[ONAY] Plaka yetkili! Kapı açılıyor...")
                
            kapiyi_ac()

            kapi_acik = True
            while kapi_acik:
                print("[SİSTEM] 10 Sn otomatik bekleme başladı (Web'den hemen kapatabilirsiniz)...")
                
                for _ in range(10):
                    if global_komut == "KAPAT":
                        print("\n[WEB] Manuel KAPATMA komutu tetiklendi, 10sn iptal edildi!")
                        global_komut = None
                        break 
                    time.sleep(1)
                
                while ldr.value == LDR_ARABA_VAR:
                    print("[UYARI] Süre doldu ama araç hala kapının altında! Bekleniyor...")
                    time.sleep(2)
                    if global_komut == "KAPAT":
                        print("[WEB] Güvenlik İhlali: Araç varken manuel KAPANAMAZ!")
                        global_komut = None 
                
                print("[SİSTEM] Lazer hattı temiz. Kapı kapatılmaya başlanıyor...")
                if kapiyi_kapat():
                    print("[SİSTEM] Kapı başarıyla kapandı.")
                    kapi_acik = False 
                else:
                    print("[SİSTEM] Kapanma esnasında güvenlik ihlali! Tekrar beklenecek...")
                    global_komut = None

    except KeyboardInterrupt:
        print("\n[SİSTEM] Kapatılıyor...")
    finally:
        for pin in step_pins: pin.off()
        subprocess.run("pkill rpicam-vid", shell=True)

if __name__ == "__main__":
    main()