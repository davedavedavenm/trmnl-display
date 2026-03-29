# InkyPi 

<img src="./docs/images/inky_clock.jpg" />

## Current Direction
This repository started as the upstream InkyPi project and now also carries an active TRMNL/LaraPaper-based homelab deployment focused on a Home Assistant-led e-paper appliance.

The current live system is:
- `khpi5` runs LaraPaper and the local companion scripts for private plugins
- the Pi Zero / Inky device acts as a thin TRMNL display client
- Home Assistant is the intended orchestration layer for screen modes and automations

For current project aims and live status, start with:
- [TRMNL Project Plan](./docs/TRMNL_PROJECT_PLAN.md)
- [TRMNL Progress Report](./docs/TRMNL_PROGRESS_REPORT.md)
- [Live Deployment Workflow](./docs/LIVE_DEPLOYMENT_WORKFLOW.md)

## Primary Focus
The main product direction is no longer "generic web UI for an e-ink Pi". It is:

- **Home Assistant Edition**
  - Home Assistant decides what the screen should show and when
  - LaraPaper renders the active recipe
  - the Pi display client only fetches and renders the final image
- **Shareable TRMNL recipes/plugins**
  - recipes should be exportable, reusable, and standards-compliant
  - local helper scripts are acceptable, but recipe-facing settings should live in `settings.yml`
  - whenever possible, plugin behaviour should align with official TRMNL conventions
- **ACeP-first colour rendering**
  - the target display is a 7-colour panel
  - colour regressions are bugs unless they are an explicit selectable mode

## Current Product Tracks
- Multi-calendar recipe productization
- Local Sonos recipe with full-colour rendering
- Home Assistant orchestration for mode switching and overrides
- Recipe/shareability improvements so useful local work can be published cleanly

## Community Patterns
The current architecture is consistent with how the TRMNL and wider e-paper/Home Assistant community is already working:

- **Home Assistant decides, recipe/plugin renders**
  - community TRMNL projects such as [ha_trmnl_weather_station](https://github.com/TilmanGriesel/ha_trmnl_weather_station) use Home Assistant to assemble live state and push it into a TRMNL recipe/plugin via webhook
- **Screenshot flows are common, but they are a different product tradeoff**
  - official TRMNL guidance supports a Home Assistant Screenshot flow for dashboard capture, and wider Inkplate projects use scheduled Lovelace screenshots for e-paper panels
  - this is useful for dense dashboards, but it is less shareable and less recipe-native than structured payloads and Liquid templates
- **Thin display clients are normal**
  - many open-source e-paper/Home Assistant projects treat the display device as a fetch-and-render endpoint while the server or Home Assistant instance does the real orchestration work

This repo therefore prefers:
- Home Assistant for orchestration and decision logic
- LaraPaper/TRMNL recipes for presentation
- thin display clients that only fetch and render the prepared image

Reference material:
- [TRMNL Home Assistant Integration](https://help.trmnl.com/en/articles/12494449-home-assistant-integration)
- [TRMNL Home Assistant Screenshot](https://help.trmnl.com/en/articles/13281388-home-assistant-screenshot)
- [TRMNL Image Display](https://help.trmnl.com/en/articles/11479051-image-display)
- [ha_trmnl_weather_station](https://github.com/TilmanGriesel/ha_trmnl_weather_station)
- [hass-inkplate-dashboards](https://github.com/brodykenrick/hass-inkplate-dashboards)
- [Home-Assistant-eink-remote-display](https://github.com/briandorey/Home-Assistant-eink-remote-display)

## Working Rules For This Repo
- Treat local edits as incomplete until the corresponding change is deployed to `khpi5` and validated end to end.
- For TRMNL/LaraPaper work, follow the path `local edit -> deploy to khpi5 -> verify LaraPaper render/preview -> verify device pull -> verify physical screen`.
- "Full colour" in this repo means using the display's supported ACeP palette, not grayscale-safe fallback rendering.
- Prefer official TRMNL documentation and official/community-supported recipe guidance when choosing architecture or plugin behavior.
- When documentation and real-world render behavior conflict, prefer the empirically validated live render path until a replacement is tested side by side on the actual screen.
- When a screen looks grayscale, inspect the live LaraPaper output first. Do not assume the recipe is at fault before checking the `khpi5` device model and palette configuration.

## About InkyPi 
InkyPi is an open-source, customizable E-Ink display powered by a Raspberry Pi. Designed for simplicity and flexibility, it allows you to effortlessly display the content you care about, with a simple web interface that makes setup and configuration effortless.

**Features**:
- Natural paper-like aethetic: crisp, minimalist visuals that are easy on the eyes, with no glare or backlight
- Web Interface allows you to update and configure the display from any device on your network
- Minimize distractions: no LEDS, noise, or notifications, just the content you care about
- Easy installation and configuration, perfect for beginners and makers alike
- Open source project allowing you to modify, customize, and create your own plugins
- Set up scheduled playlists to display different plugins at designated times

**Plugins**:

- Image Upload: Upload and display any image from your browser
- Daily Newspaper/Comic: Show daily comics and front pages of major newspapers from around the world
- Clock: Customizable clock faces for displaying time
- AI Image/Text: Generate images and dynamic text from prompts using OpenAI's models
- Weather: Display current weather conditions and multi-day forecasts with a customizable layout
- Calendar: Visualize your calendar from Google, Outlook, or Apple Calendar with customizable layouts

And additional plugins coming soon! For documentation on building custom plugins, see [Building InkyPi Plugins](./docs/building_plugins.md).

See [the wiki](https://github.com/fatihak/InkyPi/wiki) for a list of community-maintained third-party plugins.

## Hardware 
- Raspberry Pi (4 | 3 | Zero 2 W)
    - Recommended to get 40 pin Pre Soldered Header
- MicroSD Card (min 8 GB) like [this one](https://amzn.to/3G3Tq9W)
- E-Ink Display:
    - Inky Impression by Pimoroni
        - **[13.3 Inch Display](https://collabs.shop/q2jmza)**
        - **[7.3 Inch Display](https://collabs.shop/q2jmza)**
        - **[5.7 Inch Display](https://collabs.shop/ns6m6m)**
        - **[4 Inch Display](https://collabs.shop/cpwtbh)**
    - Inky wHAT by Pimoroni
        - **[4.2 Inch Display](https://collabs.shop/jrzqmf)**
    - Waveshare e-Paper Displays
        - Spectra 6 (E6) Full Color **[4 inch](https://www.waveshare.com/4inch-e-paper-hat-plus-e.htm?&aff_id=111126)** **[7.3 inch](https://www.waveshare.com/7.3inch-e-paper-hat-e.htm?&aff_id=111126)** **[13.3 inch](https://www.waveshare.com/13.3inch-e-paper-hat-plus-e.htm?&aff_id=111126)**
        - Black and White **[7.5 inch](https://www.waveshare.com/7.5inch-e-paper-hat.htm?&aff_id=111126)** **[13.3 inch](https://www.waveshare.com/13.3inch-e-paper-hat-k.htm?&aff_id=111126)**
        - See [Waveshare e-paper displays](https://www.waveshare.com/product/raspberry-pi/displays/e-paper.htm?&aff_id=111126) or visit their [Amazon store](https://amzn.to/3HPRTEZ) for additional models. Note that some models like the IT8951 based displays are not supported. See later section on [Waveshare e-Paper](#waveshare-display-support) compatibility for more information.
- Picture Frame or 3D Stand
    - See [community.md](./docs/community.md) for 3D models, custom builds, and other submissions from the community

**Disclosure:** The links above are affiliate links. I may earn a commission from qualifying purchases made through them, at no extra cost to you, which helps maintain and develop this project.

## Installation
To install InkyPi, follow these steps:

1. Clone the repository:
    ```bash
    git clone https://github.com/fatihak/InkyPi.git
    ```
2. Navigate to the project directory:
    ```bash
    cd InkyPi
    ```
3. Run the installation script with sudo:
    ```bash
    sudo bash install/install.sh [-W <waveshare device model>]
    ``` 
     Option: 
    
    * -W \<waveshare device model\> - specify this parameter **ONLY** if installing for a Waveshare display.  After the -W option specify the Waveshare device model e.g. epd7in3f.

    e.g. for Inky displays use:
    ```bash
    sudo bash install/install.sh
    ```

    and for [Waveshare displays](#waveshare-display-support) use:
    ```bash
    sudo bash install/install.sh -W epd7in3f
    ```


After the installation is complete, the script will prompt you to reboot your Raspberry Pi. Once rebooted, the display will update to show the InkyPi splash screen.

Note: 
- The installation script requires sudo privileges to install and run the service. We recommend starting with a fresh installation of Raspberry Pi OS to avoid potential conflicts with existing software or configurations.
- The installation process will automatically enable the required SPI and I2C interfaces on your Raspberry Pi.

For more details, including instructions on how to image your microSD with Raspberry Pi OS, refer to [installation.md](./docs/installation.md). You can also checkout [this YouTube tutorial](https://youtu.be/L5PvQj1vfC4).

## Update
To update your InkyPi with the latest code changes, follow these steps:
1. Navigate to the project directory:
    ```bash
    cd InkyPi
    ```
2. Fetch the latest changes from the repository:
    ```bash
    git pull
    ```
3. Run the update script with sudo:
    ```bash
    sudo bash install/update.sh
    ```
This process ensures that any new updates, including code changes and additional dependencies, are properly applied without requiring a full reinstallation.

## Uninstall
To install InkyPi, simply run the following command:

```bash
sudo bash install/uninstall.sh
```

## Roadmap
The InkyPi project is constantly evolving, with many exciting features and improvements planned for the future.

- Productize the Home Assistant Edition workflow
- Continue building shareable TRMNL recipes/plugins
- Improve orchestration between Home Assistant, LaraPaper, and the display client
- Preserve strong ACeP colour behaviour across recipes

Check out the public [trello board](https://trello.com/b/SWJYWqe4/inkypi) to explore upcoming features and vote on what you'd like to see next!

## Waveshare Display Support

Waveshare offers a range of e-Paper displays, similar to the Inky screens from Pimoroni, but with slightly different requirements. While Inky displays auto-configure via the inky Python library, Waveshare displays require model-specific drivers from their [Python EPD library](https://github.com/waveshareteam/e-Paper/tree/master/RaspberryPi_JetsonNano/python/lib/waveshare_epd).

This project has been tested with several Waveshare models. **Displays based on the IT8951 controller are not supported**, and **screens smaller than 4 inches are not recommended** due to limited resolution.

If your display model has a corresponding driver in the link above, it’s likely to be compatible. When running the installation script, use the -W option to specify your display model (without the .py extension). The script will automatically fetch and install the correct driver.

## License

Distributed under the GPL 3.0 License, see [LICENSE](./LICENSE) for more information.

This project includes fonts and icons with separate licensing and attribution requirements. See [Attribution](./docs/attribution.md) for details.

## Issues

Check out the [troubleshooting guide](./docs/troubleshooting.md). If you're still having trouble, feel free to create an issue on the [GitHub Issues](https://github.com/fatihak/InkyPi/issues) page.

If you're using a Pi Zero W, note that there are known issues during the installation process. See [Known Issues during Pi Zero W Installation](./docs/troubleshooting.md#known-issues-during-pi-zero-w-installation) section in the troubleshooting guide for additional details..

## Sponsoring

InkyPi is maintained and developed with the help of sponsors. If you enjoy the project or find it useful, consider supporting its continued development.

<p align="center">
<a href="https://github.com/sponsors/fatihak" target="_blank"><img src="https://user-images.githubusercontent.com/345274/133218454-014a4101-b36a-48c6-a1f6-342881974938.png" alt="Become a Patreon" height="35" width="auto"></a>
<a href="https://www.patreon.com/akzdev" target="_blank"><img src="https://c5.patreon.com/external/logo/become_a_patron_button.png" alt="Become a Patreon" height="35" width="auto"></a>
<a href="https://www.buymeacoffee.com/akzdev" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="35" width="auto"></a>
</p>


## Acknowledgements

Check out these similar projects:

- [PaperPi](https://github.com/txoof/PaperPi) - awesome project that supports waveshare devices
    - shoutout to @txoof for assisting with InkyPi's installation process
- [InkyCal](https://github.com/aceinnolab/Inkycal) - has modular plugins for building custom dashboards
- [PiInk](https://github.com/tlstommy/PiInk) - inspiration behind InkyPi's flask web ui
- [rpi_weather_display](https://github.com/sjnims/rpi_weather_display) - alternative eink weather dashboard with advanced power efficiency
