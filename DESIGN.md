---
name: Assistant foncier
description: A land request kept as a coupon book; lots are coupons, the request is a carbon copy, confirming stamps it.
colors:
  carrier-navy: "#0d1b3d"
  carrier-navy-2: "#1a2b55"
  navy-ink: "#c9d3ea"
  jet-red: "#d7262d"
  jet-red-ink: "#b31d23"
  coupon-white: "#ffffff"
  stock: "#f2f2f0"
  stock-2: "#e6e6e2"
  ink: "#141a2b"
  ink-2: "#4a5268"
  rule: "#c9ccd4"
  carbon-purple: "#4b2e83"
  carbon-wash: "#f6f2fc"
  carbon-copy: "#ddd2f2"
  carbon-copy-2: "#cbbbe8"
  status-green: "#1f7a4a"
  demo-amber: "#8a5a00"
  demo-amber-bg: "#fff1cf"
typography:
  display:
    fontFamily: "Barlow Condensed, Changa, Arial Narrow, system-ui, sans-serif"
    fontSize: "4.5rem"
    fontWeight: 700
    lineHeight: 0.8
    letterSpacing: "0.02em"
  headline:
    fontFamily: "Barlow Condensed, Changa, Arial Narrow, system-ui, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "0.02em"
  title:
    fontFamily: "Barlow Condensed, Changa, Arial Narrow, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.06em"
  body:
    fontFamily: "Tajawal, Segoe UI, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Barlow Condensed, Changa, Arial Narrow, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "0.1em"
  numeral:
    fontFamily: "Red Hat Mono, ui-monospace, Cascadia Mono, monospace"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.3
    fontFeature: "tnum"
rounded:
  plot: "1px"
  sm: "3px"
  stamp: "6px"
  pill: "50%"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "24px"
components:
  button-confirm:
    backgroundColor: "{colors.jet-red}"
    textColor: "{colors.coupon-white}"
    typography: "{typography.title}"
    rounded: "{rounded.sm}"
    padding: "13px 16px"
  button-confirm-hover:
    backgroundColor: "{colors.jet-red-ink}"
  button-send:
    backgroundColor: "{colors.carrier-navy}"
    textColor: "{colors.coupon-white}"
    rounded: "{rounded.sm}"
    padding: "0 16px"
    height: "38px"
  button-send-hover:
    backgroundColor: "{colors.carrier-navy-2}"
  button-coupon-action:
    backgroundColor: "{colors.coupon-white}"
    textColor: "{colors.carrier-navy}"
    rounded: "{rounded.sm}"
    padding: "7px 12px"
  button-coupon-action-hover:
    backgroundColor: "{colors.carrier-navy}"
    textColor: "{colors.coupon-white}"
  button-icon:
    backgroundColor: "{colors.coupon-white}"
    textColor: "{colors.carrier-navy}"
    rounded: "{rounded.pill}"
    size: "38px"
  chip-demo:
    backgroundColor: "{colors.demo-amber-bg}"
    textColor: "{colors.demo-amber}"
    rounded: "{rounded.sm}"
    padding: "3px 10px"
  chip-model:
    backgroundColor: "{colors.carrier-navy-2}"
    textColor: "{colors.navy-ink}"
    rounded: "{rounded.sm}"
    padding: "3px 10px"
  coupon:
    backgroundColor: "{colors.coupon-white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
  carbon-copy:
    backgroundColor: "{colors.carbon-copy}"
    textColor: "{colors.carbon-purple}"
    rounded: "{rounded.sm}"
  composer-field:
    backgroundColor: "{colors.coupon-white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "6px 6px 6px 12px"
---

# Design System: Assistant foncier

## Overview

**Creative North Star: "The Ticket Wallet"**

A land request is kept the way a jet-age carrier kept a journey: in a wallet of printed coupons. Each lot the agent finds is a coupon with a serial block, a zone code set huge in condensed caps, and tabbed figure cells filled in by the system in carbon purple. The request is a lavender carbon copy with a perforated stub; confirming presses a bilingual rubber stamp onto it and the stub tears away to show the tracking number. The shell is carrier navy with a jet-red rule; everything inside sits on pale stock paper.

The interface is dense and operational: three working panes at once, every figure in a monospace numeral, every label in tight airline caps. Depth comes from ruled edges and tabbed heads, not from shadow. Colour carries meaning, not decoration: navy is the carrier's voice, purple is whatever the system filled in, red is the one act only the investor can perform, green/purple/red repeat as lot status.

Arabic is a first-class reading of the same wallet, not a mirror afterthought: the caps stack falls through to Changa for Arabic glyphs, letter-spacing drops to zero, tabs and punched corners flip with `dir="rtl"`, and the stamp is bilingual.

**Key Characteristics:**
- Carrier navy shell with a 4px jet-red rule under the top bar.
- Coupons: white, 1.5px navy rule, punched half-circles at mid-height, 72px zone code.
- Tabbed field heads: a small caps tab sits on top of a ruled cell, sharing its border.
- Carbon purple for every system-filled figure, lavender for the draft copy.
- Ink-speckled rubber stamps for states (VENDU, RÉSERVÉ, CONFIRMÉE / مؤكّدة).
- Flat colour; edges are ruled, not shadowed.

## Colors

A printed-ephemera palette: one dark carrier colour, one alarm red held back for commitment, one carbon purple for filled-in values, on near-white stock.

### Primary
- **Carrier Navy** (carrier-navy): the shell (top bar), pane titles, coupon and slip rules, the send button, zone-plan track, map frame. The voice of the carrier.
- **Carrier Navy Raised** (carrier-navy-2): hover on navy buttons, the model chip on the top bar.
- **Navy Ink** (navy-ink): secondary text and outlines on navy (sub-brand line, language switch border).

### Secondary
- **Jet Red** (jet-red): the Confirm button, the top-bar rule, the `///` mark before pane titles, rubber stamps, sold status, the selected coupon's rule, the active map label, the live mic.
- **Jet Red Ink** (jet-red-ink): Confirm hover, blocked-lookup and error text where red must hold on white.

### Tertiary
- **Carbon Purple** (carbon-purple): every value the system writes in: coupon figures, lookup tabs and rows, the investor's own question slip, reserved status, the carbon copy's text and rules, the thinking dots.
- **Carbon Wash** (carbon-wash): fill behind carbon-ruled rows (the investor's slip, lookup rows).
- **Carbon Copy** (carbon-copy) and **Carbon Copy Deep** (carbon-copy-2): the request draft paper, and its dashed empty outline / text selection.

### Neutral
- **Coupon White** (coupon-white): coupons, the agent's answer slip, inputs, tab backgrounds.
- **Stock** (stock): page and pane ground; also the fill of punched holes so they read as cut through.
- **Stock Deep** (stock-2): placeholder bars in the ghost coupon.
- **Ink** (ink) and **Ink Muted** (ink-2): prose and secondary prose.
- **Rule** (rule): hairline pane dividers, quiet borders, dashed ghost outlines, scrollbar thumb.

### Status
- **Status Green** (status-green): available lots (status tab, plan plots).
- **Demo Amber** (demo-amber on demo-amber-bg): the demo-data chip and notice, the fallback model state. Used only to say the data is invented or the model is a fallback.

### Named Rules
**The One Commitment Rule.** Jet red fills exactly one button on screen: Confirm. Elsewhere red is a rule, a mark, a stamp or a status, never a second filled call to action.

**The Carbon Rule.** Anything the system filled in (figures, lookups, the draft) is carbon purple; anything printed by the carrier (labels, codes, frames) is navy. If you cannot say who wrote a value, you have not decided its colour.

## Typography

**Caps Font:** Barlow Condensed (Latin), with Changa supplying Arabic glyphs in the same stack, then Arial Narrow
**Body Font:** Tajawal (with Segoe UI, system-ui)
**Numeral Font:** Red Hat Mono (with ui-monospace, Cascadia Mono)

**Character:** Airline caps for anything printed on the ticket, a quiet bilingual grotesk for what people say, and a carbon monospace for every number. Body uses tabular numerals throughout.

### Hierarchy
- **Display** (700, 4.5rem, line-height 0.8): the zone code on a coupon (KAI). 3rem under 760px. Nowhere else.
- **Headline** (700, 1.75rem, uppercase): the brand name in the top bar.
- **Title** (600, 1.25rem, 0.06em, uppercase): pane titles, led by a jet-red `///`.
- **Body** (400, 1rem, 1.5): conversation and prose; welcome lead at 1.25rem capped at 46ch. Arabic body steps up to 1.0625rem with 1.75 line-height in answers.
- **Label** (600, 0.75rem or 0.6875rem, 0.1em, uppercase): slip tabs, figure tabs, coupon heads, copy field labels.
- **Numeral** (Red Hat Mono 600, 1rem in coupon cells, 1.25rem in copy fields, 2.25rem for the tracking number): serials, areas, prices, tool calls, counts.

### Named Rules
**The Zero-Tracking Arabic Rule.** Every letter-spaced caps style resets to `letter-spacing: 0` under `dir="rtl"`; Arabic is never tracked.

**The Numerals Are Carbon Rule.** Figures, serials and codes always set in Red Hat Mono; prose never does.

## Layout

A fixed-height three-pane workspace under the top bar: conversation, lots, request + map, at `38fr / 34fr / 28fr` with minimums of 360 / 320 / 300px, divided by 1px rule hairlines (logical `border-inline-end`, so the order flips in RTL). Each pane scrolls on its own; the composer is pinned at the foot of the conversation. Pane gutters are 24px; internal rhythm runs on 8 / 12 / 16 / 24px.

Below 1100px the grid becomes two columns with the conversation spanning both rows. Below 760px panes stack, the page scrolls instead of the panes, gutters drop to 16px, the send button collapses to a 38px icon, and the demo chip hides in favour of the amber notice under the bar.

The zone plan draws plots to scale on a navy track (44px high), one row per zone, with matched plots at full opacity.

## Elevation & Depth

Flat. Depth is printed, not lit: 1.5px navy rules frame coupons, slips, the composer and the map; tabs sit on their cells by overlapping the border by its own width; dashed rules mark tear lines and empty states; punched half-circles in stock colour cut the coupon and the perforation. There is no resting box-shadow anywhere.

The only shadows are state signals: a 2px inset white ring on a matched plan plot, and a soft red pulse ring on the mic while listening.

### Named Rules
**The Ruled-Not-Shadowed Rule.** Separate surfaces with a rule, a tab or a perforation; never with a drop shadow.

## Shapes

Nearly square corners (3px) on everything rectangular. Tabs round only their top corners; the cell beneath squares the corner the tab sits on (flipped in RTL). Coupons carry two 14px punched half-circles at mid-height; the carbon copy's perforation is a 2px dashed carbon line ending in 16px half-circles. Stamps are the only tilted shapes (-9deg on coupons, -11deg on the copy), with a speckled ink mask (fractal-noise alpha mask, `--ink-mask`) and multiply blending. Round shapes are reserved for icon buttons, status dots and punch holes.

## Components

### Buttons
- **Shape:** 3px corners, condensed caps, 0.06–0.08em tracking.
- **Confirm:** jet red fill, white caps, full width of the stub, 13px 16px; hover darkens to jet-red-ink. The single filled red button.
- **Send:** navy fill, white caps with an arrow icon, 38px tall; hover to navy-raised. Icon-only under 760px.
- **Coupon action (Réserver):** white with 1.5px navy rule; hover inverts to navy fill.
- **Icon button (mic):** 38px circle, rule border, navy icon; while listening it fills jet red with a pulse ring.
- **Focus:** 2px navy outline at 2px offset (white on the top bar).

### Chips
- **Demo:** amber text on amber wash, caps, 3px corners.
- **Model status:** navy-raised fill, mono text, green dot when live, amber when fallback, navy-ink dot when offline.
- **Language switch:** outlined segmented pair (FR / ع); the pressed side fills white with navy text. Switching to ع sets `dir="rtl"`.

### Conversation slips
- **Investor:** right-aligned slip, 1.5px carbon rule on carbon wash, tab reading the speaker in carbon caps.
- **Agent:** full-width white slip with a navy rule and navy tab. Its foot carries a dashed-ruled lookups strip: a caps toggle with mono meta, opening one tabbed carbon row per tool call (result line, mono call). Blocked lookups turn jet-red-ink on a pale red wash.
- **Thinking:** three carbon dots blinking.

### Inputs / Fields
- **Composer:** white field, 1.5px navy rule, 3px corners; focus-within shifts the rule to carbon purple. Selects use a 1px rule border.

### Lot Coupon (signature)
White coupon with 1.5px navy rule and punched sides. Head strip: navy serial block (mono), zone name in navy caps, status tab filled green / carbon / red. Body: 72px zone code beside the place name, then three tabbed figure cells (surface, price, price per m²) with carbon mono values. Foot: sectors line and the coupon action. Sold and reserved coupons carry a tilted rubber stamp. Selecting a coupon lifts it 2px, turns its rule red and dims the others to 0.45. The empty state is a dashed ghost coupon.

### Carbon-Copy Request (signature)
Lavender carbon-copy paper with a 1.5px carbon rule: head (caps title, mono serial), a two-column list of carbon fields (caps label, 1.25rem mono value), a perforation, then the stub with the note and Confirm. On confirm the paper deepens, fields collapse to one column to clear space, a double-ruled bilingual stamp (CONFIRMÉE / مؤكّدة, with date) presses in, and the stub tears down along the perforation, showing the 2.25rem mono tracking number.

### Map
Leaflet with tiles tinted toward navy (grayscale, sepia, hue-rotate), framed by a 1.5px navy rule. Zone labels are navy-ruled caps tags, jet red when active. Zoom controls are navy-ruled, shadowless, in caps.

### Motion
One easing, `cubic-bezier(0.16, 1, 0.3, 1)`. Coupons deal in only when a search returns (420ms rise, 60ms stagger); the copy arrives with an upward clip reveal (480ms); the stamp presses (420ms) and the stub tears (620ms after 380ms). Hover transitions run 160ms. Re-renders such as a language switch show the settled state without replaying. Under `prefers-reduced-motion` all animation and transition is off.

## Do's and Don'ts

### Do:
- **Do** frame every surface with a ruled edge (1.5px navy for coupons and slips, 1px rule hairline for dividers) and keep corners at 3px.
- **Do** set every system-filled number in Red Hat Mono, carbon purple.
- **Do** head fields with a tab that shares the cell's border, and flip the squared corner in RTL.
- **Do** reserve the filled jet-red button for the one action only the investor can take.
- **Do** drop letter-spacing to 0 on caps styles under `dir="rtl"`.
- **Do** play motion once, on new data only, and never on re-render.

### Don't:
- **Don't** add drop shadows or gradients to surfaces; the only patterned fill is the hatched sold plot, the only shadows are the matched-plot ring and the listening pulse.
- **Don't** add a second filled red button beside Confirm.
- **Don't** use carbon purple for carrier-printed labels or navy for system-filled values.
- **Don't** use rounded cards or chat bubbles; turns are ruled slips with tabs.
- **Don't** present the product as an official AFI service or use AFI's logo; keep the amber demo-data notice wherever data is invented.
