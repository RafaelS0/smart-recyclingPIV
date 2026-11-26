#include <Arduino.h>
#include <ArduinoJson.h>
#include <HX711.h>
#include "config.h"
#include <math.h>

HX711 organicScale, recyclableScale;
char piLine[640];size_t piLength=0;bool piDiscard=false;
char output[1900];StaticJsonDocument<2048> packet;
unsigned long objectNumber=0, lastSnapshot=0, waitStarted=0, lastPresence=0, lastHello=0, lastPiContact=0;
bool piSeen=false;
bool pending=false,present=false;char objectId[48];char piSession[17]={0};
struct Sample {int ir;unsigned long pulse[3];float distance,organicDistance,recyclableDistance,organicWeight,recyclableWeight;bool metal;};
Sample sample;
uint32_t crc32(const char *s){uint32_t c=0xffffffff;while(*s){c^=(uint8_t)*s++;for(int i=0;i<8;i++)c=(c>>1)^((c&1)?0xedb88320:0);}return c^0xffffffff;}
float distanceCm(int trig,int echo){if(trig<0||echo<0)return NAN;digitalWrite(trig,LOW);delayMicroseconds(2);digitalWrite(trig,HIGH);delayMicroseconds(10);digitalWrite(trig,LOW);unsigned long t=pulseIn(echo,HIGH,25000);return t?t*0.0343f/2:NAN;}
unsigned long colorPulse(bool s2,bool s3){digitalWrite(S2_PIN,s2);digitalWrite(S3_PIN,s3);delay(20);return pulseIn(COLOR_OUT_PIN,LOW,100000);}
float weight(HX711 &scale,int pin,float factor){if(pin<0||factor==0||!scale.is_ready())return NAN;float value=scale.get_units(1);return value>=0?value:NAN;}
void acquire(){sample.ir=digitalRead(IR_PIN);sample.pulse[0]=colorPulse(LOW,LOW);sample.pulse[1]=colorPulse(HIGH,HIGH);sample.pulse[2]=colorPulse(LOW,HIGH);sample.metal=METAL_PIN>=0&&(digitalRead(METAL_PIN)==(METAL_ACTIVE_LOW?LOW:HIGH));sample.distance=distanceCm(OBJECT_TRIG,OBJECT_ECHO);delay(30);sample.organicDistance=distanceCm(ORGANIC_TRIG,ORGANIC_ECHO);delay(30);sample.recyclableDistance=distanceCm(RECYCLABLE_TRIG,RECYCLABLE_ECHO);sample.organicWeight=weight(organicScale,ORGANIC_HX_DT,ORGANIC_SCALE);sample.recyclableWeight=weight(recyclableScale,RECYCLABLE_HX_DT,RECYCLABLE_SCALE);}
void nullable(JsonObject d,const char *key,float value){if(isnan(value))d[key]=nullptr;else d[key]=value;}
float occupancy(float d,float empty,float full){return !isnan(d)&&empty>full&&full>0?constrain(100.0f*(empty-d)/(empty-full),0.0f,100.0f):NAN;}
const char *sensorClass(){if(METAL_PIN>=0&&sample.metal)return "reciclavel";if(!SENSOR_RULES_VALIDATED)return "indefinido";for(int i=0;i<3;i++)if(!sample.pulse[i]||!ORGANIC_MIN_PULSE[i])return "indefinido";if(sample.ir==(IR_RECYCLABLE_IS_LOW?LOW:HIGH))return "reciclavel";return sample.pulse[0]>ORGANIC_MIN_PULSE[0]&&sample.pulse[1]>ORGANIC_MIN_PULSE[1]&&sample.pulse[2]>ORGANIC_MIN_PULSE[2]?"organico":"reciclavel";}
void createPacket(const char *type){packet.clear();packet["schema_version"]=1;packet["type"]=type;if(!strcmp(type,"telemetry"))packet["raspberry_serial_online"]=piSeen&&millis()-lastPiContact<45000;JsonObject d=packet.createNestedObject("data");d["device_role"]="esp32";d["infrared"]=sample.ir;d["infrared_mode"]="digital";if(METAL_PIN>=0)d["metal"]=sample.metal;else d["metal"]=nullptr;d["color_calibrated"]=COLOR_CALIBRATION_CONFIRMED;JsonArray pulses=d.createNestedArray("color_pulse_us");const char *channels[]={"color_r","color_g","color_b"};for(int i=0;i<3;i++){if(sample.pulse[i])pulses.add(sample.pulse[i]);else pulses.add(nullptr);if(COLOR_CALIBRATION_CONFIRMED&&sample.pulse[i]&&BLACK_US[i]>WHITE_US[i])d[channels[i]]=constrain(map(sample.pulse[i],WHITE_US[i],BLACK_US[i],255,0),0,255);else d[channels[i]]=nullptr;}nullable(d,"distance_cm",sample.distance);nullable(d,"organic_bin_distance_cm",sample.organicDistance);nullable(d,"recyclable_bin_distance_cm",sample.recyclableDistance);nullable(d,"organic_fill_pct",occupancy(sample.organicDistance,ORGANIC_EMPTY_CM,ORGANIC_FULL_CM));nullable(d,"recyclable_fill_pct",occupancy(sample.recyclableDistance,RECYCLABLE_EMPTY_CM,RECYCLABLE_FULL_CM));nullable(d,"organic_weight_g",sample.organicWeight);nullable(d,"recyclable_weight_g",sample.recyclableWeight);if(CONVEYOR_FEEDBACK_PIN>=0)d["conveyor_running"]=digitalRead(CONVEYOR_FEEDBACK_PIN)==HIGH;else d["conveyor_running"]=nullptr;d["servo_position_deg"]=nullptr;JsonArray faults=d.createNestedArray("faults");for(int i=0;i<3;i++)if(!sample.pulse[i]){faults.add("tcs230_timeout");break;}}
void transmit(){if(packet.overflowed()||measureJson(packet)>=sizeof(output)){Serial.println(F("ERROR packet too large; not sent"));return;}serializeJson(packet,output,sizeof(output));uint32_t crc=crc32(output);Serial1.print(output);Serial1.print('\t');char hex[9];snprintf(hex,sizeof(hex),"%08lx",(unsigned long)crc);Serial1.println(hex);}
void finishObject(JsonObjectConst ai=JsonObjectConst()){
 const char *s=sensorClass();const char *a=ai.isNull()?"indefinido":ai["material"]|"indefinido";const char *result="indefinido",*fusion="unavailable";
 if(strcmp(s,"indefinido")&&strcmp(a,"indefinido")){if(!strcmp(s,a)){result=s;fusion="agreement";}else fusion="divergence";}
 else if(strcmp(a,"indefinido")){result=a;fusion="ai";}else if(strcmp(s,"indefinido")){result=s;fusion="sensors";}
 createPacket("classification");JsonObject d=packet["data"];d["object_id"]=objectId;d["material"]=result;d["sensor_material"]=s;d["fusion"]=fusion;
 if(!ai.isNull()){d["ai"]=ai;d["confidence"]=(!strcmp(fusion,"ai")||!strcmp(fusion,"agreement"))?ai["confidence"]:JsonVariantConst();}else{d["confidence"]=nullptr;d["faults"].as<JsonArray>().add("ai_unavailable_or_timeout");}
 transmit();pending=false;Serial.print(F("CLASSIFICATION "));Serial.println(result);
}
void triggerObject(){if(pending)return;acquire();if(piSession[0])snprintf(objectId,sizeof(objectId),"%s-%lu",piSession,++objectNumber);else snprintf(objectId,sizeof(objectId),"no-ai-%lu-%lu",millis(),++objectNumber);pending=true;waitStarted=millis();if(!piSession[0]){finishObject();return;}StaticJsonDocument<160> request;request["type"]="infer";request["object_id"]=objectId;serializeJson(request,Serial2);Serial2.println();}
void readPi(){
 while(Serial2.available()){
  char c=Serial2.read();
  if(c=='\n'){
   if(!piDiscard&&piLength){
    piLine[piLength]=0;StaticJsonDocument<640> reply;
    if(!deserializeJson(reply,piLine)){
     const char *type=reply["type"]|"";
     if(!pending&&!strcmp(type,"session")){
      const char *nonce=reply["session_id"]|"";
      if(strlen(nonce)==16){strncpy(piSession,nonce,sizeof(piSession)-1);piSession[16]=0;piSeen=true;lastPiContact=millis();}
     }else if(!strcmp(type,"pong")){
      piSeen=true;lastPiContact=millis();
     }else if(pending&&!strcmp(type,"ai_result")&&!strcmp(reply["object_id"]|"",objectId)){
      piSeen=true;lastPiContact=millis();
      if(reply["ok"]==true)finishObject(reply["ai"].as<JsonObjectConst>());else finishObject();
     }
    }
   }
   piLength=0;piDiscard=false;
  }else if(c!='\r'){
   if(piLength<sizeof(piLine)-1&&!piDiscard)piLine[piLength++]=c;else{piDiscard=true;piLength=0;}
  }
 }
}
void setup(){Serial.begin(115200);Serial1.begin(LINK_BAUD);Serial2.begin(LINK_BAUD);pinMode(IR_PIN,INPUT);int colorPins[]={S0_PIN,S1_PIN,S2_PIN,S3_PIN};for(int p:colorPins)pinMode(p,OUTPUT);pinMode(COLOR_OUT_PIN,INPUT);digitalWrite(S0_PIN,HIGH);digitalWrite(S1_PIN,LOW);if(METAL_PIN>=0)pinMode(METAL_PIN,INPUT_PULLUP);if(CONVEYOR_FEEDBACK_PIN>=0)pinMode(CONVEYOR_FEEDBACK_PIN,INPUT);int trig[]={OBJECT_TRIG,ORGANIC_TRIG,RECYCLABLE_TRIG},echo[]={OBJECT_ECHO,ORGANIC_ECHO,RECYCLABLE_ECHO};for(int i=0;i<3;i++)if(trig[i]>=0&&echo[i]>=0){pinMode(trig[i],OUTPUT);pinMode(echo[i],INPUT);}if(ORGANIC_HX_DT>=0&&ORGANIC_HX_SCK>=0){organicScale.begin(ORGANIC_HX_DT,ORGANIC_HX_SCK);organicScale.set_scale(ORGANIC_SCALE);organicScale.set_offset(ORGANIC_ZERO_OFFSET);}if(RECYCLABLE_HX_DT>=0&&RECYCLABLE_HX_SCK>=0){recyclableScale.begin(RECYCLABLE_HX_DT,RECYCLABLE_HX_SCK);recyclableScale.set_scale(RECYCLABLE_SCALE);recyclableScale.set_offset(RECYCLABLE_ZERO_OFFSET);}Serial.println(F("Monitoring only. C triggers one real object; no motor/servo outputs."));}
void loop(){
 readPi();
 if(!pending&&millis()-lastHello>=(piSession[0]?15000UL:3000UL)){
  lastHello=millis();
  if(piSession[0])Serial2.println(F("{\"type\":\"ping\"}"));
  else Serial2.println(F("{\"type\":\"hello\"}"));
 }
 if(pending&&millis()-waitStarted>=AI_TIMEOUT_MS)finishObject();
 while(Serial.available()){
  char c=Serial.read();
  if(c=='C'||c=='c')triggerObject();
  else if(!pending&&(c=='R'||c=='r')){
   acquire();createPacket("telemetry");serializeJson(packet,Serial);Serial.println();
   if(ORGANIC_HX_DT>=0&&organicScale.is_ready()){Serial.print(F("ORGANIC_HX_RAW "));Serial.println(organicScale.read());}
   if(RECYCLABLE_HX_DT>=0&&recyclableScale.is_ready()){Serial.print(F("RECYCLABLE_HX_RAW "));Serial.println(recyclableScale.read());}
  }
 }
 if(!pending&&AUTOMATIC_OBJECT_TRIGGER&&millis()-lastPresence>=100){
  lastPresence=millis();float d=distanceCm(OBJECT_TRIG,OBJECT_ECHO);
  if(!isnan(d)){if(!present&&d<OBJECT_PRESENT_CM){present=true;triggerObject();}else if(d>OBJECT_CLEAR_CM)present=false;}
 }
 if(!pending&&millis()-lastSnapshot>=SNAPSHOT_INTERVAL_MS){lastSnapshot=millis();acquire();createPacket("telemetry");transmit();}
}
