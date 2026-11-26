#pragma once
// ESP32 dev board; confirm wiring before upload.
constexpr int MEGA_RX_PIN=16, MEGA_TX_PIN=17;
constexpr unsigned long LINK_BAUD=115200;
constexpr int MAX_QUEUED_EVENTS=64;

// Academic routes accept plain JSON over HTTPS without a device key.
constexpr bool ACADEMIC_ENDPOINTS=true;
constexpr unsigned long ACADEMIC_REPORT_INTERVAL_MS=60000;
