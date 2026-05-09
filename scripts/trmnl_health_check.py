#!/usr/bin/env python3
"""
TRMNL Display Health Check
Validates the full pipeline: LaraPaper, Nango, Pi, plugins.
Runs on khpi5.
"""
import subprocess
import sys
import time
from datetime import datetime, timezone

OK = "\033[32mOK\033[0m"
FAIL = "\033[31mFAIL\033[0m"
WARN = "\033[33mWARN\033[0m"


def run(cmd: list[str], timeout: int = 10) -> tuple[bool, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except Exception as e:
        return False, str(e)


def check(step: str) -> None:
    sys.stdout.write(f"  {step:.<50s}")
    sys.stdout.flush()


def result(ok: bool, detail: str = "") -> None:
    print(f"[{OK if ok else FAIL}]")
    if detail:
        for line in detail.splitlines():
            print(f"    {line}")


def main():
    print(f"TRMNL Display Health Check — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print()

    all_ok = True

    # 1. LaraPaper container
    check("LaraPaper container")
    ok, out = run(["docker", "ps", "--filter", "name=larapaper-app-1", "--format", "{{.Status}}"])
    running = ok and "Up" in out
    result(running, out.splitlines()[0] if out else "")
    all_ok &= running

    # 2. LaraPaper API (without auth headers, 404 is expected — just check reachable)
    check("LaraPaper API reachable")
    ok, out = run(["curl", "-sf", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "5", "http://localhost:4567/"])
    result(ok, out + (" (root)" if ok else ""))
    all_ok &= ok

    # 3. Pi connectivity
    check("Pi display client (192.168.1.74)")
    ok, out = run(["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes", "trmnl-pi", "echo ok"])
    result(ok, out)
    all_ok &= ok

    # 4. Pi display service
    check("Pi trmnl-display.service")
    ok, out = run(["ssh", "trmnl-pi", "systemctl is-active trmnl-display.service"])
    show_ok = ok and out.strip() == "active"
    result(show_ok, out.strip())
    all_ok &= show_ok

    # 5. Nango API
    check("Nango API reachable")
    ok, out = run(["curl", "-sf", "-o", "/dev/null", "-w", "%{http_code}", "https://nango.example.com/health"])
    result(ok, out)
    if not ok:
        all_ok = False

    # 6. Plugin health via DB
    check("LaraPaper plugins with valid images")
    try:
        r = subprocess.run(
            ["docker", "exec", "larapaper-app-1", "php", "-r",
             "require '/var/www/html/vendor/autoload.php';"
             "$app = require '/var/www/html/bootstrap/app.php';"
             "$app->make(\"Illuminate\\Contracts\\Console\\Kernel\")->bootstrap();"
             "$plugins = DB::table('plugins')->whereNotNull('current_image')->get(['name', 'current_image', 'updated_at']);"
             "foreach ($plugins as $p) { echo json_encode(['name' => $p->name, 'image' => $p->current_image, 'updated' => $p->updated_at]) . \"\n\"; }"],
            capture_output=True, text=True, timeout=15)
        if r.returncode == 0 and r.stdout.strip():
            import json
            plugins_info = []
            for line in r.stdout.strip().splitlines():
                try:
                    plugins_info.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
            print(f"[{OK}] ({len(plugins_info)} active)")
            for p in plugins_info:
                print(f"    {p['name']}: {p['image']} (updated {p.get('updated', '?')})")
        else:
            print(f"[{WARN}] Unable to query plugin table")
    except Exception as e:
        print(f"[{FAIL}] {e}")
        all_ok = False

    # 7. Pi last refresh
    check("Pi last successful refresh")
    ok, out = run(["ssh", "trmnl-pi", "journalctl -u trmnl-display.service --no-pager -n 200 --output=short-iso | grep 'Refresh complete' | tail -1"])
    if ok and out.strip():
        result(True, out.strip()[:80])
    else:
        result(False, "no recent Refresh complete found")
        all_ok = False

    # 8. Pi sleep timers
    check("Pi sleep/wake timers active")
    ok, out = run(["ssh", "trmnl-pi", "systemctl is-active trmnl-display-night-stop.timer trmnl-display-morning-start.timer"])
    if ok:
        lines = [l for l in out.strip().splitlines() if l]
        result(True, ", ".join(lines))
    else:
        result(False, out.strip())

    print()
    if all_ok:
        print(f"[{OK}] ALL CHECKS PASSED")
    else:
        print(f"[{FAIL}] SOME CHECKS FAILED — review above")
        sys.exit(1)


if __name__ == "__main__":
    main()
