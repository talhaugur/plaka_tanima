#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

// Kolaylık olsun diye terminalden servoyu kontrol eden fonksiyonlar
void kapiyi_ac() {
    printf("[SERVO] Kapı açılıyor (90 derece)...\n");
    // Raspberry Pi 4/5 için donanımsal PWM komutu (GPIO 18)
    system("pinctrl set 18 op dh 2>/dev/null || gpio -g write 18 1"); 
}

void kapiyi_kapat() {
    printf("[SERVO] Güvenli. Kapı kapanıyor (0 derece).\n");
    system("pinctrl set 18 op dl 2>/dev/null || gpio -g write 18 0");
}

int lazer_durumu_oku() {
    char buffer[128];
    // GPIO 17'den anlık lojik değeri okur
    FILE *fp = popen("gpioget --find 17 2>/dev/null", "r");
    if (fp != NULL) {
        if (fgets(buffer, sizeof(buffer), fp) != NULL) {
            pclose(fp);
            return buffer[0] - '0'; // 0 veya 1 döner
        }
        pclose(fp);
    }
    return 1; // Hata durumunda güvenli tarafta kalmak için 1 dönelim
}

int main() {
    // Servo pini ayarı (GPIO 18 Çıkış olarak ayarlanıyor)
    system("pinctrl set 18 op 2>/dev/null");

    printf("==================================================\n");
    printf("=== Otopark Bariyeri & Güvenlik Sistemi Aktif ===\n");
    printf("==================================================\n");

    // Başlangıçta kapıyı kapalı tutalım
    kapiyi_kapat();

    while (1) {
        printf("\n[SİSTEM] (Simülasyon) Plaka okundu saymak ve kapıyı açmak için ENTER'a bas...\n");
        getchar(); // Kullanıcının enter'a basmasını bekler (İleride burası kamera tetiklemesi olacak)

        kapiyi_ac();
        usleep(1000000); // Kapının açılması için 1 saniye bekle

        printf("[GÜVENLİK] Araç geçişi bekleniyor, lazer hattı devrede...\n");

        // Araç geçene kadar bu döngüde çakılı kalacağız
        while (1) {
            int lazer = lazer_durumu_oku();

            // Eğer senin modül ters mantıksa buradaki '0'ı '1' yapabilirsin
            if (lazer == 0) { 
                printf("[UYARI] Araç algılandı (Lazer Kesik)! Kapı KAPANAMAZ.\n");
            } else {
                printf("[TEMİZ] Lazer hattı net. Araç geçti veya henüz girmedi.\n");
                
                // Güvenlik amacıyla hat netleştikten sonra 2 saniye daha bekleyelim
                printf("[SİSTEM] Kapı kapatılmak üzere geri sayım: 2 saniye...\n");
                sleep(2);
                
                // Son bir kez daha kontrol edelim, tam kapanırken araç gelmiş mi?
                if (lazer_durumu_oku() == 1) {
                    break; // İç döngüden çık, yani kapıyı kapatmaya git
                }
            }
            usleep(500000); // Her yarım saniyede bir kontrol et
        }

        kapiyi_kapat();
        printf("[SİSTEM] Döngü başa dönüyor.\n");
    }

    return 0;
}