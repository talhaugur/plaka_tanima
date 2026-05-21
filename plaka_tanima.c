#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <pigpio.h> // Kurduğumuz canavar kütüphane

#define LDR_PIN   17  // LDR Modülünün DO pini (GPIO 17)
#define SERVO_PIN 18  // Servonun Sinyal kablosu (GPIO 18)

void kapiyi_ac() {
    printf("\n[SERVO] Kapı pürüzsüz şekilde açılıyor (90 derece)...\n");
    // pigpio arka planda işlemcinin donanımsal saatini kullanır.
    // 1500us darbe genişliği servoyu tam 90 dereceye pürüzsüzce taşır.
    gpioServo(SERVO_PIN, 1500); 
}

void kapiyi_kapat() {
    printf("[SERVO] Güvenli. Kapı pürüzsüz şekilde kapanıyor (0 derece).\n");
    // 1000us darbe genişliği servoyu 0 dereceye (başlangıç pozisyonu) getirir.
    gpioServo(SERVO_PIN, 1000);
}

int main() {
    // pigpio kütüphanesini başlatıyoruz
    if (gpioInitialise() < 0) {
        fprintf(stderr, "HATA: pigpio kütüphanesi başlatılamadı!\n");
        return 1;
    }

    // Pinlerin yönlerini kütüphane fonksiyonlarıyla tanımlıyoruz
    gpioSetMode(LDR_PIN, PI_INPUT);
    gpioSetMode(SERVO_PIN, PI_OUTPUT);

    printf("==================================================\n");
    printf("===  pigpio Altyapılı Profesyonel Bariyer Sistemi ===\n");
    printf("==================================================\n");

    // Sistem ilk açıldığında kapıyı kapalı pozisyona çekelim
    kapiyi_kapat();

    while (1) {
        printf("\n[SİSTEM] Kapıyı açmak için ENTER'a bas...\n");
        getchar(); // İleride burası kamera tetiklemesi olacak

        kapiyi_ac();
        sleep(1); // Servonun hareketini tamamlaması için 1 saniye pürüzsüz bekle

        printf("[GÜVENLİK] Lazer hattı devrede, araç kontrol ediliyor...\n");

        while (1) {
            // LDR durumunu kütüphane üzerinden doğrudan okuyoruz (Hızlı ve stabil)
            int lazer = gpioRead(LDR_PIN); 

            // Eğer lazeri kestiğinde "[UYARI]" yerine "[TEMİZ]" yazıyorsa modülün ters mantıktır.
            // O zaman aşağıdaki '== 0' koşulunu '== 1' yapman gerekir.
            if (lazer == 1) { 
                printf("[UYARI] Araç algılandı (Lazer Hattı Kesik)! Kapı KAPANAMAZ.\n");
            } else {
                printf("[TEMİZ] Lazer hattı net. Araç geçti veya alan boş.\n");
                printf("[SİSTEM] Kapı kapatılmak üzere geri sayım: 2 saniye...\n");
                sleep(2);
                
                // Kapanmadan hemen önce son bir güvenlik kontrolü daha yapıyoruz
                if (gpioRead(LDR_PIN) != 1) {
                    break; // Eğer hâlâ temizse iç döngüden çık ve kapıyı kapatmaya git
                }
            }
            usleep(100000); // 100ms'de bir (saniyede 10 kez) çok akıcı kontrol
        }

        kapiyi_kapat();
        sleep(1); // Kapanma tamamlansın
        printf("[SİSTEM] Döngü başa döndü, sonraki araç bekleniyor.\n");
    }

    // Program bir şekilde sonlanırsa kütüphaneyi güvenli kapat
    gpioTerminate();
    return 0;
}