#include "ECE140_WIFI.h"
#include "ECE140_MQTT.h"

// Define Device ID as a string literal
#define DEVICE_ID "wearwise"

ECE140_WIFI wifi;
ECE140_MQTT mqtt(CLIENT_ID, BASE_TOPIC);

const char* ucsdUsername = UCSD_USERNAME;
const char* ucsdPassword = UCSD_PASSWORD;
const char* wifiSsid = WIFI_SSID;
const char* nonEnterpriseWifiPassword = NON_ENTERPRISE_WIFI_PASSWORD;
const char* ssid = "nj";
const char* pw = "6265222296aA";

void setup() {
    Serial.begin(115200);
    wifi.connectToWPAEnterprise(wifiSsid, ucsdUsername, ucsdPassword);
    //wifi.connectToWiFi(ssid, pw);
}

void loop() {
    float temperature = temperatureRead();
    String message = "{ \"temp\": " + String(temperature) +
                     ", \"unit\": \"°F\", \"device_id\": \"" + String(DEVICE_ID) + "\" }";

    if (mqtt.publishMessage("readings", message)) {
        Serial.println("Message published: " + message);
    } else {
        Serial.println("Failed to publish message.");
    }
    mqtt.loop();
    delay(2000);
}
