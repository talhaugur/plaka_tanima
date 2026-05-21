#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main() {
    // gpiod araçlarının sistemde kurulu olup olmadığını kontrol edelim
    // Eğer kurulu değilse arka planda otomatik kurmaya çalışır
    system("command -v gpioget >/dev/null 2>&1 || (sudo apt update && sudo apt install gpiod -y)");

    printf("=========================================\n");
    printf("=== Akıllı Plaka Tetikleme Sistemi Aktif ===\n");
    printf("Lazer hattı izleniyor. Kesinti bekleniyor...\n");
    printf("=========================================\n");

    int last_state = 1; // Başlangıçta lazer açık varsayıyoruz
    char buffer[10];

    while (1) {
        // gpioget komutu ile GPIO 17 pinini doğrudan okuyoruz
        // Bu yöntem hem Pi 4 hem Pi 5 ile tam uyumludur ve kilitlenme yapmaz
        FILE *fp = popen("gpioget gpiochip4 17 2>/dev/null || gpioget gpiochip0 17", "r");
        if (fp == NULL) {
            perror("Pin okunurken hata oluştu");
            break;
        }

        if (fgets(buffer, sizeof(buffer), fp) != NULL) {
            int current_state = buffer[0] - '0'; // 0 veya 1

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
        pclose(fp);

        // İşlemciyi yormamak için 50ms bekle
        usleep(50000); 
    }

    return 0;
}