import os
from utils.app_utils import resolve_path, get_font
from plugins.base_plugin.base_plugin import BasePlugin
from plugins.calendar_album.constants import LOCALE_MAP, FONT_SIZES
from PIL import Image, ImageColor, ImageDraw, ImageFont
import icalendar
import recurring_ical_events
from io import BytesIO
import logging
import requests
from datetime import datetime, timedelta
import pytz
import random

logger = logging.getLogger(__name__)

class Calendar(BasePlugin):
    def generate_settings_template(self):
        template_params = super().generate_settings_template()
        template_params['style_settings'] = True
        template_params['locale_map'] = LOCALE_MAP
        return template_params

    def generate_image(self, settings, device_config):
        # --- PATCH START: Album Logic ---
        # Use a copy of settings to avoid persisting random image selection to config
        settings = dict(settings)
        bg_file = settings.get("backgroundImageFile")
        
        try:
             logger.info(f"DEBUG Plugin: bg={bg_file} is_dir={os.path.isdir(bg_file) if bg_file else 'None'}")
        except Exception:
             logger.info("DEBUG Plugin: failed to log bg info")

        if bg_file and os.path.isdir(bg_file):
            try:
                valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
                images = [f for f in os.listdir(bg_file) if f.lower().endswith(valid_extensions)]
                logger.info(f"DEBUG Plugin: found {len(images)} images in album")
                
                if images:
                    selected_image = random.choice(images)
                    full_path = os.path.join(bg_file, selected_image)
                    settings['backgroundImageFile'] = full_path
                    logger.info(f"DEBUG Plugin: Selected random image: {full_path}")
                else:
                    logger.warning(f"DEBUG Plugin: No images found in {bg_file}")
            except Exception as e:
                logger.error(f"DEBUG Plugin: Error scanning album: {e}")
        # --- PATCH END ---

        calendar_urls = settings.get('calendarURLs[]')
        calendar_colors = settings.get('calendarColors[]')
        view = settings.get("viewMode")

        valid_views = ["timeGridDay", "timeGridWeek", "dayGrid", "dayGridMonth", "listMonth", "timeGridThreeDay", "timeGridTwoDay"]
        if not view:
            raise RuntimeError("View is required")
        elif view not in valid_views:
            raise RuntimeError(f"Invalid view: {view}")

        if not calendar_urls:
            raise RuntimeError("At least one calendar URL is required")
        for url in calendar_urls:
            if not url.strip():
                raise RuntimeError("Invalid calendar URL")

        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]
        
        timezone = device_config.get_config("timezone", default="America/New_York")
        time_format = device_config.get_config("time_format", default="12h")
        tz = pytz.timezone(timezone)

        current_dt = datetime.now(tz)
        start, end = self.get_view_range(view, current_dt, settings)
        logger.info(f"DEBUG: VIEW MODE = {view}"); logger.debug(f"Fetching events for {start} --> [{current_dt}] --> {end}")
        events = self.fetch_ics_events(calendar_urls, calendar_colors, tz, start, end)
      
        if not events:
            logger.warn("No events found for ics url")

        # Map 3-day view to generic for template logic if needed, but we handle it in template
        # Keeping view variable as is so template knows which one it is

        if view == 'timeGridWeek' and settings.get("displayPreviousDays") != "true":
            view = 'timeGrid'
        
        # NOTE: For timeGridThreeDay, we will handle the mapping in the template HTML
        
        logger.info(f"DEBUG SETTINGS: startTimeInterval={settings.get('startTimeInterval')}, endTimeInterval={settings.get('endTimeInterval')}")
        template_params = {
            "view": view,
            "events": events,
            "current_dt": current_dt.replace(minute=0, second=0, microsecond=0).isoformat(),
            "timezone": timezone,
            "plugin_settings": settings,
            "time_format": time_format,
            "font_scale": FONT_SIZES.get(settings.get("fontSize", "normal"))
        }

        image = self.render_image(dimensions, "calendar.html", "calendar.css", template_params)

        if not image:
            raise RuntimeError("Failed to take screenshot, please check logs.")
        return image

    def fetch_ics_events(self, calendar_urls, colors, tz, start_range, end_range):
        parsed_events = []
        if not isinstance(colors, list): colors = [colors]

        for calendar_url, color in zip(calendar_urls, colors):
            cal = self.fetch_calendar(calendar_url)
            events = recurring_ical_events.of(cal).between(start_range, end_range)
            contrast_color = self.get_contrast_color(color)

            for event in events:
                start, end, all_day = self.parse_data_points(event, tz)
                parsed_event = {
                    "title": str(event.get("summary")),
                    "start": start,
                    "backgroundColor": color,
                    "textColor": contrast_color,
                    "allDay": all_day
                }
                if end:
                    parsed_event['end'] = end

                parsed_events.append(parsed_event)

        return parsed_events

    def get_view_range(self, view, current_dt, settings):
        start = datetime(current_dt.year, current_dt.month, current_dt.day)
        
        if view == "timeGridTwoDay":
            start = current_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=2)
        elif view == "timeGridThreeDay":
            # Start today, show 3 days
            end = start + timedelta(days=3)
        elif view == "timeGridDay":
            end = start + timedelta(days=1)
        elif view == "timeGridWeek":
            if settings.get("displayPreviousDays") == "true":
                week_start_day = int(settings.get("weekStartDay", 1))
                python_week_start = (week_start_day - 1) % 7
                offset = (current_dt.weekday() - python_week_start) % 7
                start = current_dt - timedelta(days=offset)
                start = datetime(start.year, start.month, start.day)
            end = start + timedelta(days=7)
        elif view == "dayGrid":
            start = current_dt - timedelta(weeks=1)
            end = current_dt + timedelta(weeks=int(settings.get("displayWeeks") or 4))
        elif view == "dayGridMonth":
            start = datetime(current_dt.year, current_dt.month, 1) - timedelta(weeks=1)
            end = datetime(current_dt.year, current_dt.month, 1) + timedelta(weeks=6)
        elif view == "listMonth":
            end = start + timedelta(weeks=5)
        return start, end
        
    def parse_data_points(self, event, tz):
        all_day = False
        dtstart = event.decoded("dtstart")
        if isinstance(dtstart, datetime):
            start = dtstart.astimezone(tz).isoformat()
        else:
            start = dtstart.isoformat()
            all_day = True

        end = None
        if "dtend" in event:
            dtend = event.decoded("dtend")
            if isinstance(dtend, datetime):
                end = dtend.astimezone(tz).isoformat()
            else:
                end = dtend.isoformat()
        elif "duration" in event:
            duration = event.decoded("duration")
            end = (dtstart + duration).isoformat()
        return start, end, all_day

    def fetch_calendar(self, calendar_url):
        try:
            response = requests.get(calendar_url)
            response.raise_for_status()
            return icalendar.Calendar.from_ical(response.text)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch iCalendar url: {str(e)}")

    def get_contrast_color(self, color):
        r, g, b = ImageColor.getrgb(color)
        yiq = (r * 299 + g * 587 + b * 114) / 1000
        return '#000000' if yiq >= 150 else '#ffffff'
