#pragma once
// Preserved from RafaelS0/smart-recyclingPIV.
constexpr int IR_PIN=9, S0_PIN=4, S1_PIN=5, S2_PIN=6, S3_PIN=7, COLOR_OUT_PIN=8;
// Proposed monitoring pinout accepted by the user on 2026-11-17. Wire exactly as documented.
constexpr int METAL_PIN=22, OBJECT_TRIG=24, OBJECT_ECHO=25;
constexpr int ORGANIC_TRIG=26, ORGANIC_ECHO=27, RECYCLABLE_TRIG=28, RECYCLABLE_ECHO=29;
constexpr int ORGANIC_HX_DT=30, ORGANIC_HX_SCK=31, RECYCLABLE_HX_DT=32, RECYCLABLE_HX_SCK=33;
// No physical motion feedback was specified: do not report a guessed state.
constexpr int CONVEYOR_FEEDBACK_PIN=-1;
// Reserved for a separately validated local controller; not driven by this firmware.
constexpr int RESERVED_SERVO_PIN=44, RESERVED_STEP_PIN=35, RESERVED_DIR_PIN=36, RESERVED_ENABLE_PIN=37;
constexpr bool METAL_ACTIVE_LOW=true;
// Existing white/black pulse references from teste_cor.ino. Confirm on your bench.
constexpr bool COLOR_CALIBRATION_CONFIRMED=false;
constexpr long WHITE_US[3]={50,56,44}, BLACK_US[3]={273,283,222};
// Classification thresholds were zero upstream. Do NOT enable without validation.
constexpr bool SENSOR_RULES_VALIDATED=false;
constexpr unsigned long ORGANIC_MIN_PULSE[3]={0,0,0};
constexpr bool IR_RECYCLABLE_IS_LOW=true;
// HX711: calibration factor (raw units per gram) + measured zero offset. Zero disables.
constexpr float ORGANIC_SCALE=0, RECYCLABLE_SCALE=0;
constexpr long ORGANIC_ZERO_OFFSET=0, RECYCLABLE_ZERO_OFFSET=0;
// Empty/full distances measured from each bin sensor. Zero disables occupancy.
constexpr float ORGANIC_EMPTY_CM=0, ORGANIC_FULL_CM=0, RECYCLABLE_EMPTY_CM=0, RECYCLABLE_FULL_CM=0;
// Default: trigger with C in USB monitor. Optional ultrasonic presence trigger needs calibration.
constexpr bool AUTOMATIC_OBJECT_TRIGGER=false;
constexpr float OBJECT_PRESENT_CM=8, OBJECT_CLEAR_CM=12;
constexpr unsigned long SNAPSHOT_INTERVAL_MS=10000, AI_TIMEOUT_MS=2500;
// Mega Serial1 TX18/RX19 -> ESP32 via level conversion. Serial2 TX16/RX17 -> Pi USB TTL.
constexpr unsigned long LINK_BAUD=115200;
