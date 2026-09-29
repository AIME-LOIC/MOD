# Compound Ops — Night Deployment (game kit)

Units: meters, Y-up. Compound slab: 211.2 x 115.2 m. Outer world: ~780 x 640 m.
Spawn: (105, 58). Open `compound_game.html` in any browser (internet needed once for three.js r128).

## Modes (start menu)

- **TRAINING** — *start here.* **Camp Alpha is its own remote desert map** — fenced base in open sand, blowing sand on the wind, support buildings outside the fence, zero hostiles. **7 guided stations in enforced order**, each marked by a **green guidance beam** with a compass readout (distance + direction) and a "next:" hint: 1 rifle range (12 reactive targets) · 2 drone line (lead your shots) · 3 grenade range (painted rings, G) · 4 sniper challenge (60 m steel, Hawkeye + RMB) · 5 CQB house clear (real upstairs floor) · 6 obstacle course (4 checkpoints) · 7 tower climb (hold W on the rungs). **The cargo plane refuses to board until all 7 are done.**
- **THE DEPLOY FLIGHT** — board the plane after all 7 stations: it **lifts off over the desert camp**, the world switches under you mid-flight, then you ride over **forest → the huge lake → the city skyline**, descending to the forest LZ (105,-158). When you want out, **an extraction plane is parked at the LZ** (105,-166): press E to climb out, cross back over the lake and forest, and land **back at Camp Alpha** to refit and go again — the war loop is yours.
- **CAMPAIGN** — 6 story ops, and the story begins in training: *Boot Camp* (all 7 stations → board the plane → desert-to-war flight), *First Blood* (clear the compound), *Blackout* (sabotage the port shipment, survive the QRF), *Riverside* (locate & escort the informant HVT out of the city), *Scorched Earth* (break the warzone garrison), *WARZONE CITY* (cross the river by boat and take the enemy capital). Progress op-to-op; failures can be retried.
- **SINGLE PLAY** — free-roam open world with patrol zones to clear, on any of the 4 maps.
- **PLAY ONLINE** — Quick match, public room browser or private room codes, via the deployable backend (`game_server.js`). Co-op, deathmatch (with extra bot enemies) and **1v1 DUEL** (2-player rooms, real PvP damage, headshots count, first to 5 wins, warm-up bots while you wait) with anyone, anywhere. Maps: COMPOUND, DOWNTOWN, KILLHOUSE, REALCITY, SOS CAMPUS, OUTSKIRTS, BLACKOUT.
- **WATER everywhere** — the river, lake and bays are swimmable: buoyancy holds you at the surface, strokes cost stamina, exhausted swimmers sink and drown. Boats bob on the waves with bow wakes, cars sink to the riverbed (bail out or drown), grenades splash in and fizzle as duds. The school campus has a rooftop-height swimming pool and the hotel roofs have pool parties.
- **REALCITY — a real-world-data city map**: built from `warzone_city.glb` (your Blender export with surveyed terrain, roads, piers, waterfront, rubble fields and landmark ruins), plus procedurally-built real houses with window openings, interiors, and stairs to the roof filling out the blocks. If the GLB can't be found (e.g. opening the file directly without a server), it falls back to a fully playable procedural city — never a black screen.
- **SOS CAMPUS — a school map**: built from `sos_technical_school_v3.glb` (trimesh export of the SOS Technical School survey: 13 named teaching blocks, boys/girls dorms, admin + labs, main hall, dining & kitchen, workshops, football pitch, basketball court, gatehouse and hedge line on a 320×320 m campus). Every building gets AABB colliders and a walkable roof with a ladder; a fallback campus is built if the GLB can't load.
- **SERVER PLAY (LAN)** — Co-op (fight bots together) or Deathmatch (first to 15) with friends on your network.

## Play ONLINE (deploy the backend)

The backend is **`game_server.js`** — dependency-free Node (16+) that serves the game *and* runs the multiplayer: public rooms, quick-match matchmaking, private room codes, in-game chat, a persistent global leaderboard, plus rate limiting and payload caps so it's safe on the public internet.

**One-click on Render:** the repo ships a **`render.yaml`** blueprint (repo root). In Render: **New → Blueprint** → pick this repo → **Apply** — done. Free-plan note: the instance sleeps after ~15 min idle; the first request wakes it (~30 s).

**Deploy in one line on any host (Render / Railway / Fly / VPS / Pterodactyl):**

```
node game_server.js          # start command — respects the PORT env var
```

- **Health check path:** `GET /api/health` → `{"ok":true,...}`
- **Room browser API:** `GET /api/rooms` → live JSON list of public rooms
- **Docker:** `docker build -t compound-ops . && docker run -p 8080:8080 compound-ops`
- **Leaderboard data** persists to `data/scores.json` (created automatically; survives restarts).

Then: open `https://your-deployment/` → **PLAY ONLINE** →

1. **QUICK MATCH** — instantly joins the fullest public room (or opens one).
2. **BROWSE ROOMS** — live list; click a room to join.
3. **Room code** — type e.g. `alpha`, pick **HOST CO-OP** or **DEATHMATCH**, and share the code with friends; they type the same code on any device.

In-game: **T** = chat, leaderboard shows top operators (kills/deaths/wins across all matches on that server).

No deployment? **PLAY ONLINE** also works against a friend running the LAN server: it auto-connects to `location.host`, or open the game locally and the menu uses whatever host served the page. Quick match and the room browser degrade gracefully to LAN rooms.

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
| WASD / arrows | Move (Shift = sprint — drains stamina, refills when you slow down) |
| Space | Jump (climb crates, stairs, onto roofs) |
| Mouse click | Mouse-look (pointer lock) · LMB fire |
| Hold RMB | ADS — zoom + tighter spread ("scouting" scope view) |
| R | Reload · G | Grenade · E | Enter/exit nearest car |
| T | Chat (online / LAN) · 1 / 2 / 3 / 4 / Tab | Switch operator (Ranger / Vega / Dash / Hawkeye-sniper) |
| Touch | Left half = move stick, right = look, FIRE / JUMP / ADS / GRN / R buttons |

## What's in the build

- **Houses stay intact** — roofs are permanent (no more vanishing when you walk in). Every building has an **interior staircase to the roof** with parapets; the roof has a stairwell slot you climb out of. Use roofs as overwatch.
- **Bullet fixes** — walls, crates, containers and vehicles now actually block shots (2D ray vs box with elevation + roof-height checks). Headshot = instant kill (above ~1.5 m), body = 5 shots (20 dmg). Bots also die reliably to run-overs at speed.
- **Jumping & scouting** — Space to jump (~1.1 m), full gravity; RMB hold = ADS with FOV zoom, slower sway, reduced spread, weapon pulls to center.
- **Dark CoD-style look** — dusk sky dome with stars + burnt horizon, low warm sun, fog, vignette, ACES tonemapping, warm interior/street lights, flickering campfire, emissive lamp heads.- **Huge enterable city — 250+ buildings**: downtown towers, mid-rise blocks, small homes, industrial sheds and a west-bank district — roughly **356 buildings**, most with doorways, **interior rooms, upper floors and staircases all the way to the top**, **broken windows with jagged shards and low sills you can vault through**, roof parapets for overwatch. Geometry is **baked into 80 m map tiles and streamed Google-Maps-style**: only tiles within ~340 m of you are rendered (and the shadow camera follows you), so it stays smooth even with ~37,000 colliders.
- **Expanded map — the journey south**: leave the compound through 3 gates (north, south, west):
  - **Forest** (west & north) with instanced pines/leafy trees, rocks, bushes, and a camp (tents + campfire) in the north woods.
  - **WARZONE district** (north, past the forest): a destroyed city — collapsed ruins you can enter, rubble piles, burning cars with flickering firelight & rising smoke, scorch marks, a lit ring road with lamp posts, and a hostile garrison. Campaign op 4 (*Scorched Earth*) lives here.
  - **THE RIVER** (past the warzone): a wide dark waterway with quays, landing jetties, broken bridge arches and a **drivable motorboat** moored at the north quay — press E aboard to pilot it across (you can't swim; soldiers wade slowly, cars sink to the quay).
  - **WARZONE CITY** (south bank, campaign op 5): the map-image city rebuilt in 3D — **WATERFRONT** (docks, piers, warehouses, OBJ ECHO), **INDUSTRIAL DISTRICT** (NW blocks + burning smokestacks), **DOWNTOWN CORRIDOR** (tall towers with multi-story interiors, lit lobbies, roof parapets — OBJ ALPHA & DELTA), **PARK DISTRICT** (E: woods, ruins, glowing fountain pond), **RESIDENTIAL SECTOR B** (S row) — ~90 enterable buildings, most with interior rooms, upper floors and staircases; ~30 of them are **on fire** (emissive cores, flickering light, rising smoke columns). Objectives beam colored light; ammo caches and burning-vehicle hotspots are scattered on every street; the minimap draws the river, city blocks and warzone ruins.
  - **SNIPER** — operator 4 *Hawkeye* carries a scoped bolt rifle: hold RMB for a true scope view (18° FOV with crosshair overlay), one-shot kills to the torso (85 dmg), slower cycling fire.
- **Outpost city "Riverside"** (north side): 6 enterable buildings with lit interiors, street lamps, road network.
- **Distant hills** ringing the horizon + drivable roads linking everything — roads read clearly at night (lighter asphalt, painted center dashes, roadside lamps) with **signposts** at every gate (WARZONE / CITY / WEST HILLS / RIVERSIDE / BOAT CROSSING).
- **Grenades** — G or GRN button: physical throw with bounces, 2 s fuse, 8 m blast that kills enemies (and can hurt you).
- **Realism layer** — layered gunshot cracks (rifle vs sniper), sub-bass explosion boom, footsteps at speed, two-stage reload clicks, hitmarker tick; sprint stamina + FOV kick, landing camera dip after falls, faster head-bob when running, dust puffs on bullet impacts, muzzle smoke, crosshair that expands while moving/firing and tightens on ADS; nearby bots hear gunfire and come hunting.
- **Real smoke** — soft sprite-particle plumes (600-particle pool with recycling) rising from burning buildings, cars, smokestacks and grenade blasts, plus contrails behind the jets. No more blob shapes.
- **Life in the streets** — **enemy patrol cars** drive the city avenues (hijack with E, destroy with grenades — they torch and smoke); **jets cross the sky** high overhead with contrails and a blinking beacon; **enemy snipers** (scoped, ~15–20% of spawns) hold long sightlines and hit hard; **WAR DOGS** (12 of them) sniff you out through walls, sprint you down, circle and bite — kill them before they reach you.
- **SUBWAY** — a full underground station under the big-city avenue: two street entrances with glowing M-signs and stair descents, a 320 m tunnel platform with pillars, benches, a wrecked train car, flickering strip lights, ammo caches and **tunnel guards**. Deep enough that street level is a different fight.
- **THE HUGE LAKE** — a 40 m waterway plus two bays (and an island camp) between the compound and the main city. Too deep to wade; cross by **boat** (4 moored: north shore, island, south shore, old river quay) — cars sink at the shore.
- **CAMP ALPHA — its own remote DESERT map** (no city, no houses for kilometres — dunes on the horizon, **sand visibly drifting on the wind**): fenced yard with the concept-art layout — **watchtower with camo-net roof + searchlight and a climbable ladder**, **4 security towers with ladders**, string lights, **TRAINING CAMP ALPHA banner**, the 2-storey **URBAN TACTICS TRAINING HOUSE** (internal switchback stairs **plus** the external showpiece stair, both landing flush — ground → level 2 → roof), supply racks with coiled hoses, tire wall, monkey bars, A-frame rope climb, vault hurdles, **chain-link fence with a north gate to the plane strip**, humvees, camo truck, tent city, flag, campfire. Barracks/mess/armory sit outside the fence. Cars **slip and slow in deep sand** and kick up dust plumes; sand blows across the yard whether you're on foot or driving.
- **EXTRA TRAININGS** — **drone line**: 4 moving aerial drones crossing the range (hittable in flight, explode into smoke); **grenade range**: painted rings at 12/18/24 m, stand behind the line and throw (G) for 1–3 pts; **sniper challenge**: three 0.35 m steel plates at 60 m from the tower line; **obstacle course** with timing board. All scores feed the same hitmarker/audio feedback as combat.
- **Heavily destroyed houses** — pancaked floor slabs, blown-out wall segments, exposed rebar, rubble cones and smoke — across the compound side, the outskirts and the warzone.
- **Squad fights on its own** — teammates are not escorts: they pick their own targets, close to firing range, strafe, take cover behind nearby obstacles, and get killfeed credit for their kills. They still fall back to you if you outrun them by 55 m.
- **Compass & killfeed** — N/NE/E… heading strip, killfeed entries for every kill, HEADSHOT callouts.
- **Fixed door entry** — an invisible collision wall along building rooflines blocked all doorways; fixed. Walk through any door, take the stairs up, snipe from the parapet.
- **Dead stays dead** — killed enemies do not respawn (single-player/campaign); waves only in fresh matches.
- **Interiors done right** — every multi-storey building has an **inside dogleg staircase** (wood flights with sloped handrails and posts, landings, a well hole through each floor slab) that always connects floor to floor to the roof. **Houses never spawn on roads or in the lake.** Distant hills sit on a horizon ground sheet — nothing floats.
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
| warzone_city.glb | REALCITY map source — real-world survey mesh (Blender export) baked into the map. |
| sos_technical_school_v3.glb | SOS CAMPUS map source — school survey mesh (trimesh export) baked into the map. |
| character_human.glb | Organic skinned human (27 joints, Idle+Walk clips, vertex-color camo, Blender build). Drives the player squad in-game when loadable; the procedural rig remains the fallback. Verify with `node ../tools/verify_glb.js character_human.glb`. |
| car_sedan / car_van / car_pickup .glb | Authored drivable vehicles (tools/glbkit.py + build_assets.py). Take bullet and explosion damage; they torch into wrecks. |
| house_small / house_duplex .glb | Authored enterable houses — interiors, stairs, porches. |
| skyscraper.glb / hotel.glb | Authored enterable towers: 12 office floors + helipad roof / 8 guest floors + rooftop pool (a real water zone). Star of the DOWNTOWN map. |
| game_server.js | **Deployable ONLINE multiplayer backend** — static hosting + rooms + quick match + chat + persistent leaderboard + rate limiting. Run with `node game_server.js [port]` (PORT env respected). |
| Dockerfile | Container deploy for the online backend (`docker build -t compound-ops .`). |
| lan_server.js | Dependency-free Node LAN server (static hosting + room relay). Run with `node lan_server.js [port]`. |
| START SERVER (LAN).bat / start-server.sh | One-click launchers that open the firewall and start the server. |
| e2e_test.js, physics_test.js, backend_test.js, leave_test.js, arena_test.js, school_test.js, water_test.js, downtown_test.js, duel_test.js | Node test suites (no deps): run `node physics_test.js`, `node backend_test.js`, `node arena_test.js`, `node school_test.js`, `node water_test.js`, `node downtown_test.js`, `node duel_test.js`, etc. |
| compound_map_fixed.glb | Original compound map mesh (unchanged). |
| character_ranger.glb / character_vega.glb | Original character rigs (unchanged). |
| ../tools/ | Asset pipeline: `blender_bridge.py` (live Blender ↔ agent bridge), `build_character.py` (headless character builder), `verify_glb.js` (dependency-free GLB checker), `verify_glb.html` (browser verify page), `blend_cmd.sh` (bridge client), `CONNECT-BLENDER.md` (setup guide). |
| map_colliders.json | Original compound collision boxes (unchanged). |

## Known limits

- Bullets don't collide with roofs (they're support surfaces, not solid boxes) — you can't shoot someone *through* a roof, but ground-to-roof arcs pass over fine.
- Bot AI is patrol/chase with LOS checks (snipers hold position, squads strafe & seek cover) — no pathfinding; bots don't climb stairs.
- Car vs car physics are arcade-simple (cars stop on impact; no crush damage).
- Performance: the city renders as streamed tiles (2–6 draw calls per frame area) with ~12 dynamic lights; tested at ~3 ms/frame in headless runs.
