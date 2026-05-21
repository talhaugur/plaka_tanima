#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

int main() {
    printf("=========================================\n");
    printf("=== Akıllı Plaka Tetikleme Sistemi Aktif ===\n");
    printf("Lazer hattı izleniyor. Kesinti bekleniyor...\n");
    printf("=========================================\n");

    int last_state = 1; // Başlangıçta lazer hattı çekili (1) varsayıyoruz
    char buffer[128];

    while (1) {
        // gpioget komutunu en güncel ve akıllı parametreyle çağırıyoruz.
        // --find parametresi sayesinde çip numarasını (gpiochipX) sistem kendi bulur.
        FILE *fp = popen("gpioget --find 17 2>/dev/null", "r");
        if (fp == NULL) {
            perror("Pin okuma komutu başlatılamadı");
            break;
        }

        if (fgets(buffer, sizeof(buffer), fp) != NULL) {
            // Çıkan sonucun ilk karakterini alıyoruz (0 veya 1)
            int current_state = buffer[0] - '0'; 

            // Değerin geçerli (0 veya 1) olduğundan emin olalım
            if (current_state == 0 || current_state == 1) {
                
                // Lazer önceden vuruyordu (1), şimdi kesildi (0)
                if (current_state == 0 && last_state == 1) {
                    printf("\n[ALERT] Lazer Kesildi! Araç Geçiyor...\n");
                    printf("[CAMERA] Tetikleme sinyali gönderildi!\n");
                    last_state = 0;
                } 
                // Araç geçti, lazer tekrar LDR'nin üzerine düştü (1)
                else if (current_state == 1 && last_state == 0) {
                    printf("[INFO] Lazer Hattı Tekrar Net. Sistem Hazır.\n");
                    last_state = 1;
                }
            }
        }
        pclose(fp);

        // İşlemciyi yormamak için 50ms bekle (Örnekleme hızı)
        usleep(50000); 
    }

    return 0;
}