#pragma once
// jc3248-pet — GIF-render module (pet.h)
//
// The pet owns a single LGFX_Sprite framebuffer (`spr`), decodes an animated
// "bufo" GIF pack from LittleFS, upscales it 3x (nearest-neighbor), and centers
// it on the 320x480 panel above an ~80px reserved bottom HUD strip. This module
// ONLY draws into `spr`; main.cpp owns the native axs panel driver and pushes
// the sprite to the screen. pet.cpp NEVER touches the axs:: driver.
//
// Pipeline ported faithfully from the proven buddy renderer
// (lab/claude-desktop-buddy/src/character.cpp), stripped to v1 idle-only.
#include <LovyanGFX.hpp>
#include <stdint.h>

// The single framebuffer. Defined in pet.cpp, pushed by main.cpp.
extern LGFX_Sprite spr;

// Create spr FIRST, mount LittleFS, load the first /characters/* pack, and
// decode frame 0 into spr. Call once after Serial is up. Does NOT push.
void pet_setup();

// Advance the idle animation: when the current frame's delay has elapsed,
// decode the next frame into spr (rotating idle GIFs at end-of-loop). Returns
// true iff spr changed this call (so main.cpp can push only on change).
bool pet_tick();

// Touch reaction: call when the panel is tapped (main.cpp reads axs::read_touch
// — the TU that owns the driver). Plays the reaction GIF (heart, else celebrate)
// for ~4s, then returns to idle. Re-tapping extends the reaction. No-op if the
// pack has no reaction state.
void pet_on_touch();

// BLE bridge status → HUD. main.cpp owns the ble module and feeds these in:
// link state + pairing passkey (0 = not pairing), and the latest heartbeat.
void pet_set_link(bool connected, uint32_t passkey);
void pet_set_activity(int total, int running, int waiting, const char* msg, long tokens);
// Usage windows → shown on the HUD: percent (0..100, -1=none) + seconds-until-reset (-1=none).
void pet_set_usage(int pct5h, long reset5h, int pct7d, long reset7d);
void pet_set_extra_usage(int pctGrok, int pctClaude, int pctClaudeWeek,
                         long resetGrok=-1, long resetClaude=-1, long resetClaudeWeek=-1);

// Page control: 0 = animated pet/work state, 1 = CodexBar quota HUD.
void pet_set_page(uint8_t page);
void pet_next_page();
void pet_prev_page();

// Debug/bridge test hook: force a named GIF state for a short window.
// Supported: idle, busy, attention, sleep, heart, celebrate, dizzy.
bool pet_force_state(const char* state, uint32_t ms);

// Force the next pet_tick() to repaint a fresh full frame now (clears any overlay).
void pet_force_redraw();
