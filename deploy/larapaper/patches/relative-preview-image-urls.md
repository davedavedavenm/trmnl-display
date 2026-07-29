# Relative Preview Image URLs

LaraPaper's device dashboard and device configure views use:

```php
Storage::disk('public')->url('images/generated/' . $current_image_uuid . '.' . $file_extension)
```

In this deployment, `APP_URL` is `https://trmnl.example.com`, so that call renders preview images as absolute proxied URLs. When the UI is opened at `http://192.168.1.143:4567`, the page loads from the LAN origin but the preview image is requested through Pangolin. Pangolin can redirect the image request to auth, which leaves the LaraPaper device screen preview broken even though the generated PNG exists locally.

Live patch applied on `2026-05-01` and reapplied after the LaraPaper `0.35.0` update on `2026-05-19`:

```php
'/storage/images/generated/' . $current_image_uuid . '.' . $file_extension
```

Patch both live files inside the LaraPaper container:

- `/var/www/html/resources/views/livewire/device-dashboard.blade.php`
- `/var/www/html/resources/views/livewire/devices/configure.blade.php`

Validation:

```bash
curl -I http://192.168.1.143:4567/storage/images/generated/<uuid>.png
```

The response should be `200 OK`. This patch may need to be reapplied after pulling a new `ghcr.io/usetrmnl/larapaper` image.
