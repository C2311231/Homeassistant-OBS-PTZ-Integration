# PTZ + OBS + Home Assistant Automation Bridge (Prototype)

This is a quick prototype project I built for a local nonprofit to integrate:

- Two PTZ cameras (20x and 30x)
- OBS WebSocket control (scenes, transitions, streaming)
- Home Assistant input booleans & input buttons as triggers

## Features

- PTZ preset recall and scene switching logic
- Automated streaming start/stop sequences
- Home Assistant WebSocket subscription and event handling
- OBS WebSocket reconnect logic
- Async event loop that orchestrates everything
- Deployed via docker container

## Possible Future Improvements

- Configuration file instead of hardcoded IPs
- Robust reconnect and retry logic
- Move to structured events and modular command handlers
- UI for managing presets and actions

## Notes

- This prototype ran successfully in production for over a year with no reported issues
- This is an early proof-of-concept.
- All IP addresses, tokens, and presets have been removed.
- Everything was originally hardcoded because it was built quickly for a live environment.
- Not production ready, but demonstrates system integration and async automation.
