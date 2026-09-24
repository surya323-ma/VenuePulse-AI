import networkx as nx

# Rough average walking speed inside a dense venue (meters/"distance-unit" per minute).
# The venue graph's `distance` values are treated as arbitrary walkway-length units;
# this constant only needs to be internally consistent to produce a plausible ETA.
WALK_UNITS_PER_MINUTE = 20.0


def calculate_weight(u, v, d, G, node_counts):
    """
    Calculate dynamic edge weight based on base distance and destination node congestion.
    """
    base_dist = d['distance']
    dest_count = node_counts.get(v, 0)
    dest_capacity = G.nodes[v]['capacity']

    ratio = dest_count / dest_capacity if dest_capacity > 0 else 1.0
    penalty = 1.0
    if ratio > 0.9:
        penalty = 10.0
    elif ratio > 0.7:
        penalty = 3.0
    elif ratio > 0.4:
        penalty = 1.5

    return base_dist * penalty


def find_best_route(G, node_counts, source, target):
    """
    Finds the optimal path between source and target taking actual congestion into account.
    """
    try:
        path = nx.shortest_path(
            G, source=source, target=target,
            weight=lambda u, v, d: calculate_weight(u, v, d, G, node_counts)
        )
        return path
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None


def _path_stats(G, node_counts, path):
    raw_distance = 0
    congestion_cost = 0
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        d = G.get_edge_data(u, v)
        raw_distance += d['distance']
        congestion_cost += calculate_weight(u, v, d, G, node_counts)
    eta_minutes = raw_distance / WALK_UNITS_PER_MINUTE
    return {
        'path': path,
        'hops': len(path) - 1,
        'raw_distance': raw_distance,
        'congestion_cost': round(congestion_cost, 1),
        'eta_minutes': round(eta_minutes, 1),
    }


def find_alternate_routes(G, node_counts, source, target, k=2):
    """
    Returns up to `k` congestion-aware route options (best first), each as a dict with
    path, hop count, raw distance, congestion-weighted cost, and an ETA estimate.
    Falls back to a single route if no alternates exist.
    """
    if source == target:
        return []

    H = G.copy()
    for u, v, d in H.edges(data=True):
        d['dyn_weight'] = calculate_weight(u, v, d, G, node_counts)

    routes = []
    try:
        for i, path in enumerate(nx.shortest_simple_paths(H, source, target, weight='dyn_weight')):
            if i >= k:
                break
            routes.append(_path_stats(G, node_counts, path))
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []

    return routes
