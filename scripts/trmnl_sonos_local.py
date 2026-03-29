from dotenv import load_dotenv
from io import BytesIO
import datetime
import os
import base64
import requests
import soco
from PIL import Image, ImageEnhance, ImageOps

load_dotenv()
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


def build_processed_album_art_data_uri(url: str, saturation: float, contrast: float) -> str:
    if not url:
        return ""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert("RGB")
        img = ImageOps.exif_transpose(img)
        img = ImageEnhance.Color(img).enhance(saturation)
        img = ImageEnhance.Contrast(img).enhance(contrast)
        out = BytesIO()
        img.save(out, format="PNG")
        return "data:image/png;base64," + base64.b64encode(out.getvalue()).decode("ascii")
    except Exception:
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

def build_groups(speakers):
    groups = {}
    for sp in speakers:
        try:
            coord = sp.group.coordinator
            key = coord.uid
            groups.setdefault(key, {"coordinator": coord, "members": []})
            groups[key]["members"].append(sp.player_name)
        except Exception:
            continue
    return list(groups.values())


def pick_group(groups):
    if PREFERRED_ROOM:
        for group in groups:
            members = [name.lower() for name in group["members"]]
            if PREFERRED_ROOM.lower() in members or group["coordinator"].player_name.lower() == PREFERRED_ROOM.lower():
                return group

    active, fallback = [], []
    for group in groups:
        try:
            coord = group["coordinator"]
            info = coord.get_current_transport_info()
            track = coord.get_current_track_info()
            state = info.get("current_transport_state", "")
            if state == "PLAYING":
                active.append(group)
            elif track.get("title"):
                fallback.append(group)
        except Exception:
            continue

    if active:
        return active[0]
    if fallback:
        return fallback[0]
    return groups[0] if groups else None

def main():
    if not WEBHOOK_URL:
        raise RuntimeError("TRMNL_WEBHOOK_URL is required")
    speakers = soco.discover(timeout=5) or []
    groups = build_groups(list(speakers))
    selected_group = pick_group(groups)
    if selected_group is None:
        raise RuntimeError("No Sonos speakers discovered")
    speaker = selected_group["coordinator"]
    transport = speaker.get_current_transport_info()
    track = speaker.get_current_track_info()
    state = transport.get("current_transport_state", "UNKNOWN")
    raw_album_art_url = track.get("album_art") or ""
    album_art_variants = build_album_art_variants(raw_album_art_url)
    queue_preview = []
    try:
        queue = list(speaker.get_queue(start=0, max_items=8))
        current_pos = int(track.get("playlist_position") or 1) - 1
        if current_pos < 0:
            current_pos = 0
        for item in queue[current_pos + 1:current_pos + 4]:
            queue_preview.append(
                {
                    "title": getattr(item, "title", "") or "Unknown Track",
                    "artist": getattr(item, "creator", "") or "",
                    "album": getattr(item, "album", "") or "",
                }
            )
    except Exception:
        queue_preview = []

    active_groups = []
    for group in groups:
        try:
            coord = group["coordinator"]
            info = coord.get_current_transport_info()
            now_track = coord.get_current_track_info()
            if info.get("current_transport_state") == "PLAYING":
                active_groups.append(
                    {
                        "room_name": coord.player_name,
                        "members": group["members"],
                        "title": now_track.get("title") or "",
                        "artist": now_track.get("artist") or "",
                        "uri": now_track.get("uri") or "",
                    }
                )
        except Exception:
            continue

    same_content_rooms = []
    selected_uri = track.get("uri") or ""
    for group in active_groups:
        if group["room_name"] == speaker.player_name:
            continue
        if selected_uri and group["uri"] == selected_uri:
            same_content_rooms.extend(group["members"])

    other_active_rooms = []
    for group in active_groups:
        if group["room_name"] == speaker.player_name:
            continue
        other_active_rooms.extend(group["members"])

    payload = {
        "merge_variables": {
            "updated_at": datetime.datetime.now().strftime(UPDATED_AT_FORMAT),
            "room_name": speaker.player_name,
            "group_rooms": selected_group["members"],
            "group_size": len(selected_group["members"]),
            "state": state.replace("_", " "),
            "title": track.get("title") or "Nothing Playing",
            "artist": track.get("artist") or "Unknown Artist",
            "album": track.get("album") or "",
            "album_art_url": raw_album_art_url,
            "album_art_data_uri": album_art_variants["default"],
            "album_art_balanced_data_uri": album_art_variants["balanced"],
            "album_art_vivid_data_uri": album_art_variants["vivid"],
            "album_art_mono_data_uri": album_art_variants["mono"],
            "source": track.get("uri", "").split(":", 1)[0] if track.get("uri") else "",
            "multiple_active": len(active_groups) > 1,
            "other_active_rooms": other_active_rooms,
            "same_content_rooms": same_content_rooms,
            "next_tracks": queue_preview,
        }
    }
    response = requests.post(WEBHOOK_URL, json=payload, timeout=20)
    if response.status_code != 200:
        raise RuntimeError(f"Webhook failed: {response.status_code} {response.text}")

if __name__ == "__main__":
    main()
