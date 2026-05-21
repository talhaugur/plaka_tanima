#include <stdio.h>
#include <unistd.h>
#include <gpiod.h>

#define CONSUMER "Plaka_Tetikleyici"
#define GPIO_PIN 17  // LDR sinyalinin bağlı olduğu GPIO pini

int main() {
    struct gpiod_chip *chip;
    struct gpiod_line *line;
    int line_value;
    int last_state = 1; // Başlangıçta lazer açık (Lojik 1) varsayıyoruz

    // GPIO çipini aç (Raspberry Pi 4 ve 5 için genellikle "gpiochip4" veya "gpiochip0")
    chip = gpiod_chip_open_by_number(0); 
    if (!chip) {
        perror("GPIO Çipi açılamadı! (Alternatif olarak open_by_name deneyin)");
        return 1;
    }

    // İlgili pini al
    line = gpiod_chip_get_line(chip, GPIO_PIN);
    if (!line) {
        perror("Pin alınamadı");
        gpiod_chip_close(chip);
        return 1;
    }

    // Pini GİRİŞ (Input) olarak ayarla
    if (gpiod_line_request_input(line, CONSUMER) < 0) {
        perror("Pin giriş olarak ayarlanamadı");
        gpiod_chip_close(chip);
        return 1;
    }

    printf("=== Akıllı Plaka Tetikleme Sistemi Aktif ===\n");
    printf("Lazer hattı izleniyor...\n");

    while (1) {
        // Pindeki anlık değeri oku (1 veya 0)
        line_value = gpiod_line_get_value(line);

        if (line_value == 0 && last_state == 1) {
            // Lazer önceden vuruyordu (1), şimdi kesildi (0)
            printf("\n[ALERT] Lazer Kesildi! Araç Geçiyor...\n");
            printf("[CAMERA] Tetikleme sinyali gönderildi! Fotoğraf çekiliyor...\n");
            
            // Buraya ileride kamera geldikten sonra fotoğraf çekme fonksiyonunu ekleyeceksin.
            
            last_state = 0;
        } 
        else if (line_value == 1 && last_state == 0) {
            // Araç geçti, lazer tekrar LDR'nin üzerine düştü
            printf("[INFO] Lazer Hattı Tekrar Net. Sistem Hazır.\n");
            last_state = 1;
        }

        // İşlemciyi yormamak için 50 milisaniye bekle (Örnekleme hızı)
        usleep(50000); 
    }

    // Program kapanırsa (Ctrl+C) kaynakları temizle
    gpiod_line_release(line);
    gpiod_chip_close(chip);
    return 0;
}