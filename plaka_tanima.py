import os
import subprocess
import time
import requests
from gpiozero import PWMOutputDevice, DigitalInputDevice
from gpiozero.pins.pigpio import PiGPIOFactory

# --- API AYARLARI ---
API_TOKEN = "e8dbc6b3a35577a8af907c118920c24ae404d3bb" 

# --- SERVO (PULSE TIME) KALİBRASYONU ---
# Hobi servoları 50Hz (20ms periyot) ile çalışır.
# Aşağıdaki değerler doğrudan motorun dönüş sınırlarını belirler:
KAPALI_SINYAL = 0.05  # Yaklaşık 1.0ms (0 derece - Kapalı)
ACIK_SINYAL = 0.11    # Yaklaşık 2.0ms (Tam 90 derece açısı için)
# NOT: Eğer hala 90 dereceye ulaşmazsa ACIK_SINYAL değerini 0.11 veya 0.12 yap!
# Eğer 90 dereceyi geçerse ACIK_SINYAL değerini 0.09 yap.

BARIYER_HIZI = 0.0008  # Adımlar arası bekleme süresi (Pürüzsüzlük ayarı)

# --- DONANIM AYARLARI ---
try:
    factory = PiGPIOFactory()
    # Servo pinini doğrudan PWM (Sinyal Süresi) cihazı olarak tanımlıyoruz (Frekans: 50Hz)
    servo = PWMOutputDevice(18, frequency=50, pin_factory=factory)
except OSError:
    print("[HATA] pigpio servisi arka planda çalışmıyor! Terminale 'sudo pigpiod' yazın.")
    exit(1)

LDR_PIN = 17
ldr = DigitalInputDevice(LDR_PIN)

# --- SİSTEM AYARLARI ---
GECERLI_PLAKA = "02ABG585"
GECICI_RESIM = "plaka.jpg"

# Başlangıçta mevcut sinyal durumunu tutuyoruz
su_anki_sinyal = KAPALI_SINYAL
servo.value = KAPALI_SINYAL

# Sinyal değerini mikroskobik adımlarla değiştirerek pürüzsüz hareket sağlıyoruz
def pruzsuz_hareket_et(hedef_sinyal):
    global su_anki_sinyal
    
    # Sinyalin artacağını mı azalacağını mı belirliyoruz
    adim = 0.001 if hedef_sinyal > su_anki_sinyal else -0.001
    
    # Hedef sinyal değerine ulaşana kadar küçük adımlarla ilerle
    while abs(su_anki_sinyal - hedef_sinyal) > 0.0005:
        su_anki_sinyal += adim
        servo.value = su_anki_sinyal
        time.sleep(BARIYER_HIZI)
        
    # Tam değere eşitle
    su_anki_sinyal = hedef_sinyal
    servo.value = hedef_sinyal

def kapiyi_ac():
    print("\n[SERVO] Kapı KALİBRE EDİLMİŞ sinyal ile açılıyor (Tam 90 derece)...")
    pruzsuz_hareket_et(ACIK_SINYAL)

def kapiyi_kapat():
    print("[SERVO] Güvenli. Kapı KALİBRE EDİLMİŞ sinyal ile kapanıyor (0 derece)...")
    pruzsuz_hareket_et(KAPALI_SINYAL)

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
    print("===  PWM Sinyal Kalibrasyonlu Bariyer Sistemi  ===")
    print("==================================================")
    
    kapiyi_kapat()
    
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
        servo.value = 0 # Motorun enerjisini kes (titremeyi önler)
        subprocess.run("pkill rpicam-vid", shell=True)
        print("[SİSTEM] Kamera kapatıldı, çıkış yapılıyor.")

if __name__ == "__main__":
    main()
