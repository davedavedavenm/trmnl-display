import datetime
import requests
from src.plugins.base_plugin import BasePlugin

class HADashboard(BasePlugin):
    def generate_image(self, settings, device_config):
        ha_url = settings.get("ha_url", "").strip()
        ha_token = settings.get("ha_token", "").strip()
        sonos_entities = [e.strip() for e in settings.get("sonos_entities", "").split(",") if e.strip()]

        if not ha_url or not ha_token:
            raise RuntimeError("Home Assistant URL and Token are required.")

        data = {
            "updated_at": datetime.datetime.now().strftime("%d %b %H:%M"),
            "people": self._fetch_people(ha_url, ha_token),
            "weather": self._fetch_weather(ha_url, ha_token),
            "sonos": self._fetch_sonos(ha_url, ha_token, sonos_entities),
            "home": self._fetch_home_status(ha_url, ha_token),
        }

        return self.render_image(
            dimensions=(800, 480),
            html_file="dashboard.html",
            template_params={"plugin_settings": data}
        )

    def _fetch_entity(self, ha_url, ha_token, entity_id):
        resp = requests.get(
            f"{ha_url}/api/states/{entity_id}",
            headers={"Authorization": f"Bearer {ha_token}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def _fetch_people(self, ha_url, ha_token):
        people = []
        for eid in ["person.david", "person.jennifer"]:
            try:
                e = self._fetch_entity(ha_url, ha_token, eid)
                people.append({
                    "name": e["attributes"].get("friendly_name", eid).split("'s")[0].split("'")[0],
                    "state": e["state"],
                })
            except Exception:
                people.append({"name": eid, "state": "unknown"})
        return people

    def _fetch_weather(self, ha_url, ha_token):
        try:
            e = self._fetch_entity(ha_url, ha_token, "weather.forecast_home")
            attrs = e["attributes"]
            return {
                "condition": e["state"],
                "temperature": attrs.get("temperature"),
                "humidity": attrs.get("humidity"),
                "wind_speed": attrs.get("wind_speed"),
            }
        except Exception:
            return {}

    def _fetch_sonos(self, ha_url, ha_token, sonos_entities):
        rooms = []
        for eid in sonos_entities:
            try:
                e = self._fetch_entity(ha_url, ha_token, eid)
                if e["state"] in ("unavailable", "unknown"):
                    continue
                
                picture = e["attributes"].get("entity_picture", "")
                if picture and picture.startswith("/"):
                    picture = f"{ha_url}{picture}"

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

    def _fetch_home_status(self, ha_url, ha_token):
        result = {}
        try:
            door = self._fetch_entity(ha_url, ha_token, "binary_sensor.nuki_flat_door_locked")
            result["door_locked"] = door["state"] == "on"
        except Exception:
            result["door_locked"] = None

        try:
            washer = self._fetch_entity(ha_url, ha_token, "binary_sensor.wash_dryer_status")
            result["washer_running"] = washer["state"] == "on"
        except Exception:
            result["washer_running"] = None

        try:
            blind = self._fetch_entity(ha_url, ha_token, "cover.blinds_controller_curtain")
            result["blind_position"] = blind["attributes"].get("current_position", "unknown")
        except Exception:
            result["blind_position"] = "unknown"

        try:
            thermo = self._fetch_entity(ha_url, ha_token, "climate.thermostat")
            if thermo["state"] not in ("unavailable", "unknown"):
                result["thermostat_temp"] = thermo["attributes"].get("current_temperature")
            else:
                result["thermostat_temp"] = None
        except Exception:
            result["thermostat_temp"] = None

        return result
