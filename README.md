# Contra (NES) — the Stage 1 pit skip

An investigation into an undocumented, unreproduced glitch in *Contra* (NES, USA): the runner **DK28** fell into a pit roughly halfway through Stage 1 and, instead of dying and respawning, the game went straight to Stage 2 — skipping the second half of the stage and the boss.

This repo contains the write-up below and the Python tools used for the analysis (a 6502 disassembler, a control-flow code mapper, a headless logic-only NES emulator, and several analysis scripts). **No ROM, ROM dump or footage is included** — bring your own legally obtained ROM.

**TL;DR**

- The only way the game ever enters its stage-clear sequence is one check at `$CEEA`: `LDA $3B / BNE $CF25` ("is the stage-clear flag set?").
- No code path in the game can set that flag, or the game-mode byte, except the boss's death routines. Every indexed/indirect store that could alias those bytes was traced and ruled out, and lag-frame NMIs can't corrupt them.
- The most plausible cause is a **hardware read error / bit flip** at that single check, e.g. a dirty cartridge connection misreading `BNE` (`$D0`) as `BEQ` (`$F0`). Seven different one-bit errors at `$CEEA–$CEEC` produce the skip. DK28 was playing on original hardware.
- **Simulating that misread for one frame while the player falls into a pit reproduces the clip:** the pit death, the lives medal dropping 2→1, a fade 160 frames after the body leaves the screen, and Stage 2 with REST 2. All the timings match the footage to within a few frames. The respawned player isn't visible in the clip because it blinks on alternate frames and the footage was captured at 30 fps.
- This shows a single misread *can* produce exactly this footage. It isn't proof that one did.

---

## 1. The ROM

| | |
|---|---|
| Game | Contra (USA) |
| Mapper | 2 (UxROM), 8 × 16 KB PRG, CHR-RAM, vertical mirroring |
| SHA-1 (file, with iNES header) | `c9ea66bb7cb30ad5343f1721b1d4d3219859319b` |
| SHA-1 (PRG data, header stripped) | `979494e7869ac7ab4815fdbd1dc99f893f713fbf` |

Banks 0–6 are switchable at `$8000–$BFFF`; bank 7 is fixed at `$C000–$FFFF`. Addresses below are written `bank:address` (e.g. `7:CEEA`, `3:BDFA`).

## 2. What the clip shows

From DK28's clip, around **0:11–0:14** (run timer ≈ 0:41–0:47):

1. DK28 is in the rocky cliff section in the middle of Stage 1, with two flying weapon capsules on screen.
2. They jump right and drop into a pit, land at the very bottom, and briefly crouch/stand there.
3. The player sprite **vanishes with no death animation**. There is no respawn.
4. The screen sits frozen for **~2.7 seconds**, fades to black, and shows **STAGE 2 / BASE1** (lives still shown as REST 2).

## 3. How the game normally gets from Stage 1 to Stage 2

The game-mode byte `$2C` is dispatched through a jump table at `7:CE35`:

| Mode `$2C` | Handler | Purpose |
|---|---|---|
| `00` | `7:CE4B` | Load level header for level `$30`, clear `$3B` |
| `01`–`03` | `7:CE7E`, `7:CE9B`, `7:CED8` | Stage intro screen, set-up |
| `04` | `7:CEE3` | **In-level gameplay** |
| `05` | `7:CF2E` | End of stage: next level, or game-over/continue |
| `06`, `07` | `7:CF9D`, `7:CFE1` | Continue / end screens |
| `08` | `7:CFEA` | **Stage cleared — wait** |
| `09` | `7:D01F` → `3:BDFA` | **Scripted walk-off** |
| `0A` | `7:D02E` | Both players out — delay before game over |

The full chain, confirmed with a write-trace of a real boss kill (`trace_clear.py`):

1. **Boss core destroyed.** In Stage 1 the core is enemy type `$11` (state table `0:8BC7`). Its "destroyed" state is `7:E740`, which calls `7:EAEA`. This sets **`$3B = 1`** (stage clear) and **`$2A = $FF`** (timer "hold").
2. **Mode `04` → `08`.** Every frame of mode `04` runs `7:CEEA  LDA $3B / BNE $CF25`, and `CF25` sets `$2C = 8`. **This is the only place in the game that sets mode `08`.**
3. **Mode `08` waits.** The level keeps running, and players can still die. About two seconds later the boss's explosion routine arms the timer (`0:8C2E`: `$2A = $30`). Once `$2A` counts down to 0, mode `08` requires at least one player who is not game-over (`$38,X = 0`) and is alive (`$90,X = 1`). Then it plays the clear jingle and moves to mode `09`.
4. **Mode `09` walk-off** (bank 3, sub-state `$2D`):
   - `0`: Mark each live player as walking (`$0192/$0193`). Wait until nobody is mid-jump, then set `$3B = $81`.
   - `1`: Run the per-stage walk script. **A player who is off-screen is removed instantly with no animation** (`3:BF8A`). When nobody is still walking, set `$0190 = $A0`.
   - `2`: Set `$3B = $02` and count `$0190` down: **160 frames ≈ 2.7 s**, then mode `05`.
5. **Mode `05`.** If `$3B ≠ 0`, keep weapons, `INC $30` (level number), and go to mode `00`. If `$3B = 0`, go to game-over/continue instead.

### Variables around the stage-clear flag

| Address | Meaning | Written by |
|---|---|---|
| `$29` | Delay before game over | `7:CF0C` |
| `$2A`/`$2B` | General timer (`$FF` = wait for the boss) | `7:EAEF`, `7:EAF6`, counted down by `7:C315` |
| `$2C` | Game mode | the six mode changes above |
| `$2D` | Sub-state within a mode | `3:BE72`, `7:CF2B` |
| `$30` | Level number (0 = Stage 1) | `7:CF4D` |
| `$32`/`$33` | P1/P2 lives | death, extra lives |
| `$38`/`$39` | P1/P2 game-over flags | `7:DA08` |
| `$3A` | Continues left | `7:CF89` |
| `$3B` | Stage clear: `0` playing, `1` boss dead, `$81` walking off (bit 7 also disables the screen-edge and ceiling clamps), `$02` fading out | `7:EAF3`, `3:BE30`, `3:BF7A`, cleared at `7:CE65` |
| `$86` | Boss parts remaining (multi-part bosses, `0:A038`; not used in Stage 1) | |
| `$0190`–`$0194` | Walk-off delay, timeout, per-player walk state, players alive | bank 3, `7:D012` |

### What is actually required (flag-poking experiment, `force_clear.py`)

| Poke mid-Stage 1 | Result |
|---|---|
| `$3B=1`, `$2A=0` | Stage 2 loads |
| `$3B=1`, `$2A=$FF` | Stuck in mode `08` forever |
| `$3B=1`, player dead | Stage 2 loads, after waiting for the respawn |
| `$3B=1`, player game-over | Game-over screen |
| `$2C=8` with `$3B=0` | **Stage 2 loads** (mode `09` sets `$3B` itself) |

So the only hard requirement is reaching mode `08` with a timer that can run out and one player alive.

## 4. Can you trigger it by falling? (emulator testing)

Using the headless emulator in `scripts/emu.py`, which runs the game logic only:

- **Random play** (8 seeds, ≈20,000 frames each, forced invincibility): no scroll or position jumps. All boss kills were normal.
- **Systematic drops** (`exp2.py`): at every 16 px of scroll across Stage 1 (193 positions), the player was dropped from the top at every 8 px column, then held still, right, and left. Zero anomalies. All 773 deaths respawned at the normal spots.
- **Pit drops with stage-exit detection** (`exp4.py`): 112 scroll positions across screens 5–11, 41 columns each, three input patterns, no invincibility. **Zero early stage exits.**

A plain fall into a pit does not cause the skip, at least without lag frames or PPU timing, which this emulator doesn't model.

## 5. Static analysis: what can set mode `08` without the boss?

`codemap.py` builds a map of real code by following control flow from the reset and NMI vectors, the bank-switch trampolines, the inline jump tables (`JSR $C857`) and the enemy routine tables. That gives 13,762 instructions, so level and graphics data aren't mistaken for code. All of the following analysis uses that map.

### Software paths: all ruled out

- **Writes to `$2C`:** only the six intended mode changes (`7:CE7B`, `CEC2`, `CF27`, `CF67`, `CFAF`, `D01C`). No indexed or indirect store anywhere can reach `$2C` (`alias_scan.py`).
- **Writes to `$3B`:** the five intended writes, plus seven indexed stores from the arrays just below it:
  - `$38,X` (game-over flags) would need `X = 3`.
  - `$32,X` (lives, including the extra-life `INC $32,X` at `7:C502`) would need `X = 9`.

  Every one of these indexes traces back to a player number (0 or 1): the player loops, or the bullet-owner byte written at `6:B587` from the firing player's index.
- **Indirect stores:** only three exist. RAM clears at `7:C12C` and `7:C494`, and `7:CDA8`, whose pointer high byte is hard-coded to `$07`.
- **Lag-frame NMI race:** game logic runs inside the NMI. On a lag frame, the next NMI takes a short path (`7:C0B6`) that only runs the sound driver. Everything that path can reach (`reach.py`) writes only `$1B`, `$07ED`, `$E0–$EF` and page-1 sound RAM, and no game logic uses those.
- **Enemy routines:** in Stage 1 only the boss core (type `$11`, state 3 → `E740`) reaches stage clear. Normal enemies never get routed there when killed: `7:E96A` picks their "destroyed" state from a per-type table.
  - One latent weakness: the enemy dispatcher (`7:E659`) doesn't bounds-check the type number. Stage 1's table (`7:E6C8`) defines only types `$10–$12`, and Stage 2's table follows it in ROM. A slot with type `$13`+ would therefore run Stage 2 enemy code, including a boss with a stage-clear state.
  - All writers of the enemy type byte (`$0528,X`) store constants or level data, so this would need some other corruption first.

### Bit flips: the plausible cause

The decision is one instruction pair, `7:CEEA  A5 3B  LDA $3B` / `7:CEEC  D0 37  BNE $CF25`. One-bit corruptions:

| Corruption | Result |
|---|---|
| RAM `$3B`, any of the 8 bits | Mode `08` next frame |
| ROM `$CEEC` `D0`→`F0` (bit 5) | `BNE` becomes `BEQ`: taken exactly when `$3B = 0`, so always triggers |
| ROM `$CEEC` bit 6 or 7 (`BCC`/`BVC`) | Triggers depending on the CPU flags |
| ROM `$CEEB` `3B`→`3A` | Reads continues (= 3) → triggers |
| ROM `$CEEB` `3B`→`39` | Reads P2 game-over (= 1 in one-player) → triggers |
| ROM `$CEEB` `3B`→`1B` | Reads the NMI-busy flag (= 1 during game logic) → triggers |
| ROM `$CEEB` `3B`→`7B` | Reads `$7B` (= `$FC` in Stage 1) → triggers |
| RAM `$2C`, any bit (`04` → `05`/`06`/`00`/`0C`+) | Game over, continue screen, Stage 1 restart, or crash. **Never mode `08`**, which needs two bits. |

A misread from a dirty or poorly seated cartridge affects ROM fetches, and seven different single-bit errors at those three bytes lead straight to the skip. It also explains why nobody can reproduce it.

## 6. Simulating the misread

`sim_misread.py` and `sim_misread3.py` replay a fall into a bottomless pit in Stage 1's cliff section. For exactly one frame, the emulator returns `$F0` instead of `$D0` when the CPU reads `$CEEC`. Nothing else is changed: no values are forced and there's no controller input after the drop.

### What the clip shows, frame by frame

The clip was checked at its full 60 fps rate, and the top-left lives medals were zoomed in on:

| Time | Event |
|---|---|
| 11.45–12.00 | Player at the bottom of the pit, in the pit-death pop-up animation |
| 12.00 | Player gone; only the two capsules still move, flying off the top right |
| 12.75–13.47 | Nothing on screen changes |
| **13.47** | **Lives medals drop from 2 to 1**, the end of the death sequence (`7:D9FA DEC $32`) |
| 13.47–14.83 | Nothing on screen changes. No respawn is visible. |
| 14.83 | Fade to black, then the Stage 2 card: "REST 2" |

The card prints `$32 + 1` while the player isn't game-over (`7:CA6F`), so "REST 2" means `$32 = 1`. That fits a life being used in the pit.

### Clip vs simulation

| | Clip | One-frame misread while falling |
|---|---|---|
| Body gone → lives decrement | 88 frames | 84 frames |
| Body gone → fade | ~170 frames | 160 frames |
| Lives decrement → fade | 82 frames | 76 frames |
| Lives at Stage 2 | `$32 = 1` | `$32 = 1` |
| Without the misread | — | Normal respawn, the game continues |

Sequence in the simulation:
1. The misread switches the game to mode `08`, then `09` on the next frame. The walk-off clears controller input every frame, so the player is no longer under control.
2. The fall death happens normally, and the walk-off removes the body once it's below the screen (`3:BF8A`).
3. No one is left walking, so the 160-frame countdown starts.
4. The death timer runs out, a life is used, and the player respawns.
5. The countdown ends and Stage 2 loads.

Any single frame between leaving the ledge and the fall death gives the same result. A misread *after* the death doesn't match: mode `08` waits for the respawn, and the respawned player visibly walks off for about 7 s.

### Why the respawn isn't visible in the clip

A respawned player is invincible for 128 frames (`7:D50D`), and during that time the sprite is hidden on every other frame (`2:B004`, based on bit 0 of the frame counter `$1A`). The fade comes 76 frames after the respawn, so the player blinks the whole time. DK28's clip only changes on alternate frames: the 60 fps file follows a strict `0101…` pattern, so it was captured at 30 fps. A 30 fps capture keeps every other NES frame, so a sprite that blinks on alternate frames appears either solid or not at all. This footage landed on the "not at all" side.

### Caveats

- The exact pit isn't known. The simulations used several pits in the same cliff section, and the timings didn't depend on which one.
- The emulator models game logic only, with no PPU, but every event compared here is game logic.
- This shows that a single misread reproduces the footage exactly. It doesn't prove that one happened.

## 7. Conclusion

- The game's code has no software path into the stage-clear sequence other than killing a boss.
- A single cartridge misread at `7:CEEA–CEEC` (or a bit flip in RAM `$3B`) while DK28 was falling sends the game into its own end-of-stage sequence. Simulated, it reproduces everything in the clip, with matching timings.
- DK28 was on original hardware, where intermittent cartridge misreads are a known problem. That would also explain why nobody has been able to reproduce the skip.

## 8. Tools

All scripts are in `scripts/` and take the ROM path as their first argument. Run them from inside `scripts/` with plain `python3` (not `python3 -I`), so the local `dis.py` takes precedence over Python's built-in `dis` module. No dependencies beyond the Python 3 standard library.

| Script | What it does |
|---|---|
| `dis.py ROM BANK START END` | Linear 6502 disassembler for one bank range |
| `codemap.py ROM` | Recursive-descent code map → `codemap.pkl` |
| `alias_scan.py 2C 3B` | Indexed/indirect stores (real code only) that could hit the given zero-page bytes |
| `reach.py ROM` | RAM written by everything reachable from the lag-frame NMI path |
| `enemy_tables.py ROM LEVEL` | Each level's enemy state tables, flagging states that can reach stage clear |
| `level.py ROM` | Stage 1 header and a text collision map |
| `emu.py` | Minimal headless NES (CPU + UxROM + controllers; no PPU, no lag modelling) |
| `boot.py ROM` | Boots to Stage 1 and saves `start.pkl` (needed by the experiment scripts) |
| `trace_clear.py ROM` | Plays a boss kill into Stage 2, logging every write to the stage-flow variables |
| `force_clear.py ROM` | The flag-poking experiment in section 3 |
| `sim_misread.py ROM` | One-frame `$CEEC` misread (`BNE`→`BEQ`) injected at each frame across a pit fall |
| `sim_misread3.py ROM` | Clean bottomless-pit falls with the misread, timing the death, lives decrement, respawn and fade |
| `exp1.py`–`exp5.py` | Random play, systematic drops, screen-counter test, pit drops, pit-jump replay |

To regenerate a full disassembly: `for b in 0 1 2 3 4 5 6; do python3 dis.py ROM $b 8000 C000 > bank$b.asm; done; python3 dis.py ROM 7 C000 10000 > bank7.asm`.

## Credits

Glitch discovered by **DK28**. Contra © Konami. This repository contains no Konami code or data.
