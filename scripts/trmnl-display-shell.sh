#!/bin/bash
# trmnl-display-shell - Lightweight shell replacement for the Go trmnl-display client.
# Fetches images from LaraPaper BYOS server and renders them via show_img.
# Replaces the Go binary to work around a Go runtime + libgpiod fork incompatibility.

trap '' HUP INT TERM USR1 USR2 PIPE ALRM

CONFIG_DIR="${HOME}/.config/trmnl"
CONFIG_FILE="${CONFIG_DIR}/config.json"
TMPDIR="${TMPDIR:-/tmp}"
TMP_IMG=""

cleanup() {
    if [[ -n "${TMP_IMG}" && -f "${TMP_IMG}" ]]; then
        rm -f "${TMP_IMG}"
    fi
}
trap cleanup EXIT

BASE_URL=$(python3 -c "
import json, sys
try:
    with open('${CONFIG_FILE}') as f:
        d = json.load(f)
    print(d.get('base_url', 'https://trmnl.app'))
except:
    sys.exit(1)
") || { echo "Failed to read config"; exit 1; }

DEVICE_ID=$(python3 -c "
import json, sys
try:
    with open('${CONFIG_FILE}') as f:
        d = json.load(f)
    print(d.get('device_id', ''))
except:
    sys.exit(1)
") || { echo "Failed to read device_id"; exit 1; }

API_KEY=$(python3 -c "
import json, sys
try:
    with open('${CONFIG_FILE}') as f:
        d = json.load(f)
    print(d.get('api_key', ''))
except:
    sys.exit(1)
") || true

echo "Using base URL: ${BASE_URL}"

while true; do
    RESPONSE=$(curl -sf -m 30 \
        -H "ID: ${DEVICE_ID}" \
        -H "access-token: ${API_KEY}" \
        -H "Content-Type: application/json" \
        -H "battery-voltage: 100.00" \
        -H "rssi: 0" \
        "${BASE_URL}/api/display" 2>/dev/null)
    if [[ $? -ne 0 ]]; then
        echo "Error fetching display, retrying in 60s..."
        sleep 60
        continue
    fi

    PARSED=$(echo "${RESPONSE}" | python3 -c "
import json, sys, urllib.parse
d = json.load(sys.stdin)
url = d.get('image_url', '')
p = urllib.parse.urlparse(url)
if p.netloc and p.netloc not in ['192.168.1.143']:
    url = urllib.parse.urljoin('${BASE_URL}/', p.path)
print(json.dumps({
    'image_url': url,
    'refresh_rate': d.get('refresh_rate', 600),
    'special_function': d.get('special_function', ''),
}))
" 2>/dev/null)
    if [[ $? -ne 0 || -z "${PARSED}" ]]; then
        echo "Error parsing response, retrying in 60s..."
        sleep 60
        continue
    fi

    IMAGE_URL=$(echo "${PARSED}" | python3 -c "import json,sys; print(json.load(sys.stdin)['image_url'])" 2>/dev/null)
    REFRESH_RATE=$(echo "${PARSED}" | python3 -c "import json,sys; print(json.load(sys.stdin)['refresh_rate'])" 2>/dev/null)
    SPECIAL=$(echo "${PARSED}" | python3 -c "import json,sys; print(json.load(sys.stdin).get('special_function',''))" 2>/dev/null)

    [[ -z "${IMAGE_URL}" ]] && { sleep "${REFRESH_RATE:-600}"; continue; }

    if [[ "${SPECIAL}" == "sleep" ]]; then
        echo "Display sleeping, waiting ${REFRESH_RATE:-600}s..."
        sleep "${REFRESH_RATE:-600}"
        continue
    fi

    TMP_IMG=$(mktemp -u "${TMPDIR}/trmnl-display.XXXXXX.png")

    if curl -sf -m 30 -o "${TMP_IMG}" "${IMAGE_URL}" 2>/dev/null && [[ -s "${TMP_IMG}" ]]; then
        if /usr/local/bin/show_img.bin "file=${TMP_IMG}" "invert=false" "mode=full" 2>/dev/null; then
            echo "Displayed: ${TMP_IMG}"
        else
            echo "show_img failed (exit $?), retrying on next cycle..."
        fi
    else
        echo "Error downloading image"
    fi

    rm -f "${TMP_IMG}"
    TMP_IMG=""

    SLEEP_FOR="${REFRESH_RATE:-600}"
    [[ "${SLEEP_FOR}" =~ ^[0-9]+$ ]] && [[ "${SLEEP_FOR}" -lt 60 ]] && SLEEP_FOR=60
    [[ -z "${SLEEP_FOR}" ]] && SLEEP_FOR=600
    echo "Cycle complete, sleeping ${SLEEP_FOR}s..."
    sleep "${SLEEP_FOR}"
    echo "Sleep done, looping..."
done
echo "ERROR: exited main loop unexpectedly"
