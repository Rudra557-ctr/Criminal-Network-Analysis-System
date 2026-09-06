# UI Redesign Implementation Plan — De-generic the SaaS, Keep the Product

Status: **approved direction, ready to build**
File under redesign: `frontend/index.html` (single file, 5053 lines — all changes here, no backend changes)
Direction decisions (locked):
- Visual direction: **Keep light SaaS, de-generic it** (not tactical-HUD takeover, not formal dossier)
- Scope: **Full system + icons** (tokens + HTML structure + SVG icon set + responsive)
- Theme target: **Both equally** (light + dark retuned in parallel)

## 1. Goals / Non-goals

Goals:
- Remove the 10 generic-AI tells (card sprawl, rainbow gradients, pill-everything, emoji icons, flat type, 900px scroll column, identical views) without changing product behavior.
- Ship a token system that works in both ` :root` (light) and `html[data-theme="dark"]` (obsidian) with 1:1 parity.
- Replace ~163 emoji tokens with a small inline SVG set.
- Keep all view IDs, JS function names, API calls identical — pure presentational refactor.

Non-goals:
- No new views, routes, endpoints, or analytics logic.
- No framework migration (stays vanilla + 3d-force-graph + Leaflet + jsPDF).
- No copy rewrite beyond de-emojifying labels (legal disclaimers stay verbatim).

## 2. Token system (edit `<style>` lines ~7-280 only)

### 2.1 Color — light (`:root`)
Keep ocean hue (product identity), kill glassmorphism:
- `--bg: #EDF2F7` (flat, replaces `#F0F9FF` + 4x radial wash). Delete body `radial-gradient` stack (line 27), keep `background-attachment` removal.
- `--panel: #FFFFFF` (flat, replaces `rgba(255,255,255,.94)` + `linear-gradient(180deg,white→#F0F9FF)` on `.card/.btn/.drawer/.modal`).
- `--border: #D7E3EE` (flat 1px, replaces `rgba(186,230,253,.85)` everywhere).
- `--accent: #0369A1` (single primary; demote `#06B6D4` to info-only). `--accent-hover: #075985`. `--accent-light: #E0F2FE` (flat tint for selected rows, replaces `rgba(14,165,233,.12)`).
- `--text: #0F172A`, `--muted: #64748B` (cooler, better contrast than `#082F49/#475569`).
- Semantic (new, both themes): `--danger:#DC2626, --warn:#D97706, --success:#059669, --info:#0284C7`.

### 2.2 Color — dark (`html[data-theme="dark"]` lines ~81-163)
Parity, not glow:
- `--bg:#0B0F16` flat (delete radial `circle at 50% 0%` wash line 96).
- `--panel:#111722` flat (delete `linear-gradient(180deg,white .08→#121721→#090C12)` on `.card` line 115).
- `--border: #232D3D` flat (replaces `rgba(255,255,255,.14)`).
- `--accent:#38BDF8` stays, but remove glow shadows (`0 0 18px cyan`, `pulseGlow`). Active nav = flat fill + 2px left bar, no gradient (lines 106-113).
- Text/muted stay `#F1F5F9/#94A3B8`. Semantic dark: danger `#FCA5A5`, warn `#FCD34D`, success `#34D399`.

### 2.3 Typography
- H2: `21px/800 → 26px/750, letter-spacing:-0.02em, margin-bottom:4px` (line 47). Takedown override `22px → 26px` (line ~858).
- H3: `15px/700 → 16px/700, letter-spacing:-0.01em` (line 48). Modal H3 stays 17px.
- `p.sub`: `13px → 13px/500, margin-bottom:12px` (was 16px) — kills double-stack gap.
- Body/table/inputs stay 13-14px. `th` stays 11px caps but color → `var(--muted)` (was `#0369A1`, line 59) so headers stop shouting in accent color.
- Masthead `.sidebar h1`: `13px/800/.06em → 12px/800/.08em uppercase muted`, plus new second line (case-no/classification, see §4). Stops competing with H2.
- Mono stays `ui-monospace/Menlo` for hashes/IDs only — never for prose.

### 2.4 Spacing / layout
- `.main-content`: `24px 32px → 28px 36px`, `.view max-width: 900px → 1120px` (line 42-43). This alone fixes the 500px-graph-in-900px-column scroll problem.
- `.card padding:20px mb:16px → padding:16px 18px mb:14px` (line 46). Denser without feeling cramped.
- New primitives (add to CSS):
  - `.stat-strip {display:flex; gap:10px; margin-bottom:14px}` + `.stat {flex:1; background:var(--panel); border:1px solid var(--border); border-radius:6px; padding:12px 14px}` — replaces single-stat `.card`s.
  - `.frame {border:1px solid var(--border); border-radius:6px; overflow:hidden}` — for Leaflet/3D canvases (replaces card-as-picture-frame).
  - `.toolbar {display:flex; gap:8px; flex-wrap:wrap; align-items:center}` — replaces ad-hoc inline flex toolbars.
  - `.view-head {margin-bottom:14px}` + `.view-head h2 + .sub` tight stack (4px/8px, not 8px/16px).

### 2.5 Radius (the big de-generic lever)
- Cards/frames/modals: `14px → 8px`. Demo/td cards: `12px → 8px`. Buttons/inputs/graphs: `8px → 6px`. Tags/req/opt: `5px/4px → 4px`.
- `999px` reserved for: `.threat` pills, avatar circles, `td-active-tag` only. Un-pill: `.scorebar/.riskbar` → `4px`, `.casepill/.profilepill` → `6px`.
- Net effect: ~107 radius hits collapse to 3 values (4/6/8) + pills-where-meaningful.

### 2.6 Shadows
- Light: one shadow `--shadow: 0 1px 2px rgba(15,23,42,.06)` for cards/modals. Delete `--card-shadow` blue triple-layer (line 20), `btn-primary` blue glow (line 52-53), drawer `-16px blue` (line 180), modal `0 24px 64px blue` (line 196).
- Dark: `--shadow: 0 1px 2px rgba(0,0,0,.5)` + 1px `inset white .06` top highlight only. Delete `0 0 18px cyan` glows (lines 106-141), `pulseGlow` animation (line 179 → static amber border).
- Hover: `translateY(-1px)` stays on primary CTAs only; remove from `.demo-card/.td-strat-card/.btn` generic lift (lines 51/73/212).

### 2.7 Gradients — kill list
Delete 27 `linear-gradient`s except **one**: `.btn-primary` flat `#0369A1` (light) / `#38BDF8` (dark) — or keep a subtle `135deg` CTA gradient as the single brand accent. Everything else (`sidebar`, `.card`, `.btn`, `.drawer`, `.modal`, `.td-*`, avatar, `scorebar>div`) → flat. `scorebar>div` becomes flat `var(--accent)` → `var(--danger)` stepped, not blended.

## 3. Icon system (replaces ~163 emoji)

New: 16px inline SVG sprite (stroke 1.5, `currentColor`), ~18 icons: dashboard, folder, users, clock, wallet, radio, map-pin, archive, link/chain, crosshair, report, search, camera, refresh, download, x, chevron, shield-check.
- Nav (lines 287-299): `Geospatial Map → map-pin SVG`, `Blockchain Ledger → link SVG`, `Tactical Simulator → crosshair SVG`. Other 8 nav items stay text-only (current state is fine — don't add icons where none exist).
- Buttons: `📋 Templates → doc SVG`, `⚡ Create/Execute → plus/bolt SVG`, `▶ Run/Demo/PLAY → play SVG`, `🔄 Refresh → refresh SVG`, `📄 Export → download SVG`, `✦ Shiny Dark → moon/sun SVG`, `⏻ Logout → logout SVG`, `💡 Recommendations → keep text "Suggested leads" + spark SVG or drop icon`.
- Evidence filters (line 750-755): `📱/💳/📄/👁️ → radio/wallet/doc/eye SVG`. Takedown role pills (`👑/🌉/💳` line 903-905): text-only `Leaders / Bridges / Mules` (rank conveyed by position, not crown emoji).
- Geo cards (`🗼/🔥/🚶`): small SVG or none — card titles carry meaning.
- JS-injected emoji (`⚠️ SIMULATION ONLY`, `💳/📄/👁️/📱/📍` legends lines 2178-2741, `◉/◆/○/✓` step glyphs): replace with CSS badges (`.badge-warn`) and text (`SIMULATION ONLY`, `Trail: CDR`).
- Rule: no emoji in buttons/nav/H2 after refactor. Emoji allowed nowhere in chrome; data-driven content (station names) untouched.

## 4. Global chrome changes

- Sidebar: flat bg, `h1` becomes two lines — `CNAS` wordmark (12px/800) + `Case <id> · <classification>` (11px mono muted, bound to `#casePill` text instead of a floating pill). Nav buttons: 6px radius, active = flat accent fill + 2px left bar (no gradient/glow/translateX).
- View headers: wrap each `h2 + p.sub + actions` in `.view-head > .toolbar`. Delete duplicated brand H2 on login vs dashboard (login keeps brand; dashboard H2 becomes case-aware `Active investigations`).
- Classification/disclaimer `p.sub` stays verbatim but styled `12px muted`, never accent-colored.

## 5. Card-culling map (59 → ~32)

Merge/delete, per static HTML lines:
- Evidence (731/735/739 → 1 `.stat-strip` with 3 `.stat`s). Table card (745) stays, search + filters become `.toolbar`.
- Blockchain (776/780/784/791 → 1 `.stat-strip` with 4 `.stat`s). Verifier (801) + Certificate (820) stay as 2-col grid. Blocks explorer (838) stays.
- Takedown KPIs (939/944/949/954 `td-kpi-card` → 1 `.stat-strip`). Strategy grid, manifest, SWAT stay (real density, not sprawl).
- Geospatial: control bar (655) stays as `.toolbar` (not card), map card (688) → `.frame`, 3 analytics cards (694/704/714) stay but 3-col grid.
- Dashboard (348/352) + Investigations (384/406): deduplicate — one `create-case` partial, dashboard keeps list-first, investigations keeps form-first. Delete third copy in `view-new` or route `view-new` → investigations.
- Timeline (586/597/601/605): merge `Key dates + Unusual periods + All flagged` into one card with 3 tabbed sections; playback card stays separate.
- Financial (614/618), Comms (627/631): keep 2 cards each (genuinely different data) but differentiate: story card flat, table card with row dividers + sticky `th`.
- Overview (464/469/473/477/490): keep 5 but de-uniform: Summary = definition table (no card tint), Findings = numbered list (no bullets-in-card), Leads = rows (not cards), Recommendations = 3-col compact, Graph = `.frame` + left rail.
- Person (547/551/561/573/577): same treatment as Overview.
- Processing (458): keep single status card, replace `○/✓` emoji steps with CSS step list.

## 6. Per-view build spec (HTML lines)

1. Login 308-339: center column 440px, flat card, SVG moon toggle, no radial bg.
2. Dashboard 341-374: `.view-head` + stat-strip (active cases, entities, last run) + list card + create-case partial.
3. Investigations 376-413: form-first, same partial, recent list with delete affordance (existing `canDelete` logic untouched).
4. Overview 461-522: summary table → `<dl>` rows; leads → `.lead` rows with right-aligned threat; graph filters → compact rail; canvas → `.frame`.
5. People/Person 524-581: search toolbar single row; mugshot 72px 8px radius (was 10px); hop toggle segmented (not two primaries).
6. Timeline 583-609: playback controls segmented + range full-width; burst banner static amber left-border (no pulse).
7. Financial/Comms: amounts right-aligned tabular-nums; pairs/towers toggle segmented.
8. Geospatial 643-724: toolbar (suspect select + layer checkboxes + day scrub) un-carded; map `.frame` 540px; 3 lists with sticky mini-headers.
9. Evidence 726-760: stat-strip + toolbar + dense table (`td` 8px 10px, sticky `th`, mono IDs 11px).
10. Blockchain 762-847: stat-strip + 2-col tools + blocks as ledger rows (mono hash, prev-hash link, expand).
11. Takedown 849-1019: keep HUD pill (drop 🎯 emoji, keep text `TACTICAL HUD // MHA-NCRB`); strategy cards flat 8px with 2px top accent when active (no gradient); KPI strip; SWAT 3-box flat tints (keep red/blue/amber semantics, flatten to 6% tint + 1px border).
12. Reports 1021-1034: toolbar + paper-style preview (white, serif headings, 720px measure) — only view allowed a document voice.
13. Drawer/modals 1036-1180: drawer 400px flat; modal-card 8px flat + 1 shadow; tabs underline-style (not pill buttons).

## 7. Responsive (add 2 breakpoints, keep existing 3)

- Keep `@1150/800/650`. Add `@1100px`: `.view` full-width, overview/person 2-col → 1-col, geo analytics 3 → 1. Add `@700px`: stat-strip wrap 2→1, toolbar horizontal scroll, sidebar topbar (already row-wraps at 800 — tighten to full-width bar with horizontal nav scroll).
- Canvases: `#leafletMap 540px → clamp(360px,50vh,540px)`; `#mainGraph3D 500px → clamp(320px,45vh,500px)`; `#personCanvasContainer` same.

## 8. Phased build (all in `frontend/index.html`)

- Phase 0 — safety: `cp frontend/index.html /tmp/index.html.bak`, screenshot each view light+dark (baseline).
- Phase 1 — tokens: `:root` + dark overrides + radius/shadow/gradient deletions (§2). Verify: no layout shift, only flatter.
- Phase 2 — primitives: add `.stat-strip/.stat/.frame/.toolbar/.view-head/.badge` CSS, no HTML yet. Verify: stylesheet parses, unused classes harmless.
- Phase 3 — chrome: sidebar + view-head wraps + masthead second line. Verify: nav active states, hash routing intact.
- Phase 4 — card cull (§5) + per-view HTML (§6), highest-traffic first: Evidence → Blockchain → Overview → Person → Geospatial → Takedown → Timeline/Financial/Comms → Dashboard/Investigations → Reports.
- Phase 5 — icons: SVG sprite + button/nav/filter swaps + JS legend/step glyph replacement. Grep `[\U0001F300-\U0001FAFF]` must return 0 in chrome (data strings exempt).
- Phase 6 — responsive + polish: new breakpoints, tabular-nums, focus states (`:focus-visible` 2px accent outline), `prefers-reduced-motion` disables pulse/translate.

## 9. Verification per phase

- `python3 -m http.server` + click-through: login → dashboard → investigations → overview (3D renders) → person → timeline play → geospatial (Leaflet tiles) → evidence filter → blockchain verify → takedown simulate → OP-ORDER modal → reports PDF export.
- `rg 'linear-gradient|radial-gradient' frontend/index.html` → only 1 CTA hit. `rg 'border-radius: (14|12)px'` → 0. `rg '📍|⛓|🎯|📋|⚡|▶|🔄|💡|🗼|🔥|🚶'` in chrome → 0.
- Backend untouched: `git status` shows only `frontend/index.html` (+ this plan). `python3 -m pytest tests/ -q` still green (no API changes to break).
- A11y spot-checks: contrast ≥4.5 body, focus visible, tables keep `<th scope>`, sliders keep labels.

## 10. Risks / rollback

- Single-file blast radius: mitigate with `/tmp` backup + atomic per-phase commits.
- 3D/Leaflet fixed-height assumptions: clamp() keeps JS sizing calls valid (no JS edits needed).
- Emoji-in-JS strings: sed carefully — only chrome strings, never evidentiary text. Rollback = restore backup + revert one phase commit.
