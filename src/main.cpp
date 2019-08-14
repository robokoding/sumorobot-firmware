/*
    This the code that runs on the SumoRobots
*/
// Include BLE libraries
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <BLE2904.h>
// Include other libraries
#include <string.h>
#include <Ticker.h>
#include <NewPing.h>
#include <Arduino.h>
#include <Preferences.h>

#define DEBUG true

#define VERSION "0.8.0"
#define VERSION_TIMESTAMP "2019.08.13 08:00"

// See the following for generating UUIDs:
// https://www.uuidgenerator.net/
#define NUS_SERVICE_UUID           "6E400001-B5A3-F393-E0A9-E50E24DCCA9E" // NUS service UUID
#define NUS_CHARACTERISTIC_RX_UUID "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
#define NUS_CHARACTERISTIC_TX_UUID "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

// Cleate BLE variables
BLEServer * bleServer = NULL;
bool deviceConnected = false;
bool oldDeviceConnected = false;
BLECharacteristic * nusTxCharacteristic;
BLECharacteristic * batteryLevelCharacteristic;

// Create preferences persistence
Preferences preferences;

// Create timers
Ticker sonarTimer;
Ticker batteryTimer;
Ticker connectionLedTimer;

// Battery stuff
float batteryVoltage;
bool robotMoving = false;
uint8_t batteryLevel = 0;
uint8_t tempBatteryLevel = 0;

// Sonar stuff
uint8_t sonarValue;
NewPing sonar(27, 14, 200);
uint8_t sonarThreshold = 40;

// Line stuff
uint16_t leftLineValue;
uint16_t rightLineValue;
uint16_t leftLineValueField = 0;
uint16_t rightLineValueField = 0;
uint16_t leftLineThreshold = 1000;
uint16_t rightLineThreshold = 1000;

// Other sensor stuff
uint8_t sensorValues[6];
bool ledFeedbackEnabled = true;

// Move command names
std::string cmdStop("stop");
std::string cmdLeft("left");
std::string cmdRight("right");
std::string cmdForward("forward");
std::string cmdBackward("backward");
// Other command names
std::string cmdLed("led");
std::string cmdLine("line");
std::string cmdName("name");
std::string cmdSonar("sonar");
std::string cmdServo("servo");
std::string cmdLedFeedback("ledf");

void setLed(char led, char value) {
  // Convert the value to a HIGH or LOW
  bool state = value == '1' ? HIGH : LOW; 
  if (led == 'c') {
    // Connection status LED is opposite value
    digitalWrite(5, !state);
  }
  else if (led == 's') {
    digitalWrite(16, state);
  }
  else if (led == 'r') {
    digitalWrite(12, state);
  }
  else if (led == 'l') {
    digitalWrite(17, state);
  }
}

void setServo(char servo, int8_t speed) {
  Serial.println(speed);
  if (servo == 'l') {
    ledcWrite(1, map(speed, -100, 100, 1, 100));
  }
  else if (servo == 'r') {
    ledcWrite(2, map(speed, -100, 100, 1, 30));
  }
}

void updateSensorFeedback() {
  if (sonarValue <= sonarThreshold) {
    digitalWrite(16, HIGH);
  }
  else {
    digitalWrite(16, LOW);
  }
  if (abs(leftLineValue - leftLineValueField) > leftLineThreshold) {
    digitalWrite(17, HIGH);
  }
  else {
    digitalWrite(17, LOW);
  }
  if (abs(rightLineValue - rightLineValueField) > rightLineThreshold) {
    digitalWrite(12, HIGH);
  }
  else {
    digitalWrite(12, LOW);
  }
}

void updateSonarValue() {
  // Update the sensor values
  sonarValue = sonar.ping_cm();
  // When we didn't receive a ping back
  // set to max distance
  if (sonarValue == 0) sonarValue = 255;
  leftLineValue = analogRead(34);
  rightLineValue = analogRead(33);
  if (ledFeedbackEnabled) updateSensorFeedback();
  sensorValues[0] = sonarValue;
  sensorValues[1] = leftLineValue >> 8;
  sensorValues[2] = leftLineValue;
  sensorValues[3] = rightLineValue >> 8;
  sensorValues[4] = rightLineValue;
  sensorValues[5] = digitalRead(25);
  // When BLE is connected
  if (deviceConnected) {
    // Notify the new sensor values
    nusTxCharacteristic->setValue(sensorValues, 6);
    nusTxCharacteristic->notify();
  }
}

void updateBatteryLevel() {
  // Don't update battery level when robot is moving
  // the servo motors lower the battery voltage
  // TODO: wait still a little more after moving
  // for the voltage to settle
  if (robotMoving) {
    return;
  }

  // Calculate the battery voltage
  batteryVoltage = 2.12 * (analogRead(32) * 3.3 / 4096);
  // Calculate battery percentage
  tempBatteryLevel = 0.0 + ((100.0 - 0.0) / (4.2 - 3.2)) * (batteryVoltage - 3.2);
  // When battery level changed more than 3%
  if (abs(batteryLevel - tempBatteryLevel) > 3) {
    // Update battery level
    batteryLevel = tempBatteryLevel;
  }
  // Notify the new battery level
  batteryLevelCharacteristic->setValue(&batteryLevel, 1);
  batteryLevelCharacteristic->notify();
#if DEBUG
  Serial.print(batteryVoltage);
  Serial.print(" : ");
  Serial.println(batteryLevel);
#endif
}

void blinkConnectionLed() {
  digitalWrite(5, LOW);
  delay(20);
  digitalWrite(5, HIGH);
}

// BLE connect and disconnect callbacks
class MyServerCallbacks: public BLEServerCallbacks {
  void onConnect(BLEServer * pServer) {
    deviceConnected = true;
  };

  void onDisconnect(BLEServer * pServer) {
    deviceConnected = false;
  }
};

// BLE NUS received callback
class MyCallbacks: public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic * nusRxCharacteristic) {
    // Get the received command over BLE
    std::string cmd = nusRxCharacteristic->getValue();
#if DEBUG
    Serial.println(cmd.c_str());
#endif
    if (cmd.length() > 0) {
      //int speed = atoi(rxValue.c_str());
      //Serial.println(speed);
      //ledcWrite(1, speed); // left 1 ... 100
      //ledcWrite(2, speed); // right 1 ... 30
      // Specify command
      if (cmd == cmdForward) {
        robotMoving = true;
        ledcWrite(1, 100);
        ledcWrite(2, 1);
      }
      else if (cmd == cmdBackward) {
        robotMoving = true;
        ledcWrite(1, 1);
        ledcWrite(2, 30);
      }
      else if (cmd == cmdLeft) {
        robotMoving = true;
        ledcWrite(1, 1);
        ledcWrite(2, 1);
      }
      else if (cmd == cmdRight) {
        robotMoving = true;
        ledcWrite(1, 100);
        ledcWrite(2, 30);
      }
      else if (cmd == cmdStop) {
        robotMoving = false;
        ledcWrite(1, 0);
        ledcWrite(2, 0);
      }
      else if (cmd == cmdLedFeedback) {
        ledFeedbackEnabled = !ledFeedbackEnabled;
      }
      else if (cmd.find(cmdLed) != std::string::npos) {
        setLed(cmd.at(3), cmd.at(4));
      }
      else if (cmd.find(cmdLine) != std::string::npos) {
        // Get the threshold value
        leftLineThreshold = atoi(cmd.substr(4, cmd.length() - 4).c_str());
        rightLineThreshold = leftLineThreshold;
        // Remember value on the field (white or black)
        leftLineValueField = analogRead(34);
        rightLineValueField = analogRead(33);
        // Save the threshold value in the persistence
        preferences.begin("sumorobot", false);
        preferences.putUInt("line_threshold", leftLineThreshold);
        preferences.end();
      }
      else if (cmd.find(cmdSonar) != std::string::npos) {
        sonarThreshold = atoi(cmd.substr(5, cmd.length() - 5).c_str());
        // Save the threshold value in the persistence
        preferences.begin("sumorobot", false);
        preferences.putUInt("sonar_threshold", sonarThreshold);
        preferences.end();
      }
      else if (cmd.find(cmdServo) != std::string::npos) {
        setServo(cmd.at(5), atoi(cmd.substr(6, cmd.length() - 6).c_str()));
      }
      else if (cmd.find(cmdName) != std::string::npos) {
        preferences.begin("sumorobot", false);
        preferences.putString("name", cmd.substr(4, cmd.length() - 4).c_str());
        preferences.end();
      }
    }
  }
};

void setup() {
#if DEBUG
  Serial.begin(115200);
#endif

  // Start preferences persistence
  preferences.begin("sumorobot", false);

  // Create the BLE device
  Serial.println(preferences.getString("name", "SumoRobot").c_str());
  BLEDevice::init(preferences.getString("name", "SumoRobot").c_str());

  preferences.end();

  // Create the BLE server
  bleServer = BLEDevice::createServer();
  bleServer->setCallbacks(new MyServerCallbacks());

  // Create device info service and characteristic
  BLEService * deviceInfoService = bleServer->createService(BLEUUID((uint16_t) 0x180a));
  BLECharacteristic * modelCharacteristic = deviceInfoService->createCharacteristic(
    (uint16_t) 0x2A24, BLECharacteristic::PROPERTY_READ);
  BLECharacteristic * firmwareCharacteristic = deviceInfoService->createCharacteristic(
    (uint16_t) 0x2A26, BLECharacteristic::PROPERTY_READ);
  BLECharacteristic * manufacturerCharacteristic = deviceInfoService->createCharacteristic(
    (uint16_t) 0x2a29, BLECharacteristic::PROPERTY_READ);
  manufacturerCharacteristic->setValue("RoboKoding LTD");
  modelCharacteristic->setValue("SumoRobot");
  firmwareCharacteristic->setValue(VERSION);

  // Create battery service
  BLEService * batteryService = bleServer->createService(BLEUUID((uint16_t) 0x180f));
  // Mandatory battery level characteristic with notification and presence descriptor
  BLE2904* batteryLevelDescriptor = new BLE2904();
	batteryLevelDescriptor->setFormat(BLE2904::FORMAT_UINT8);
	batteryLevelDescriptor->setNamespace(1);
	batteryLevelDescriptor->setUnit(0x27ad);
  // Create battery level characteristics
  batteryLevelCharacteristic = batteryService->createCharacteristic(
    (uint16_t) 0x2a19, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
  batteryLevelCharacteristic->addDescriptor(batteryLevelDescriptor);
	batteryLevelCharacteristic->addDescriptor(new BLE2902());

  // Create the BLE NUS service
  BLEService * nusService = bleServer->createService(NUS_SERVICE_UUID);

  // Create a BLE NUS transmit characteristic
  nusTxCharacteristic = nusService->createCharacteristic(
    NUS_CHARACTERISTIC_TX_UUID, BLECharacteristic::PROPERTY_NOTIFY);
  nusTxCharacteristic->addDescriptor(new BLE2902());

  // Create a BLE NUS receive characteristics
  BLECharacteristic * nusRxCharacteristic = nusService->createCharacteristic(
    NUS_CHARACTERISTIC_RX_UUID, BLECharacteristic::PROPERTY_WRITE);
  nusRxCharacteristic->setCallbacks(new MyCallbacks());

  // Start the services
  deviceInfoService->start();
  batteryService->start();
  nusService->start();

  // Start advertising
  bleServer->getAdvertising()->start();

#if DEBUG
  Serial.println("Waiting a client connection to notify...");
#endif

  // Setup BLE connection status LED
  pinMode(5, OUTPUT);
  connectionLedTimer.attach_ms(2000, blinkConnectionLed);

  // Setup the left servo PWM
  ledcSetup(1, 50, 10);
  ledcAttachPin(15, 1);

  // Setup the right servo PWM
  ledcSetup(2, 50, 8);
  ledcAttachPin(4, 2);

  // Phototransistor pull-ups
  pinMode(19, INPUT_PULLUP);
  pinMode(23, INPUT_PULLUP);

  // Setup battery charge detection pin
  pinMode(25, INPUT);

  // Setup sensor feedback LED pins
  pinMode(16, OUTPUT);
  pinMode(17, OUTPUT);
  pinMode(12, OUTPUT);

  // Setup ADC for reading phototransistors and battery
  analogSetAttenuation(ADC_11db);
  adcAttachPin(32);
  adcAttachPin(33);
  adcAttachPin(34);

  // Setup sonar timer to update it's value
  sonarTimer.attach_ms(50, updateSonarValue);

  // Setup battery level timer to update it's value
  batteryTimer.attach(5, updateBatteryLevel);
  updateBatteryLevel();
}

void loop() {
  // When BLE got disconnected
  if (!deviceConnected && oldDeviceConnected) {
    delay(500); // Give the bluetooth stack the chance to get things ready
    bleServer->startAdvertising(); // Restart advertising
#if DEBUG
    Serial.println("start advertising");
#endif
    oldDeviceConnected = deviceConnected;
    connectionLedTimer.attach_ms(2000, blinkConnectionLed);
  }
  // When BLE got connected
  if (deviceConnected && !oldDeviceConnected) {
    oldDeviceConnected = deviceConnected;
    connectionLedTimer.detach();
    digitalWrite(5, LOW);
  }
}