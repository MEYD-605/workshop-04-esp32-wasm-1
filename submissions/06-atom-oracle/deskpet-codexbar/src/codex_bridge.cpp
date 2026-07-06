#include "codex_bridge.h"
#include "pet.h"

#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoOTA.h>
#include <Preferences.h>
#include <ArduinoJson.h>

#if __has_include("wifi_private.h")
#include "wifi_private.h"
#endif

static WebServer server(80);
static Preferences wprefs;
static bool wifiOk = false;
static bool otaReady = false;
static uint32_t lastStatusMs = 0;
static char ipBuf[24] = "-";
static String serialCfgLine;
static uint32_t lastWifiRetryMs = 0;

static void applyStatus(int total, int running, int waiting, const char* msg, long tokens,
                        int pct5h=-1, long reset5h=-1, int pct7d=-1, long reset7d=-1,
                        int pctGrok=-1, int pctClaude=-1, int pctClaudeWeek=-1,
                        long resetGrok=-1, long resetClaude=-1, long resetClaudeWeek=-1) {
  pet_set_link(true, 0);
  pet_set_activity(total, running, waiting, msg ? msg : "codex", tokens);
  pet_set_usage(pct5h, reset5h, pct7d, reset7d);
  pet_set_extra_usage(pctGrok, pctClaude, pctClaudeWeek, resetGrok, resetClaude, resetClaudeWeek);
  pet_force_redraw();
  lastStatusMs = millis();
  Serial.printf("[bridge] status total=%d running=%d waiting=%d tokens=%ld msg=%s\n",
                total, running, waiting, tokens, msg ? msg : "codex");
  if (pct5h >= 0 || reset5h >= 0 || pct7d >= 0 || reset7d >= 0 || pctGrok >= 0 || pctClaude >= 0 || pctClaudeWeek >= 0 ||
      resetGrok >= 0 || resetClaude >= 0 || resetClaudeWeek >= 0) {
    Serial.printf("[bridge] usage pct5h=%d reset5h=%ld pct7d=%d reset7d=%ld grok=%d claude=%d cwk=%d resetGrok=%ld resetClaude=%ld resetCwk=%ld\n",
                  pct5h, reset5h, pct7d, reset7d, pctGrok, pctClaude, pctClaudeWeek, resetGrok, resetClaude, resetClaudeWeek);
  }
}

static void sendText(int code, const String& body) {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Headers", "content-type");
  server.send(code, "text/plain; charset=utf-8", body);
}

static void handleRoot() {
  String body;
  body += "Atom ESP32 Codex bridge\n";
  body += "IP: "; body += ipBuf; body += "\n";
  body += "POST /api/status JSON: {total,running,waiting,msg,tokens,pct5h,reset5h,pct7d,reset7d}\n";
  body += "GET /api/status?running=1&waiting=0&total=1&msg=Codex%20working&tokens=123\n";
  body += "POST /wifi form/query: ssid + pass\n";
  sendText(200, body);
}

static void handlePing() { sendText(200, "ok atom-codex-bridge"); }

static void handleStatus() {
  if (server.method() == HTTP_OPTIONS) { sendText(204, ""); return; }
  int total=server.arg("total").length()?server.arg("total").toInt():1;
  int running=server.arg("running").length()?server.arg("running").toInt():0;
  int waiting=server.arg("waiting").length()?server.arg("waiting").toInt():0;
  long tokens=server.arg("tokens").length()?server.arg("tokens").toInt():0;
  int pct5h=server.arg("pct5h").length()?server.arg("pct5h").toInt():-1;
  long reset5h=server.arg("reset5h").length()?server.arg("reset5h").toInt():-1;
  int pct7d=server.arg("pct7d").length()?server.arg("pct7d").toInt():-1;
  long reset7d=server.arg("reset7d").length()?server.arg("reset7d").toInt():-1;
  int pctGrok=server.arg("grok").length()?server.arg("grok").toInt():-1;
  int pctClaude=server.arg("claude").length()?server.arg("claude").toInt():-1;
  int pctClaudeWeek=server.arg("cwk").length()?server.arg("cwk").toInt():-1;
  long resetGrok=server.arg("resetGrok").length()?server.arg("resetGrok").toInt():-1;
  long resetClaude=server.arg("resetClaude").length()?server.arg("resetClaude").toInt():-1;
  long resetClaudeWeek=server.arg("resetCwk").length()?server.arg("resetCwk").toInt():-1;
  String msg=server.arg("msg");
  String forceState=server.arg("forceState");
  uint32_t forceMs=server.arg("forceMs").length()?(uint32_t)server.arg("forceMs").toInt():0;
  String pagePin=server.arg("pagePin");
  if (server.hasArg("plain") && server.arg("plain").length()) {
    StaticJsonDocument<512> doc;
    DeserializationError err = deserializeJson(doc, server.arg("plain"));
    if (!err) {
      total=doc["total"] | total; running=doc["running"] | running; waiting=doc["waiting"] | waiting;
      tokens=doc["tokens"] | tokens; pct5h=doc["pct5h"] | pct5h; reset5h=doc["reset5h"] | reset5h;
      pct7d=doc["pct7d"] | pct7d; reset7d=doc["reset7d"] | reset7d;
      pctGrok=doc["grok"] | pctGrok; pctClaude=doc["claude"] | pctClaude; pctClaudeWeek=doc["cwk"] | pctClaudeWeek;
      resetGrok=doc["resetGrok"] | resetGrok; resetClaude=doc["resetClaude"] | resetClaude; resetClaudeWeek=doc["resetCwk"] | resetClaudeWeek;
      msg=(const char*)(doc["msg"] | msg.c_str());
      forceState=(const char*)(doc["forceState"] | forceState.c_str());
      forceMs=doc["forceMs"] | forceMs;
      pagePin=(const char*)(doc["pagePin"] | pagePin.c_str());
    }
  }
  if (!msg.length()) msg = running ? "Codex working" : waiting ? "Codex waiting" : "Codex idle";
  applyStatus(total, running, waiting, msg.c_str(), tokens, pct5h, reset5h, pct7d, reset7d,
              pctGrok, pctClaude, pctClaudeWeek, resetGrok, resetClaude, resetClaudeWeek);
  if (pagePin.length()) { pagePin.trim(); pagePin.toLowerCase(); pet_set_page_pinned(pagePin == "1" || pagePin == "true" || pagePin == "on"); }
  if (forceState.length()) { forceState.trim(); pet_force_state(forceState.c_str(), forceMs ? forceMs : 3500); }
  sendText(200, "ok status applied");
}

static void handleWifi() {
  String ssid = server.arg("ssid");
  String pass = server.arg("pass");
  if (!ssid.length()) { sendText(400, "missing ssid"); return; }
  wprefs.begin("wifi", false);
  wprefs.putString("ssid", ssid);
  wprefs.putString("pass", pass);
  wprefs.end();
  sendText(200, "saved; rebooting");
  delay(500);
  ESP.restart();
}

static bool connectSavedWifi() {
  wprefs.begin("wifi", true);
  String ssid = wprefs.getString("ssid", "");
  String pass = wprefs.getString("pass", "");
  wprefs.end();
  bool bootstrap = false;
  if (!ssid.length()) {
#if defined(ATOM_WIFI_SSID) && defined(ATOM_WIFI_PASS)
    ssid = ATOM_WIFI_SSID;
    pass = ATOM_WIFI_PASS;
    bootstrap = true;
    Serial.println("[wifi] no saved SSID; using private bootstrap creds");
#else
    Serial.println("[wifi] no saved SSID; setup AP only");
    return false;
#endif
  }
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(ssid.c_str(), pass.c_str());
  Serial.printf("[wifi] Connecting to SSID: %s\n", ssid.c_str());
  uint32_t until = millis() + 30000;
  while (millis() < until && WiFi.status() != WL_CONNECTED) { delay(250); }
  if (WiFi.status() == WL_CONNECTED) {
    wifiOk = true;
    snprintf(ipBuf, sizeof(ipBuf), "%s", WiFi.localIP().toString().c_str());
    Serial.printf("[wifi] Connected. IP=%s RSSI=%d\n", ipBuf, WiFi.RSSI());
    if (bootstrap) {
      wprefs.begin("wifi", false);
      wprefs.putString("ssid", ssid);
      wprefs.putString("pass", pass);
      wprefs.end();
      Serial.println("[wifi] bootstrap creds saved to NVS");
    }
    return true;
  }
  Serial.printf("[wifi] connect failed; status=%d; setup AP enabled\n", (int)WiFi.status());
  return false;
}

static void startSetupAp() {
  // Keep STA alive while setup AP is open, so saved Wi-Fi can retry and OTA can recover.
  delay(100);
  WiFi.persistent(false);
  WiFi.mode(WIFI_AP_STA);
  WiFi.setSleep(false);
  IPAddress ip(192,168,4,1), gw(192,168,4,1), mask(255,255,255,0);
  WiFi.softAPConfig(ip, gw, mask);
  bool apOk = WiFi.softAP("Atom-ESP32-Setup", "atomsetup275", 1, 0, 1);
  snprintf(ipBuf, sizeof(ipBuf), "%s", WiFi.softAPIP().toString().c_str());
  Serial.printf("[portal] AP %s\n", apOk ? "ready" : "failed");
  Serial.printf("[portal] Connect to Wi-Fi AP: Atom-ESP32-Setup\n");
  Serial.printf("[portal] Open http://%s/\n", ipBuf);
}

static void retrySavedWifi() {
  if (wifiOk) return;
  if (millis() - lastWifiRetryMs < 20000) return;
  lastWifiRetryMs = millis();
  wprefs.begin("wifi", true);
  String ssid = wprefs.getString("ssid", "");
  String pass = wprefs.getString("pass", "");
  wprefs.end();
  if (!ssid.length()) return;
  Serial.printf("[wifi] retry saved SSID: %s\n", ssid.c_str());
  WiFi.mode(WIFI_AP_STA);
  WiFi.setSleep(false);
  WiFi.begin(ssid.c_str(), pass.c_str());
  uint32_t until = millis() + 12000;
  while (millis() < until && WiFi.status() != WL_CONNECTED) {
    server.handleClient();
    delay(250);
  }
  if (WiFi.status() == WL_CONNECTED) {
    wifiOk = true;
    snprintf(ipBuf, sizeof(ipBuf), "%s", WiFi.localIP().toString().c_str());
    Serial.printf("[wifi] Connected. IP=%s RSSI=%d\n", ipBuf, WiFi.RSSI());
    if (!otaReady) {
      ArduinoOTA.setHostname("atom-esp32s3");
      ArduinoOTA.begin();
      otaReady = true;
      Serial.printf("[ota] Ready. Hostname=atom-esp32s3.local IP=%s\n", ipBuf);
    }
  } else {
    Serial.printf("[wifi] retry failed; status=%d; AP remains active\n", (int)WiFi.status());
  }
}

void codexBridgeInit() {
  bool ok = connectSavedWifi();
  if (!ok) startSetupAp();

  server.on("/", HTTP_GET, handleRoot);
  server.on("/api/ping", HTTP_GET, handlePing);
  server.on("/api/status", HTTP_GET, handleStatus);
  server.on("/api/status", HTTP_POST, handleStatus);
  server.on("/wifi", HTTP_GET, handleWifi);
  server.on("/wifi", HTTP_POST, handleWifi);
  server.begin();
  Serial.printf("[bridge] HTTP ready at http://%s/\n", ipBuf);

  if (wifiOk) {
    ArduinoOTA.setHostname("atom-esp32s3");
    ArduinoOTA.begin();
    otaReady = true;
    Serial.printf("[ota] Ready. Hostname=atom-esp32s3.local IP=%s\n", ipBuf);
  }
  applyStatus(1, 0, 0, "Codex bridge ready", 0);
}


static void handleSerialConfig() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      String line = serialCfgLine;
      serialCfgLine = "";
      if (line.startsWith("WIFI|")) {
        int sep = line.indexOf('|', 5);
        if (sep > 5) {
          String ssid = line.substring(5, sep);
          String pass = line.substring(sep + 1);
          wprefs.begin("wifi", false);
          wprefs.putString("ssid", ssid);
          wprefs.putString("pass", pass);
          wprefs.end();
          Serial.println("[wifi] serial credentials saved to NVS; rebooting");
          delay(250);
          ESP.restart();
        } else {
          Serial.println("[wifi] serial config ignored: bad format");
        }
      } else if (line.startsWith("STATUS|")) {
        int p1 = line.indexOf('|', 7);
        int p2 = line.indexOf('|', p1 + 1);
        int p3 = line.indexOf('|', p2 + 1);
        int p4 = line.indexOf('|', p3 + 1);
        if (p1 > 0 && p2 > p1 && p3 > p2 && p4 > p3) {
          int total = line.substring(7, p1).toInt();
          int running = line.substring(p1 + 1, p2).toInt();
          int waiting = line.substring(p2 + 1, p3).toInt();
          long tokens = line.substring(p3 + 1, p4).toInt();
          int pct5h = -1, pct7d = -1, pctGrok = -1, pctClaude = -1, pctClaudeWeek = -1;
          long reset5h = -1, reset7d = -1, resetGrok = -1, resetClaude = -1, resetClaudeWeek = -1;
          int p5 = line.indexOf('|', p4 + 1);
          String msg;
          if (p5 > p4) {
            msg = line.substring(p4 + 1, p5);
            int p6 = line.indexOf('|', p5 + 1);
            int p7 = line.indexOf('|', p6 + 1);
            int p8 = line.indexOf('|', p7 + 1);
            if (p6 > p5 && p7 > p6 && p8 > p7) {
              pct5h = line.substring(p5 + 1, p6).toInt();
              reset5h = line.substring(p6 + 1, p7).toInt();
              pct7d = line.substring(p7 + 1, p8).toInt();
              int p9 = line.indexOf('|', p8 + 1);
              if (p9 > p8) {
                reset7d = line.substring(p8 + 1, p9).toInt();
                int p10 = line.indexOf('|', p9 + 1);
                int p11 = line.indexOf('|', p10 + 1);
                if (p10 > p9 && p11 > p10) {
                  pctGrok = line.substring(p9 + 1, p10).toInt();
                  pctClaude = line.substring(p10 + 1, p11).toInt();
                  int p12 = line.indexOf('|', p11 + 1);
                  if (p12 > p11) {
                    pctClaudeWeek = line.substring(p11 + 1, p12).toInt();
                    int p13 = line.indexOf('|', p12 + 1);
                    if (p13 > p12) {
                      resetGrok = line.substring(p12 + 1, p13).toInt();
                      int p14 = line.indexOf('|', p13 + 1);
                      if (p14 > p13) {
                        resetClaude = line.substring(p13 + 1, p14).toInt();
                        resetClaudeWeek = line.substring(p14 + 1).toInt();
                      } else {
                        resetClaude = line.substring(p13 + 1).toInt();
                      }
                    } else {
                      resetGrok = line.substring(p12 + 1).toInt();
                    }
                  } else {
                    pctClaudeWeek = line.substring(p11 + 1).toInt();
                  }
                }
              } else {
                reset7d = line.substring(p8 + 1).toInt();
              }
            }
          } else {
            msg = line.substring(p4 + 1);
          }
          applyStatus(total, running, waiting, msg.c_str(), tokens, pct5h, reset5h, pct7d, reset7d,
                      pctGrok, pctClaude, pctClaudeWeek, resetGrok, resetClaude, resetClaudeWeek);
          Serial.println("[bridge] serial status applied");
        } else {
          Serial.println("[bridge] serial status ignored: bad format");
        }
      } else if (line.startsWith("PAGE|")) {
        String page = line.substring(5); page.trim(); page.toLowerCase();
        if (page == "next") pet_next_page();
        else if (page == "prev" || page == "previous") pet_prev_page();
        else if (page == "pin" || page == "pinned" || page == "lock") pet_set_page_pinned(true);
        else if (page == "unpin" || page == "unlock") pet_set_page_pinned(false);
        else if (page == "togglepin") pet_set_page_pinned(!pet_page_pinned());
        else pet_set_page((uint8_t)page.toInt());
        Serial.printf("[bridge] serial page applied: %s\n", page.c_str());
      } else if (line.startsWith("STATE|")) {
        int sep = line.indexOf('|', 6);
        String state = sep > 6 ? line.substring(6, sep) : line.substring(6);
        uint32_t ms = sep > 6 ? (uint32_t)line.substring(sep + 1).toInt() : 3000;
        state.trim();
        if (pet_force_state(state.c_str(), ms)) {
          Serial.printf("[bridge] serial state applied: %s\n", state.c_str());
        } else {
          Serial.printf("[bridge] serial state ignored: %s\n", state.c_str());
        }
      }
      continue;
    }
    if (serialCfgLine.length() < 160) serialCfgLine += c;
  }
}

void codexBridgeLoop() {
  handleSerialConfig();
  server.handleClient();
  retrySavedWifi();
  if (otaReady) ArduinoOTA.handle();
}

bool codexBridgeActive() {
  return (millis() - lastStatusMs) < 75000;
}

const char* codexBridgeIp() { return ipBuf; }
