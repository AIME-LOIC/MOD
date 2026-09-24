# Compound Ops — Night Deployment (game kit)

Units: meters, Y-up. Compound slab: 211.2 x 115.2 m. Outer world: ~780 x 640 m.
Spawn: (105, 58). Open `compound_game.html` in any browser (internet needed once for three.js r128).

## Modes (start menu)

- **CAMPAIGN** — 3 story ops: *First Blood* (clear the compound), *Blackout* (sabotage the port shipment, survive the QRF), *Riverside* (locate & escort the informant HVT out of the city). Progress op-to-op; failures can be retried.
- **SINGLE PLAY** — free-roam open world with patrol zones to clear, on any of the 3 maps.
- **SERVER PLAY (LAN)** — Co-op (fight bots together) or Deathmatch (first to 15) with friends on your network.

## LAN play in 3 steps

1. On the **host PC**: double-click `START SERVER (LAN).bat` (Windows) or run `./start-server.sh` (Linux/macOS). It opens firewall port 8080 automatically (may ask for admin) and prints an address like `http://192.168.1.20:8080/compound_game.html`.
2. On **every other PC**: open that exact address in the browser — or just open `compound_game.html` locally (even from a file) and type the host IP (e.g. `10.15.4.27:8080`) into the **server address** box in SERVER PLAY.
3. In the menu choose **SERVER PLAY (LAN)**, type the same **room name** on all PCs, pick **CO-OP** or **DEATHMATCH** and deploy.

No internet is needed *between* PCs — the server runs entirely on the host. Each PC needs one-time internet access to load the three.js library (or download `three.min.js` locally and edit the `<script src>` line).

**Other PCs can't connect?**
- Windows: run `netsh advfirewall firewall add rule name="CompoundOps" dir=in action=allow protocol=TCP localport=8080` as admin (the .bat does this for you).
- Linux: `sudo ufw allow 8080/tcp`.
- Both PCs must be on the same network (same router / subnet) — guest Wi-Fi isolation will block it.
- Type the IP exactly as printed by the server; ping it first to check reachability.

Disconnected players are detected within seconds and removed from the room; the client auto-reconnects if the connection blips.

## Controls

| Input | Action |
|---|---|
| WASD / arrows | Move (Shift = sprint) |
| Space | Jump (climb crates, stairs, onto roofs) |
| Mouse click | Mouse-look (pointer lock) · LMB fire |
| Hold RMB | ADS — zoom + tighter spread ("scouting" scope view) |
| R | Reload · G | Grenade · E | Enter/exit nearest car |
| 1 / 2 / 3 / Tab | Switch operator (Ranger / Vega / Dash) |
| Touch | Left half = move stick, right = look, FIRE / JUMP / ADS / GRN / R buttons |

## What's in the build

- **Houses stay intact** — roofs are permanent (no more vanishing when you walk in). Every building has an **interior staircase to the roof** with parapets; the roof has a stairwell slot you climb out of. Use roofs as overwatch.
- **Bullet fixes** — walls, crates, containers and vehicles now actually block shots (2D ray vs box with elevation + roof-height checks). Headshot = instant kill (above ~1.5 m), body = 5 shots (20 dmg). Bots also die reliably to run-overs at speed.
- **Jumping & scouting** — Space to jump (~1.1 m), full gravity; RMB hold = ADS with FOV zoom, slower sway, reduced spread, weapon pulls to center.
- **Dark CoD-style look** — dusk sky dome with stars + burnt horizon, low warm sun, fog, vignette, ACES tonemapping, warm interior/street lights, flickering campfire, emissive lamp heads.
- **Expanded map** — leave the compound through 3 gates (north, south, west):
  - **Forest** (west & north) with instanced pines/leafy trees, rocks, bushes, and a camp (tents + campfire) in the north woods.
  - **WARZONE district** (north, past the forest): a destroyed city — collapsed ruins you can enter, rubble piles, burning cars with flickering firelight & rising smoke, scorch marks, a lit ring road with lamp posts, and a hostile garrison. Campaign op 4 (*Scorched Earth*) and 5 single-play patrol zones live here.
  - **Outpost city "Riverside"** (south): 6 enterable buildings with lit interiors, street lamps, road network.
  - **Distant hills** ringing the horizon + drivable roads linking everything — roads read clearly at night (lighter asphalt, painted center dashes, roadside lamps) with **signposts** at every gate (WARZONE / CITY / WEST HILLS / RIVERSIDE).
- **Grenades** — G or GRN button: physical throw with bounces, 2 s fuse, 8 m blast that kills enemies (and can hurt you).
- **Compass & killfeed** — N/NE/E… heading strip, killfeed entries for every kill, HEADSHOT callouts.
- **Fixed door entry** — an invisible collision wall along building rooflines blocked all doorways; fixed. Walk through any door, take the stairs up, snipe from the parapet.
- **Dead stays dead** — killed enemies do not respawn (single-player/campaign); waves only in fresh matches.
- **Better driving** — chase camera behind the car, body roll in turns, steering front wheels, speed-sensitive grip + handbrake drift (Space), crash damage, run-over kills. **Cars are solid now**: walkers and bots bump into parked cars instead of clipping through, driving into a parked car stops you with a bang, and squadmates get shoved clear of your path.
- **Drivable cars** — 4 sedans (compound x2, city, west road). Press E near one: throttle/reverse, steering, wheel spin + steer visuals, crash damage + bounce, bots can be run over. Squadmates teleport to you if you leave them >55 m behind.
- **Your team** — 3 operators (Ranger, Vega, Dash). Switch anytime; the other two follow you in formation, engage enemies on their own, respawn with you.
- **Real-looking props** — canvas-generated textures: stenciled wooden crates, ribbed oil barrels, ribbed containers, camo cloth on characters, concrete facades, painted asphalt with cracks.

## Characters (upgraded)

Still rigid-part rigs (no skinning), but now with camo texture maps, plate carrier + mag pouches + straps, radio with antenna, knee pads, shoulder pads, holster, thigh rigs, boots, balaclava/goggles — much less "lego".

## Files

| File | What it is |
|---|---|
| compound_game.html | Playable prototype (this build). All gameplay is inline JS. |
| lan_server.js | Dependency-free Node LAN server (static hosting + room relay). Run with `node lan_server.js [port]`. |
| START SERVER (LAN).bat / start-server.sh | One-click launchers that open the firewall and start the server. |
| e2e_test.js, physics_test.js, leave_test.js, close_repro.js | Node test suites (no deps): run `node physics_test.js` etc. |
| compound_map_fixed.glb | Original compound map mesh (unchanged). |
| character_ranger.glb / character_vega.glb | Original character rigs (unchanged). |
| map_colliders.json | Original compound collision boxes (unchanged). |

## Known limits

- Bullets don't collide with roofs (they're support surfaces, not solid boxes) — you can't shoot someone *through* a roof, but ground-to-roof arcs pass over fine.
- Bot AI is still patrol/chase with LOS checks, no pathfinding; bots don't climb stairs.
- Car vs car physics are arcade-simple (cars stop on impact; no crush damage).
- Performance: ~12 dynamic lights + instanced foliage; fine on desktop, may need lowering on old phones.
