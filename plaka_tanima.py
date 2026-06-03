import os
import subprocess
import time
import requests
from gpiozero import OutputDevice, DigitalInputDevice

# --- API AYARLARI ---
API_TOKEN = "e8dbc6b3a35577a8af907c118920c24ae404d3bb" 

# --- STEP MOTOR AYARLARI ---
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
# Eğer hala fazla dönüyorsa bu değeri 500 veya 480 yap. Eksik dönüyorsa 550 yap.
ADIM_90_DERECE = 512 
MOTOR_HIZI = 0.001 

# --- SENSÖR AYARLARI ---
LDR_PIN = 17
ldr = DigitalInputDevice(LDR_PIN)

# --- SİSTEM AYARLARI ---
GECERLI_PLAKA = "02ABG585"
GECICI_RESIM = "plaka.jpg"

def motoru_dondur(adim_sayisi, yon, guvenlik_kontrolu=False):
    """
    yon: 1 ise açılma (saat yönü), -1 ise kapanma.
    guvenlik_kontrolu: True ise adım atarken LDR'yi kontrol eder.
    Geri dönüş değeri: Eğer hareket tamamlansa True, güvenlik sebebiyle iptal olursa atılan_adim_sayisi döner.
    """
    atilan_adim = 0
    for _ in range(adim_sayisi):
        # Eğer güvenlik kontrolü açıksa ve lazer kesildiyse (LDR == 1) hareketi durdur
        if guvenlik_kontrolu and ldr.value == 1:
            print("[ACİL DURUM] Kapanırken araç algılandı! Hareket durduruluyor...")
            return atilan_adim # Kaç adım inmişse onu döndür ki o kadar geri çıksın

        for step in range(8):
            seq_index = step if yon == 1 else (7 - step)
            for pin_num in range(4):
                if step_sequence[seq_index][pin_num] == 1:
                    step_pins[pin_num].on()
                else:
                    step_pins[pin_num].off()
            time.sleep(MOTOR_HIZI)
        atilan_adim += 1
        
    return True # Hareket sorunsuz tamamlandı

def kapiyi_ac():
    print("\n[STEP MOTOR] Bariyer pürüzsüzce 90 derece YUKARI kaldırılıyor...")
    motoru_dondur(ADIM_90_DERECE, yon=1)

def kapiyi_kapat():
    print("[STEP MOTOR] Güvenli. Bariyer pürüzsüzce AŞAĞI indiriliyor...")
    
    # Kapanırken güvenlik kontrolünü (LDR takibini) aktif ediyoruz
    sonuc = motoru_dondur(ADIM_90_DERECE, yon=-1, guvenlik_kontrolu=True)
    
    # Eğer sonuc True değilse, kapı tam kapanamadan araya biri girmiş demektir
    if sonuc is not True:
        # İnilen adım sayısı kadar geri yukarı (yon=1) çık
        print("[GÜVENLİK] Kapı çarpmasını önlemek için tekrar AÇILIYOR!")
        motoru_dondur(sonuc, yon=1) 
        return False # Kapı kapanamadı bilgisini ana döngüye gönder
    
    # Sorunsuz kapandıysa motorun enerjisini kes
    for pin in step_pins:
        pin.off()
    return True # Kapı başarıyla kapandı

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

            # Araç tamamen geçene kadar kapıyı açık tutan ana kontrol döngüsü
            kapi_acik = True
            while kapi_acik:
                print("[GÜVENLİK] Lazer hattı devrede, araç geçişi izleniyor...")
                
                while True:
                    if ldr.value == 1:
                        print("[UYARI] Araç algılandı (Lazer Hattı Kesik)! Kapı KAPANAMAZ.")
                    else:
                        print("[TEMİZ] Lazer hattı net. Araç geçti veya alan boş.")
                        print("[SİSTEM] Kapı kapatılmak üzere geri sayım: 2 saniye...")
                        time.sleep(2)
                        
                        if ldr.value == 0:
                            break 
                    
                    time.sleep(0.1)

                # Araç geçti sanıp kapıyı kapatmayı deniyoruz
                if kapiyi_kapat():
                    kapi_acik = False # Kapı başarıyla kapandı, ana döngüden çık
                else:
                    # Kapı kapanırken araya biri girdi ve kapı geri açıldı!
                    # Bu yüzden kapi_acik = True kalacak ve sistem aracın çekilmesini beklemeye devam edecek.
                    print("[SİSTEM] Lütfen bariyerin altını boşaltın!")
                    time.sleep(2)

            time.sleep(1)
            print("[SİSTEM] Araç başarıyla geçti. Sistem sıfırlandı.")

    except KeyboardInterrupt:
        print("\n[SİSTEM] Program kapatılıyor...")
    finally:
        for pin in step_pins:
            pin.off()
        subprocess.run("pkill rpicam-vid", shell=True)
        print("[SİSTEM] Kamera kapatıldı, çıkış yapılıyor.")

if __name__ == "__main__":
    main()