#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>

int main() {
    // GPIO 17 pinini sisteme açıyoruz (Export)
    int export_fd = open("/sys/class/gpio/export", O_WRONLY);
    if (export_fd >= 0) {
        write(export_fd, "17", 2);
        close(export_fd);
    }

    // Sistemin pini hazırlaması için çok kısa bir bekleme
    usleep(100000); 

    // Pini GİRİŞ (in) olarak ayarlıyoruz
    int dir_fd = open("/sys/class/gpio/gpio17/direction", O_WRONLY);
    if (dir_fd < 0) {
        perror("GPIO yönü ayarlanamadı! Lütfen sudo ile çalıştırmayı deneyin.");
        return 1;
    }
    write(dir_fd, "in", 2);
    close(dir_fd);

    int val_fd;
    char value;
    int last_state = 1; // Başlangıçta lazer hattı çekili (1) varsayıyoruz

    printf("=========================================\n");
    printf("=== Akıllı Plaka Tetikleme Sistemi Aktif ===\n");
    printf("Lazer hattı izleniyor. Kesinti bekleniyor...\n");
    printf("=========================================\n");

    while (1) {
        // Pin değerini okuyoruz
        val_fd = open("/sys/class/gpio/gpio17/value", O_RDONLY);
        if (val_fd >= 0) {
            read(val_fd, &value, 1);
            close(val_fd);
        }

        int current_state = value - '0'; // Karakteri sayıya (0 veya 1) çevir

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

        // İşlemciyi yormamak için 50ms bekle (Örnekleme hızı)
        usleep(50000); 
    }

    return 0;
}