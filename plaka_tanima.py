import os
import subprocess
import time
import requests
import shutil
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

ADIM_90_DERECE = 512 
MOTOR_HIZI = 0.001 

# --- SENSÖR AYARLARI ---
LDR_PIN = 17
ldr = DigitalInputDevice(LDR_PIN)

# --- SİSTEM VE DOSYA AYARLARI ---
GECICI_RESIM = "plaka.jpg"
SON_GECIS_RESIM = "son_gecis.jpg" # Web'de göstermek için kopyalayacağımız dosya
PLAKA_DOSYASI = "plakalar.txt"

# Web panelinde göstermek için anlık veriler
sistem_durumu = {
    "son_plaka": "Henüz geçiş yok",
    "son_zaman": "-",
    "durum": "Bekleniyor..."
}

# --- PLAKA YÖNETİM FONKSİYONLARI ---
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

# İlk kurulumda örnek plakayı dosyaya yazalım
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
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #333; text-align: center; padding: 20px; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); max-width: 500px; margin: 0 auto 20px auto; }
        img { max-width: 100%; border-radius: 8px; border: 2px solid #ddd; }
        .btn { background: #28a745; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; }
        .btn-sil { background: #dc3545; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 14px; }
        input { padding: 10px; width: 60%; border: 1px solid #ccc; border-radius: 5px; }
        ul { list-style: none; padding: 0; }
        li { background: #e9ecef; margin: 5px 0; padding: 10px; border-radius: 5px; display: flex; justify-content: space-between; align-items: center; }
        .durum { font-size: 18px; font-weight: bold; color: #0056b3; }
    </style>
</head>
<body>
    <h2>Akıllı Bariyer Yönetim Paneli</h2>
    
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
    return render_template_string(HTML_SABLON, 
                                  plakalar=plaka_listesini_getir(), 
                                  sistem_durumu=sistem_durumu, 
                                  rand=time.time())

@app.route("/foto")
def foto():
    if os.path.exists(SON_GECIS_RESIM):
        return send_file(SON_GECIS_RESIM, mimetype='image/jpeg')
    return "Fotoğraf yok", 404

@app.route("/ekle", methods=["POST"])
def ekle():
    yeni_plaka = request.form.get("yeni_plaka")
    plaka_ekle(yeni_plaka)
    return "<script>window.location.href='/';</script>"

@app.route("/sil/<plaka>")
def sil(plaka):
    plaka_sil(plaka)
    return "<script>window.location.href='/';</script>"

def web_sunucusunu_baslat():
    # Arka planda 5000 portundan yayına başlar
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# --- DONANIM VE YZ FONKSİYONLARI ---
def motoru_dondur(adim_sayisi, yon, guvenlik_kontrolu=False):
    atilan_adim = 0
    for _ in range(adim_sayisi):
        if guvenlik_kontrolu and ldr.value == 1:
            print("[ACİL DURUM] Kapanırken araç algılandı! Hareket durduruluyor...")
            return atilan_adim 

        for step in range(8):
            seq_index = step if yon == 1 else (7 - step)
            for pin_num in range(4):
                if step_sequence[seq_index][pin_num] == 1:
                    step_pins[pin_num].on()
                else:
                    step_pins[pin_num].off()
            time.sleep(MOTOR_HIZI)
        atilan_adim += 1
        
    return True 

def kapiyi_ac():
    motoru_dondur(ADIM_90_DERECE, yon=1)

def kapiyi_kapat():
    sonuc = motoru_dondur(ADIM_90_DERECE, yon=-1, guvenlik_kontrolu=True)
    if sonuc is not True:
        print("[GÜVENLİK] Kapı çarpmasını önlemek için tekrar AÇILIYOR!")
        motoru_dondur(sonuc, yon=1) 
        return False 
    
    for pin in step_pins:
        pin.off()
    return True 

def plaka_kontrol_et():
    print("\n[KAMERA] Analiz için anlık fotoğraf yakalanıyor...")
    
    if os.path.exists(GECICI_RESIM):
        os.remove(GECICI_RESIM)

    subprocess.run("pkill rpicam-vid", shell=True)
    time.sleep(1) 

    cmd_capture = f"rpicam-still -n --immediate -o {GECICI_RESIM}"
    subprocess.run(cmd_capture, shell=True) 

    cmd_video = "DISPLAY=:0 rpicam-vid -t 0 --width 640 --height 480 --inline --preview 0,0,640,480 &"
    subprocess.Popen(cmd_video, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not os.path.exists(GECICI_RESIM):
        return False

    # Web'de göstermek için son çekilen fotoğrafı sakla
    shutil.copy(GECICI_RESIM, SON_GECIS_RESIM)

    with open(GECICI_RESIM, "rb") as fp:
        try:
            response = requests.post(
                "https://api.platerecognizer.com/v1/plate-reader/",
                data={"regions": "tr"},
                files={"upload": fp},
                headers={"Authorization": f"Token {API_TOKEN}"}
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                results = data.get("results", [])
                
                if results:
                    okunan_plaka = results[0].get("plate", "").upper()
                    print(f"[KAMERA GÖRDÜ] Okunan Plaka: {okunan_plaka}")
                    
                    # Web paneli için verileri güncelle
                    sistem_durumu["son_plaka"] = okunan_plaka
                    sistem_durumu["son_zaman"] = time.strftime("%H:%M:%S - %d/%m/%Y")
                    
                    izinli_plakalar = plaka_listesini_getir()
                    if okunan_plaka in izinli_plakalar:
                        sistem_durumu["durum"] = "GİRİŞ ONAYLANDI"
                        return True
                    else:
                        sistem_durumu["durum"] = "REDDEDİLDİ (Kayıtsız Plaka)"
                else:
                    sistem_durumu["son_plaka"] = "Okunamadı"
                    sistem_durumu["durum"] = "Plaka Tespit Edilemedi"
        except Exception as e:
            print(f"[HATA] Bağlantı hatası: {e}")
            
    return False

def main():
    print("==================================================")
    print("===  Bulut Bağlantılı Akıllı Bariyer Sistemi   ===")
    print("==================================================")
    
    # Web sunucusunu arka planda başlat
    Thread(target=web_sunucusunu_baslat, daemon=True).start()
    print("[SİSTEM] Web yönetim paneli aktif! (Port: 5000)")

    for pin in step_pins:
        pin.off()
    
    print("[KAMERA] Canlı video akışı başlatılıyor...")
    cmd_video = "DISPLAY=:0 rpicam-vid -t 0 --width 640 --height 480 --inline --preview 0,0,640,480 &"
    subprocess.Popen(cmd_video, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)

    try:
        while True:
            if not plaka_kontrol_et():
                time.sleep(3)
                continue

            kapiyi_ac()
            time.sleep(1) 

            kapi_acik = True
            while kapi_acik:
                while True:
                    if ldr.value == 0:
                        pass # Lazer kesik
                    else:
                        time.sleep(2)
                        if ldr.value == 0:
                            break 
                    time.sleep(0.1)

                if kapiyi_kapat():
                    kapi_acik = False 
                else:
                    time.sleep(2)

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[SİSTEM] Program kapatılıyor...")
    finally:
        for pin in step_pins:
            pin.off()
        subprocess.run("pkill rpicam-vid", shell=True)

if __name__ == "__main__":
    main()