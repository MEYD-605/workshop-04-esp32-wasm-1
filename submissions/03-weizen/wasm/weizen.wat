;; Weizen Oracle — tiny ZERO-IMPORT wasm module for ESP32 (wasm3 / WAMR)
;; Pure functions → identical result on browser / zig / wasm3 / WAMR. Easy to verify.
(module
  ;; add(a, b) -> a + b   (the workshop's canonical check: add(2,3)=5)
  (func $add (export "add") (param i32 i32) (result i32)
    (i32.add (local.get 0) (local.get 1)))

  ;; brew(glasses) -> glasses * 2  ("pour glass to glass" — one becomes the next 🍺)
  (func $brew (export "brew") (param i32) (result i32)
    (i32.mul (local.get 0) (i32.const 2)))
)
