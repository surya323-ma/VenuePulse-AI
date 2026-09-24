# 🏟️ VenuePulse-AI

Predictive crowd-flow monitoring and smart routing for large-scale event venues, plus a
global tracker of major live events.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

`streamlit-autorefresh` is optional — the app runs fine without it, it just enables the
one-click **Live Mode** toggle (auto-stepping the simulation on a timer). Without it,
step the simulation manually with the **Step** button.

## What's in the project

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI — Global Tracker + Venue Simulation, in tabs |
| `ui.py` | **New.** Design system: CSS, KPI cards, badges, alert banners |
| `utils.py` | Venue graph construction, status helpers, formatting helpers |
| `simulation.py` | Step-based crowd movement model |
| `routing.py` | Congestion-aware pathfinding, now with alternate routes + ETA |
| `prediction.py` | Linear-regression short-term congestion forecast, now with trend direction |
| `requirements.txt` | Dependencies |

## What was added on top of the original app

**New features**
- **KPI dashboard** — people inside now, total entries, total exits, busiest zone, active alert count.
- **Tabbed layout** (Live Map / Analytics / Routing / Zone Details) instead of two cramped columns — each concern gets room to breathe.
- **Live Mode** — auto-steps the simulation on a timer instead of manual clicking only.
- **Alternate routing** — shows the best route *and* a backup, each with hop count, congestion cost, and an estimated walk time (not just a plain node list).
- **Trend-aware forecasting** — predictions now say whether a zone is rising, falling, or stable, not just its raw number.
- **Analytics tab** — occupancy-over-time line chart (pick any zones to compare), a live load bar chart, a 5-step forecast table, and CSV export of the simulation history.
- **Zone Details tab** — sortable table of every zone with a visual utilization progress bar.
- **Global Tracker upgrades** — KPI row (event counts, nearest event with live distance calculation via haversine), and a distance table to every tracked event.
- **Live/Paused status pill** in the header so it's always clear whether the sim is running.

**Backend fixes/improvements**
- `simulation.py` now tracks cumulative arrivals/exits and exposes `total_inside` / `peak_zone()` instead of the UI having to recompute this inline.
- `routing.py` adds `find_alternate_routes()` (Yen's algorithm via `nx.shortest_simple_paths`) and an ETA estimate; the original `find_best_route()` is untouched for backward compatibility.
- `prediction.py` now returns a third `trends` dict alongside `predictions` and `risks`.
- History buffer extended from 10 → 30 steps so trend charts have enough data to be meaningful.

**UI/UX**
- Full dark design system in `ui.py`: consistent color tokens, card components, status badges, alert banners, animated "live" indicator — instead of two inline CSS classes.
- Sidebar reorganized into collapsible sections (Event / Simulation Controls / Routing) so it doesn't read as one long unlabeled stack of widgets.
- Map legend added so marker colors are self-explanatory without hovering.
- Route steps shown as connected chips with zone-type icons instead of a plain arrow-joined string.
