import os
import subprocess
import time
import requests
from gpiozero import OutputDevice, DigitalInputDevice

# --- API AYARLARI ---
API_TOKEN = "e8dbc6b3a35577a8af907c118920c24ae404d3bb" 

# --- STEP MOTOR AYARLARI ---
# ULN2003 motor sürücü kartının pinleri
PIN_IN1 = 18
PIN_IN2 = 23
PIN_IN3 = 24
PIN_IN4 = 25

step_pins = [
    OutputDevice(PIN_IN1),
    OutputDevice(PIN_IN2),
    OutputDevice(PIN_IN3),
    OutputDevice(PIN_IN4)
]

# 28BYJ-48 motoru için yarım adım (Half-step) dizilimi (En pürüzsüz dönüş)
step_sequence = [
    [1,0,0,0],
    [1,1,0,0],
    [0,1,0,0],
    [0,1,1,0],
    [0,0,1,0],
    [0,0,1,1],
    [0,0,0,1],
    [1,0,0,1]
]

# Kalibrasyon Ayarları: 
# 28BYJ-48 tam turu (360 derece) 4096 adımdır. Çeyrek tur (90 derece) = 1024 adım.
# Eğer kapı 90 dereceyi biraz geçerse bu değeri 1000 yap, eksik kalırsa 1050 yap.
ADIM_90_DERECE = 1024 
MOTOR_HIZI = 0.001 # Adımlar arası bekleme süresi (Küçüldükçe bariyer hızlanır)

# --- SENSÖR AYARLARI ---
LDR_PIN = 17
ldr = DigitalInputDevice(LDR_PIN)

# --- SİSTEM AYARLARI ---
GECERLI_PLAKA = "02ABG585"
GECICI_RESIM = "plaka.jpg"

def motoru_dondur(adim_sayisi, yon):
    """yon: 1 ise açılma (saat yönü), -1 ise kapanma (tersi)"""
    for _ in range(adim_sayisi):
        for step in range(8):
            # Yöne göre dizilimde ileri veya geri gidiyoruz
            seq_index = step if yon == 1 else (7 - step)
            for pin_num in range(4):
                if step_sequence[seq_index][pin_num] == 1:
                    step_pins[pin_num].on()
                else:
                    step_pins[pin_num].off()
            time.sleep(MOTOR_HIZI)

def kapiyi_ac():
    print("\n[STEP MOTOR] Bariyer pürüzsüzce 90 derece YUKARI kaldırılıyor...")
    motoru_dondur(ADIM_90_DERECE, yon=1)
    # Motor açık pozisyonda beklerken kolun düşmemesi için enerjiyi kesmiyoruz (tutunma torku devrede)

def kapiyi_kapat():
    print("[STEP MOTOR] Güvenli. Bariyer pürüzsüzce AŞAĞI indiriliyor...")
    motoru_dondur(ADIM_90_DERECE, yon=-1)
    
    # Motor kapalı pozisyondayken ısınıp bozulmaması için tüm pinlerin enerjisini kesiyoruz
    for pin in step_pins:
        pin.off()

# === KAMERA VE YAPAY ZEKA KISMI (HİÇ DOKUNULMADI) ===
def plaka_kontrol_et():
    print("\n[KAMERA] Analiz için anlık fotoğraf yakalanıyor...")
    
    if os.path.exists(GECICI_RESIM):
        os.remove(GECICI_RESIM)

    subprocess.run("pkill rpicam-vid", shell=True)
    time.sleep(1) 

    print("[SİSTEM] rpicam-still komutu tetikleniyor...")
    cmd_capture = f"rpicam-still -n --immediate -o {GECICI_RESIM}"
    subprocess.run(cmd_capture, shell=True) 

    cmd_video = "DISPLAY=:0 rpicam-vid -t 0 --width 640 --height 480 --inline --preview 0,0,640,480 &"
    subprocess.Popen(cmd_video, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not os.path.exists(GECICI_RESIM):
        print("[HATA] Fotoğraf oluşturulamadı! Lütfen bağlantıyı kontrol edin.")
        return False

    print("[YAPAY ZEKA] Plaka API üzerinden analiz ediliyor...")
    
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
                    
                    if GECERLI_PLAKA in okunan_plaka:
                        return True
                else:
                    print("[ALPR] Fotoğrafta plaka tespit edilemedi.")
            else:
                print(f"[HATA] API Hatası: {response.status_code}")
        except Exception as e:
            print(f"[HATA] Bağlantı hatası oluştu: {e}")
            
    return False

def main():
    print("==================================================")
    print("===  Step Motorlu Profesyonel Bariyer Sistemi  ===")
    print("==================================================")
    
    # Motorun mevcut konumunu "kapalı" (sıfır noktası) olarak kabul et
    for pin in step_pins:
        pin.off()
    
    print("[KAMERA] Canlı video akışı başlatılıyor...")
    cmd_video = "DISPLAY=:0 rpicam-vid -t 0 --width 640 --height 480 --inline --preview 0,0,640,480 &"
    subprocess.Popen(cmd_video, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)

    try:
        while True:
            print("\n[SİSTEM] Araç bekleniyor (Plaka taraması devrede)...")
            
            if not plaka_kontrol_et():
                print("[GÜVENLİK] Tanımsız plaka veya erişim reddedildi.")
                time.sleep(3)
                continue

            print(f"[ONAY] Plaka doğrulandı: {GECERLI_PLAKA}. Giriş izni verildi!")
            kapiyi_ac()
            time.sleep(1) 

            print("[GÜVENLİK] Lazer hattı devrede, araç geçişi izleniyor...")
            
            while True:
                if ldr.value == 0:
                    print("[UYARI] Araç algılandı (Lazer Hattı Kesik)! Kapı KAPANAMAZ.")
                else:
                    print("[TEMİZ] Lazer hattı net. Araç geçti veya alan boş.")
                    print("[SİSTEM] Kapı kapatılmak üzere geri sayım: 2 saniye...")
                    time.sleep(2)
                    
                    if ldr.value == 1:
                        break 
                
                time.sleep(0.1)

            kapiyi_kapat()
            time.sleep(1)
            print("[SİSTEM] Araç başarıyla geçti. Sistem sıfırlandı.")

    except KeyboardInterrupt:
        print("\n[SİSTEM] Program kapatılıyor...")
    finally:
        # Kapatırken motorun enerjisini kes
        for pin in step_pins:
            pin.off()
        subprocess.run("pkill rpicam-vid", shell=True)
        print("[SİSTEM] Kamera kapatıldı, çıkış yapılıyor.")

if __name__ == "__main__":
    main()