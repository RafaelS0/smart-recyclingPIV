#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <LittleFS.h>
#include <time.h>
#include <esp_system.h>
#include "config.h"
#include "tls_ca.h"
#if __has_include("secrets.h")
#include "secrets.h"
#else
#include "secrets.example.h"
#endif
SemaphoreHandle_t fsMutex;
char serialLine[4096];size_t serialLength=0;bool discardLine=false;
unsigned long lastHeartbeat=0, lastAcademicReport=0;
bool academicReportSent=false;
uint32_t crc32(const char *s){uint32_t c=0xffffffff;while(*s){c^=(uint8_t)*s++;for(int i=0;i<8;i++)c=(c>>1)^((c&1)?0xedb88320:0);}return c^0xffffffff;}
String uuid(){char buf[37];snprintf(buf,sizeof(buf),"%08lx-%08lx-%08lx-%08lx",(unsigned long)esp_random(),(unsigned long)esp_random(),(unsigned long)esp_random(),(unsigned long)esp_random());return String(buf);}
String sampleTime(){time_t now=time(nullptr);if(now<1704067200)return "";struct tm t;gmtime_r(&now,&t);char text[25];strftime(text,sizeof(text),"%Y-%m-%dT%H:%M:%SZ",&t);return String(text);}
int queueCount(){File root=LittleFS.open("/");int n=0;for(File f=root.openNextFile();f;f=root.openNextFile())if(String(f.name()).endsWith(".json"))n++;return n;}
bool persist(const JsonDocument &doc, const String &id) {
    xSemaphoreTake(fsMutex, portMAX_DELAY);
    if (queueCount() >= MAX_QUEUED_EVENTS) {
        xSemaphoreGive(fsMutex);
        Serial.println("ERROR storage queue full: event not saved");
        return false;
    }
    String path = "/q_" + id + ".json";
    String temporary = path + ".tmp";
    File file = LittleFS.open(temporary, "w");
    bool ok = false;
    if (file) {
        const size_t size = serializeJson(doc, file);
        file.flush();
        file.close();
        ok = size == measureJson(doc) && LittleFS.rename(temporary, path);
    }
    xSemaphoreGive(fsMutex);
    if (!ok) Serial.println("ERROR durable queue write failed");
    return ok;
}

bool enqueue(JsonDocument &doc) {
    String id = uuid();
    doc.remove("raspberry_serial_online");
    doc["schema_version"] = 1;
    doc["device_id"] = DEVICE_ID;
    doc["event_id"] = id;
    String stamp = sampleTime();
    if (stamp.length()) doc["timestamp"] = stamp;
    else doc["timestamp"] = nullptr;
    if (doc["type"] == "classification") {
        doc["data"]["controller_object_id"] = doc["data"]["object_id"];
        doc["data"]["object_id"] = id;
    }
    return persist(doc, id);
}

bool enqueueAcademic(const JsonDocument &serialDocument) {
    const bool classification = serialDocument["type"] == "classification";
    if (!classification && academicReportSent &&
        millis() - lastAcademicReport < ACADEMIC_REPORT_INTERVAL_MS) return false;

    const String stamp = sampleTime();
    if (stamp.isEmpty()) {
        if (classification) Serial.println("ERROR classification skipped: waiting for NTP clock");
        return false;
    }
    const String id = uuid();
    JsonObjectConst data = serialDocument["data"].as<JsonObjectConst>();
    StaticJsonDocument<512> body;
    body["timestamp"] = stamp;

    if (classification) {
        body["event_id"] = id;
        body["material"] = data["material"];
        if (data["metal"].isNull()) body["metal"] = nullptr;
        else body["metal"] = data["metal"].as<bool>() ? 1 : 0;
        if (data["infrared"].isNull()) body["ir"] = nullptr;
        else body["ir"] = data["infrared"].as<int>();
        if (!data["color_r"].isNull() && !data["color_g"].isNull() && !data["color_b"].isNull()) {
            JsonArray rgb = body.createNestedArray("color");
            rgb.add(data["color_r"].as<int>());
            rgb.add(data["color_g"].as<int>());
            rgb.add(data["color_b"].as<int>());
        } else body["color"] = nullptr;
        body["rasp_material"] = data["ai"]["material"];
        body["rasp_acuracia"] = data["ai"]["confidence"];
        body["acuracia_final"] = data["confidence"];
        return !body.overflowed() && persist(body, "evento_" + id);
    }

    body["organicos_cm"] = data["organic_bin_distance_cm"];
    body["reciclaveis_cm"] = data["recyclable_bin_distance_cm"];
    const bool binsSaved = persist(body, "lixeiras_" + id);
    body.clear();
    body["timestamp"] = stamp;
    JsonArrayConst pulses = data["color_pulse_us"].as<JsonArrayConst>();
    if (pulses.size() == 3) {
        body["sensor_cor"] = !pulses[0].isNull() && !pulses[1].isNull() && !pulses[2].isNull();
    } else body["sensor_cor"] = nullptr;
    body["raspberry"] = serialDocument["raspberry_serial_online"];
    // Digital values alone cannot prove an attached sensor, and the servos have no feedback.
    body["sensor_indutivo"] = nullptr;
    body["sensor_ir"] = nullptr;
    body["servo_topo"] = nullptr;
    body["servo_calha"] = nullptr;
    const bool statusSaved = persist(body, "dispositivos_" + id);
    lastAcademicReport = millis();
    academicReportSent = true;
    return binsSaved || statusSaved;
}

const char *academicRoute(const String &path) {
    if (path.startsWith("/q_evento_")) return "/api/eventos";
    if (path.startsWith("/q_lixeiras_")) return "/api/lixeiras";
    if (path.startsWith("/q_dispositivos_")) return "/api/dispositivos";
    return nullptr;
}

void receiveFrame(){serialLine[serialLength]=0;char *tab=strrchr(serialLine,'\t');if(!tab||strlen(tab+1)!=8){Serial.println("DROP invalid frame");return;}char *end=nullptr;unsigned long expected=strtoul(tab+1,&end,16);if(*end){Serial.println("DROP invalid CRC");return;}*tab=0;if(crc32(serialLine)!=expected){Serial.println("DROP checksum mismatch");return;}DynamicJsonDocument doc(4096);if(deserializeJson(doc,serialLine)||doc["schema_version"]!=1||!doc["data"].is<JsonObject>()){Serial.println("DROP invalid JSON");return;}const char *type=doc["type"]|"";if(strcmp(type,"classification")&&strcmp(type,"telemetry")){Serial.println("DROP unsupported event type");return;}if (ACADEMIC_ENDPOINTS ? enqueueAcademic(doc) : enqueue(doc)) Serial.println("UART event stored");}
String nextQueued(){String selected="";File root=LittleFS.open("/");for(File f=root.openNextFile();f;f=root.openNextFile()){String name=f.name();if(name.startsWith("q_")||name.startsWith("/q_")){if(name.endsWith(".json")&&(selected==""||name<selected))selected=name;}}if(selected.length()&&!selected.startsWith("/"))selected="/"+selected;return selected;}
void sender(void *){unsigned long backoff=1000;for(;;){if(!strlen(WIFI_SSID)||(!ACADEMIC_ENDPOINTS&&!strlen(DEVICE_KEY))){vTaskDelay(pdMS_TO_TICKS(5000));continue;}if(WiFi.status()!=WL_CONNECTED){WiFi.reconnect();vTaskDelay(pdMS_TO_TICKS(5000));continue;}if(sampleTime().isEmpty()){vTaskDelay(pdMS_TO_TICKS(1000));continue;}xSemaphoreTake(fsMutex,portMAX_DELAY);String path=nextQueued(),payload;if(path.length()){File file=LittleFS.open(path,"r");if(file){payload=file.readString();file.close();}}xSemaphoreGive(fsMutex);if(!payload.length()){vTaskDelay(pdMS_TO_TICKS(400));continue;}WiFiClientSecure tls;tls.setCACert(ROOT_CA);tls.setTimeout(15000);HTTPClient http;http.setConnectTimeout(10000);http.setTimeout(15000);int status=-1;
 const char *route=academicRoute(path);
 String url=API_URL;
 if(route){
  const int apiStart=url.lastIndexOf("/api/");
  if(apiStart<0){Serial.println("ERROR API_URL must include /api/");vTaskDelay(pdMS_TO_TICKS(5000));continue;}
  url=url.substring(0,apiStart)+route;
 }
 if(http.begin(tls,url)){http.addHeader("Content-Type","application/json");if(!route)http.addHeader("X-Device-Key",DEVICE_KEY);status=http.POST((uint8_t*)payload.c_str(),payload.length());http.end();}if(status==200||status==201){xSemaphoreTake(fsMutex,portMAX_DELAY);LittleFS.remove(path);xSemaphoreGive(fsMutex);backoff=1000;Serial.println("HTTPS event acknowledged");}else if(status==422||status==409||status==400){xSemaphoreTake(fsMutex,portMAX_DELAY);String rejected=path;rejected.replace("/q_","/rejected_");LittleFS.rename(path,rejected);xSemaphoreGive(fsMutex);Serial.printf("ERROR event rejected HTTP %d; preserved for diagnosis\n",status);vTaskDelay(pdMS_TO_TICKS(1000));}else{Serial.printf("HTTPS retry pending (%d); credential values omitted\n",status);vTaskDelay(pdMS_TO_TICKS(backoff));backoff=min(backoff*2,60000UL);}}}
void setup(){Serial.begin(115200);Serial2.begin(LINK_BAUD,SERIAL_8N1,MEGA_RX_PIN,MEGA_TX_PIN);fsMutex=xSemaphoreCreateMutex();if(!LittleFS.begin(false)){Serial.println("LittleFS not initialized. Format ONCE with explicit maintenance sketch, never auto-format in production.");while(true)delay(1000);}WiFi.mode(WIFI_STA);WiFi.setAutoReconnect(true);if(strlen(WIFI_SSID))WiFi.begin(WIFI_SSID,WIFI_PASSWORD);configTime(0,0,"pool.ntp.org","time.google.com");xTaskCreatePinnedToCore(sender,"https_sender",12288,nullptr,1,nullptr,0);Serial.println("Bridge ready. UART reception and HTTPS delivery run independently.");}
void loop(){while(Serial2.available()){char c=Serial2.read();if(c=='\n'){if(!discardLine&&serialLength)receiveFrame();discardLine=false;serialLength=0;}else if(c!='\r'){if(!discardLine&&serialLength<sizeof(serialLine)-1)serialLine[serialLength++]=c;else{discardLine=true;serialLength=0;}}}if(!ACADEMIC_ENDPOINTS&&millis()-lastHeartbeat>=30000){lastHeartbeat=millis();DynamicJsonDocument doc(512);doc["type"]="heartbeat";doc["data"]["device_role"]="esp32";enqueue(doc);}delay(1);}
