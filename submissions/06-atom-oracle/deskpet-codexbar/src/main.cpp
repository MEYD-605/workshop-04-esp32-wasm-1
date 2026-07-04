// jc3248-pet — a fresh, minimal GIF pet for the Guition JC3248W535
// (ESP32-S3 + AXS15231 320x480 QSPI), built on the PROVEN gallery foundation.
//
// TU rule: the axs:: driver keeps STATIC state, so ONLY this file calls
// axs::init/push/fill_solid/read_touch. pet.cpp draws into the shared `spr`;
// ble.cpp only parses heartbeats into a snapshot. main.cpp wires it all.
//
// Boot: fast settle (no colour loop) -> black -> pet_setup() (sprite FIRST, then
// LittleFS + character pack) -> push -> bleInit() (AFTER the sprite, so Bluedroid can't
// fragment PSRAM before the 307KB framebuffer is allocated).
#define LGFX_USE_V1
#include <LovyanGFX.hpp>
#include <Arduino.h>
#include "axs15231_qspi.h"   // namespace axs (include LovyanGFX first)
#include "pet.h"             // extern spr; pet_setup/pet_tick/pet_on_touch/pet_set_*
#include "ble.h"             // bleInit/bleConnected/blePasskey/blePoll + BleSnapshot
#include "audio.h"           // audioInit/audioBlip/audioRibbit — I2S TU, never calls axs::
#include "codex_bridge.h"    // Wi-Fi/OTA + HTTP Codex status bridge
#include <Preferences.h>     // NVS — remember the backlight level across reboots

// --- Backlight brightness (drag-to-set, persisted, BLE-settable) ------------
static const uint8_t BL_MIN = 12;            // floor — very dim but never fully off (~5%)
static uint8_t     g_bright = 200;           // current backlight level (0..255)
static Preferences g_prefs;
static bool        g_bleEnabled = false;   // Wi-Fi Codex bridge build: BLE optional/off to save RAM

// Apply a level now; persist=true also remembers it in NVS.
static void brightness_apply(int v, bool persist) {
  if (v < BL_MIN) v = BL_MIN;
  if (v > 255)    v = 255;
  g_bright = (uint8_t)v;
  axs::set_backlight(g_bright);
  if (persist) { g_prefs.begin("pet", false); g_prefs.putUChar("bl", g_bright); g_prefs.end(); }
}

// Brightness acknowledgement card: on a tap-to-dim/brighten, draw a centered
// "+ NN%" / "- NN%" card + mini bar into the sprite and push JUST that region
// (the proven push_region). Held ~0.8s by s_ackUntil, then the animation repaints.
static uint16_t s_ackbuf[200 * 96];
static uint32_t s_ackUntil = 0;
static void show_ack(uint8_t level, bool up) {
  const int sw = spr.width();
  const int cw = 200, ch = 96, cx = (sw - cw) / 2, cy = 150;
  spr.fillRect(cx, cy, cw, ch, 0x18E3);                  // card bg
  spr.drawRect(cx, cy, cw, ch, 0x8410);                  // border
  int pct = (int)level * 100 / 255;
  char t[12]; snprintf(t, sizeof(t), "%c %d%%", up ? '+' : '-', pct);
  spr.setTextDatum(textdatum_t::middle_center);
  spr.setTextColor(up ? 0x07E0 : 0xFD20); spr.setTextSize(4);
  spr.drawString(t, sw / 2, cy + 32);
  int bw = cw - 40, bx = cx + 20, by = cy + ch - 22;     // mini bar under the text
  spr.fillRect(bx, by, bw, 12, 0x2104);
  spr.fillRect(bx, by, level * bw / 255, 12, 0xFD20);
  const uint16_t* sb = (const uint16_t*)spr.getBuffer();
  for (int r = 0; r < ch; r++)
    memcpy(&s_ackbuf[r * cw], &sb[(size_t)(cy + r) * sw + cx], (size_t)cw * 2);
  axs::push_region(cx, cy, cw, ch, s_ackbuf);
  s_ackUntil = millis() + 2000;                          // linger ~2s — easy to read
  Serial.printf("[pet] brightness %s %d%%\n", up ? "UP" : "DOWN", pct);
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n=== jc3248-pet === boot (GIF pet + BLE)");
  axs::init(/*warmup=*/false);   // fast ~1.5s settle — no 10s colour loop
  axs::fill_solid(0x0000);       // black slate
  pet_setup();                   // creates spr FIRST, mounts FS, loads bufo, draws frame 0
  axs::push((const uint16_t*)spr.getBuffer());
  Serial.println("[pet] first frame pushed");

  // Recovery-safe backlight restore: never boot with an invisible saved brightness.
  g_prefs.begin("pet", false);
  uint8_t saved_bl = g_prefs.getUChar("bl", 200);
  if (saved_bl < 120) { saved_bl = 200; g_prefs.putUChar("bl", saved_bl); }
  brightness_apply(saved_bl, /*persist=*/false);
  g_prefs.end();
  Serial.printf("[pet] backlight restored: %u\n", g_bright);

  // BLE bridge AFTER the sprite is allocated. Advertise NUS as "Atom-XXXX"
  // (last 2 bytes of the chip MAC) so the desktop picker can find us.
  char name[16];
  uint64_t mac = ESP.getEfuseMac();
  snprintf(name, sizeof(name), "Atom-%04X", (unsigned)(mac & 0xFFFF));
  codexBridgeInit();
  // Wi-Fi Codex bridge + OTA uses enough RAM; keep BLE/audio off in this build.
  // BLE can be re-enabled later if we move to NimBLE or shrink buffers.
  g_bleEnabled = false;
}

void loop() {
  codexBridgeLoop();
  // BLE: pull any new heartbeat (parsed on THIS thread by blePoll) + link/passkey
  // state into the pet's HUD. ble.cpp never touches the sprite or axs::.
  BleSnapshot snap;
  if (blePoll(&snap)) {
    pet_set_activity(snap.total, snap.running, snap.waiting, snap.msg, snap.tokens);
    pet_set_usage(snap.pct5h, snap.reset5h, snap.pct7d, snap.reset7d);
    if (snap.brightness >= 0) {                // the app set the backlight over BLE
      brightness_apply(snap.brightness, /*persist=*/true);
      Serial.printf("[pet] backlight <- BLE: %d\n", snap.brightness);
    }
  }
  pet_set_link(bleConnected() || codexBridgeActive(), blePasskey());

  // --- Touch (only this TU calls axs::): tap ZONES — robust on a single-touch
  //     panel. Tap the TOP third = brighter, BOTTOM third = dimmer (each shows an
  //     ack card), the MIDDLE (the pet) = heart. One tap = one step; no drag. ---
  static bool    t_down = false;
  static int16_t t_y = 0;
  static int     t_miss = 0;
  const int BL_STEP = 20;                        // ~8% per tap — gradual, not jumpy

  int16_t tx, ty;
#if defined(ATOM_CODEX_BRIDGE)
  // Gesture tracker for the Codex bridge build:
  // finger down -> track movement -> resolve swipe or tap on release.
  static bool    g_touchDown = false;
  static bool    g_gestureDone = false;
  static int16_t g_startX = 0, g_startY = 0, g_lastX = 0, g_lastY = 0;
  static uint32_t g_startMs = 0;
  static int     g_miss = 0;
  static uint32_t g_touchCooldownUntil = 0;
  const int SWIPE_DX = 45;
  const int SWIPE_SLOP = 35;
  const uint32_t SWIPE_MAX_MS = 700;

  if (millis() >= g_touchCooldownUntil && axs::read_touch(&tx, &ty)) {
    g_miss = 0;
    if (!g_touchDown) {
      g_touchDown = true;
      g_gestureDone = false;
      g_startX = g_lastX = tx;
      g_startY = g_lastY = ty;
      g_startMs = millis();
      Serial.printf("[touch] down %d,%d\n", tx, ty);
    } else {
      g_lastX = tx;
      g_lastY = ty;
    }
    int dx = g_lastX - g_startX;
    int dy = g_lastY - g_startY;
    uint32_t dt = millis() - g_startMs;
    if (!g_gestureDone && dt <= SWIPE_MAX_MS && abs(dx) >= SWIPE_DX && abs(dx) > abs(dy) && abs(dy) <= SWIPE_SLOP) {
      if (dx < 0) { audioBlip(true);  pet_next_page(); Serial.println("[touch] swipe left -> next page"); }
      else        { audioBlip(false); pet_prev_page(); Serial.println("[touch] swipe right -> prev page"); }
      g_gestureDone = true;
      g_touchCooldownUntil = millis() + 500;
    }
  } else if (g_touchDown && ++g_miss > 3) {
    g_touchDown = false;
    g_touchCooldownUntil = millis() + 350;
    if (!g_gestureDone) {
      // Tap fallback: edge taps change page; middle/top/bottom keep original actions.
      if (g_startX < 70)       { audioBlip(false); pet_prev_page(); Serial.println("[touch] left edge -> prev page"); }
      else if (g_startX > 250) { audioBlip(true);  pet_next_page(); Serial.println("[touch] right edge -> next page"); }
      else if (g_startY < 150) { audioBlip(true);  brightness_apply(g_bright + BL_STEP, /*persist=*/true); show_ack(g_bright, true); }
      else if (g_startY > 330) { audioBlip(false); brightness_apply(g_bright - BL_STEP, /*persist=*/true); show_ack(g_bright, false); }
      else                     { audioRibbit();    pet_on_touch(); }
    }
  }
#else
  if (axs::read_touch(&tx, &ty)) {
    t_miss = 0;
    if (!t_down) { t_down = true; t_y = ty; }    // remember where the tap landed
  } else if (t_down && ++t_miss > 3) {           // finger up → resolve the tap
    t_down = false;
    if (t_y < 150)      { audioBlip(true);  brightness_apply(g_bright + BL_STEP, /*persist=*/true); show_ack(g_bright, true); }
    else if (t_y > 330) { audioBlip(false); brightness_apply(g_bright - BL_STEP, /*persist=*/true); show_ack(g_bright, false); }
    else                { audioRibbit();    pet_on_touch(); }   // middle (the pet) = heart
  }
#endif

  if (millis() < s_ackUntil) { /* showing the ack card — hold it */ }
  else if (pet_tick()) axs::push((const uint16_t*)spr.getBuffer());
}
