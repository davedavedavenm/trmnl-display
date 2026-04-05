from dotenv import load_dotenv
import datetime
import os
import requests

load_dotenv()

HA_URL = os.getenv("HA_URL", "http://192.168.1.89:8123").strip()
HA_TOKEN = os.getenv("HA_TOKEN", "").strip()
TRMNL_WEBHOOK_URL = os.getenv("TRMNL_WEBHOOK_URL", "").strip()
TRMNL_UPDATED_AT_FORMAT = os.getenv("TRMNL_UPDATED_AT_FORMAT", "%d %b %H:%M")

SONOS_ENTITIES = [
    "media_player.living_room",
    "media_player.bedroom",
    "media_player.kitchen",
    "media_player.gym",
    "media_player.sonos_roam",
]

PERSON_ENTITIES = [
    "person.david",
    "person.jennifer",
]


def fetch_entity(entity_id: str) -> dict:
    resp = requests.get(
        f"{HA_URL}/api/states/{entity_id}",
        headers={"Authorization": f"Bearer {HA_TOKEN}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_people() -> list:
    people = []
    for eid in PERSON_ENTITIES:
        try:
            e = fetch_entity(eid)
            people.append({
                "name": e["attributes"].get("friendly_name", eid).split("'s")[0].split("'")[0],
                "state": e["state"],
            })
        except Exception as err:
            print(f"Error fetching {eid}: {err}")
            people.append({"name": eid, "state": "unknown"})
    return people


def fetch_weather() -> dict:
    try:
        e = fetch_entity("weather.forecast_home")
        attrs = e["attributes"]
        return {
            "condition": e["state"],
            "temperature": attrs.get("temperature"),
            "humidity": attrs.get("humidity"),
            "wind_speed": attrs.get("wind_speed"),
        }
    except Exception as err:
        print(f"Error fetching weather: {err}")
        return {}


def fetch_sonos() -> list:
    rooms = []
    for eid in SONOS_ENTITIES:
        try:
            e = fetch_entity(eid)
            if e["state"] in ("unavailable", "unknown"):
                continue
            
            picture = e["attributes"].get("entity_picture", "")
            if picture and picture.startswith("/"):
                picture = f"{HA_URL}{picture}"

            rooms.append({
                "room": e["attributes"].get("friendly_name", eid),
                "state": e["state"],
                "title": e["attributes"].get("media_title", ""),
                "artist": e["attributes"].get("media_artist", ""),
                "picture": picture,
            })
        except Exception:
            continue
    return rooms


def fetch_home_status() -> dict:
    result = {}
    try:
        door = fetch_entity("binary_sensor.nuki_flat_door_locked")
        result["door_locked"] = door["state"] == "on"
    except Exception:
        result["door_locked"] = None

    try:
        washer = fetch_entity("binary_sensor.wash_dryer_status")
        result["washer_running"] = washer["state"] == "on"
    except Exception:
        result["washer_running"] = None

    try:
        blind = fetch_entity("cover.blinds_controller_curtain")
        result["blind_position"] = blind["attributes"].get("current_position", "unknown")
    except Exception:
        result["blind_position"] = "unknown"

    try:
        thermo = fetch_entity("climate.thermostat")
        if thermo["state"] not in ("unavailable", "unknown"):
            result["thermostat_temp"] = thermo["attributes"].get("current_temperature")
        else:
            result["thermostat_temp"] = None
    except Exception:
        result["thermostat_temp"] = None

    return result


def main() -> None:
    if not TRMNL_WEBHOOK_URL:
        raise RuntimeError("TRMNL_WEBHOOK_URL is required")
    if not HA_TOKEN:
        raise RuntimeError("HA_TOKEN is required")

    payload = {
        "merge_variables": {
            "updated_at": datetime.datetime.now().strftime(TRMNL_UPDATED_AT_FORMAT),
            "people": fetch_people(),
            "weather": fetch_weather(),
            "sonos": fetch_sonos(),
            "home": fetch_home_status(),
        }
    }

    resp = requests.post(TRMNL_WEBHOOK_URL, json=payload, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f"Webhook failed: {resp.status_code} {resp.text}")
    print(f"OK - dashboard pushed at {payload['merge_variables']['updated_at']}")


if __name__ == "__main__":
    main()
