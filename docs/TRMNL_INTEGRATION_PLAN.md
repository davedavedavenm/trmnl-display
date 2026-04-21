# TRMNL BYOS Integration & Migration Plan

## Overview
This plan outlines the transition from Inky Impression 7.3's Python/Playwright architecture to a TRMNL-compatible "Bring Your Own Server" (BYOS) system. This aims to leverage TRMNL's optimized Go-based client, 4-level grayscale support, and zero-flicker refresh technology while maintaining local control.

## 1. Hardware & Driver Verification
- **Goal:** Confirm the exact Waveshare e-paper model for driver compatibility.
- **Tasks:**
  - Inspect src/display/waveshare_display.py and local config.
  - Verify SPI pin mapping between Inky Impression 7.3's current setup and 	rmnl-display requirements.
  - Confirm support for TRMNL's "Zero-Flicker" LUT (Lookup Table) hacking.

## 2. Environment Preparation
- **Goal:** Ensure a clean slate for TRMNL services without resource contention.
- **Tasks:**
  - Create a systemctl stop script for the Inky Impression 7.3 service.
  - Install Go 1.24+ runtime on the Raspberry Pi for the 	rmnl-display client.
  - Install Docker (if not present) for the official TRMNL BYOS server (Terminus).

## 3. Local Server Deployment (BYOS)
- **Goal:** Run a self-hosted TRMNL backend on the same Raspberry Pi.
- **Options:**
  - **Option A: Terminus (Official)**: Use the Ruby-based flagship server (recommended for stability).
  - **Option B: BYOS Fast API**: Use the Python-based implementation for easier integration with existing Inky Impression 7.3 logic.
- **Configuration:** Set ase_url to http://localhost:8000 or similar for local loopback.

## 4. Client Installation (	rmnl-display)
- **Goal:** Deploy the lightweight Go client.
- **Tasks:**
  - Clone usetrmnl/trmnl-display.
  - Build the client for the correct display (framebuffer, Waveshare, or Inky Impression).
  - Configure ~/.config/trmnl/config.json with a local API Key and BYOD Device ID.

## 5. Plugin & Recipe Migration
- **Goal:** Transition existing Inky Impression 7.3 functionality to the TRMNL ecosystem.
- **Tasks:**
  - Audit existing Inky Impression 7.3 plugins (Weather, Calendar, etc.) against the 850+ existing TRMNL Recipes.
  - Implement any missing Inky Impression 7.3 logic as TRMNL "Private Plugins" or "Third Party" renderers.
  - Leverage TRMNL's HTML/CSS framework for better e-ink visuals (Tailor).

## 6. Evaluation & Validation
- **Performance:** Benchmark CPU/RAM usage of 	rmnl-display vs. Inky Impression 7.3.
- **Quality:** Validate 4-level grayscale and zero-flicker refresh performance.
- **Reliability:** Stress-test the background refresh cycle using the TRMNL playlist manager.
