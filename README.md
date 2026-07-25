# Rowenta Robot Vacuum for Home Assistant

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=sfDuhNinja&repository=ha-rowenta&category=integration)

Custom integration for Rowenta X-Plorer robot vacuums (confirmed on the
**Series 120 AI**, firmware `SER120-*`) that talk the same local
"RobEye"/ROMY-protocol HTTP API as ROMY-branded robots and other
Groupe SEB (Rowenta/Tefal) models.

Unlike the [official ROMY integration](https://www.home-assistant.io/integrations/romy/),
this one also implements **room-by-room cleaning** through Home Assistant's
native `vacuum.clean_area` (area-to-segment mapping) and a generic
`vacuum.send_command` passthrough for experimenting with undocumented
endpoints.

100% local. No cloud account, no app, no internet dependency. Talks
directly to the robot over your LAN.

## Features

| Home Assistant feature | Backed by |
|---|---|
| Start / resume | `set/clean_start_or_continue` |
| Stop / Pause | `set/stop` |
| Return to dock | `set/go_home` |
| Fan speed (Silent/Eco/Normal/Boost, matching the app) | `set/switch_cleaning_parameter_set` |
| Clean specific room(s) (`vacuum.clean_area`) | `set/clean_map` |
| Spot-clean current position (`vacuum.clean_spot`) | `set/clean_spot` |
| Raw command passthrough (`vacuum.send_command`) | any `get/*` or `set/*` endpoint |
| Commands confirmed via the robot's own result tracking, not just fired-and-assumed | `get/command_result` |
| Battery, distance, area cleaned, run count, dustbin dirt level | `get/status`, `get/statistics`, `get/sensor_values` |
| Dustbin / water tank binary sensors | `get/sensor_values` |
| Problem sensor (stuck wheel/brush/fan, dustbin missing, lifted, etc.) | `get/robot_flags` |
| Auto-discovery | `_aicu-http._tcp.local.` mDNS |

Docked state is covered by the vacuum entity's own activity (no separate
"docked" sensor needed).

**Not implemented:** `LOCATE` — no such endpoint exists on this firmware,
confirmed by probing every plausible name. `MAP` (live map image) would
need a companion `camera` entity rendering `get/cleaning_grid_map`, which
is a fair bit more work than the rest of this list; open an issue if you
want it.

## Installation

### HACS

Click the badge above — it opens your Home Assistant instance straight to
the "add custom repository" dialog (requires [My Home Assistant](https://www.home-assistant.io/integrations/my/)
to be linked to this HA instance, on by default).

Or add it manually:

1. HACS → the 3-dot menu → **Custom repositories**
2. Add `https://github.com/sfDuhNinja/ha-rowenta`, category **Integration**
3. Install **Rowenta Robot Vacuum**, then restart Home Assistant

### Manual

Copy `custom_components/rowenta` into your Home Assistant `config/custom_components/`
directory and restart.

## Setup

Settings → Devices & Services → Add Integration → **Rowenta Robot Vacuum**.
The robot is usually auto-discovered on your network; otherwise enter its
IP address manually.

If your robot's local HTTP interface is locked, you'll be asked for the
8-digit code printed under the dustbin (the QR code there encodes it too).

### Room-by-room cleaning

`CLEAN_AREA` in Home Assistant works by mapping the robot's internal room
IDs to your HA areas. After setup, open the vacuum entity's settings and
use the room-mapping dialog to link each detected room to an HA area, then
use `vacuum.clean_area` (or the Areas card) to start a targeted clean.

## Why this exists / credits

Reverse engineered from live traffic against a real Rowenta X-Plorer
Series 120 AI, cross-checked against prior community work on the same
protocol family:

- [xeniter/romy](https://github.com/xeniter/romy) — the official ROMY
  Python SDK and Home Assistant integration
- [ChadiEM/rowenta-robot-vacuum-exporter](https://github.com/ChadiEM/rowenta-robot-vacuum-exporter) —
  Prometheus exporter confirming the API on a Rowenta X-Plorer Series 80
- The [Home Assistant community "Rowenta vacuum cleaner" thread](https://community.home-assistant.io/t/rowenta-vacuum-cleaner-ht-component/244131)
  and the [openHAB ROMY thread](https://community.openhab.org/t/romy-robot-integration-via-http-binding-austrian-vacuum-robot-highly-recommended/143307)

This is an unofficial, community-reverse-engineered integration. It is not
affiliated with or endorsed by Groupe SEB, Rowenta, or ROMY Robotics. The
bundled icon (`custom_components/rowenta/brand/`) is Rowenta's own logo,
sourced from rowenta.com and used solely to identify the represented brand,
per [Home Assistant's brand image guidelines](https://github.com/home-assistant/brands#trademark-legal-notices) —
its use does not imply endorsement.

Built by [sfDuhNinja](https://github.com/sfDuhNinja) with
[Claude](https://claude.com/claude-code) (Anthropic) as co-author — from the
initial live protocol reverse-engineering through every fix since. Commits
carry a `Co-Authored-By: Claude` trailer accordingly.

## License

MIT — see [LICENSE](LICENSE).
