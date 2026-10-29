"""Compare a manual pickup plan with the KohaRoute plan for one date (report Section 12).

This is a report tool, not an app feature. It only reads the database; it never changes it.

What it does
  1. Reads the routes KohaRoute saved for the date (distance, duration, stops, loads).
  2. Reads the manual plan from a JSON file (which vehicle visits which bookings, in order).
  3. Asks ORS Directions for the road distance and driving time of each manual route
     (depot -> stops in the given order -> depot). This is the same road network and the
     same "driving-car" profile that the ORS Optimization API used for KohaRoute.
  4. Prints the comparison table and saves it as Markdown and CSV.

Usage (run from the repo root, with the backend environment active)
  python scripts/compare_routes.py --date 2026-10-29 --write-template
      -> writes manual_plan.json listing the day's bookings; fill in the stop order by hand
  python scripts/compare_routes.py --date 2026-10-29 --manual manual_plan.json
      -> prints the comparison and writes comparison_output/

Only the Python standard library is used. The ORS key is read from ORS_API_KEY or backend/.env.
"""

import argparse
import csv
import json
import math
import os
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO_ROOT / "backend" / "koharoute.db"
ENV_FILE = REPO_ROOT / "backend" / ".env"
ORS_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"


# ----------------------------------------------------------------------------- inputs
def load_ors_key() -> str:
    key = os.environ.get("ORS_API_KEY", "").strip()
    if not key and ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("ORS_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    return key


def connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        sys.exit(f"Database not found: {db_path}\nRun `python -m app.seed` in backend/ first.")
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_depot(conn) -> tuple[float, float]:
    row = conn.execute("SELECT value FROM settings WHERE key = 'depot'").fetchone()
    if row is None:
        sys.exit("No depot in settings. Run `python -m app.seed` first.")
    depot = json.loads(row["value"]) if isinstance(row["value"], str) else row["value"]
    return float(depot["longitude"]), float(depot["latitude"])


def load_koharoute_plan(conn, day: str) -> list[dict]:
    routes = conn.execute(
        """SELECT r.id, r.vehicle_name, r.vehicle_plate_number, r.vehicle_capacity_kg,
                  r.vehicle_capacity_litres, r.total_distance_m, r.total_duration_s,
                  u.full_name AS driver
           FROM routes r JOIN users u ON u.id = r.driver_id
           WHERE r.pickup_date = ? ORDER BY r.id""",
        (day,),
    ).fetchall()
    plan = []
    for r in routes:
        stops = conn.execute(
            """SELECT b.reference FROM route_stops s JOIN bookings b ON b.id = s.booking_id
               WHERE s.route_id = ? ORDER BY s.sequence""",
            (r["id"],),
        ).fetchall()
        plan.append(
            {
                "driver": r["driver"],
                "vehicle": r["vehicle_plate_number"],
                "vehicle_name": r["vehicle_name"],
                "capacity_kg": r["vehicle_capacity_kg"],
                "capacity_l": r["vehicle_capacity_litres"],
                "stops": [s["reference"] for s in stops],
                "distance_m": r["total_distance_m"],
                "duration_s": r["total_duration_s"],
            }
        )
    return plan


def load_bookings(conn, day: str) -> dict[str, dict]:
    """Bookings on the date that were routed (Scheduled or later) or left Approved (unassigned)."""
    rows = conn.execute(
        """SELECT reference, address_text, latitude, longitude, estimated_weight_kg,
                  estimated_volume_l, status
           FROM bookings
           WHERE pickup_date = ? AND status IN ('approved','scheduled','completed','missed')
           ORDER BY id""",
        (day,),
    ).fetchall()
    return {
        r["reference"]: {
            "address": r["address_text"],
            "location": (float(r["longitude"]), float(r["latitude"])),
            "kg": int(r["estimated_weight_kg"]),
            "l": int(r["estimated_volume_l"]),
            "status": r["status"],
        }
        for r in rows
    }


# ----------------------------------------------------------------------------- distances
def ors_directions(key: str, coords: list[tuple[float, float]]) -> tuple[int, int]:
    body = json.dumps({"coordinates": [list(c) for c in coords]}).encode()
    request = urllib.request.Request(
        ORS_DIRECTIONS_URL,
        data=body,
        headers={"Authorization": key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        sys.exit(f"ORS Directions failed ({error.code}): {error.read().decode()[:300]}")
    except urllib.error.URLError as error:
        sys.exit(f"ORS could not be reached: {error.reason}")
    summary = data["routes"][0]["summary"]
    return round(summary.get("distance", 0)), round(summary.get("duration", 0))


def offline_estimate(coords: list[tuple[float, float]]) -> tuple[int, int]:
    """Straight-line x 1.4 at 40 km/h. Only for testing the script without a key; never report it."""
    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        p1, p2 = math.radians(lat1), math.radians(lat2)
        a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(
            math.radians(lon2 - lon1) / 2
        ) ** 2
        total += 2 * 6_371_000 * math.asin(math.sqrt(a)) * 1.4
    return round(total), round(total / (40_000 / 3600))


# ----------------------------------------------------------------------------- manual plan
def write_template(path: Path, kr_plan: list[dict], bookings: dict[str, dict], depot) -> None:
    template = {
        "planned_by": "WHO MADE THIS PLAN",
        "method": "HOW IT WAS MADE (for example: grouped by suburb on a paper map, no software)",
        "routes": [
            {"driver": r["driver"], "vehicle": r["vehicle"], "stops": []} for r in kr_plan
        ],
        "bookings_to_place": [
            {
                "reference": ref,
                "address": b["address"],
                "latitude": b["location"][1],
                "longitude": b["location"][0],
                "map": f"https://www.google.com/maps?q={b['location'][1]},{b['location'][0]}",
                "kg": b["kg"],
                "litres": b["l"],
            }
            for ref, b in bookings.items()
        ],
        "depot": {
            "latitude": depot[1],
            "longitude": depot[0],
            "map": f"https://www.google.com/maps?q={depot[1]},{depot[0]}",
        },
    }
    path.write_text(json.dumps(template, indent=2), encoding="utf-8")
    print(f"Template written to {path}")
    print("Put every booking reference into one route's \"stops\" list, in visiting order.")
    print("Plan it WITHOUT looking at the KohaRoute result, then run with --manual.")


def load_manual(path: Path, kr_plan: list[dict], bookings: dict[str, dict]) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    capacity = {r["vehicle"]: (r["capacity_kg"], r["capacity_l"], r["vehicle_name"]) for r in kr_plan}
    seen: list[str] = []
    for route in data["routes"]:
        if route["vehicle"] not in capacity:
            sys.exit(f"Manual plan uses vehicle {route['vehicle']}, which has no KohaRoute route that day.")
        for ref in route["stops"]:
            if ref not in bookings:
                sys.exit(f"Manual plan has unknown booking {ref} for this date.")
        seen += route["stops"]
    duplicates = {ref for ref in seen if seen.count(ref) > 1}
    if duplicates:
        sys.exit(f"These bookings are in the manual plan more than once: {sorted(duplicates)}")
    kr_routed = {ref for r in kr_plan for ref in r["stops"]}
    missing = kr_routed - set(seen)
    if missing:
        sys.exit(f"The manual plan must visit the same bookings as KohaRoute. Missing: {sorted(missing)}")
    for route in data["routes"]:
        route["capacity_kg"], route["capacity_l"], route["vehicle_name"] = capacity[route["vehicle"]]
    return data


# ----------------------------------------------------------------------------- comparison
def summarise(routes: list[dict], bookings: dict[str, dict]) -> dict:
    used = [r for r in routes if r["stops"]]
    loads = []
    over = False
    for r in used:
        kg = sum(bookings[ref]["kg"] for ref in r["stops"])
        litres = sum(bookings[ref]["l"] for ref in r["stops"])
        over |= kg > r["capacity_kg"] or litres > r["capacity_l"]
        loads.append(
            f"{r['vehicle']}: {kg}/{r['capacity_kg']} kg ({kg / r['capacity_kg']:.0%}), "
            f"{litres}/{r['capacity_l']} L ({litres / r['capacity_l']:.0%})"
        )
    return {
        "km": sum(r["distance_m"] for r in used) / 1000,
        "min": sum(r["duration_s"] for r in used) / 60,
        "stops": " / ".join(f"{r['vehicle']} {len(r['stops'])}" for r in used),
        "load": "; ".join(loads) + ("  OVER CAPACITY" if over else ""),
    }


def diff(manual: float, kr: float) -> str:
    change = kr - manual
    pct = f" ({change / manual:+.1%})" if manual else ""
    return f"{change:+.1f}{pct}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--date", required=True, help="Pickup date that has KohaRoute routes, YYYY-MM-DD")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--manual", type=Path, help="Manual plan JSON")
    parser.add_argument("--write-template", action="store_true", help="Write manual_plan.json to fill in")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "comparison_output")
    parser.add_argument("--offline-estimate", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    conn = connect(args.db)
    depot = load_depot(conn)
    kr_plan = load_koharoute_plan(conn, args.date)
    if not kr_plan:
        sys.exit(f"No KohaRoute routes on {args.date}. Click Generate on /admin/routes first.")
    bookings = load_bookings(conn, args.date)

    if args.write_template:
        write_template(args.manual or Path("manual_plan.json"), kr_plan, bookings, depot)
        return
    if not args.manual:
        sys.exit("Give --manual manual_plan.json (or --write-template to create one).")

    manual = load_manual(args.manual, kr_plan, bookings)
    key = load_ors_key()
    if not key and not args.offline_estimate:
        sys.exit("ORS_API_KEY not found in the environment or backend/.env.")
    for route in manual["routes"]:
        if not route["stops"]:
            route["distance_m"] = route["duration_s"] = 0
            continue
        coords = [depot] + [bookings[ref]["location"] for ref in route["stops"]] + [depot]
        measure = offline_estimate if args.offline_estimate else (lambda c: ors_directions(key, c))
        route["distance_m"], route["duration_s"] = measure(coords)

    m, k = summarise(manual["routes"], bookings), summarise(kr_plan, bookings)
    rows = [
        ("Total distance (km)", f"{m['km']:.1f}", f"{k['km']:.1f}", diff(m["km"], k["km"])),
        ("Total duration (minutes)", f"{m['min']:.0f}", f"{k['min']:.0f}", diff(m["min"], k["min"])),
        ("Stops per driver", m["stops"], k["stops"], "-"),
        ("Planned weight and volume against each vehicle's capacity", m["load"], k["load"], "-"),
    ]

    lines = [
        f"KohaRoute comparison for {args.date}",
        f"Bookings compared: {sum(len(r['stops']) for r in kr_plan)}  |  Depot: {depot[1]:.4f}, {depot[0]:.4f}",
        f"Manual plan by: {manual.get('planned_by', '-')}  |  Method: {manual.get('method', '-')}",
        "Distances and times: ORS driving-car road network for both plans (driving time only,",
        "no time at each stop). Weights and volumes are booking estimates.",
    ]
    if args.offline_estimate:
        lines.insert(0, "*** OFFLINE ESTIMATE (straight line x 1.4) - TEST ONLY, DO NOT REPORT ***")
    lines += ["", "Route detail:"]
    for label, plan in (("Manual", manual["routes"]), ("KohaRoute", kr_plan)):
        for r in plan:
            if r["stops"]:
                lines.append(
                    f"  {label:9} {r['vehicle']}: depot -> {' -> '.join(r['stops'])} -> depot  "
                    f"({r['distance_m'] / 1000:.1f} km, {r['duration_s'] / 60:.0f} min)"
                )
    md = ["| Measure | Manual plan | KohaRoute plan | Difference (KohaRoute - manual) |", "|---|---|---|---|"]
    md += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]

    print("\n".join(lines) + "\n\n" + "\n".join(md))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "comparison_result.md").write_text("\n".join(lines) + "\n\n" + "\n".join(md) + "\n", encoding="utf-8")
    with open(args.out_dir / "comparison_result.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Measure", "Manual plan", "KohaRoute plan", "Difference (KohaRoute - manual)"])
        writer.writerows(rows)
    print(f"\nSaved to {args.out_dir}/comparison_result.md and .csv")


if __name__ == "__main__":
    main()
