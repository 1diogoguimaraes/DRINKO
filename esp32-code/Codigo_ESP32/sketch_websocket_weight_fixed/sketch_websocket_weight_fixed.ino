#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include <Adafruit_NeoPixel.h>
#include "HX711.h"
#include <driver/adc.h>
#include <esp_adc_cal.h>
#include <esp_now.h>



// HX711 circuit wiring
#define DT 18
#define SCK 19

//LED Strip pins define
#define PIN_WS2812B 16  // ESP32 pin
#define NUM_PIXELS 5    // Number of LEDs

Adafruit_NeoPixel ws2812b(NUM_PIXELS, PIN_WS2812B, NEO_GRB + NEO_KHZ800);
HX711 scale;


unsigned long lastLoopPrint = 0;


unsigned long lastStatusSent = 0;
const unsigned long STATUS_INTERVAL = 5000;  // 5 seconds


// calibration factor (you must calibrate!)
float calibration_factor;  // adjust after calibration

// ----------------- Battery Monitoring -----------------
const int BATTERY_PIN = 33;
const float R1 = 200000.0;
const float R2 = 100000.0;
const float vref = 1100;
const int NUM_SAMPLES = 32;
esp_adc_cal_characteristics_t adc_chars;
unsigned long lastBatteryRead = 0;
const unsigned long BATTERY_INTERVAL = 1000;  // 1 second
float ADC_CORRECTION;


// WiFi credentials
const char* ssid = "TP-LINK_F53BD8";
const char* password = "53739063";

// webSockets server
const char* ws_server = "192.168.0.101";  // FastAPI server IP
const int ws_port = 8000;
String device_id = "";  // unique per ESP32


uint8_t nextDeviceMac[6];
bool nextDeviceSet = false;


// Create WiFi
WiFiClient espClient;

WebSocketsClient webSocket;  // Declare at the top


// Define possible states
enum DeviceState {
  STANDBY,
  CUP,
  INVALID_CUP,
  READY,
  IN_RELAY,
  LOCKED,
  START,
  BEFORE_DRINKING,
  DRINKING,
  FINISH,
  WIN,
  LOSS,
  WAITING
};

volatile DeviceState currentState = STANDBY;
DeviceState lastSentState = STANDBY;  // or any initial state

//variables to server
int match_id;
String mode = "";
int team;
int relayPosition;
float start_weight = 0;
float end_weight = 0;
float batteryLevel;

//weight scale
float weight = 0;

//flags
bool gameReadyFlag = false;
bool startFlag = false;
bool f1_countdown = false;
bool modeSelected = false;
bool foulFlag = false;
bool doneFlag = false;

float standart_weight = 40;

// Global stopwatch variables
unsigned long foulRelayTime = 0;
unsigned long foulRelayStart = 0;

unsigned long reactionStart = 0;
unsigned long reactionTime = 0;

unsigned long drinkingStart = 0;
unsigned long drinkingTime = 0;

const unsigned long DRINKING_TIMEOUT = 1200000;
// Countdown vars
unsigned long countdownStart = 0;
int countdownSeconds = 3;  // adjust as needed
bool countdownRunning = false;



//----results sent---
bool resultsSent = false;
unsigned long finishTime = 0;
float stableWeight = 0;

// ===== NEW: Weight Stabilization Variables =====
#define STABLE_READINGS 5        // Number of consecutive stable readings needed
#define STABLE_THRESHOLD 2.0     // Max difference (grams) to consider stable
#define WEIGHT_LIFTED_THRESHOLD 10.0  // Weight below this = cup lifted

float weightBuffer[STABLE_READINGS];
int weightBufferIndex = 0;
bool weightBufferFull = false;
unsigned long lastWeightRead = 0;
const unsigned long WEIGHT_READ_INTERVAL = 20;  // Read every 20ms for responsiveness

bool startWeightStable = false;
bool endWeightStable = false;
unsigned long stableStartTime = 0;
const unsigned long STABLE_DURATION = 300;  // Weight must be stable for 300ms



// ----- LED Task -----
TaskHandle_t ledTaskHandle = NULL;

// State variables for blinking
unsigned long lastBlink = 0;
bool blinkState = false;

// Globals for drinking led
int chaseIndex = 0;
unsigned long lastChase = 0;


//similar to main loop function but handle the led efects based on currentState
// Updated setStrip with optional position
void setStrip(bool blink, int count, uint32_t color, int delayTime = 500, int position = -1) {
  if (count > NUM_PIXELS) count = NUM_PIXELS;

  // Handle blinking
  if (blink) {
    unsigned long now = millis();
    if (now - lastBlink >= delayTime) {
      lastBlink = now;
      blinkState = !blinkState;  // toggle ON/OFF
    }

    if (!blinkState) {
      ws2812b.clear();
      return;
    }
  }

  ws2812b.clear();

  if (position >= 0 && mode == "relay") {
    // ----- Relay mode logic -----
    int ledsToLight = min(position + 1, NUM_PIXELS);  // +1 so pos=0 → 1 LED
    for (int i = 0; i < ledsToLight; i++) {
      ws2812b.setPixelColor(i, color);
    }
  } else {
    // ----- Normal behavior -----
    for (int i = 0; i < count; i++) {
      ws2812b.setPixelColor(i, color);
    }
  }
}




void ledTask(void* parameter) {
  while (true) {
    switch (currentState) {
      case STANDBY:
        setStrip(true, NUM_PIXELS, ws2812b.Color(0, 0, 10), 500, relayPosition);  // Blinking blue
        break;
      case INVALID_CUP:
        setStrip(true, NUM_PIXELS, ws2812b.Color(10, 0, 0), 200, 0);  // Blinking Red
        break;
      case CUP:
        setStrip(true, NUM_PIXELS, ws2812b.Color(0, 10, 0), 200, 0);  // Blinking Green
        break;
      case READY:
        setStrip(true, NUM_PIXELS, ws2812b.Color(10, 0, 10), 200, relayPosition);  // Blinking purple
        break;
      case LOCKED:
        setStrip(false, NUM_PIXELS, ws2812b.Color(10, 0, 0), 0, relayPosition);  // Blinking Red
        break;
      case START:
        if (countdownRunning) {
          unsigned long elapsed = (millis() - countdownStart) / 1000;
          int remaining = countdownSeconds - elapsed;

          // Simple effect: show remaining seconds as lit LEDs
          ws2812b.clear();
          for (int i = 0; i < remaining && i < NUM_PIXELS; i++) {
            ws2812b.setPixelColor(i, ws2812b.Color(0, 10, 0));  // green
          }
        } else {
          // fallback if not counting
          setStrip(false, NUM_PIXELS, ws2812b.Color(0, 10, 0));
        }
        break;
      case IN_RELAY:
        setStrip(true, NUM_PIXELS, ws2812b.Color(10, 0, 0), 50, relayPosition);
        break;
      case BEFORE_DRINKING:
        setStrip(true, NUM_PIXELS, ws2812b.Color(0, 10, 10), 50, relayPosition);
        break;

      case DRINKING:
        {
          //static int chaseIndex = 0;
          //static unsigned long lastChase = 0;

          unsigned long now = millis();
          if (now - lastChase >= 150) {  // animation speed
            lastChase = now;

            ws2812b.clear();

            // "1 ON, 2 OFF" pattern moving left to right
            for (int i = 0; i < NUM_PIXELS; i++) {
              if ((i - chaseIndex + NUM_PIXELS) % 3 == 0) {
                ws2812b.setPixelColor(i, ws2812b.Color(0, 50, 0));  // green
              }
            }

            ws2812b.show();

            chaseIndex++;
            if (chaseIndex >= 3) {  // pattern shifts every 3 frames
              chaseIndex = 0;
            }
          }
          break;
        }

      case FINISH:
        setStrip(false, NUM_PIXELS, ws2812b.Color(10, 10, 0));  // Yellow
        break;
      case WIN:
        setStrip(false, NUM_PIXELS, ws2812b.Color(0, 10, 0), 150);  // Solid green
        break;
      case LOSS:
        setStrip(true, NUM_PIXELS, ws2812b.Color(10, 0, 0), 150);  // Blinking red
        break;
      case WAITING:
        setStrip(true, NUM_PIXELS, ws2812b.Color(10, 10, 10), 200);  // Blinking White
        break;

      default:
        ws2812b.clear();
        break;
    }

    ws2812b.show();
    vTaskDelay(5 / portTICK_PERIOD_MS);
  }
}



//color functions -------------------

//-------------------

// Convert enum to string
String stateToString(DeviceState state) {
  switch (state) {
    case STANDBY: return "standby";
    case READY: return "ready";
    case CUP: return "cup";
    case INVALID_CUP: return "invalid_cup";
    case IN_RELAY: return "in_relay";
    case LOCKED: return "locked";
    case START: return "start";
    case BEFORE_DRINKING: return "before_drinking";
    case DRINKING: return "drinking";
    case FINISH: return "finish";
    case WIN: return "win";
    case LOSS: return "loss";
    case WAITING: return "waiting";
    default: return "unknown";
  }
}

// Convert string to enum
DeviceState stringToState(String stateStr) {
  stateStr.toLowerCase();
  if (stateStr == "standby") return STANDBY;
  if (stateStr == "ready") return READY;
  if (stateStr == "in_relay") return IN_RELAY;
  if (stateStr == "cup") return CUP;
  if (stateStr == "invalid_cup") return INVALID_CUP;
  if (stateStr == "locked") return LOCKED;
  if (stateStr == "start") return START;
  if (stateStr == "before_drinking") return BEFORE_DRINKING;
  if (stateStr == "drinking") return DRINKING;
  if (stateStr == "finish") return FINISH;
  if (stateStr == "win") return WIN;
  if (stateStr == "loss") return LOSS;
  if (stateStr == "waiting") return WAITING;
  return currentState;  // default fallback
}

// ===== NEW: Fast Weight Reading Function =====
float readWeightFast() {
  if (!scale.is_ready()) {
    return weight;  // Return last known weight if not ready
  }
  
  // Use single reading for speed (10-20ms instead of 80ms)
  weight = scale.get_units(1);
  return weight;
}

// ===== NEW: Weight Stabilization Check =====
bool isWeightStable(float currentWeight) {
  // Add to circular buffer
  weightBuffer[weightBufferIndex] = currentWeight;
  weightBufferIndex = (weightBufferIndex + 1) % STABLE_READINGS;
  
  if (!weightBufferFull && weightBufferIndex == 0) {
    weightBufferFull = true;
  }
  
  if (!weightBufferFull) {
    return false;  // Need full buffer first
  }
  
  // Check if all readings are within threshold
  float minWeight = weightBuffer[0];
  float maxWeight = weightBuffer[0];
  
  for (int i = 1; i < STABLE_READINGS; i++) {
    if (weightBuffer[i] < minWeight) minWeight = weightBuffer[i];
    if (weightBuffer[i] > maxWeight) maxWeight = weightBuffer[i];
  }
  
  return (maxWeight - minWeight) <= STABLE_THRESHOLD;
}

// ===== NEW: Get Average of Stable Weight =====
float getStableWeightAverage() {
  if (!weightBufferFull) return weight;
  
  float sum = 0;
  for (int i = 0; i < STABLE_READINGS; i++) {
    sum += weightBuffer[i];
  }
  return sum / STABLE_READINGS;
}

// ===== NEW: Reset Weight Buffer =====
void resetWeightBuffer() {
  weightBufferIndex = 0;
  weightBufferFull = false;
  stableStartTime = 0;
}

// ===== NEW: Check if Cup is Lifted (Fast Detection) =====
bool isCupLifted() {
  return weight < WEIGHT_LIFTED_THRESHOLD;
}

// ===== NEW: Check if Cup is Present (Fast Detection) =====
bool isCupPresent() {
  return weight > WEIGHT_LIFTED_THRESHOLD;
}

// Send status JSON
void sendStatus() {
  StaticJsonDocument<256> doc;
  doc["type"] = "status";
  doc["state"] = stateToString(currentState);
  doc["match_id"] = match_id;
  doc["mode"] = mode;
  doc["team"] = team;
  doc["relay_pos"] = relayPosition;
  doc["battery"] = batteryLevel;

  String json;
  serializeJson(doc, json);
  webSocket.sendTXT(json);

  Serial.print("Sent: ");
  Serial.println(json);
}

void sendRelay() {
  StaticJsonDocument<128> doc;
  doc["type"] = "relay_done";
  doc["match_id"] = match_id;
  doc["team"] = team;
  doc["position"] = relayPosition;  // my position (server decides who's next)

  String json;
  serializeJson(doc, json);
  webSocket.sendTXT(json);

  Serial.print("Sent: ");
  Serial.println(json);
}

void sendWeight() {
  StaticJsonDocument<64> doc;
  doc["type"] = "weight";
  doc["weight"] = start_weight;

  String json;
  serializeJson(doc, json);
  webSocket.sendTXT(json);

  Serial.print("Sent: ");
  Serial.println(json);
}

void sendResults() {
  StaticJsonDocument<256> doc;
  doc["type"] = "results";
  doc["start_weight"] = start_weight;
  doc["end_weight"] = end_weight;
  doc["reaction_time_seconds"] = reactionTime/1000.0;
  doc["time_seconds"] = drinkingTime/1000.0 + reactionTime/1000.0;
  doc["foul"] = foulFlag;

  String json;
  serializeJson(doc, json);
  webSocket.sendTXT(json);

  Serial.print("Sent: ");
  Serial.println(json);
}

void changeState(DeviceState newState) {
  if (newState != currentState) {
    if (newState == DRINKING) {
      chaseIndex = 0;  // reset animation when entering
      lastChase = 0;
    }
    
    // Reset weight buffer when changing to states that need stable weight
    if (newState == STANDBY || newState == CUP || newState == INVALID_CUP || newState == FINISH) {
      resetWeightBuffer();
      startWeightStable = false;
      endWeightStable = false;
    }
    
    Serial.print("State changed to: ");
    Serial.println(stateToString(newState));

    currentState = newState;

    // Only send when changed
    sendStatus();
    lastSentState = newState;
    if (newState == STANDBY) lastStatusSent = millis();
  }
}

void sendReady() {
  StaticJsonDocument<128> doc;
  doc["type"] = "ready";
  doc["device_id"] = device_id;

  String json;
  serializeJson(doc, json);
  webSocket.sendTXT(json);

  Serial.print("Sent: ");
  Serial.println(json);
}
//----- Battery funtions ----

float readBatteryVoltage() {
  uint32_t total = 0;
  for (int i = 0; i < NUM_SAMPLES; i++) {
    total += adc1_get_raw(ADC1_CHANNEL_5);
    delay(2);
  }
  uint32_t rawAvg = total / NUM_SAMPLES;
  uint32_t mv = esp_adc_cal_raw_to_voltage(rawAvg, &adc_chars);
  float v_adc = mv / 1000.0f;
  float vbat = v_adc * (R1 + R2) / R2;
  return vbat * ADC_CORRECTION;
}






float smoothBattery(float newVal) {
  static float avg = 0;
  avg = 0.9 * avg + 0.1 * newVal;  // exponential smoothing
  return avg;
}


float getBatteryPercent(float v_bat) {
  // Simple 18650 approximation curve
  const float volts[] = { 4.20, 4.00, 3.85, 3.70, 3.55, 3.40, 3.20, 3.00 };
  const float percent[] = { 100, 85, 75, 55, 35, 20, 10, 0 };
  int n = sizeof(volts) / sizeof(volts[0]);

  if (v_bat >= volts[0]) return 100;
  if (v_bat <= volts[n - 1]) return 0;

  for (int i = 0; i < n - 1; i++) {
    if (v_bat <= volts[i] && v_bat > volts[i + 1]) {
      // Linear interpolate
      float slope = (percent[i + 1] - percent[i]) / (volts[i + 1] - volts[i]);
      return percent[i] + slope * (v_bat - volts[i]);
    }
  }
  return 0;  // fallback
}


// Handle webSockets events
void onwebSocketsEvent(WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_DISCONNECTED:
      Serial.println("[WS] Disconnected!");
      break;

    case WStype_CONNECTED:
      Serial.printf("[WS] Connected to: %s\n", payload);
      sendStatus();  // only send AFTER connection established
      break;

    case WStype_TEXT:
      {
        Serial.printf("[WS] Message: %s\n", payload);

        StaticJsonDocument<256> doc;
        DeserializationError err = deserializeJson(doc, payload, length);
        if (err) {
          Serial.print("JSON parse error: ");
          Serial.println(err.c_str());
          return;
        }

        const char* type = doc["type"];
        if (!type) return;

        if (strcmp(type, "config") == 0) {
          match_id = doc["match_id"] | 0;
          mode = String((const char*)doc["match_type"]);
          team = doc["team"] | -1;
          relayPosition = doc["position"] | -1;

          // Parse next device MAC (if provided)
          if (doc.containsKey("next_device") && !doc["next_device"].isNull()) {
            String macStr = String((const char*)doc["next_device"]);
            int values[6];
            if (sscanf(macStr.c_str(), "%x:%x:%x:%x:%x:%x",
                       &values[0], &values[1], &values[2],
                       &values[3], &values[4], &values[5])
                == 6) {
              for (int i = 0; i < 6; i++) nextDeviceMac[i] = (uint8_t)values[i];
              nextDeviceSet = true;

              esp_now_peer_info_t peerInfo = {};
              memcpy(peerInfo.peer_addr, nextDeviceMac, 6);
              peerInfo.channel = 0;
              peerInfo.encrypt = false;

              if (esp_now_add_peer(&peerInfo) == ESP_OK) {
                Serial.printf("Next peer set: %s\n", macStr.c_str());
              } else {
                Serial.println("⚠️ Failed to add peer");
              }
            }
          } else {
            nextDeviceSet = false;  // no next device
          }

        } else if (strcmp(type, "relay_turn") == 0) {
          // this ESP is now active in relay mode
          changeState(BEFORE_DRINKING);

        } else if (strcmp(type, "game_ready") == 0) {
          Serial.println("Game is ready, locking device!");
          gameReadyFlag = true;  // ESP moves from READY → LOCKED
        } else if (strcmp(type, "start") == 0) {
          Serial.println("Start signal received!");
          startFlag = true;
        } else if (strcmp(type, "in_relay") == 0) {
          Serial.println("Relay started signal received!");
          changeState(IN_RELAY);
        } else if (strcmp(type, "victory") == 0) {
          int winner = doc["team"];
          Serial.printf("Victory! Winner team = %d\n", winner);
          // maybe play LED animation here
        } else if (strcmp(type, "match_end") == 0) {
          int winner_team = doc["winner_team"] | -1;
          int your_team = doc["your_team"] | -1;

          if (winner_team == your_team) {
            changeState(WIN);
          } else {
            changeState(LOSS);
          }
          // stay in WIN/LOSS until reset comes
        } else if (strcmp(type, "reset") == 0) {
          Serial.println("Reset command received!");
          match_id = NULL;
          mode = "";
          team = -1;
          relayPosition = -1;
          start_weight = 0;
          end_weight = 0;
          reactionTime = 0;
          drinkingTime = 0;
          gameReadyFlag = false;
          startFlag = false;
          foulFlag = false;
          doneFlag = false;
          resultsSent = false;
          finishTime = 0;
          stableWeight = 0;
          resetWeightBuffer();
          startWeightStable = false;
          endWeightStable = false;

          changeState(STANDBY);
        }


        else {
          Serial.printf("Unknown message type: %s\n", type);
        }
        sendStatus();
        break;
      }


    case WStype_ERROR:
      Serial.println("[WS] ERROR!");
      if (payload && length > 0) {
        Serial.printf("[WS] Error payload: %s\n", payload);
      }
      break;

    case WStype_PING:
      Serial.println("[WSc] Got PING");
      break;
    case WStype_PONG:
      Serial.println("[WSc] Got PONG");
      break;

    default:
      Serial.printf("[WS] Event: %d\n", type);
      break;
  }
}

void finishRelay() {
  if (nextDeviceSet) {
    uint8_t baton = 0xA1;
    bool sent = false;
    for (int i = 0; i < 3 && !sent; i++) {
      esp_err_t result = esp_now_send(nextDeviceMac, &baton, 1);
      if (result == ESP_OK) {
        sent = true;
        Serial.println("Sent ESP-NOW trigger to next device!");
      } else {
        Serial.printf("ESP-NOW send failed (%d), retry %d\n", result, i + 1);
        delay(2);
      }
    }
  } else {
    Serial.println("No next device MAC set!");
  }
  sendRelay();  // server notification
}





// Foul relay timer
void startFoulRelayTimer() {
  foulRelayStart = millis();
}

void stopFoulRelayTimer() {
  if (reactionStart > 0) {
    foulRelayTime = millis() - foulRelayStart;
    foulRelayStart = 0;  // reset
    Serial.print("Reaction time (ms): ");
    Serial.println(foulRelayTime);
  }
}


// Reaction timer
void startReactionTimer() {
  reactionStart = millis();
}

void stopReactionTimer() {
  if (reactionStart > 0) {
    reactionTime = millis() - reactionStart;
    reactionStart = 0;  // reset
    Serial.print("Reaction time (ms): ");
    Serial.println(reactionTime);
  }
}

// Drinking timer
void startDrinkingTimer() {
  drinkingStart = millis();
}

void stopDrinkingTimer() {
  if (drinkingStart > 0) {
    drinkingTime = millis() - drinkingStart;
    drinkingStart = 0;  // reset
    Serial.print("Drinking time (ms): ");
    Serial.println(drinkingTime);
  }
}
bool isCupValid(float weight) {
  if (weight >= standart_weight) {
    return true;
  } else {
    return false;
  }  // Placeholder: replace with actual validation logic
}

void setupEspNow() {
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  // Register receive callback
  esp_now_register_recv_cb(onEspNowRecv);
}

void onEspNowRecv(const esp_now_recv_info_t* info, const uint8_t* data, int len) {
  if (len == 1 && data[0] == 0xA1) {
    changeState(BEFORE_DRINKING);
  }
}



// Connect to WiFi
void setupWiFi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    setStrip(true, NUM_PIXELS, ws2812b.Color(0, 10, 0), 200, 0);
  }

  Serial.println("\nWiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void getIDAndCalibration() {
  String mac = WiFi.macAddress();

  // Lookup table for your 10 ESPs
  if (mac == "84:1F:E8:16:89:08") {
    device_id = "ESP-001";
    calibration_factor = 428;
    ADC_CORRECTION = 0.9851f;
  } else if (mac == "84:1F:E8:17:2E:44") {
    device_id = "ESP-002";
    calibration_factor = 434.5;
  } else if (mac == "84:1F:E8:1A:B2:F8") {
    device_id = "ESP-003";
    calibration_factor = 407.7;
    ADC_CORRECTION = 1.0145f; 
  } else if (mac == "24:6F:28:AA:BB:04") {
    device_id = "ESP-004";
    calibration_factor = -6988.0;
  } else if (mac == "24:6F:28:AA:BB:05") {
    device_id = "ESP-005";
    calibration_factor = -7066.7;
  } else if (mac == "24:6F:28:AA:BB:06") {
    device_id = "ESP-006";
    calibration_factor = -7033.9;
  } else if (mac == "24:6F:28:AA:BB:07") {
    device_id = "ESP-007";
    calibration_factor = -7091.1;
  } else if (mac == "24:6F:28:AA:BB:08") {
    device_id = "ESP-008";
    calibration_factor = -7010.0;
  } else if (mac == "24:6F:28:AA:BB:09") {
    device_id = "ESP-009";
    calibration_factor = -7077.2;
  } else if (mac == "24:6F:28:AA:BB:0A") {
    device_id = "ESP-010";
    calibration_factor = -7044.8;
  } else {
    device_id = "ESP-UNK";         // unknown device
    calibration_factor = -7050.0;  // default
  }

  Serial.printf("MAC: %s → Device ID: %s | Calibration: %.2f\n",
                mac.c_str(), device_id.c_str(), calibration_factor);
}

void setup() {
  Serial.begin(115200);

  setupWiFi();
  delay(2000);
  getIDAndCalibration();
  setupEspNow();

  // Battery ADC
  adc1_config_width(ADC_WIDTH_BIT_12);
  adc1_config_channel_atten(ADC1_CHANNEL_5, ADC_ATTEN_DB_2_5);
  esp_adc_cal_characterize(ADC_UNIT_1, ADC_ATTEN_DB_2_5, ADC_WIDTH_BIT_12, vref, &adc_chars);

  scale.begin(DT, SCK);
  scale.set_scale(calibration_factor);  // set calibration factor
  scale.tare();                         // reset the scale to 0

  ws2812b.begin();
  ws2812b.clear();
  ws2812b.show();

  xTaskCreatePinnedToCore(
    ledTask,         // Task function
    "LED Task",      // Name
    4096,            // Stack size
    NULL,            // Params
    1,               // Priority
    &ledTaskHandle,  // Task handle
    0                // Core (0 or 1)
  );

  // Connect webSockets
  String url = "/ws/device/";
  url += device_id;
  Serial.print("Connecting to: ws://");
  Serial.print(ws_server);
  Serial.print(":");
  Serial.print(ws_port);
  Serial.println(url);

  webSocket.begin(ws_server, ws_port, url.c_str());
  webSocket.onEvent(onwebSocketsEvent);
  webSocket.setReconnectInterval(5000);
  webSocket.enableHeartbeat(9000, 3000, 2);  // keep alive
}

void loop() {

  webSocket.loop();

  unsigned long now = millis();
  if (now - lastLoopPrint > 1000) {  // print once per second
    Serial.printf("State: %s | Weight: %.1fg\n", stateToString(currentState).c_str(), weight);
    lastLoopPrint = now;
  }
  
  unsigned long nowBat = millis();
  if (nowBat - lastBatteryRead >= BATTERY_INTERVAL) {
    lastBatteryRead = nowBat;
    float v_bat = readBatteryVoltage();
    batteryLevel = getBatteryPercent(smoothBattery(v_bat));
    Serial.printf("Battery: %.2f V | %.1f %%\n", v_bat, batteryLevel);
  }

  // ===== READ WEIGHT AT FIXED INTERVALS FOR CONSISTENT TIMING =====
  if (millis() - lastWeightRead >= WEIGHT_READ_INTERVAL) {
    lastWeightRead = millis();
    readWeightFast();  // Updates global 'weight' variable
  }

  // Update state
  switch (currentState) {
    case STANDBY:
      // Verify when cup is placed, validates weight of cup
      if (isCupPresent()) {
        Serial.println("Cup detected!");
        resetWeightBuffer();
        changeState(isCupValid(weight) ? CUP : INVALID_CUP);
      }

      // Send periodic status every 5 seconds
      if (millis() - lastStatusSent >= STATUS_INTERVAL) {
        lastStatusSent = millis();
        sendStatus();
        Serial.println("📡 Periodic status sent (STANDBY)");
      }
      break;

      
    case INVALID_CUP:  //-------------------------------------
      // Cup placed is invalid, add weight to cup to change to valid
      // If cup removed goes to standby
      if (!isCupPresent()) {
        changeState(STANDBY);
      } else {
        // Check for stable weight before sending
        if (isWeightStable(weight)) {
          if (stableStartTime == 0) {
            stableStartTime = millis();
          } else if (millis() - stableStartTime >= STABLE_DURATION) {
            start_weight = getStableWeightAverage();
            sendWeight();
            changeState(isCupValid(start_weight) ? CUP : INVALID_CUP);
            stableStartTime = 0;
          }
        } else {
          stableStartTime = 0;  // Reset if weight becomes unstable
        }
      }
      break;
      
    case CUP:  //-------------------------------------
      // Cup placed, waiting for game config
      // If cup removed goes to standby
      if (!isCupPresent()) {
        changeState(STANDBY);
      } else {
        // Check for stable weight before sending
        if (isWeightStable(weight)) {
          if (stableStartTime == 0) {
            stableStartTime = millis();
          } else if (millis() - stableStartTime >= STABLE_DURATION) {
            start_weight = getStableWeightAverage();
            sendWeight();
            
            // Check if ready to proceed
            if (mode.length() > 0 && team >= 0 && relayPosition >= 0) {
              startWeightStable = true;
              changeState(READY);
              sendReady();
            } else {
              // Re-validate cup
              changeState(isCupValid(start_weight) ? CUP : INVALID_CUP);
            }
            stableStartTime = 0;
          }
        } else {
          stableStartTime = 0;  // Reset if weight becomes unstable
        }
      }
      break;
      
    case READY:  //-------------------------------------
      // Game mode chosen, ready waiting for instructions
      if (mode.length() > 0 && team >= 0 && relayPosition >= 0) {
        // Stay ready
      } else {
        changeState(CUP);
      }

      if (gameReadyFlag) {
        changeState(LOCKED);
      }
      break;

    case LOCKED:  //-------------------------------------
      if (startFlag) {
        changeState(START);
        startFlag = false;
      }
      break;

    case START:
      {
        if (!countdownRunning) {
          countdownStart = millis();
          countdownRunning = true;
          Serial.println("Countdown started!");
        }

        unsigned long elapsed = (millis() - countdownStart) / 1000;  // seconds passed
        int remaining = countdownSeconds - elapsed;

        if (remaining > 0) {
          // Still counting down - check for early lift (FOUL)
          if (isCupLifted()) {
            foulFlag = true;
            Serial.println("⚠️ FOUL! Cup lifted before countdown finished.");
            Serial.println("Proceeding to BEFORE_DRINKING despite foul.");
            changeState(BEFORE_DRINKING);
            countdownRunning = false;
          }
        } else {
          // Countdown done → go to BEFORE_DRINKING
          Serial.println("✅ Countdown finished → BEFORE_DRINKING");
          changeState(BEFORE_DRINKING);
          countdownRunning = false;
        }
        break;
      }

    case IN_RELAY:
      // Waiting for turn in relay mode
      if (isCupLifted()) {
        foulFlag = true;
        Serial.println("⚠️ FOUL! Cup lifted during relay wait.");
        changeState(BEFORE_DRINKING);
      }
      break;

    case BEFORE_DRINKING:
      if (!foulFlag) {
        if (reactionStart == 0) {
          startReactionTimer();
        }
        
        // Fast detection of cup lift
        if (isCupLifted()) {
          stopReactionTimer();
          Serial.printf("⚡ Cup lifted! Reaction time: %lu ms\n", reactionTime);
          changeState(DRINKING);
        }
      } else {
        reactionTime = 0;  // Force 0 for foul
        changeState(DRINKING);
      }
      break;

    case DRINKING:
      if (drinkingStart == 0) {
        startDrinkingTimer();
      }

      // Fast detection of cup placement
      if (isCupPresent()) {
        stopDrinkingTimer();
        Serial.printf("⚡ Cup placed! Drinking time: %lu ms\n", drinkingTime);
        resetWeightBuffer();
        changeState(FINISH);
      }
      
      // Timeout check
      if (drinkingTime > DRINKING_TIMEOUT) {
        Serial.println("⏱️ DRINKING TIMEOUT - Forcing finish");
        stopDrinkingTimer();
        foulFlag = true;  // Mark as foul for taking too long
        changeState(FINISH);
      }
      break;

    case FINISH:
      // Immediately trigger relay if needed
      if (mode == "relay" && !resultsSent) {
        finishRelay();  // Send baton immediately
      }

      // Wait for stable weight before sending results
      if (isWeightStable(weight)) {
        if (stableStartTime == 0) {
          stableStartTime = millis();
          Serial.println("🔍 Waiting for stable end weight...");
        } else if (millis() - stableStartTime >= STABLE_DURATION) {
          // Weight has been stable for required duration
          end_weight = getStableWeightAverage();
          
          if (!resultsSent) {
            resultsSent = true;
            Serial.printf("📊 Stable end weight: %.2fg\n", end_weight);
            sendResults();
            changeState(WAITING);
          }
          stableStartTime = 0;
        }
      } else {
        stableStartTime = 0;  // Reset timer if weight becomes unstable
      }
      break;

    case WIN:
      // Victory state - do nothing until reset
      break;

    case LOSS:
      // Loss state - do nothing until reset
      break;
      
    case WAITING:  //-------------------------------------
      // Waiting for server to process results
      if (doneFlag) {
        start_weight = 0;
        end_weight = 0;
        reactionTime = 0;
        drinkingTime = 0;
        gameReadyFlag = false;
        startFlag = false;
        doneFlag = false;
        resetWeightBuffer();
        startWeightStable = false;
        endWeightStable = false;
        changeState(STANDBY);
      }
      break;
  }
}