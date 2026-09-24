import io
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from geopy.geocoders import Nominatim

from utils import create_venue_graph, get_node_status, get_global_events, get_status_hex, format_number, node_type_icon
from simulation import CrowdSimulation
from routing import find_best_route, find_alternate_routes
from prediction import predict_future_congestion
from ui import inject_css, app_header, render_kpi_row, status_badge, alert_banner, STATUS_COLORS

try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False

st.set_page_config(page_title="VenuePulse-AI", layout="wide", page_icon="🏟️")
inject_css()

# ---------------------------------------------------------------
# Geocoder
# ---------------------------------------------------------------
@st.cache_data
def get_coordinates(location_name):
    try:
        geolocator = Nominatim(user_agent="VenuePulse_ai_bot")
        location = geolocator.geocode(location_name)
        if location:
            return location.latitude, location.longitude
    except Exception:
        pass
    return None, None


@st.cache_data
def haversine_km(lat1, lon1, lat2, lon2):
    import math
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(min(1, a ** 0.5))


# ---------------------------------------------------------------
# Session state
# ---------------------------------------------------------------
if 'current_event' not in st.session_state:
    st.session_state.current_event = 'MetLife Stadium (NY)'
    st.session_state.graph = create_venue_graph(st.session_state.current_event)
    st.session_state.sim = CrowdSimulation(st.session_state.graph)
    st.session_state.running = False
    st.session_state.route_source = 'Gate_A'
    st.session_state.route_target = 'Exit_N'
    st.session_state.live_mode = False

# ---------------------------------------------------------------
# Sidebar — global navigation
# ---------------------------------------------------------------
st.sidebar.markdown("### 🏟️ VenuePulse-AI")
app_mode = st.sidebar.radio("View", ["🌍 Global Tracker", "🏟️ Venue Simulation"], label_visibility="collapsed")
st.sidebar.markdown("---")

# =================================================================
# GLOBAL TRACKER
# =================================================================
if app_mode == "🌍 Global Tracker":
    app_header("Global Crowd Events Tracker", " VenuePulse-AI· WORLD VIEW")
    st.write("Live overview of major crowd events worldwide, with distance from your location.")

    st.sidebar.markdown("#### 📍 Your Location")
    user_location = st.sidebar.text_input("City, Country", "New Delhi, India", label_visibility="collapsed",
                                           placeholder="e.g. Mumbai, India")

    user_lat, user_lon = get_coordinates(user_location)
    if user_location and (user_lat is None):
        st.sidebar.caption("⚠️ Couldn't geocode that location — showing world view instead.")

    events = get_global_events()
    event_names = list(events.keys())
    lats = [events[e]['lat'] for e in event_names]
    lons = [events[e]['lon'] for e in event_names]
    types = [events[e]['type'] for e in event_names]

    # ---- KPI row ----
    kpi_items = [
        {"label": "Tracked Events", "value": str(len(events))},
        {"label": "Sports Events", "value": str(sum(1 for t in types if t == "Sports"))},
        {"label": "Concerts", "value": str(sum(1 for t in types if t == "Concert"))},
    ]
    if user_lat and user_lon:
        nearest = min(event_names, key=lambda e: haversine_km(user_lat, user_lon, events[e]['lat'], events[e]['lon']))
        nearest_km = haversine_km(user_lat, user_lon, events[nearest]['lat'], events[nearest]['lon'])
        kpi_items.append({"label": "Nearest Event", "value": nearest.split('(')[0].strip(),
                           "sub": f"{format_number(nearest_km)} km away"})
    else:
        kpi_items.append({"label": "Nearest Event", "value": "—", "sub": "Enter a location to compute"})
    render_kpi_row(kpi_items)
    st.write("")

    # ---- Map ----
    map_data = [
        go.Scattermapbox(
            lat=lats, lon=lons,
            mode='markers+text',
            marker=dict(size=15, color='#FF3D00', symbol='circle'),
            text=event_names,
            textposition="top right",
            hoverinfo='text',
            name='Live Events',
        )
    ]
    if user_lat and user_lon:
        map_data.append(go.Scattermapbox(
            lat=[user_lat], lon=[user_lon],
            mode='markers+text',
            marker=dict(size=20, color='#00E676', symbol='star'),
            text=["Your Location"],
            textposition="bottom center",
            hoverinfo='text',
            name='You',
        ))

    center_lat = user_lat if user_lat else 20.0
    center_lon = user_lon if user_lon else 0.0

    fig = go.Figure(data=map_data, layout=go.Layout(
        mapbox_style="carto-darkmatter",
        mapbox_center={"lat": center_lat, "lon": center_lon},
        mapbox_zoom=2 if not (user_lat and user_lon) else 1.5,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        height=560,
        showlegend=True,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#F5F7FA")),
        paper_bgcolor='rgba(0,0,0,0)',
    ))
    st.plotly_chart(fig, use_container_width=True)

    # ---- Distance table ----
    if user_lat and user_lon:
        with st.expander("📏 Distance to every tracked event", expanded=False):
            rows = []
            for e in event_names:
                km = haversine_km(user_lat, user_lon, events[e]['lat'], events[e]['lon'])
                rows.append({"Event": e, "Type": events[e]['type'], "Capacity": format_number(events[e]['capacity']),
                             "Distance (km)": round(km, 1)})
            df = pd.DataFrame(rows).sort_values("Distance (km)")
            st.dataframe(df, use_container_width=True, hide_index=True)

    alert_banner("Switch to Venue Simulation to see live crowd flow, predictive alerts and smart routing inside any of these venues.", "ok")

# =================================================================
# VENUE SIMULATION
# =================================================================
elif app_mode == "🏟️ Venue Simulation":
    events = get_global_events()

    # ---- Sidebar: event + controls ----
    with st.sidebar.expander("🎪 Event", expanded=True):
        selected_event = st.selectbox("Global Event", list(events.keys()),
                                       index=list(events.keys()).index(st.session_state.current_event))
        if selected_event != st.session_state.current_event:
            st.session_state.current_event = selected_event
            st.session_state.graph = create_venue_graph(selected_event)
            st.session_state.sim = CrowdSimulation(st.session_state.graph)
            st.rerun()

    with st.sidebar.expander("▶️ Simulation Controls", expanded=True):
        entry_rate = st.slider("Entry Rate (people/step)", 10, 500, 100, key='entry_rate')
        speed = st.slider("Movement Speed", 0.5, 2.0, 1.0, 0.1, key='speed')

        c1, c2 = st.columns(2)
        step_clicked = c1.button("⏭️ Step", use_container_width=True)
        reset_clicked = c2.button("🔄 Reset", use_container_width=True)

        if AUTOREFRESH_AVAILABLE:
            st.session_state.live_mode = st.toggle("🔴 Live Mode (auto-step)", value=st.session_state.live_mode)
            if st.session_state.live_mode:
                refresh_ms = st.slider("Refresh interval (sec)", 1, 10, 2) * 1000
                st_autorefresh(interval=refresh_ms, key="live_autorefresh")
        else:
            st.caption("💡 Install `streamlit-autorefresh` to enable one-click Live Mode.")

        if step_clicked or st.session_state.live_mode:
            st.session_state.running = True
            st.session_state.sim.step(entry_rate=entry_rate, movement_speed_multiplier=speed)
        if reset_clicked:
            st.session_state.sim = CrowdSimulation(st.session_state.graph)
            st.session_state.live_mode = False

    with st.sidebar.expander("🧭 Routing", expanded=True):
        zones = list(st.session_state.graph.nodes())
        if st.session_state.route_source not in zones:
            st.session_state.route_source = zones[0]
        if st.session_state.route_target not in zones:
            st.session_state.route_target = zones[-1]

        src_idx = zones.index(st.session_state.route_source)
        tgt_idx = zones.index(st.session_state.route_target)
        st.session_state.route_source = st.selectbox(
            "Start Zone", zones, index=src_idx,
            format_func=lambda x: f"{node_type_icon(st.session_state.graph.nodes[x]['type'])} {st.session_state.graph.nodes[x]['name']}")
        st.session_state.route_target = st.selectbox(
            "Destination Zone", zones, index=tgt_idx,
            format_func=lambda x: f"{node_type_icon(st.session_state.graph.nodes[x]['type'])} {st.session_state.graph.nodes[x]['name']}")

    # ---- Core computations ----
    G = st.session_state.graph
    sim = st.session_state.sim
    routes = find_alternate_routes(G, sim.node_counts, st.session_state.route_source, st.session_state.route_target, k=2)
    best_path = routes[0]['path'] if routes else None
    predictions, risks, trends = predict_future_congestion(sim.history, G, steps_ahead=5)

    # ---- Header ----
    app_header(st.session_state.current_event, "VenuePulse-AI · VENUE SIMULATION", live=st.session_state.live_mode)

    # ---- KPI row ----
    peak_node, peak_count = sim.peak_zone()
    peak_name = G.nodes[peak_node]['name'] if peak_node else "—"
    n_alerts = sum(1 for r in risks.values() if "High" in r or "Critical" in r)
    render_kpi_row([
        {"label": "Inside Venue Now", "value": format_number(sim.total_inside)},
        {"label": "Total Entries", "value": format_number(sim.total_arrivals)},
        {"label": "Total Exited", "value": format_number(sim.total_exited)},
        {"label": "Busiest Zone", "value": peak_name, "sub": f"{format_number(peak_count)} people"},
        {"label": "Active Alerts", "value": str(n_alerts), "sub": f"Step {sim.step_count}"},
    ])
    st.write("")

    tab_map, tab_analytics, tab_routing, tab_zones = st.tabs(
        ["🗺️ Live Map", "📊 Analytics", "🧭 Routing", "📋 Zone Details"]
    )

    # -------------------------------------------------------------
    # TAB: Live Map
    # -------------------------------------------------------------
    with tab_map:
        edge_lat, edge_lon = [], []
        for edge in G.edges():
            lat0, lon0 = G.nodes[edge[0]]['lat'], G.nodes[edge[0]]['lon']
            lat1, lon1 = G.nodes[edge[1]]['lat'], G.nodes[edge[1]]['lon']
            edge_lat.extend([lat0, lat1, None])
            edge_lon.extend([lon0, lon1, None])

        edge_trace = go.Scattermapbox(lat=edge_lat, lon=edge_lon, line=dict(width=1, color='#3A4358'),
                                       hoverinfo='none', mode='lines', name='Walkways')

        path_lat, path_lon = [], []
        if best_path:
            for i in range(len(best_path) - 1):
                lat0, lon0 = G.nodes[best_path[i]]['lat'], G.nodes[best_path[i]]['lon']
                lat1, lon1 = G.nodes[best_path[i + 1]]['lat'], G.nodes[best_path[i + 1]]['lon']
                path_lat.extend([lat0, lat1, None])
                path_lon.extend([lon0, lon1, None])

        path_trace = go.Scattermapbox(lat=path_lat, lon=path_lon, line=dict(width=4, color='#00E676'),
                                       hoverinfo='none', mode='lines', name='Recommended Route')

        node_lat, node_lon, node_text, node_color, node_size = [], [], [], [], []
        for node in G.nodes():
            node_lat.append(G.nodes[node]['lat'])
            node_lon.append(G.nodes[node]['lon'])
            count = sim.node_counts[node]
            cap = G.nodes[node]['capacity']
            status, color_key = get_node_status(count, cap)
            node_text.append(f"{G.nodes[node]['name']}<br>People: {count}/{cap}<br>Status: {status}")
            node_color.append(get_status_hex(color_key))
            size = min(32, max(11, (count / cap) * 30 + 11)) if cap > 0 else 11
            node_size.append(size)

        node_trace = go.Scattermapbox(
            lat=node_lat, lon=node_lon, mode='markers+text',
            text=[G.nodes[n]['name'] for n in G.nodes()],
            textposition="top center", hoverinfo='text', hovertext=node_text,
            marker=dict(color=node_color, size=node_size),
            name='Zones',
        )

        event_base_lat = events[st.session_state.current_event]['lat']
        event_base_lon = events[st.session_state.current_event]['lon']

        fig = go.Figure(data=[edge_trace, path_trace, node_trace], layout=go.Layout(
            showlegend=False, hovermode='closest', margin=dict(b=0, l=0, r=0, t=0),
            mapbox=dict(style="carto-darkmatter", center=dict(lat=event_base_lat, lon=event_base_lon), zoom=16),
            paper_bgcolor='rgba(0,0,0,0)', height=560,
        ))
        st.plotly_chart(fig, use_container_width=True)

        legend_cols = st.columns(4)
        for col, (key, label) in zip(legend_cols, [("green", "Low"), ("yellow", "Medium"), ("orange", "High"), ("red", "Critical")]):
            col.markdown(status_badge(key) + f" {label}", unsafe_allow_html=True)

        # Alerts feed
        st.markdown("##### ⚠️ Live Alerts")
        alert_rows = [(n, r) for n, r in risks.items() if "High" in r or "Critical" in r]
        if not alert_rows:
            alert_banner("All zones are operating within safe limits.", "ok")
        else:
            for n, r in sorted(alert_rows, key=lambda x: "Critical" not in x[1]):
                level = "critical" if "Critical" in r else "warning"
                trend_arrow = {"up": "↗ rising", "down": "↘ falling", "stable": "→ stable"}[trends[n]]
                alert_banner(f"<b>{G.nodes[n]['name']}</b> — {r} · projected {trend_arrow} "
                             f"(next: {format_number(predictions[n][-1])} people)", level)

    # -------------------------------------------------------------
    # TAB: Analytics
    # -------------------------------------------------------------
    with tab_analytics:
        if len(sim.history) < 2:
            st.info("Run a few simulation steps to unlock trend charts and predictions.")
        else:
            hist_df = pd.DataFrame(sim.history)
            hist_df.index.name = "step"
            hist_df = hist_df.reset_index()

            left, right = st.columns([3, 2])

            with left:
                st.markdown("##### Occupancy Over Time")
                zones_to_plot = st.multiselect(
                    "Zones to chart", list(G.nodes()),
                    default=[peak_node] if peak_node else list(G.nodes())[:3],
                    format_func=lambda x: G.nodes[x]['name'],
                )
                if zones_to_plot:
                    plot_df = hist_df.melt(id_vars="step", value_vars=zones_to_plot,
                                            var_name="zone", value_name="people")
                    plot_df["zone"] = plot_df["zone"].map(lambda z: G.nodes[z]['name'])
                    line_fig = px.line(plot_df, x="step", y="people", color="zone", markers=True)
                    line_fig.update_layout(
                        height=380, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color="#F5F7FA"), legend=dict(orientation="h", y=-0.25),
                        margin=dict(t=10, b=10, l=10, r=10),
                    )
                    line_fig.update_xaxes(gridcolor="#262E3D")
                    line_fig.update_yaxes(gridcolor="#262E3D")
                    st.plotly_chart(line_fig, use_container_width=True)

            with right:
                st.markdown("##### Current Load by Zone")
                bar_df = pd.DataFrame([
                    {"Zone": G.nodes[n]['name'], "People": sim.node_counts[n],
                     "Capacity": G.nodes[n]['capacity']}
                    for n in G.nodes()
                ]).sort_values("People", ascending=True)
                bar_fig = px.bar(bar_df, x="People", y="Zone", orientation="h")
                bar_fig.update_traces(marker_color="#00E676")
                bar_fig.update_layout(
                    height=380, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color="#F5F7FA"), margin=dict(t=10, b=10, l=10, r=10),
                )
                bar_fig.update_xaxes(gridcolor="#262E3D")
                bar_fig.update_yaxes(gridcolor="#262E3D")
                st.plotly_chart(bar_fig, use_container_width=True)

            st.markdown("##### 5-Step Forecast (per zone)")
            forecast_rows = []
            for n in G.nodes():
                forecast_rows.append({
                    "Zone": G.nodes[n]['name'],
                    "Now": sim.node_counts[n],
                    "+5 steps": predictions[n][-1],
                    "Trend": {"up": "↗", "down": "↘", "stable": "→"}[trends[n]],
                    "Risk": risks[n],
                })
            st.dataframe(pd.DataFrame(forecast_rows), use_container_width=True, hide_index=True)

            # Export
            csv_buf = io.StringIO()
            hist_df.to_csv(csv_buf, index=False)
            st.download_button(
                "⬇️ Download Simulation History (CSV)",
                data=csv_buf.getvalue(),
                file_name=f"VenuePulse_{st.session_state.current_event.split(' ')[0]}_{datetime.now():%Y%m%d_%H%M}.csv",
                mime="text/csv",
            )

    # -------------------------------------------------------------
    # TAB: Routing
    # -------------------------------------------------------------
    with tab_routing:
        st.markdown("##### 🧠 Congestion-Aware Route Options")
        if not routes:
            st.warning("No path found between the selected zones.")
        else:
            route_cols = st.columns(len(routes))
            for i, (col, r) in enumerate(zip(route_cols, routes)):
                with col:
                    tag = "🏆 Best Route" if i == 0 else f"Alternate {i}"
                    st.markdown(f"**{tag}**")
                    chips = ""
                    for j, node in enumerate(r['path']):
                        chips += f'<span class="route-chip">{node_type_icon(G.nodes[node]["type"])} {G.nodes[node]["name"]}</span>'
                        if j < len(r['path']) - 1:
                            chips += '<span class="route-arrow">→</span>'
                    st.markdown(chips, unsafe_allow_html=True)
                    st.metric("Estimated Walk Time", f"{r['eta_minutes']} min")
                    st.caption(f"{r['hops']} hops · congestion cost {r['congestion_cost']}")

        st.markdown("---")
        st.markdown("##### Compare Routes")
        if routes:
            comp_df = pd.DataFrame([
                {"Route": "Best" if i == 0 else f"Alternate {i}",
                 "Zones": " → ".join(G.nodes[n]['name'] for n in r['path']),
                 "Hops": r['hops'], "ETA (min)": r['eta_minutes'], "Congestion Cost": r['congestion_cost']}
                for i, r in enumerate(routes)
            ])
            st.dataframe(comp_df, use_container_width=True, hide_index=True)

    # -------------------------------------------------------------
    # TAB: Zone Details
    # -------------------------------------------------------------
    with tab_zones:
        st.markdown("##### 📋 All Zones")
        rows = []
        for n, attrs in G.nodes(data=True):
            count = sim.node_counts[n]
            cap = attrs['capacity']
            status, color_key = get_node_status(count, cap)
            rows.append({
                "Zone": f"{node_type_icon(attrs['type'])} {attrs['name']}",
                "Type": attrs['type'].title(),
                "People": count,
                "Capacity": cap,
                "Utilization": f"{(count / cap * 100) if cap else 0:.0f}%",
                "Status": status,
                "Trend": {"up": "↗ Rising", "down": "↘ Falling", "stable": "→ Stable"}[trends.get(n, "stable")],
            })
        zone_df = pd.DataFrame(rows).sort_values("People", ascending=False)
        st.dataframe(
            zone_df, use_container_width=True, hide_index=True,
            column_config={
                "Utilization": st.column_config.ProgressColumn(
                    "Utilization", min_value=0, max_value=100, format="%d%%"
                ),
            },
        )
