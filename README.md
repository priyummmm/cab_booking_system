# 🚕 CabGo — Minimal & Fast Cab Booking System

A lightweight desktop cab-booking application built entirely with **Python's standard library** — Tkinter for the GUI and SQLite for storage. No frameworks, no browser engine, no external dependencies.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-green)
![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey?logo=sqlite)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Why It's Fast

| Approach | Startup | Memory | Dependencies |
|---|---|---|---|
| **CabGo (Tkinter)** | Instant | ~15–25 MB | None (stdlib only) |
| Electron-based apps | 1–3 sec | 150–300 MB | Node, Chromium |
| Web app + local server | 1–2 sec | 50–100 MB | Flask/Django, browser |

Tkinter is a thin wrapper over native Tk widgets, so the app launches instantly with a tiny memory footprint. SQLite is embedded and serverless, so there are no network round trips. The driver-search logic runs on a background thread so the UI never freezes.

## Features

- 📍 Pick pickup and drop locations from a dropdown, with a one-click swap
- 🚗 Four cab types (Mini, Sedan, SUV, Prime), each with its own fare formula
- 💰 Live fare, distance, and trip-time estimate as you change selections
- 🔍 Simulated driver search on a background thread — UI stays responsive
- 🧾 Booking confirmation with driver name, car, plate, rating, and ETA
- 📜 Ride history stored locally in SQLite, viewable and cancellable
- 🎨 Clean, minimal dark-themed interface

## Screenshots

*(Add screenshots here after running the app — e.g. `screenshots/book.png`, `screenshots/history.png`)*

## Requirements

- Python 3.8 or later
- Tkinter (bundled with most Python installs)
  - Windows / macOS: included by default
  - Linux: install if missing — `sudo apt install python3-tk`

No `pip install` needed — the project uses only the standard library (`tkinter`, `sqlite3`, `threading`, `queue`, `dataclasses`).

## Getting Started

```bash
# Clone the repository
git clone https://github.com/<your-username>/cabgo.git
cd cabgo

# Run the app
python cab_booking_system.py
```

A local `cabgo.db` SQLite file is created automatically on first run to store your ride history.

## Project Structure

```
cabgo/
├── cab_booking_system.py   # Main application (GUI + logic + database)
├── cabgo.db                # Auto-created SQLite database (gitignored)
└── README.md
```

## How It Works

1. **Book a Ride tab** — choose pickup/drop and cab type; fare and ETA update live.
2. **Find My Ride** — spins up a background thread to simulate locating a nearby driver without blocking the UI.
3. Once matched, the booking is written to SQLite and a confirmation dialog appears with driver details.
4. **My Rides tab** — browse past bookings in a sortable table and cancel any active ride.

## Customization

- Add more pickup/drop points by editing the `LOCATIONS` dictionary (name → grid coordinates).
- Adjust pricing by editing the `CAB_TYPES` dictionary (base fare, per-km rate, per-minute rate).
- Swap the abstract grid-distance model for a real geocoding/maps API if you want live locations.

## Roadmap Ideas

- [ ] Real map integration (e.g. OpenStreetMap / Google Maps API)
- [ ] Multiple user accounts / login
- [ ] Fare surge simulation based on demand
- [ ] Export ride history to CSV

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

## License

This project is licensed under the [MIT License](LICENSE).

---

Built with pure Python — no frameworks required. 🐍
