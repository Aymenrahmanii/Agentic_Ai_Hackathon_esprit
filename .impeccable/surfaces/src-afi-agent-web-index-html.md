---
version: 1
slug: "src-afi-agent-web-index-html"
primary_target: "src/afi_agent/web/index.html"
related_targets: ["src/afi_agent/web/styles.css","src/afi_agent/web/app.js"]
---

# Surface brief: land assistant workspace

Scope: the single-page web interface in `src/afi_agent/web/` (index.html, styles.css, app.js).
Mode: Operate. An investor at a laptop completes a task: find a lot, understand it, prepare
and confirm a request, and see what the agent looked up.

Audience and job: Tunisian investors (local founders speaking Derja, diaspora and foreign
investors in French, Arabic or English) searching for industrial land and reserving a lot.
Proof on screen: every fact comes from a lookup shown beside the answer. Constraints:
static files, no build step, French and Arabic interface with an RTL toggle, offline replay
mode must keep working, data labelled as invented.

Chosen direction: Ticket wallet (catalog challenger `vernacular-ephemera-jet-age-ticket-wallet`,
chosen by the user over the rolled direction).

## Direction contract

THESIS: A land request is a coupon book. Each lot the agent finds is a coupon, the request is a
carbon copy, and confirming stamps it. This refuses the category default of a grey chat panel
beside a map with one blue accent and identical rounded cards.

OWN-WORLD: Carrier navy #0D1B3D shell, jet red #D7262D for the one primary action and the
stamp, coupon white #FFFFFF on stock #F2F2F0, carbon purple #4B2E83 for every figure the system
fills in, lavender carbon copy #D9CCF0 for the draft. Condensed airline caps for labels and
codes (Changa, Latin and Arabic), a quiet grotesk for prose (Tajawal), carbon numerals in a
monospace (Red Hat Mono). Tabbed field heads, hairline-ruled boxes, square-cornered coupons with
punched corners, rubber-stamp states (VENDU, CONFIRMÉE). Flat colour, no gradients or shadows
beyond a 2px offset ink edge on coupons.

STORY: The investor asks in their own words, sees the agent's lookups under the answer, reads
the matching lots as coupons they can compare at a glance (zone code, area, price, status),
picks one, sees the request appear as a carbon copy, and confirms it; the stamp and tracking
number tell them it is done and that only they could do it.

FIRST VIEWPORT: Navy top bar: product mark and bilingual name left; FR/ع language toggle,
model status chip and an amber "demo data" chip right. Three work areas below at 1280–1600:
conversation (38%) with the composer and mic pinned at its foot and each answer carrying a
tabbed "lookups" strip; lots (34%) with the zone plan drawn to scale above a stack of lot
coupons, each led by a 64px zone code like KAI; request and map (28%) with the zone map on top
and the carbon-copy request stub below, Confirm in jet red on the stub. Empty states invite the
first question with example coupons.

FORM: Ticket wallet, a dealt catalog challenger (not on my ordered list; the roll assigned my
candidate 6, Tunisian banknotes and stamps, and the user chose this alternate). Seed key
03429142. Signature move: confirming presses a bilingual CONFIRMÉE / مؤكّدة stamp onto the
carbon copy, which then tears along its perforation to reveal the tracking number. Motion
grammar: coupons deal in once when results arrive (staggered 60ms), selection lifts one coupon
and dims the rest, the stamp presses once; all motion off under reduced motion.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Unresolved

- The product's own name (using "Assistant foncier" / "المساعد العقاري" as a working name).
- Derja speech models (browser voice is a labelled placeholder).
