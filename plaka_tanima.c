#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <pigpio.h>

#define LDR_PIN   17  // LDR Modülünün DO pini
#define SERVO_PIN 18  // Servonun Sinyal kablosu

// Kalibre ettiğin tam açılar (Önceki adıma göre revize edebilirsin)
#define KAPI_ACIK_PWM   1650  // 90 derece pozisyonu
#define KAPI_KAPALI_PWM  700  // 0 derece pozisyonu

void kapiyi_ac() {
    printf("\n[SERVO] Kapı HIZLA açılıyor (Güvenlik Önceliği)...\n");
    // Sıkışma ihtimaline karşı açılma her zaman tam güç ve hızlı olmalı
    gpioServo(SERVO_PIN, KAPI_ACIK_PWM); 
}

// Yeni akıllı ve yavaş kapanma fonksiyonu
// Eğer kapanırken lazer kesilirse 1 döner (sıkışma var), sorunsuz kapanırsa 0 döner.
int kapiyi_yavas_kapat_ve_koru() {
    printf("[SERVO] Güvenli bölge. Kapı yavaşça kapanıyor...\n");

    // Açık pozisyondan kapalı pozisyona doğru adım adım gidiyoruz
    for (int pwm = KAPI_ACIK_PWM; pwm >= KAPI_KAPALI_PWM; pwm -= 10) {
        
        // Her adımda LDR'yi kontrol et
        if (gpioRead(LDR_PIN) == 0) { // Lazer kesildiyse (Araç/Engel var!)
            printf("\n[ACİL DURUM] Kapanma esnasında engel algılandı! Kapanma iptal!\n");
            kapiyi_ac(); // Kapıyı derhal geri aç
            return 1;    // Sıkışma algılandı sinyali gönder
        }

        gpioServo(SERVO_PIN, pwm);
        
        // Bu bekleme süresi kapanma hızını belirler. 
        // 20000us (20ms) idealdir. Yavaşlatmak istersen 30000 yapabilirsin.
        usleep(20000); 
    }
    
    return 0; // Sorunsuz kapandı
}

int main() {
    if (gpioInitialise() < 0) {
        fprintf(stderr, "HATA: pigpio kütüphanesi başlatılamadı!\n");
        return 1;
    }

    gpioSetMode(LDR_PIN, PI_INPUT);
    gpioSetMode(SERVO_PIN, PI_OUTPUT);

    printf("=========================================================\n");
    printf("=== Endüstriyel Sıkışma Önleyicili Bariyer Sistemi ===\n");
    printf("=========================================================\n");

    // İlk açılışta kapıyı kapalı tut
    gpioServo(SERVO_PIN, KAPI_KAPALI_PWM);

    while (1) {
        printf("\n[SİSTEM] Kapıyı açmak için ENTER'a bas...\n");
        getchar(); 

        kapiyi_ac();
        sleep(1); // Açılma hareketi tamamlansın

        // İlk araç geçiş beklemesi (Kapı açıkken)
        printf("[GÜVENLİK] Araç geçişi bekleniyor...\n");
        while (1) {
            if (gpioRead(LDR_PIN) == 0) { 
                printf("[UYARI] Araç şu an kapının altında. Bekleniyor...\n");
            } else {
                printf("[TEMİZ] Alt alan boşaldı. 2 saniye sonra kapanma başlayacak...\n");
                sleep(2);
                
                // Kapanma emri verilmeden hemen önce son kontrol
                if (gpioRead(LDR_PIN) != 0) {
                    break; 
                }
            }
            usleep(200000);
        }

        // Kapıyı kapatmayı dene ve sıkışma kontrolü yap
        // Eğer fonksiyon 1 dönerse engel var demektir, döngü başa sarar ve kapı açık kalır
        while (kapiyi_yavas_kapat_ve_koru() == 1) {
            printf("[SİSTEM] Engel temizlenene kadar kapı açık bekletiliyor...\n");
            
            // Engel kalkana kadar burada bekle
            while (gpioRead(LDR_PIN) == 0) {
                usleep(200000);
            }
            
            printf("[SİSTEM] Engel kalktı. Yeniden kapatma deneniyor...\n");
            sleep(2); // Güvenlik amacıyla tekrar kapatmadan önce 2 saniye bekle
        }

        printf("[SİSTEM] Kapı başarıyla kapandı. Sonraki araç bekleniyor.\n");
    }

    gpioTerminate();
    return 0;
}