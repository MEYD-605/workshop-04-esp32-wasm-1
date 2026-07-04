// jc3248-pet — GIF-render module (pet.cpp)
//
// Ported VERBATIM-IN-SPIRIT from the proven buddy renderer
// (lab/claude-desktop-buddy/src/character.cpp), reduced to a v1 idle-only pet:
// load one /characters/* pack, decode + 3x-upscale + center a bufo GIF, and
// rotate through the idle_0..idle_8 GIFs forever.
//
// CRITICAL: this translation unit MUST NOT touch the native axs:: driver.
// It draws ONLY into `spr`. main.cpp owns axs::init/push/fill_solid and pushes
// the sprite. (Mirrors the buddy: character.cpp also never calls its push HAL.)
#define LGFX_USE_V1
#include <LovyanGFX.hpp>
#include <Arduino.h>
#include <LittleFS.h>
#include <AnimatedGIF.h>
#include <ArduinoJson.h>

#include "pet.h"

// Sprite size — literal panel dims; do NOT reference axs::W / axs::H here
// (that would pull in the native driver header / its static state).
#define PET_W 320
#define PET_H 480
// Reserve ~80px at the bottom for a future HUD; the pet centers above it.
#define PET_HUD_H 80
#define GIF_SCALE 3

// The single framebuffer (declared extern in pet.h, pushed by main.cpp).
LGFX_Sprite spr;

// --- Character palette ----------------------------------------------------
struct Palette {
  uint16_t body, bg, text, textDim, ink;
};
// Sensible defaults (olive body / black bg) until the manifest overrides them.
static Palette pal = { 0x6B0D, 0x0000, 0xFFFF, 0x8410, 0x0000 };

// --- Loaded pack state ----------------------------------------------------
static bool    loaded = false;
static char    basePath[48];                 // "/characters/<name>"
static const uint8_t MAX_IDLE = 16;
static char    idlePaths[MAX_IDLE][32];       // idle GIF filenames (no dir)
static uint8_t idleCount = 0;
static uint8_t idleRot   = 0;                 // which idle GIF is open
static char    petName[24] = { 0 };           // pack name, shown in the HUD

// --- BLE status (set by main.cpp from the ble bridge; rendered in the HUD) ---
static bool     s_bleConn  = false;
static uint32_t s_passkey  = 0;
static int      s_running  = 0, s_waiting = 0;
static long     s_tokens   = 0;
static char     s_msg[64]  = { 0 };
static uint32_t s_lastSnap = 0;
static long     s_reset5h  = -1;              // seconds until the 5h usage window resets (-1 = no data)
static long     s_reset7d  = -1;              // seconds until the 7d (weekly) usage window resets
static int      s_pct5h    = -1;              // 5h window usage percent (-1 = no data)
static int      s_pct7d    = -1;              // 7d window usage percent
static int      s_pctGrok  = -1;
static int      s_pctClaude = -1;
static int      s_pctCWk   = -1;
static long     s_resetGrok = -1;
static long     s_resetClaude = -1;
static long     s_resetCWk = -1;
static uint8_t  s_page     = 0;               // 0=pet, 1=CodexBar quota HUD
static const uint8_t PAGE_PET = 0;
static const uint8_t PAGE_CODEXBAR = 1;
static const uint8_t PAGE_COUNT = 2;

// Format seconds-until-reset compactly for the HUD: "4d23h" / "3h55m" / "12m" / "--".
static void fmt_reset(char* out, size_t n, long sec) {
  if (sec < 0)           snprintf(out, n, "--");
  else if (sec >= 86400) snprintf(out, n, "%ldd%ldh", sec / 86400, (sec % 86400) / 3600);
  else if (sec >= 3600)  snprintf(out, n, "%ldh%02ldm", sec / 3600, (sec % 3600) / 60);
  else                   snprintf(out, n, "%ldm", sec / 60);
}

// One usage window for the HUD: "5h 8% 3h55m" (percent + reset), or whichever parts exist.
static void fmt_window(char* out, size_t n, const char* label, int pct, long reset) {
  char r[12]; fmt_reset(r, sizeof(r), reset);
  if (pct >= 0 && reset >= 0)  snprintf(out, n, "%s %d%% %s", label, pct, r);
  else if (pct >= 0)           snprintf(out, n, "%s %d%%", label, pct);
  else                         snprintf(out, n, "%s %s", label, r);
}


static void drawQuotaLine(const char* label, int pct, long reset, int y, uint16_t color) {
  spr.setTextDatum(textdatum_t::top_left);
  spr.setTextColor(color);
  spr.setTextSize(2);
  spr.drawString(label, 22, y);

  char val[16];
  if (pct >= 0) snprintf(val, sizeof(val), "%d%%", pct);
  else snprintf(val, sizeof(val), "--");
  spr.setTextColor(pal.text);
  spr.drawString(val, 154, y);

  if (reset >= 0) {
    char r[12]; fmt_reset(r, sizeof(r), reset);
    spr.setTextColor(pal.textDim);
    spr.drawString(r, 210, y);
  }

  int barX = 22, barY = y + 25, barW = 266, barH = 12;
  spr.drawRect(barX, barY, barW, barH, pal.textDim);
  if (pct >= 0) {
    // pct is remaining quota now. Fill left-to-right by remaining, not by used.
    int remain = pct;
    if (remain < 0) remain = 0;
    if (remain > 100) remain = 100;
    uint16_t barColor = remain < 20 ? 0xF800 : (remain < 45 ? 0xFD20 : 0x07E0);
    spr.fillRect(barX + 2, barY + 2, (barW - 4) * remain / 100, barH - 4, barColor);
  }
}

static void drawCodexbarHUD() {
  spr.fillSprite(pal.bg);
  spr.setTextDatum(textdatum_t::top_left);
  spr.setTextColor(pal.textDim);
  spr.setTextSize(2);
  spr.drawString("page 2/2  < pet", 18, 12);
  spr.setTextColor(pal.text);
  spr.setTextSize(3);
  spr.drawString("CodexBar", 18, 38);
  spr.setTextColor(pal.textDim);
  spr.setTextSize(1);
  spr.drawString("workboard + quota poll", 20, 76);

  drawQuotaLine("Codex H5", s_pct5h, s_reset5h, 104, pal.text);
  drawQuotaLine("Codex Wk", s_pct7d, s_reset7d, 158, pal.text);
  drawQuotaLine("Grok", s_pctGrok, s_resetGrok, 212, pal.textDim);
  drawQuotaLine("Claude", s_pctClaude, s_resetClaude, 266, pal.textDim);
  drawQuotaLine("C-WK", s_pctCWk, s_resetCWk, 320, pal.textDim);

  spr.setTextColor(pal.textDim);
  spr.setTextSize(2);
  char st[64];
  snprintf(st, sizeof(st), "run %d  wait %d", s_running, s_waiting);
  spr.drawString(st, 20, 386);
  if (s_msg[0]) {
    char msg[34]; snprintf(msg, sizeof(msg), "%.32s", s_msg);
    spr.drawString(msg, 20, 416);
  }
  spr.drawFastHLine(0, PET_H - 34, PET_W, pal.textDim);
  spr.setTextSize(1);
  spr.drawString("swipe L/R or tap edge", 20, PET_H - 24);
}

// --- AnimatedGIF state ----------------------------------------------------
static AnimatedGIF gif;
static File        gifFile;
static int         gifX = 0, gifY = 0, gifW = 0, gifH = 0;
static bool        gifOpen = false;
static uint32_t    nextFrameAt = 0;
static uint32_t    animPauseUntil = 0;        // dwell between idle GIFs
static const uint32_t ANIM_PAUSE_MS = 3000;   // ~3s dwell before rotating

// --- Touch reaction state -------------------------------------------------
static char     reactPath[32] = { 0 };        // reaction GIF filename (heart/celebrate); empty = none
static char     heartPath[32] = { 0 };
static char     celebratePath[32] = { 0 };
static char     dizzyPath[32] = { 0 };
static bool     reacting   = false;
static uint32_t reactUntil = 0;
static const uint32_t REACT_MS = 4000;        // how long a tap reaction plays/loops

// --- Forced bridge-test state ---------------------------------------------
static char     forcePath[32] = { 0 };
static char     forceLabel[16] = { 0 };
static bool     forcing = false;
static uint32_t forceUntil = 0;

// --- Activity-driven states (from the BLE heartbeat) ----------------------
enum PetState { ST_IDLE, ST_BUSY, ST_ATTENTION, ST_SLEEP };
static PetState curState = ST_IDLE;           // what's animating now
static char     busyPath[32]  = { 0 };        // states.busy      (single gif, loops)
static char     attnPath[32]  = { 0 };        // states.attention (a permission prompt)
static char     sleepPath[32] = { 0 };        // states.sleep     (total == 0)
static int      s_total = 0;                  // session count (drives the sleep state)

// #RRGGBB (or RRGGBB) → RGB565. Ported from character.cpp::parseHexColor.
static uint16_t parseHexColor(const char* s, uint16_t fallback) {
  if (!s) return fallback;
  if (*s == '#') s++;
  uint32_t v = strtoul(s, nullptr, 16);
  return (uint16_t)(((v >> 19) & 0x1F) << 11 | ((v >> 10) & 0x3F) << 5 | ((v >> 3) & 0x1F));
}

// --- AnimatedGIF file callbacks (LittleFS) --------------------------------
static void* gifOpenCb(const char* fname, int32_t* pSize) {
  gifFile = LittleFS.open(fname, "r");
  if (!gifFile) return nullptr;
  *pSize = gifFile.size();
  return (void*)&gifFile;
}
static void gifCloseCb(void* handle) {
  File* f = (File*)handle;
  if (f) f->close();
}
static int32_t gifReadCb(GIFFILE* pFile, uint8_t* pBuf, int32_t iLen) {
  File* f = (File*)pFile->fHandle;
  int32_t n = f->read(pBuf, iLen);
  pFile->iPos = f->position();
  return n;
}
static int32_t gifSeekCb(GIFFILE* pFile, int32_t iPosition) {
  File* f = (File*)pFile->fHandle;
  f->seek(iPosition);
  pFile->iPos = (int32_t)f->position();
  return pFile->iPos;
}

// Center the upscaled GIF in the area above the bottom HUD. Ported from
// character.cpp::gifPlace (home mode). Clamp origin >= 0 so a tall GIF still
// anchors at the top-left rather than off-screen.
static void gifPlace() {
  int outW = gifW * GIF_SCALE;
  int outH = gifH * GIF_SCALE;
  gifX = (PET_W - outW) / 2;
  int usableH = PET_H - PET_HUD_H;
  gifY = (usableH - outH) / 2;
  if (gifX < 0) gifX = 0;
  if (gifY < 0) gifY = 0;
}

// Draw callback: one decoded scanline → GIF_SCALE x GIF_SCALE fillRect blocks
// (nearest-neighbor upscale). Transparent palette index → pal.bg so each frame
// fully repaints its region (GIFs are unoptimized full-frame). Ported from
// character.cpp::gifDrawCb (home-mode branch only).
//
// NORMAL rgb565 is passed to fillRect — LovyanGFX byte-swaps internally.
static void gifDrawCb(GIFDRAW* d) {
  uint16_t* pal16 = d->pPalette;
  uint8_t*  src   = d->pPixels;
  uint8_t   t     = d->ucTransparent;
  bool      hasT  = d->ucHasTransparency;
  int       srcY  = d->iY + d->y;

  int w = d->iWidth;
  if (w > 256) w = 256;
  int oy = gifY + srcY * GIF_SCALE;
  if (oy + GIF_SCALE <= 0 || oy >= PET_H) return;

  for (int i = 0; i < w; i++) {
    uint8_t  idx   = src[i];
    uint16_t color = (hasT && idx == t) ? pal.bg : pal16[idx];
    int ox  = gifX + (d->iX + i) * GIF_SCALE;
    int cx0 = ox < 0 ? 0 : ox;
    int cy0 = oy < 0 ? 0 : oy;
    int cx1 = ox + GIF_SCALE; if (cx1 > PET_W) cx1 = PET_W;
    int cy1 = oy + GIF_SCALE; if (cy1 > PET_H) cy1 = PET_H;
    if (cx0 < cx1 && cy0 < cy1) spr.fillRect(cx0, cy0, cx1 - cx0, cy1 - cy0, color);
  }
}

// Open a GIF by filename (relative to basePath). Sets gifW/gifH, places it, and
// arms timing (nextFrameAt=0 so the caller's next playFrame draws frame 0).
// Mirrors character.cpp::characterSetState's gif.open block.
static bool openGif(const char* fname) {
  if (gifOpen) { gif.close(); gifOpen = false; }

  char full[80];
  snprintf(full, sizeof(full), "%s/%s", basePath, fname);
  if (!gif.open(full, gifOpenCb, gifCloseCb, gifReadCb, gifSeekCb, gifDrawCb)) {
    Serial.printf("[pet] open failed: %s (err %d)\n", full, gif.getLastError());
    return false;
  }
  gifOpen = true;
  gifW = gif.getCanvasWidth();
  gifH = gif.getCanvasHeight();
  gifPlace();
  nextFrameAt = 0;
  Serial.printf("[pet] %s: %dx%d @ (%d,%d) heap=%u\n",
                fname, gifW, gifH, gifX, gifY, (unsigned)ESP.getFreeHeap());
  return true;
}
static bool openIdle(uint8_t rot) {
  if (idleCount == 0) return false;
  return openGif(idlePaths[rot]);
}

// Bottom HUD strip — painted into spr below the pet, AFTER each composed frame
// (so it survives the per-frame fillSprite). The pet art never overlaps it:
// gifPlace centers the GIF in (PET_H - PET_HUD_H), leaving this band clear.
static void drawHUD() {
  if (s_page == PAGE_CODEXBAR) { drawCodexbarHUD(); return; }
  const int y0 = PET_H - PET_HUD_H;                 // 400
  spr.fillRect(0, y0, PET_W, PET_HUD_H, pal.bg);
  spr.drawFastHLine(0, y0, PET_W, pal.textDim);     // divider
  spr.setTextDatum(textdatum_t::top_left);

  // Connection dot (top-right of the strip): orange=pairing, green=linked, dim=advertising.
  uint16_t dot = s_passkey ? 0xFD20 : (s_bleConn ? 0x07E0 : pal.textDim);
  spr.fillCircle(PET_W - 14, y0 + 18, 6, dot);

  // Pairing: show the 6-digit passkey big so it can be entered on the desktop.
  if (s_passkey) {
    spr.setTextColor(pal.textDim); spr.setTextSize(2);
    spr.drawString("PAIR - enter code:", 12, y0 + 6);
    char pk[8]; snprintf(pk, sizeof(pk), "%06lu", (unsigned long)s_passkey);
    spr.setTextColor(pal.text); spr.setTextSize(4);
    spr.drawString(pk, 12, y0 + 34);
    return;
  }

  // Usage shown when the heartbeat carried any usage data (percent and/or reset).
  bool haveUsage = (s_pct5h >= 0 || s_pct7d >= 0 || s_reset5h >= 0 || s_reset7d >= 0);

  // Line 1: pet name.
  spr.setTextColor(pal.text); spr.setTextSize(3);
  spr.drawString(petName[0] ? petName : "pet", 12, y0 + 6);

  if (haveUsage) {
    // Lines 2-3: the two usage windows — "5h 8% 3h55m" / "wk 41% 4d23h".
    char l5[40], l7[40];
    fmt_window(l5, sizeof(l5), "5h", s_pct5h, s_reset5h);
    fmt_window(l7, sizeof(l7), "wk", s_pct7d, s_reset7d);
    spr.setTextColor(pal.text);    spr.setTextSize(2); spr.drawString(l5, 12, y0 + 34);
    spr.setTextColor(pal.textDim); spr.setTextSize(2); spr.drawString(l7, 12, y0 + 56);
  } else {
    // Line 2: live status when linked, else local state + uptime.
    uint32_t now = millis();
    char buf[48];
    if (s_bleConn) {
      if (now - s_lastSnap > 75000)  snprintf(buf, sizeof(buf), "BLE link stale");
      else if (s_msg[0])             snprintf(buf, sizeof(buf), "%.40s", s_msg);
      else                           snprintf(buf, sizeof(buf), "run %d  wait %d  %ldt",
                                              s_running, s_waiting, s_tokens);
    } else {
      uint32_t up = now / 1000;
      snprintf(buf, sizeof(buf), "%s  BLE adv  %lu:%02lu",
               reacting ? "heart" : "idle",
               (unsigned long)(up / 60), (unsigned long)(up % 60));
    }
    spr.setTextColor(pal.textDim); spr.setTextSize(2);
    spr.drawString(buf, 12, y0 + 48);
  }
}

// BLE status setters — called by main.cpp from blePoll()/bleConnected()/blePasskey().
void pet_set_link(bool connected, uint32_t passkey) {
  s_bleConn = connected;
  s_passkey = passkey;
}
void pet_set_activity(int total, int running, int waiting, const char* msg, long tokens) {
  s_total = total; s_running = running; s_waiting = waiting; s_tokens = tokens;
  if (msg) { strncpy(s_msg, msg, sizeof(s_msg) - 1); s_msg[sizeof(s_msg) - 1] = 0; }
  else s_msg[0] = 0;
  s_lastSnap = millis();
}
// Usage windows from the heartbeat: seconds until the 5h and 7d windows reset
// (-1 = not provided). Shown as a 3rd HUD line when present.
void pet_set_usage(int pct5h, long reset5h, int pct7d, long reset7d) {
  s_pct5h = pct5h; s_reset5h = reset5h;
  s_pct7d = pct7d; s_reset7d = reset7d;
}
void pet_set_extra_usage(int pctGrok, int pctClaude, int pctClaudeWeek,
                         long resetGrok, long resetClaude, long resetClaudeWeek) {
  s_pctGrok = pctGrok;
  s_pctClaude = pctClaude;
  s_pctCWk = pctClaudeWeek;
  s_resetGrok = resetGrok;
  s_resetClaude = resetClaude;
  s_resetCWk = resetClaudeWeek;
}

void pet_set_page(uint8_t page) {
  if (page >= PAGE_COUNT) page = PAGE_PET;
  if (s_page == page) { pet_force_redraw(); return; }
  s_page = page;
  pet_force_redraw();
  Serial.printf("[pet] page -> %u\n", (unsigned)s_page);
}
void pet_next_page() { pet_set_page((uint8_t)((s_page + 1) % PAGE_COUNT)); }
void pet_prev_page() { pet_set_page((uint8_t)((s_page + PAGE_COUNT - 1) % PAGE_COUNT)); }

void pet_setup() {
  // ALLOCATE THE SPRITE FIRST — before any AnimatedGIF/JSON allocation — so the
  // 320x480x2 (~300KB) PSRAM framebuffer gets the largest contiguous block.
  spr.setColorDepth(16);
  spr.setPsram(true);
  spr.createSprite(PET_W, PET_H);
  if (!spr.getBuffer()) {
    Serial.println("[pet] FATAL: sprite alloc failed (createSprite returned null buffer)");
    return;
  }
  spr.fillSprite(pal.bg);

  // Mount LittleFS; format-on-fail so a corrupt/blank partition becomes a clean
  // mountable FS. begin() also fails when already mounted — fall through to the
  // open("/") check in that case.
  if (!LittleFS.begin(/*formatOnFail=*/true)) {
    if (!LittleFS.open("/")) {
      Serial.println("[pet] FATAL: LittleFS mount failed (even after format)");
      return;
    }
  }

  // Scan /characters/ for the first directory — the installed pack.
  static char name[24] = { 0 };
  {
    File dir = LittleFS.open("/characters");
    if (dir && dir.isDirectory()) {
      File e = dir.openNextFile();
      while (e) {
        if (e.isDirectory()) {
          // e.name() may be full path or basename depending on core; take the
          // last path component either way.
          const char* n = strrchr(e.name(), '/');
          strncpy(name, n ? n + 1 : e.name(), sizeof(name) - 1);
          name[sizeof(name) - 1] = 0;
          break;
        }
        e = dir.openNextFile();
      }
      dir.close();
    }
  }
  if (name[0] == 0) {
    Serial.println("[pet] FATAL: no characters installed under /characters");
    return;
  }

  snprintf(basePath, sizeof(basePath), "/characters/%s", name);
  strncpy(petName, name, sizeof(petName) - 1);   // shown in the HUD
  char mpath[64];
  snprintf(mpath, sizeof(mpath), "%s/manifest.json", basePath);

  File mf = LittleFS.open(mpath, "r");
  if (!mf) {
    Serial.printf("[pet] FATAL: manifest not found: %s\n", mpath);
    return;
  }

  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, mf);
  mf.close();
  if (err) {
    Serial.printf("[pet] FATAL: manifest parse: %s\n", err.c_str());
    return;
  }

  // Palette from colors{} — parse #RRGGBB into RGB565 (ported parseHexColor).
  JsonObject colors = doc["colors"];
  pal.body    = parseHexColor(colors["body"],    pal.body);
  pal.bg      = parseHexColor(colors["bg"],      pal.bg);
  pal.text    = parseHexColor(colors["text"],    pal.text);
  pal.textDim = parseHexColor(colors["textDim"], pal.textDim);
  pal.ink     = parseHexColor(colors["ink"],     pal.ink);

  // states.idle may be a single filename string OR an array (bufo: idle_0..8).
  idleCount = 0;
  JsonVariant idle = doc["states"]["idle"];
  if (idle.is<JsonArray>()) {
    for (JsonVariant e : idle.as<JsonArray>()) {
      if (idleCount >= MAX_IDLE) break;
      const char* fn = e.as<const char*>();
      if (fn) { snprintf(idlePaths[idleCount], 32, "%s", fn); idleCount++; }
    }
  } else {
    const char* fn = idle.as<const char*>();
    if (fn) { snprintf(idlePaths[idleCount], 32, "%s", fn); idleCount++; }
  }
  if (idleCount == 0) {
    Serial.println("[pet] FATAL: manifest has no idle state");
    return;
  }

  // Optional reaction/debug GIFs.
  reactPath[0] = heartPath[0] = celebratePath[0] = dizzyPath[0] = 0;
  { const char* f = doc["states"]["heart"].as<const char*>();     if (f) snprintf(heartPath,     sizeof(heartPath),     "%s", f); }
  { const char* f = doc["states"]["celebrate"].as<const char*>(); if (f) snprintf(celebratePath, sizeof(celebratePath), "%s", f); }
  { const char* f = doc["states"]["dizzy"].as<const char*>();     if (f) snprintf(dizzyPath,     sizeof(dizzyPath),     "%s", f); }
  const char* rfn = heartPath[0] ? heartPath : (celebratePath[0] ? celebratePath : nullptr);
  if (rfn) {
    snprintf(reactPath, sizeof(reactPath), "%s", rfn);
    Serial.printf("[pet] reaction GIF: %s\n", reactPath);
  }

  // Activity-state GIFs (single-gif, looped): busy / attention / sleep.
  busyPath[0] = attnPath[0] = sleepPath[0] = 0;
  { const char* f = doc["states"]["busy"].as<const char*>();      if (f) snprintf(busyPath,  sizeof(busyPath),  "%s", f); }
  { const char* f = doc["states"]["attention"].as<const char*>(); if (f) snprintf(attnPath,  sizeof(attnPath),  "%s", f); }
  { const char* f = doc["states"]["sleep"].as<const char*>();     if (f) snprintf(sleepPath, sizeof(sleepPath), "%s", f); }
  Serial.printf("[pet] states: busy=%s attn=%s sleep=%s\n",
                busyPath[0]?busyPath:"-", attnPath[0]?attnPath:"-", sleepPath[0]?sleepPath:"-");

  gif.begin(LITTLE_ENDIAN_PIXELS);
  loaded = true;
  Serial.printf("[pet] loaded '%s' from %s\n", name, basePath);

  // Decode frame 0 of the first idle GIF into spr (do NOT push — main.cpp does).
  idleRot = 0;
  spr.fillSprite(pal.bg);
  if (openIdle(idleRot)) {
    int delayMs = 0;
    gif.playFrame(false, &delayMs);
    nextFrameAt = millis() + (delayMs > 0 ? delayMs : 100);
  }
  drawHUD();   // compose the bottom strip onto the first frame
}

// Tap handler — called by main.cpp when axs::read_touch() fires. Switches to the
// reaction GIF (looping) for REACT_MS; a re-tap while reacting extends the timer.
void pet_on_touch() {
  if (!loaded || reactPath[0] == 0) return;
  reactUntil = millis() + REACT_MS;
  if (reacting) return;            // already reacting — just extended the timer
  reacting = true;
  animPauseUntil = 0;
  spr.fillSprite(pal.bg);
  openGif(reactPath);              // nextFrameAt=0 → next pet_tick draws frame 0 and pushes
  Serial.printf("[pet] touch → reaction '%s'\n", reactPath);
}

bool pet_force_state(const char* state, uint32_t ms) {
  if (!loaded || !state) return false;
  const char* fn = nullptr;
  if (!strcmp(state, "idle"))           fn = idleCount ? idlePaths[0] : nullptr;
  else if (!strcmp(state, "busy"))      fn = busyPath[0] ? busyPath : nullptr;
  else if (!strcmp(state, "attention")) fn = attnPath[0] ? attnPath : nullptr;
  else if (!strcmp(state, "sleep"))     fn = sleepPath[0] ? sleepPath : nullptr;
  else if (!strcmp(state, "heart"))     fn = heartPath[0] ? heartPath : nullptr;
  else if (!strcmp(state, "celebrate")) fn = celebratePath[0] ? celebratePath : nullptr;
  else if (!strcmp(state, "dizzy"))     fn = dizzyPath[0] ? dizzyPath : nullptr;
  if (!fn) return false;

  snprintf(forcePath, sizeof(forcePath), "%s", fn);
  snprintf(forceLabel, sizeof(forceLabel), "%s", state);
  forceUntil = millis() + (ms ? ms : 3000);
  forcing = true;
  reacting = false;
  animPauseUntil = 0;
  spr.fillSprite(pal.bg);
  openGif(forcePath);
  Serial.printf("[pet] force state -> %s (%s)\n", forceLabel, forcePath);
  return true;
}

// Desired animation state from the latest BLE heartbeat. No link / stale link → idle.
static PetState computeDesired() {
  if (!s_bleConn) return ST_IDLE;
  if (millis() - s_lastSnap > 75000) return ST_IDLE;   // link went quiet → idle
  if (s_waiting > 0) return ST_ATTENTION;              // a permission prompt is blocking
  if (s_running > 0) return ST_BUSY;                   // a session is generating
  if (s_total == 0)  return ST_SLEEP;                  // nothing open
  return ST_IDLE;
}

// Switch the animation to a state's GIF (idle resets the rotation; single-gif
// states loop). Falls back to idle if a state's GIF is missing from the manifest.
static void enterState(PetState s) {
  const char* fn = nullptr;
  if (s == ST_IDLE)            { idleRot = 0; fn = idleCount ? idlePaths[0] : nullptr; }
  else if (s == ST_BUSY)      fn = busyPath[0]  ? busyPath  : nullptr;
  else if (s == ST_ATTENTION) fn = attnPath[0]  ? attnPath  : nullptr;
  else                        fn = sleepPath[0] ? sleepPath : nullptr;
  if (!fn) { s = ST_IDLE; idleRot = 0; fn = idleCount ? idlePaths[0] : nullptr; }
  curState = s;
  animPauseUntil = 0;
  spr.fillSprite(pal.bg);
  if (fn) openGif(fn);
  Serial.printf("[pet] state -> %s\n",
                s == ST_IDLE ? "idle" : s == ST_BUSY ? "busy" :
                s == ST_ATTENTION ? "attention" : "sleep");
}

static bool tick_frame() {
  if (!loaded) return false;
  uint32_t now = millis();

  // 0) Explicit bridge-test state overrides normal activity for a short window.
  if (forcing) {
    if (now < forceUntil) {
      if (now < nextFrameAt) return false;
      spr.fillSprite(pal.bg);
      int d = 0;
      if (!gif.playFrame(false, &d)) { gif.reset(); gif.playFrame(false, &d); }
      nextFrameAt = now + (d > 0 ? d : 100);
      return true;
    }
    forcing = false;
    enterState(computeDesired());
    int d = 0; gif.playFrame(false, &d);
    nextFrameAt = now + (d > 0 ? d : 100);
    return true;
  }

  // 1) Touch reaction overrides every state for its window, then re-enters state.
  if (reacting) {
    if (now < reactUntil) {
      if (now < nextFrameAt) return false;
      spr.fillSprite(pal.bg);
      int d = 0;
      if (!gif.playFrame(false, &d)) { gif.reset(); gif.playFrame(false, &d); }  // loop reaction
      nextFrameAt = now + (d > 0 ? d : 100);
      return true;
    }
    reacting = false;
    enterState(computeDesired());      // back to whatever Claude's doing now
    int d = 0; gif.playFrame(false, &d);
    nextFrameAt = now + (d > 0 ? d : 100);
    return true;
  }

  // 2) Switch animation when the BLE-desired state changes.
  PetState want = computeDesired();
  if (want != curState) {
    enterState(want);
    int d = 0; gif.playFrame(false, &d);
    nextFrameAt = now + (d > 0 ? d : 100);
    return true;
  }

  // 3a) IDLE: rotate idle_0..N with a dwell between GIFs.
  if (curState == ST_IDLE) {
    if (!gifOpen) {
      if (animPauseUntil && now >= animPauseUntil) {
        animPauseUntil = 0;
        idleRot = (idleRot + 1) % idleCount;
        spr.fillSprite(pal.bg);
        if (openIdle(idleRot)) {
          int delayMs = 0;
          gif.playFrame(false, &delayMs);
          nextFrameAt = now + (delayMs > 0 ? delayMs : 100);
          return true;
        }
      }
      return false;
    }
    if (now < nextFrameAt) return false;
    spr.fillSprite(pal.bg);
    int delayMs = 0;
    if (!gif.playFrame(false, &delayMs)) {
      gif.close(); gifOpen = false;
      if (idleCount == 1) {
        animPauseUntil = 0; idleRot = 0;
        if (openIdle(idleRot)) { int d2 = 0; gif.playFrame(false, &d2); nextFrameAt = now + (d2 > 0 ? d2 : 100); }
      } else {
        animPauseUntil = now + ANIM_PAUSE_MS;
      }
      return true;
    }
    nextFrameAt = now + (delayMs > 0 ? delayMs : 100);
    return true;
  }

  // 3b) BUSY / ATTENTION / SLEEP: loop the single state GIF.
  if (!gifOpen) return false;
  if (now < nextFrameAt) return false;
  spr.fillSprite(pal.bg);
  int d = 0;
  if (!gif.playFrame(false, &d)) { gif.reset(); gif.playFrame(false, &d); }
  nextFrameAt = now + (d > 0 ? d : 100);
  return true;
}

// Public entry: advance one frame, then compose the HUD over it. main.cpp pushes
// only when this returns true (one drawHUD per pushed frame).
bool pet_tick() {
  bool changed = tick_frame();
  if (changed) drawHUD();
  return changed;
}

// Force the next pet_tick() to repaint a fresh full frame immediately (used after
// a brightness drag, to clear the bar overlay and snap the pet back at once).
void pet_force_redraw() {
  nextFrameAt = 0;                    // current gif: decode the next frame now
  if (animPauseUntil) animPauseUntil = 1;  // mid-dwell: end it so it reopens/rotates now
}
