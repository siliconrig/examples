#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_wifi.h"
#include "esp_now.h"
#include "esp_mac.h"
#include "nvs_flash.h"

typedef struct {
    uint32_t seq;
} __attribute__((packed)) packet_t;

typedef struct {
    uint32_t seq;
    int rssi;
    uint32_t rx_count;
    uint32_t missed;
} print_msg_t;

static uint32_t rx_count = 0;
static uint32_t last_seq = 0;
static uint32_t missed = 0;
static QueueHandle_t print_queue;

static void on_recv(const esp_now_recv_info_t *info,
                    const uint8_t *data, int len)
{
    if (len != sizeof(packet_t)) return;

    packet_t pkt;
    memcpy(&pkt, data, sizeof(pkt));
    rx_count++;

    if (last_seq > 0 && pkt.seq > last_seq + 1)
        missed += (pkt.seq - last_seq - 1);
    last_seq = pkt.seq;

    print_msg_t msg = {
        .seq = pkt.seq,
        .rssi = info->rx_ctrl->rssi,
        .rx_count = rx_count,
        .missed = missed,
    };
    xQueueSend(print_queue, &msg, 0);
}

static void print_task(void *arg)
{
    print_msg_t msg;
    while (1) {
        if (xQueueReceive(print_queue, &msg, portMAX_DELAY)) {
            printf("RX: seq=%lu rssi=%d\n",
                   (unsigned long)msg.seq, msg.rssi);

            if (msg.rx_count % 10 == 0) {
                uint32_t total = msg.rx_count + msg.missed;
                printf("SUMMARY: received=%lu missed=%lu "
                       "total=%lu loss=%.1f%%\n",
                       (unsigned long)msg.rx_count,
                       (unsigned long)msg.missed,
                       (unsigned long)total,
                       total > 0
                           ? (msg.missed * 100.0 / total)
                           : 0.0);
            }
        }
    }
}

static void wifi_init(void)
{
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_start());
    ESP_ERROR_CHECK(esp_wifi_set_max_tx_power(40)); /* 10 dBm */
}

void app_main(void)
{
    ESP_ERROR_CHECK(nvs_flash_init());
    wifi_init();

    print_queue = xQueueCreate(32, sizeof(print_msg_t));
    xTaskCreate(print_task, "print", 4096, NULL, 1, NULL);

    ESP_ERROR_CHECK(esp_now_init());
    ESP_ERROR_CHECK(esp_now_register_recv_cb(on_recv));

    printf("RECEIVER: ready\n");

    while (1) {
        vTaskDelay(portMAX_DELAY);
    }
}
