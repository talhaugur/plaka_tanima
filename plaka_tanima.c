#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

// Servo motorların pürüzsüz dönmesi için pinctrl PWM fonksiyonu
void kapiyi_ac() {
    printf("\n[SERVO] Kapı pürüzsüz şekilde açılıyor (90 derece)...\n");
    // GPIO 18 pininde 50Hz frekansta %7.5 duty cycle (1.5ms sinyal genişliği) üretir.
    // Bu komut servoyu tam 90 dereceye pürüzsüzce döndürür.
    system("pinctrl set 18 pwm f50 p7.5 2>/dev/null"); 
}

void kapiyi_kapat() {
    printf("[SERVO] Güvenli. Kapı pürüzsüz şekilde kapanıyor (0 derece).\n");
    // GPIO 18 pininde 50Hz frekansta %5 duty cycle (1.0ms sinyal genişliği) üretir.
    // Bu komut servoyu tam 0 dereceye pürüzsüzce döndürür.
    system("pinctrl set 18 pwm f50 p5.0 2>/dev/null");
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
    // LDR Pin Ayarı (GPIO 17 Giriş)
    system("pinctrl set 17 ip 2>/dev/null");

    printf("==================================================\n");
    printf("===  Pinctrl PWM Destekli Akıllı Bariyer  ===\n");
    printf("==================================================\n");

    // Başlangıçta kapıyı kapalı pozisyona getir
    kapiyi_kapat();

    while (1) {
        printf("\n[SİSTEM] Kapıyı açmak için ENTER'a bas...\n");
        getchar(); 

        kapiyi_ac();
        sleep(1); // Servonun dönme hareketini tamamlaması için bekle

        printf("[GÜVENLİK] Lazer hattı devrede, araç kontrol ediliyor...\n");

        while (1) {
            int lazer = lazer_durumu_oku();

            // LDR modülün lazeri kestiğinde LO veriyorsa araç var demektir
            if (lazer == 0) { 
                printf("[UYARI] Araç algılandı! Kapı KAPANAMAZ.\n");
            } else {
                printf("[TEMİZ] Lazer hattı net. Araç geçti veya yok.\n");
                printf("[SİSTEM] Kapı kapatılmak üzere geri sayım: 2 saniye...\n");
                sleep(2);
                
                // Kapanmadan hemen önce son bir güvenlik kontrolü daha yap
                if (lazer_durumu_oku() != 0) {
                    break; 
                }
            }
            usleep(300000); // 300ms'de bir kontrol et
        }

        kapiyi_kapat();
        sleep(1); // Kapanma hareketi tamamlansın
        printf("[SİSTEM] Döngü başa döndü.\n");
    }

    return 0;
}