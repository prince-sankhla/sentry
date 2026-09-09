/*
 * SENTRY FIELD — ESP32 rover telemetry client
 *
 * Hardware-facing reference client for the canonical local gateway:
 *   POST http://<GATEWAY-IP>:8001/telemetry
 *
 * Required Arduino libraries:
 *   WiFi (ESP32 core)
 *   HTTPClient (ESP32 core)
 *   TinyGPSPlus (optional, for a real GPS module)
 *
 * The SENTRY UI remains the mission authority. The operator first dispatches
 * the exact tender/requirement mission; this device then publishes live rover
 * telemetry to the local gateway, where it appears in /status.
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <TinyGPSPlus.h>

const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* GATEWAY_URL = "http://192.168.1.100:8001/telemetry";
const char* MACHINE_ID = "ROVER-001";

// UART2: adjust pins for the rover wiring.
static const int GPS_RX_PIN = 16;
static const int GPS_TX_PIN = 17;
static const uint32_t GPS_BAUD = 9600;

// Battery divider ADC pin. Calibrate this for the actual battery/BMS circuit.
static const int BATTERY_ADC_PIN = 34;
static const float ADC_REF_V = 3.3f;
static const float ADC_MAX = 4095.0f;
static const float DIVIDER_RATIO = 5.0f;

// Replace this with a measured rover speed from wheel encoders if available.
// Keeping this as a clearly marked integration point avoids inventing speed.
float readRoverSpeedMps() {
  return 0.0f;
}

float readBatteryPercent() {
  const int raw = analogRead(BATTERY_ADC_PIN);
  const float voltageAtAdc = (raw / ADC_MAX) * ADC_REF_V;
  const float packVoltage = voltageAtAdc * DIVIDER_RATIO;

  // Placeholder mapping for a nominal 3S Li-ion pack (12.6V full, 9.0V empty).
  // Calibrate to the actual rover battery chemistry before field use.
  float percent = ((packVoltage - 9.0f) / (12.6f - 9.0f)) * 100.0f;
  if (percent < 0.0f) percent = 0.0f;
  if (percent > 100.0f) percent = 100.0f;
  return percent;
}

TinyGPSPlus gps;
HardwareSerial GPSSerial(2);

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
}

void publishTelemetry() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  HTTPClient http;
  if (!http.begin(GATEWAY_URL)) {
    return;
  }
  http.addHeader("Content-Type", "application/json");

  const float battery = readBatteryPercent();
  const float speed = readRoverSpeedMps();

  String payload = "{";
  payload += "\"machine_id\":\"" + String(MACHINE_ID) + "\",";
  payload += "\"battery\":" + String(battery, 1) + ",";
  payload += "\"speed\":" + String(speed, 2);

  // GPS is only included when the module has a valid fix.
  if (gps.location.isValid()) {
    payload += ",\"lat\":" + String(gps.location.lat(), 7);
    payload += ",\"lon\":" + String(gps.location.lng(), 7);
  }
  payload += "}";

  const int code = http.POST(payload);
  http.end();

  // Do not fabricate a successful telemetry state locally. The gateway's
  // HTTP response is the authoritative acceptance signal.
  (void)code;
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  GPSSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  connectWiFi();
}

void loop() {
  while (GPSSerial.available()) {
    gps.encode(GPSSerial.read());
  }

  static unsigned long lastPublishMs = 0;
  const unsigned long now = millis();
  if (now - lastPublishMs >= 1000) {
    lastPublishMs = now;
    publishTelemetry();
  }
}
