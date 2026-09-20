import math
import queue
import random
import sqlite3
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from tkinter import messagebox, ttk

DB_PATH = "cabgo.db"

# --------------------------------------------------------------------------
# Domain data
# --------------------------------------------------------------------------

# Sample known locations with (x, y) coordinates on an abstract city grid.
# Using a grid instead of real maps keeps the app dependency-free and instant,
# while still giving realistic, varying distances/fares.
LOCATIONS = {
    "Civil Lines": (2.0, 8.0),
    "Railway Station": (1.0, 2.0),
    "University Campus": (4.5, 6.0),
    "Katra": (3.0, 4.5),
    "Sangam": (6.0, 1.0),
    "Airport": (9.0, 3.0),
    "Phaphamau": (2.5, 9.5),
    "Naini": (5.0, -1.0),
    "IT Chauraha": (4.0, 3.0),
    "Bamrauli": (0.0, 0.0),
}

CAB_TYPES = {
    # name: (base_fare, per_km, per_min, seats, avg_speed_kmph)
    "Mini":  {"base": 30,  "per_km": 9,  "per_min": 1.0, "seats": 4, "speed": 32},
    "Sedan": {"base": 50,  "per_km": 12, "per_min": 1.3, "seats": 4, "speed": 34},
    "SUV":   {"base": 80,  "per_km": 16, "per_min": 1.6, "seats": 6, "speed": 30},
    "Prime": {"base": 100, "per_km": 20, "per_min": 2.0, "seats": 4, "speed": 36},
}

DRIVER_FIRST_NAMES = ["Rahul", "Amit", "Suresh", "Vikram", "Sanjay", "Anil",
                       "Deepak", "Manoj", "Ravi", "Ajay", "Naveen", "Rakesh"]
CAR_MODELS = {
    "Mini": ["Maruti Alto", "Tata Tiago", "Hyundai Santro"],
    "Sedan": ["Honda City", "Maruti Ciaz", "Hyundai Verna"],
    "SUV": ["Mahindra XUV300", "Hyundai Creta", "Kia Seltos"],
    "Prime": ["Toyota Innova", "Skoda Slavia", "Honda Civic"],
}


@dataclass
class Driver:
    name: str
    car: str
    plate: str
    rating: float
    eta_min: int


def grid_distance_km(p1, p2):
    """Simple Euclidean distance on the abstract grid, scaled to km."""
    return max(math.dist(p1, p2) * 1.6, 0.8)


def find_driver(cab_type: str) -> Driver:
    """Simulate locating the nearest available driver."""
    first = random.choice(DRIVER_FIRST_NAMES)
    car = random.choice(CAR_MODELS[cab_type])
    plate = f"UP70 {random.randint(10,99)}{random.choice('ABCDEFGHJK')}{random.randint(1000,9999)}"
    rating = round(random.uniform(3.9, 5.0), 1)
    eta = random.randint(2, 8)
    return Driver(first, car, plate, rating, eta)


# --------------------------------------------------------------------------
# Database layer
# --------------------------------------------------------------------------

class BookingDB:
    def __init__(self, path=DB_PATH):
        self.conn = sqlite3.connect(path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pickup TEXT, drop_loc TEXT, distance_km REAL,
                cab_type TEXT, fare REAL, driver_name TEXT,
                car TEXT, plate TEXT, status TEXT, created_at TEXT
            )
        """)
        self.conn.commit()

    def add_booking(self, pickup, drop_loc, distance_km, cab_type, fare, driver: Driver):
        cur = self.conn.execute(
            """INSERT INTO bookings
               (pickup, drop_loc, distance_km, cab_type, fare, driver_name,
                car, plate, status, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (pickup, drop_loc, round(distance_km, 2), cab_type, round(fare, 2),
             driver.name, driver.car, driver.plate, "Confirmed",
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        self.conn.commit()
        return cur.lastrowid

    def all_bookings(self):
        return self.conn.execute(
            "SELECT id, pickup, drop_loc, distance_km, cab_type, fare, "
            "driver_name, car, plate, status, created_at "
            "FROM bookings ORDER BY id DESC"
        ).fetchall()

    def update_status(self, booking_id, status):
        self.conn.execute("UPDATE bookings SET status=? WHERE id=?", (status, booking_id))
        self.conn.commit()

    def close(self):
        self.conn.close()


# --------------------------------------------------------------------------
# GUI
# --------------------------------------------------------------------------

BG = "#0f172a"
CARD = "#1e293b"
ACCENT = "#22c55e"
ACCENT_DARK = "#16a34a"
TEXT = "#e2e8f0"
MUTED = "#94a3b8"
DANGER = "#ef4444"


class CabGoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CabGo — Book a Ride")
        self.geometry("480x640")
        self.minsize(440, 600)
        self.configure(bg=BG)

        self.db = BookingDB()
        self.result_queue = queue.Queue()
        self.selected_cab = tk.StringVar(value="Mini")

        self._build_style()
        self._build_layout()
        self._poll_queue()

    # ---------------- styling ----------------
    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TCombobox", fieldbackground=CARD, background=CARD,
                         foreground=TEXT, arrowcolor=TEXT, padding=6)
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=CARD, foreground=MUTED,
                         padding=(16, 8), font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#062e14")])
        style.configure("Treeview", background=CARD, fieldbackground=CARD,
                         foreground=TEXT, rowheight=26, borderwidth=0)
        style.configure("Treeview.Heading", background=BG, foreground=MUTED,
                         font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", ACCENT_DARK)])

    def _build_layout(self):
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=20, pady=(18, 6))
        tk.Label(header, text="🚕 CabGo", font=("Segoe UI", 20, "bold"),
                  bg=BG, fg=ACCENT).pack(anchor="w")
        tk.Label(header, text="Fast, minimal cab booking — built in pure Python",
                  font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(anchor="w")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=14, pady=10)

        self.book_tab = tk.Frame(notebook, bg=BG)
        self.history_tab = tk.Frame(notebook, bg=BG)
        notebook.add(self.book_tab, text="  Book a Ride  ")
        notebook.add(self.history_tab, text="  My Rides  ")

        self._build_book_tab()
        self._build_history_tab()

    # ---------------- book tab ----------------
    def _card(self, parent, **kw):
        f = tk.Frame(parent, bg=CARD, highlightthickness=0)
        f.pack(fill="x", pady=8, **kw)
        return f

    def _label(self, parent, text, **kw):
        return tk.Label(parent, text=text, bg=CARD, fg=MUTED,
                         font=("Segoe UI", 9, "bold"), **kw)

    def _build_book_tab(self):
        wrap = tk.Frame(self.book_tab, bg=BG)
        wrap.pack(fill="both", expand=True)

        # Locations card
        loc_card = self._card(wrap)
        inner = tk.Frame(loc_card, bg=CARD)
        inner.pack(fill="x", padx=14, pady=12)

        self._label(inner, "PICKUP").grid(row=0, column=0, sticky="w")
        self.pickup_var = tk.StringVar(value="Civil Lines")
        pickup_cb = ttk.Combobox(inner, textvariable=self.pickup_var,
                                  values=list(LOCATIONS.keys()), state="readonly")
        pickup_cb.grid(row=1, column=0, sticky="ew", pady=(2, 10))

        self._label(inner, "DROP").grid(row=2, column=0, sticky="w")
        self.drop_var = tk.StringVar(value="Airport")
        drop_cb = ttk.Combobox(inner, textvariable=self.drop_var,
                                values=list(LOCATIONS.keys()), state="readonly")
        drop_cb.grid(row=3, column=0, sticky="ew", pady=2)
        inner.columnconfigure(0, weight=1)

        swap_btn = tk.Button(inner, text="⇅ Swap", bg=CARD, fg=ACCENT,
                              activebackground=CARD, activeforeground=ACCENT,
                              relief="flat", font=("Segoe UI", 8, "bold"),
                              command=self._swap_locations, cursor="hand2")
        swap_btn.grid(row=1, column=1, rowspan=2, padx=(10, 0))

        # Cab type card
        cab_card = self._card(wrap)
        self._label(cab_card, "CAB TYPE").pack(anchor="w", padx=14, pady=(12, 4))
        cab_row = tk.Frame(cab_card, bg=CARD)
        cab_row.pack(fill="x", padx=14, pady=(0, 12))
        for name in CAB_TYPES:
            b = tk.Radiobutton(
                cab_row, text=name, variable=self.selected_cab, value=name,
                bg=CARD, fg=TEXT, selectcolor=BG, activebackground=CARD,
                activeforeground=ACCENT, font=("Segoe UI", 9, "bold"),
                indicatoron=False, relief="flat", padx=10, pady=6,
                command=self._update_estimate,
            )
            b.pack(side="left", expand=True, fill="x", padx=3)

        # Estimate card
        est_card = self._card(wrap)
        est_inner = tk.Frame(est_card, bg=CARD)
        est_inner.pack(fill="x", padx=14, pady=12)
        self.distance_label = tk.Label(est_inner, text="Distance: —", bg=CARD,
                                        fg=MUTED, font=("Segoe UI", 9))
        self.distance_label.pack(anchor="w")
        self.fare_label = tk.Label(est_inner, text="Estimated fare: ₹—", bg=CARD,
                                    fg=ACCENT, font=("Segoe UI", 16, "bold"))
        self.fare_label.pack(anchor="w", pady=(4, 0))
        self.eta_label = tk.Label(est_inner, text="", bg=CARD, fg=MUTED,
                                   font=("Segoe UI", 9))
        self.eta_label.pack(anchor="w")

        pickup_cb.bind("<<ComboboxSelected>>", lambda e: self._update_estimate())
        drop_cb.bind("<<ComboboxSelected>>", lambda e: self._update_estimate())

        # Book button + status
        self.book_btn = tk.Button(
            wrap, text="Find My Ride", bg=ACCENT, fg="#062e14",
            activebackground=ACCENT_DARK, activeforeground="#062e14",
            font=("Segoe UI", 12, "bold"), relief="flat", pady=10,
            cursor="hand2", command=self._start_booking,
        )
        self.book_btn.pack(fill="x", pady=(6, 4))

        self.status_label = tk.Label(wrap, text="", bg=BG, fg=MUTED,
                                      font=("Segoe UI", 9))
        self.status_label.pack(anchor="w", pady=(2, 0))

        self._update_estimate()

    def _swap_locations(self):
        p, d = self.pickup_var.get(), self.drop_var.get()
        self.pickup_var.set(d)
        self.drop_var.set(p)
        self._update_estimate()

    def _current_distance(self):
        p = LOCATIONS[self.pickup_var.get()]
        d = LOCATIONS[self.drop_var.get()]
        return grid_distance_km(p, d)

    def _fare_for(self, cab_type, distance_km):
        c = CAB_TYPES[cab_type]
        est_minutes = distance_km / c["speed"] * 60
        fare = c["base"] + c["per_km"] * distance_km + c["per_min"] * est_minutes
        return fare, est_minutes

    def _update_estimate(self):
        if self.pickup_var.get() == self.drop_var.get():
            self.distance_label.config(text="Pickup and drop can't be the same")
            self.fare_label.config(text="Estimated fare: ₹—")
            self.eta_label.config(text="")
            return
        dist = self._current_distance()
        fare, mins = self._fare_for(self.selected_cab.get(), dist)
        self.distance_label.config(text=f"Distance: {dist:.1f} km")
        self.fare_label.config(text=f"Estimated fare: ₹{fare:.0f}")
        self.eta_label.config(text=f"Trip time ≈ {mins:.0f} min")

    def _start_booking(self):
        if self.pickup_var.get() == self.drop_var.get():
            messagebox.showwarning("CabGo", "Pickup and drop cannot be the same location.")
            return
        self.book_btn.config(state="disabled", text="Searching…", bg=MUTED)
        self.status_label.config(text="Looking for nearby drivers...", fg=MUTED)

        pickup, drop_loc = self.pickup_var.get(), self.drop_var.get()
        cab_type = self.selected_cab.get()
        distance = self._current_distance()
        fare, _ = self._fare_for(cab_type, distance)

        # Run the "search" in a background thread so the UI stays responsive —
        # this is the core reason a native GUI + threading beats a heavier
        # browser-based stack for perceived speed.
        threading.Thread(
            target=self._search_worker,
            args=(pickup, drop_loc, distance, cab_type, fare),
            daemon=True,
        ).start()

    def _search_worker(self, pickup, drop_loc, distance, cab_type, fare):
        time.sleep(random.uniform(0.6, 1.4))  # simulate a quick, real search
        driver = find_driver(cab_type)
        self.result_queue.put(("booked", pickup, drop_loc, distance, cab_type, fare, driver))

    def _poll_queue(self):
        try:
            while True:
                event = self.result_queue.get_nowait()
                if event[0] == "booked":
                    _, pickup, drop_loc, distance, cab_type, fare, driver = event
                    booking_id = self.db.add_booking(pickup, drop_loc, distance, cab_type, fare, driver)
                    self.status_label.config(
                        text=f"✔ Booked! {driver.name} · {driver.car} · {driver.plate} · "
                             f"ETA {driver.eta_min} min",
                        fg=ACCENT,
                    )
                    self.book_btn.config(state="normal", text="Find My Ride", bg=ACCENT)
                    self._refresh_history()
                    messagebox.showinfo(
                        "Ride Confirmed",
                        f"Booking #{booking_id} confirmed!\n\n"
                        f"Driver: {driver.name} ({driver.rating}★)\n"
                        f"Car: {driver.car}  Plate: {driver.plate}\n"
                        f"Arriving in {driver.eta_min} min\n"
                        f"Fare: ₹{fare:.0f}",
                    )
        except queue.Empty:
            pass
        self.after(150, self._poll_queue)

    # ---------------- history tab ----------------
    def _build_history_tab(self):
        wrap = tk.Frame(self.history_tab, bg=BG)
        wrap.pack(fill="both", expand=True)

        top = tk.Frame(wrap, bg=BG)
        top.pack(fill="x", pady=(6, 8))
        tk.Label(top, text="Ride History", bg=BG, fg=TEXT,
                  font=("Segoe UI", 12, "bold")).pack(side="left")
        tk.Button(top, text="⟳ Refresh", bg=BG, fg=ACCENT, relief="flat",
                  activebackground=BG, activeforeground=ACCENT_DARK,
                  font=("Segoe UI", 9, "bold"), cursor="hand2",
                  command=self._refresh_history).pack(side="right")

        cols = ("id", "route", "cab", "fare", "driver", "status", "when")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", height=14)
        headings = {"id": "#", "route": "Route", "cab": "Cab", "fare": "Fare",
                    "driver": "Driver", "status": "Status", "when": "Booked At"}
        widths = {"id": 30, "route": 130, "cab": 55, "fare": 60,
                  "driver": 90, "status": 75, "when": 120}
        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], anchor="w")
        self.tree.pack(fill="both", expand=True)

        btn_row = tk.Frame(wrap, bg=BG)
        btn_row.pack(fill="x", pady=8)
        tk.Button(btn_row, text="Cancel Selected Ride", bg=DANGER, fg="white",
                  relief="flat", font=("Segoe UI", 9, "bold"), cursor="hand2",
                  activebackground="#b91c1c", activeforeground="white",
                  command=self._cancel_selected).pack(fill="x")

        self._refresh_history()

    def _refresh_history(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for b in self.db.all_bookings():
            (bid, pickup, drop_loc, dist, cab_type, fare, driver_name,
             car, plate, status, created_at) = b
            self.tree.insert("", "end", iid=str(bid), values=(
                bid, f"{pickup} → {drop_loc}", cab_type, f"₹{fare:.0f}",
                driver_name, status, created_at,
            ))

    def _cancel_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("CabGo", "Select a ride from the list first.")
            return
        booking_id = int(sel[0])
        current_status = self.tree.item(sel[0])["values"][5]
        if current_status == "Cancelled":
            messagebox.showinfo("CabGo", "This ride is already cancelled.")
            return
        if messagebox.askyesno("Cancel Ride", f"Cancel booking #{booking_id}?"):
            self.db.update_status(booking_id, "Cancelled")
            self._refresh_history()

    def destroy(self):
        self.db.close()
        super().destroy()


if __name__ == "__main__":
    app = CabGoApp()
    app.mainloop()