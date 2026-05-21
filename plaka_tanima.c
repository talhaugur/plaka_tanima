#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

void kapiyi_ac() {
    printf("[SERVO] Kapı açılıyor (90 derece)...\n");
    system("pinctrl set 18 op dh 2>/dev/null || gpio -g write 18 1"); 
}

void kapiyi_kapat() {
    printf("[SERVO] Güvenli. Kapı kapanıyor (0 derece).\n");
    system("pinctrl set 18 op dl 2>/dev/null || gpio -g write 18 0");
}

// Yeni ve hatasız pin okuma fonksiyonu
int lazer_durumu_oku() {
    char buffer[256];
    int state = 1; // Varsayılan durum

    // pinctrl ile GPIO 17'nin durumunu sorguluyoruz
    FILE *fp = popen("pinctrl get 17 2>/dev/null", "r");
    if (fp != NULL) {
        while (fgets(buffer, sizeof(buffer), fp) != NULL) {
            // Çıktının içinde "hi" (High/1) veya "lo" (Low/0) kelimelerini arıyoruz
            if (strstr(buffer, "hi") != NULL) {
                state = 1;
            } else if (strstr(buffer, "lo") != NULL) {
                state = 0;
            }
        }
        pclose(fp);
    }
    return state;
}

int main() {
    // Pin yönlendirmelerini yapıyoruz (17 Giriş, 18 Çıkış)
    system("pinctrl set 17 ip 2>/dev/null");
    system("pinctrl set 18 op 2>/dev/null");

    printf("==================================================\n");
    printf("=== Otopark Bariyeri & Güvenlik Sistemi Aktif ===\n");
    printf("==================================================\n");

    kapiyi_kapat();

    while (1) {
        printf("\n[SİSTEM] (Simülasyon) Kapıyı açmak için ENTER'a bas...\n");
        getchar(); 

        kapiyi_ac();
        usleep(1000000); // 1 saniye açılma payı

        printf("[GÜVENLİK] Lazer hattı devrede, araç kontrol ediliyor...\n");

        while (1) {
            int lazer = lazer_durumu_oku();

            // SENSÖR KONTROLÜ: Eğer lazeri kestiğinde "[UYARI]" yerine "[TEMİZ]" diyorsa, 
            // modülün ters mantıktır. O zaman aşağıdaki '== 0' kısmını '== 1' yapman gerekir.
            if (lazer == 0) { 
                printf("[UYARI] Araç algılandı (Lazer Durumu: LO)! Kapı KAPANAMAZ.\n");
            } else {
                printf("[TEMİZ] Lazer hattı net (Lazer Durumu: HI).\n");
                printf("[SİSTEM] Kapı kapatılmak üzere geri sayım: 2 saniye...\n");
                sleep(2);
                
                // Kapanmadan hemen önce son kontrol
                if (lazer_durumu_oku() != 0) {
                    break; 
                }
            }
            usleep(500000); // Yarım saniyede bir döngü
        }

        kapiyi_kapat();
        printf("[SİSTEM] Döngü başa döndü.\n");
    }

    return 0;
}