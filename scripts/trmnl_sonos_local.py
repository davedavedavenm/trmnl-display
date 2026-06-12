#!/usr/bin/env python3
import os
import datetime
import json
import base64
import sys
import requests
from io import BytesIO
from PIL import Image, ImageEnhance, ImageOps
from dotenv import load_dotenv

# Load env files
load_dotenv()
load_dotenv(os.getenv("TRMNL_SONOS_ENV", "/home/dave/.env.sonos-trmnl"))
load_dotenv("/home/dave/.env")

WEBHOOK_URL = os.getenv("TRMNL_WEBHOOK_URL", "").strip()
PREFERRED_ROOM = os.getenv("TRMNL_SONOS_ROOM", "").strip()
UPDATED_AT_FORMAT = os.getenv("TRMNL_UPDATED_AT_FORMAT", "%d %b %H:%M")

ALBUM_ART_SATURATION = float(os.getenv("TRMNL_ALBUM_ART_SATURATION", "0.65"))
ALBUM_ART_CONTRAST = float(os.getenv("TRMNL_ALBUM_ART_CONTRAST", "1.1"))
ALBUM_ART_BALANCED_SATURATION = float(os.getenv("TRMNL_ALBUM_ART_BALANCED_SATURATION", "0.9"))
ALBUM_ART_BALANCED_CONTRAST = float(os.getenv("TRMNL_ALBUM_ART_BALANCED_CONTRAST", "1.05"))
ALBUM_ART_VIVID_SATURATION = float(os.getenv("TRMNL_ALBUM_ART_VIVID_SATURATION", "1.2"))
ALBUM_ART_VIVID_CONTRAST = float(os.getenv("TRMNL_ALBUM_ART_VIVID_CONTRAST", "1.0"))
ALBUM_ART_MONO_SATURATION = float(os.getenv("TRMNL_ALBUM_ART_MONO_SATURATION", "0.0"))
ALBUM_ART_MONO_CONTRAST = float(os.getenv("TRMNL_ALBUM_ART_MONO_CONTRAST", "1.1"))

HA_URL = os.getenv("HA_URL", "http://192.168.1.89:8123").strip()
HA_TOKEN = os.getenv("HA_TOKEN", "").strip()
sonos_entities = [e.strip() for e in os.getenv("TRMNL_SONOS_ENTITIES", "media_player.living_room,media_player.bedroom,media_player.kitchen,media_player.gym,media_player.sonos_roam").split(",") if e.strip()]

def build_processed_album_art_data_uri(url: str, saturation: float, contrast: float) -> str:
    if not url:
        return ""
    try:
        fetch_url = url
        headers = {}
        if url.startswith("/"):
            fetch_url = HA_URL + url
            headers = {"Authorization": f"Bearer {HA_TOKEN}"}
        
        response = requests.get(fetch_url, headers=headers, timeout=15)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert("RGB")
        img = ImageOps.exif_transpose(img)
        img = ImageEnhance.Color(img).enhance(saturation)
        img = ImageEnhance.Contrast(img).enhance(contrast)
        out = BytesIO()
        img.save(out, format="PNG")
        return "data:image/png;base64," + base64.b64encode(out.getvalue()).decode("ascii")
    except Exception as e:
        print(f"Error processing album art: {e}", file=sys.stderr)
        return ""

def build_album_art_variants(url: str) -> dict:
    return {
        "default": build_processed_album_art_data_uri(url, ALBUM_ART_SATURATION, ALBUM_ART_CONTRAST),
        "balanced": build_processed_album_art_data_uri(
            url, ALBUM_ART_BALANCED_SATURATION, ALBUM_ART_BALANCED_CONTRAST
        ),
        "vivid": build_processed_album_art_data_uri(
            url, ALBUM_ART_VIVID_SATURATION, ALBUM_ART_VIVID_CONTRAST
        ),
        "mono": build_processed_album_art_data_uri(url, ALBUM_ART_MONO_SATURATION, ALBUM_ART_MONO_CONTRAST),
    }

def main():
    if not WEBHOOK_URL:
        raise RuntimeError("TRMNL_WEBHOOK_URL is required")
    if not HA_TOKEN:
        raise RuntimeError("HA_TOKEN is required")
        
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Fetch states
    response = requests.get(f"{HA_URL}/api/states", headers=headers, timeout=10)
    response.raise_for_status()
    states_list = response.json()
    states_map = {item["entity_id"]: item for item in states_list}
    
    sonos_players = []
    for entity_id in sonos_entities:
        if entity_id in states_map:
            sonos_players.append(states_map[entity_id])
            
    # Selection logic:
    # 1. Filter playing players
    playing_players = [p for p in sonos_players if p.get("state") == "playing"]
    # 2. Filter playing players that have track metadata (media_title)
    active_playing = [p for p in playing_players if p.get("attributes", {}).get("media_title")]
    
    selected_player = None
    if active_playing:
        # If a preferred room is active, choose it. Otherwise choose the first active playing one.
        if PREFERRED_ROOM:
            for p in active_playing:
                friendly_name = p.get("attributes", {}).get("friendly_name", "")
                if PREFERRED_ROOM.lower() in friendly_name.lower() or PREFERRED_ROOM.lower() in p["entity_id"].lower():
                    selected_player = p
                    break
        if not selected_player:
            selected_player = active_playing[0]
    elif playing_players:
        # Stale state playing fallback
        selected_player = playing_players[0]
    else:
        # Fallback when none are playing
        if PREFERRED_ROOM:
            for p in sonos_players:
                friendly_name = p.get("attributes", {}).get("friendly_name", "")
                if PREFERRED_ROOM.lower() in friendly_name.lower() or PREFERRED_ROOM.lower() in p["entity_id"].lower():
                    selected_player = p
                    break
        if not selected_player and sonos_players:
            selected_player = sonos_players[0]
            
    if selected_player:
        entity_id = selected_player["entity_id"]
        state = selected_player["state"]
        attrs = selected_player.get("attributes", {})
        room_name = attrs.get("friendly_name", entity_id.split(".")[1].replace("_", " ").title())
        
        title = attrs.get("media_title", "")
        artist = attrs.get("media_artist", "")
        
        # If state is playing but it has no metadata (like stuck Sonos Roam), map to STOPPED
        if state == "playing" and not title:
            state = "stopped"
            title = "Nothing Playing"
            artist = "Unknown Artist"
            
        if not title:
            title = "Nothing Playing"
        if not artist:
            artist = "Unknown Artist"
            
        album = attrs.get("media_album_name", "")
        raw_album_art_url = attrs.get("entity_picture", "")
        
        group_members_entities = attrs.get("group_members", [entity_id])
        group_rooms = []
        for g_entity in group_members_entities:
            if g_entity in states_map:
                g_friendly = states_map[g_entity].get("attributes", {}).get("friendly_name", g_entity.split(".")[1].replace("_", " ").title())
                group_rooms.append(g_friendly)
            else:
                group_rooms.append(g_entity.split(".")[1].replace("_", " ").title())
                
        group_size = len(group_rooms)
        source = attrs.get("app_name") or attrs.get("source") or ""
        
        active_groups_count = len(active_playing)
        multiple_active = active_groups_count > 1
        
        other_active_rooms = []
        selected_content_id = attrs.get("media_content_id", "")
        same_content_rooms = []
        
        for p in active_playing:
            if p["entity_id"] == entity_id:
                continue
            p_attrs = p.get("attributes", {})
            p_friendly = p_attrs.get("friendly_name", p["entity_id"].split(".")[1].replace("_", " ").title())
            other_active_rooms.append(p_friendly)
            
            if selected_content_id and p_attrs.get("media_content_id") == selected_content_id:
                same_content_rooms.append(p_friendly)
    else:
        state = "stopped"
        room_name = "Unknown Room"
        title = "Nothing Playing"
        artist = "Unknown Artist"
        album = ""
        raw_album_art_url = ""
        group_rooms = []
        group_size = 0
        source = ""
        multiple_active = False
        other_active_rooms = []
        same_content_rooms = []
        
    album_art_variants = build_album_art_variants(raw_album_art_url)
    
    payload = {
        "merge_variables": {
            "updated_at": datetime.datetime.now().strftime(UPDATED_AT_FORMAT),
            "room_name": room_name,
            "group_rooms": group_rooms,
            "group_size": group_size,
            "state": state.upper(),
            "title": title,
            "artist": artist,
            "album": album,
            "album_art_url": raw_album_art_url,
            "album_art_data_uri": album_art_variants["default"],
            "album_art_balanced_data_uri": album_art_variants["balanced"],
            "album_art_vivid_data_uri": album_art_variants["vivid"],
            "album_art_mono_data_uri": album_art_variants["mono"],
            "source": source,
            "multiple_active": multiple_active,
            "other_active_rooms": other_active_rooms,
            "same_content_rooms": same_content_rooms,
            "next_tracks": [],
        }
    }
    
    response = requests.post(WEBHOOK_URL, json=payload, timeout=20)
    if response.status_code != 200:
        raise RuntimeError(f"Webhook failed: {response.status_code} {response.text}")

if __name__ == "__main__":
    main()
