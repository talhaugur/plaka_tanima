#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

// Yazılımsal pürüzsüz sinyal üretici fonksiyon
// milisaniye cinsinden (1.0ms = 0 derece, 1.5ms = 90 derece)
void servo_konum_ayarla(int konum_ms) {
    int acik_kalma_suresi = konum_ms;                 // Mikro saniye (1000 veya 1500)
    int kapali_kalma_suresi = 20000 - acik_kalma_suresi; // Toplam periyot 20ms (50Hz)

    // Motorun o konuma gitmeye vakit bulması için sinyali 25 kez tekrarlıyoruz
    for (int i = 0; i < 25; i++) {
        // Pini HIGH (1) yap
        system("pinctrl set 18 op dh 2>/dev/null || gpio -g write 18 1");
        usleep(acik_kalma_suresi);

        // Pini LOW (0) yap
        system("pinctrl set 18 op dl 2>/dev/null || gpio -g write 18 0");
        usleep(kapali_kalma_suresi);
    }
}

void kapiyi_ac() {
    printf("\n[SERVO] Kapı açılıyor (90 derece)...\n");
    // 90 derece için sinyal genişliği 1500 mikro saniyedir
    servo_konum_ayarla(1500); 
}

void kapiyi_kapat() {
    printf("[SERVO] Güvenli. Kapı kapanıyor (0 derece).\n");
    // 0 derece için sinyal genişliği 1000 mikro saniyedir
    servo_konum_ayarla(1000);
}

int lazer_durumu_oku() {
    char buffer[256];
    int state = 1; 

    FILE *fp = popen("pinctrl get 17 2>/dev/null", "r");
    if (fp != NULL) {
        while (fgets(buffer, sizeof(buffer), fp) != NULL) {
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
    printf("===   Yazılımsal Hassas Bariyer Sistemi Aktif   ===\n");
    printf("==================================================\n");

    // Başlangıçta kapıyı kapat
    kapiyi_kapat();

    while (1) {
        printf("\n[SİSTEM] Kapıyı açmak için ENTER'a bas...\n");
        getchar(); 

        kapiyi_ac();

        printf("[GÜVENLİK] Lazer hattı devrede, araç kontrol ediliyor...\n");

        while (1) {
            int lazer = lazer_durumu_oku();

            if (lazer == 1) { 
                printf("[UYARI] Araç algılandı! Kapı KAPANAMAZ.\n");
            } else {
                printf("[TEMİZ] Lazer hattı net. Araç geçti veya yok.\n");
                printf("[SİSTEM] Kapı kapatılmak üzere geri sayım: 2 saniye...\n");
                sleep(2);
                
                // Son bir güvenlik kontrolü daha
                if (lazer_durumu_oku() != 1) {
                    break; 
                }
            }
            usleep(300000); 
        }

        kapiyi_kapat();
        printf("[SİSTEM] Döngü başa döndü.\n");
    }

    return 0;
}


# 1. Kütüphanenin kaynak kodunu internetten çekiyoruz
wget https://github.com/joan2937/pigpio/archive/master.zip

# 2. İndirdiğimiz sıkıştırılmış dosyayı açıyoruz
unzip master.zip

# 3. Klasörün içine giriyoruz
cd pigpio-master

# 4. Derleme işlemini başlatıyoruz
make

# 5. Derlenen kütüphaneyi sisteme kalıcı olarak yüklüyoruz
sudo make install

# 6. Ana klasörümüze geri dönüyoruz
cd ..