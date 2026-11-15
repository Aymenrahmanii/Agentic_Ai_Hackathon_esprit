# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Investors looking for industrial land in Tunisia, using the assistant alone on a laptop:

- local founders of small and medium businesses, who think and speak in Tunisian Derja;
- Tunisian diaspora and foreign investors comparing regions, in French, Arabic or English.

Their job: find an available industrial lot that fits their activity, area and budget,
understand the procedure and documents, and submit a reservation request, then follow it.
The interface is also shown to a hackathon jury (AFI and IHEC Carthage), but it is designed
for the investor at a laptop first.

## Product Purpose

A conversational front door to the industrial land services of AFI (Agence Foncière
Industrielle, Tunisia). The investor asks in their own language; the agent searches lots,
compares zones, explains procedures, prepares a request draft, tracks requests and hands over
to a human. Success: an investor goes from a question to a submitted request in one
conversation, and every fact they see comes from AFI's data.

## Positioning

It speaks Tunisian Derja in both Arabic script and Latin-script Arabizi, as well as French,
Arabic and English, and it shows its work: each answer lists the lookups it made. It cannot
submit anything on the investor's behalf; only the investor's Confirm button does.

## Operating Context

- A single conversation drives everything; the map, the plots and the request draft respond
  to what the agent found.
- Industrial zones belong to governorates; lots belong to zones and have an area (m²), a price
  per m² and a status: available, reserved or sold.
- Procedures: reserving a lot, joining an auction; each has steps and required documents.
- A request goes draft → confirmed by the investor → tracking number.
- Voice input and read-aloud exist; Derja speech models are not chosen yet, so the browser's
  own voice is a placeholder.

## Capabilities and Constraints

- Static HTML, CSS and JavaScript served by the FastAPI app (`src/afi_agent/web/`), no build
  step. Map with Leaflet and OpenStreetMap tiles; fonts from Google Fonts.
- Must work with the offline demo mode (`AFI_PROVIDER=replay`).
- Interface labels in French and Arabic, with a toggle; Arabic switches the layout to
  right-to-left. The conversation follows whatever language the user writes or speaks.
- Undecided: the product's own name.

## Brand Commitments

An independent student prototype built for the AFI hackathon (28–29 November 2026). It must
not use AFI's logo or present itself as an official AFI service.

## Evidence on Hand

- `data/seed.json`: invented placeholder zones, lots, prices and procedures. The interface
  must say the data is invented until real AFI data replaces it.
- `docs/demo/`: recorded real conversations and evaluation results.
- No real users, testimonials, partners or AFI endorsement exist; none may be implied.

## Product Principles

1. Every fact on screen comes from a lookup the investor can see.
2. The investor stays in control: the agent prepares, the investor submits.
3. The investor's language is respected, including Derja in both scripts.
4. Honest about limits: invented data, placeholder voice and offline mode are labelled.

## Accessibility & Inclusion

Arabic and Latin scripts side by side, right-to-left layout in Arabic, usable by keyboard,
readable on a laptop at normal viewing distance.
