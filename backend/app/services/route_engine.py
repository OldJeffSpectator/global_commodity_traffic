"""
V2 Route Engine: Uses a simplified strategic maritime graph (~60 key waypoints along
major shipping lanes) combined with land borders and railway corridors.
Runs Dijkstra on this compact graph for fast route computation.
"""
import os
import json
import heapq
import math
from typing import Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")

COST_OCEAN_PER_KM = 0.5
COST_STRAIT_PER_KM = 0.6
COST_CANAL_PER_KM = 1.5
COST_LAND_BORDER_PER_KM = 5.0
COST_RAILWAY_PER_KM = 2.0
COST_PORT_ACCESS_PER_KM = 1.0

LAND_BORDERS = [
    ("USA", "CAN"), ("USA", "MEX"), ("CHN", "RUS"), ("CHN", "KAZ"),
    ("CHN", "MNG"), ("CHN", "VNM"), ("CHN", "IND"), ("CHN", "PAK"),
    ("RUS", "KAZ"), ("RUS", "BLR"), ("RUS", "POL"), ("RUS", "UKR"),
    ("BLR", "POL"), ("POL", "DEU"), ("DEU", "FRA"), ("DEU", "NLD"),
    ("DEU", "BEL"), ("DEU", "CHE"), ("FRA", "ESP"), ("FRA", "ITA"),
    ("FRA", "BEL"), ("IND", "PAK"), ("IND", "BGD"), ("TUR", "IRN"),
    ("TUR", "IRQ"), ("SAU", "IRQ"), ("SAU", "ARE"), ("EGY", "ISR"),
    ("BRA", "ARG"), ("ARG", "CHL"), ("COL", "VEN"), ("MEX", "GTM"),
    ("THA", "MYS"), ("THA", "VNM"), ("KAZ", "UZB"), ("NOR", "SWE"),
    ("SWE", "FIN"), ("ITA", "CHE"), ("ESP", "PRT"), ("ZAF", "MOZ"),
    ("ZAF", "NAM"), ("NGA", "NER"), ("KOR", "PRK"), ("JPN", "KOR"),
    ("IDN", "MYS"), ("SGP", "MYS"), ("AUS", "IDN"), ("NZL", "AUS"),
    ("GBR", "FRA"), ("GBR", "IRL"), ("RUS", "FIN"), ("RUS", "MNG"),
    ("IRN", "PAK"), ("IRN", "IRQ"), ("EGY", "SDN"), ("SAU", "YEM"),
    ("TUR", "GRC"), ("TUR", "BGR"), ("ITA", "AUT"), ("DEU", "AUT"),
    ("DEU", "POL"), ("DEU", "CZE"), ("CZE", "AUT"), ("AUT", "HUN"),
    ("HUN", "UKR"), ("UKR", "POL"), ("ROU", "UKR"), ("ROU", "HUN"),
]

RAILWAY_CORRIDORS = {
    ("CHN", "KAZ"): "China-Europe Railway",
    ("KAZ", "RUS"): "China-Europe Railway",
    ("RUS", "BLR"): "China-Europe Railway",
    ("BLR", "POL"): "China-Europe Railway",
    ("POL", "DEU"): "China-Europe Railway",
    ("USA", "CAN"): "NAFTA Corridor",
    ("USA", "MEX"): "NAFTA Corridor",
}

# Strategic maritime waypoints along major shipping lanes
# (id, lat, lng, name)
MARITIME_WAYPOINTS = [
    # Atlantic Ocean
    (1, 40.0, -40.0, "North Atlantic Central"),
    (2, 10.0, -30.0, "Central Atlantic"),
    (3, -20.0, -20.0, "South Atlantic"),
    (4, 50.0, -20.0, "North Atlantic East"),
    (5, 35.0, -70.0, "North Atlantic West"),
    # Mediterranean & Approaches
    (6, 36.0, -6.0, "Strait of Gibraltar"),
    (7, 37.0, 5.0, "Western Mediterranean"),
    (8, 35.0, 20.0, "Central Mediterranean"),
    (9, 34.0, 30.0, "Eastern Mediterranean"),
    # Suez & Red Sea
    (10, 30.0, 32.5, "Suez Canal"),
    (11, 20.0, 38.0, "Red Sea"),
    (12, 12.5, 43.5, "Bab el-Mandeb"),
    # Indian Ocean
    (13, 10.0, 55.0, "Western Indian Ocean"),
    (14, 0.0, 70.0, "Central Indian Ocean"),
    (15, -10.0, 85.0, "Eastern Indian Ocean"),
    (16, -30.0, 60.0, "South Indian Ocean"),
    # Persian Gulf & Hormuz
    (17, 26.0, 56.5, "Strait of Hormuz"),
    (18, 27.0, 50.0, "Persian Gulf"),
    # Southeast Asia & Malacca
    (19, 1.5, 104.0, "Strait of Malacca (East)"),
    (20, 5.0, 98.0, "Strait of Malacca (West)"),
    (21, 5.0, 110.0, "South China Sea (South)"),
    (22, 15.0, 115.0, "South China Sea (Central)"),
    (23, 22.0, 118.0, "South China Sea (North)"),
    # East Asia
    (24, 30.0, 125.0, "East China Sea"),
    (25, 35.0, 130.0, "Sea of Japan / Korea Strait"),
    (26, 40.0, 140.0, "Northwest Pacific"),
    # Pacific Ocean
    (27, 35.0, 170.0, "North Pacific Central"),
    (28, 0.0, -150.0, "Central Pacific"),
    (29, 35.0, -140.0, "Northeast Pacific"),
    (30, -20.0, -120.0, "South Pacific"),
    (31, -35.0, 160.0, "Southwest Pacific"),
    # North America West Coast
    (32, 45.0, -125.0, "US/Canada Pacific"),
    (33, 30.0, -118.0, "US West Coast South"),
    # North America East Coast
    (34, 40.0, -72.0, "US East Coast"),
    (35, 30.0, -80.0, "US Southeast Coast"),
    # Caribbean & Panama
    (36, 20.0, -80.0, "Caribbean Sea"),
    (37, 9.0, -79.5, "Panama Canal"),
    # South America
    (38, -5.0, -35.0, "Brazil Coast"),
    (39, -35.0, -55.0, "Rio de la Plata"),
    (40, -55.0, -68.0, "Cape Horn"),
    # Africa
    (41, -34.0, 18.0, "Cape of Good Hope"),
    (42, 5.0, 0.0, "Gulf of Guinea"),
    (43, 15.0, -17.0, "West Africa"),
    # Northern Europe
    (44, 52.0, 4.0, "North Sea"),
    (45, 55.0, 12.0, "Baltic Approaches"),
    (46, 60.0, 20.0, "Baltic Sea"),
    (47, 58.0, -5.0, "North Sea (North)"),
    # Australia
    (48, -25.0, 150.0, "East Australia"),
    (49, -32.0, 115.0, "West Australia"),
    (50, -10.0, 130.0, "North Australia"),
    # Arctic/Sub-Arctic
    (51, 65.0, 30.0, "Barents Sea"),
    (52, 70.0, 170.0, "Bering Strait"),
    # Indonesia passages
    (53, -5.0, 115.0, "Java Sea"),
    (54, -8.0, 120.0, "Lombok Strait"),
]

# Connectivity between maritime waypoints (id_a, id_b)
MARITIME_EDGES = [
    # Trans-Atlantic
    (1, 2), (1, 4), (1, 5), (2, 3), (2, 38), (3, 41), (3, 38), (4, 6), (4, 44),
    (4, 47), (5, 34), (5, 35), (5, 1),
    # Mediterranean
    (6, 7), (7, 8), (8, 9), (9, 10),
    # Suez - Red Sea - Indian
    (10, 11), (11, 12), (12, 13), (13, 14), (14, 15),
    # Indian Ocean
    (13, 16), (16, 41), (15, 20), (14, 17),
    # Persian Gulf
    (17, 18), (17, 13),
    # Malacca & SE Asia
    (20, 19), (19, 21), (21, 22), (22, 23), (23, 24),
    # East Asia
    (24, 25), (25, 26), (26, 27),
    # Pacific crossings
    (27, 29), (27, 28), (29, 32), (29, 33), (28, 30), (30, 31),
    # US coasts
    (32, 33), (34, 35), (35, 36), (33, 37),
    # Panama & Caribbean
    (36, 37), (37, 40), (37, 38), (36, 5),
    # South America
    (38, 39), (39, 40), (40, 30),
    # Africa
    (41, 42), (42, 43), (43, 2), (41, 16), (41, 49),
    # Northern Europe
    (44, 45), (45, 46), (44, 47), (47, 4),
    # Australia
    (48, 31), (48, 50), (49, 15), (49, 50), (50, 53), (50, 54),
    # Indonesia
    (53, 19), (53, 21), (54, 15), (54, 53),
    # Arctic connections
    (46, 51), (51, 52), (52, 27),
    # East Asia - Pacific
    (26, 32), (24, 48),
    # Cross-connections
    (15, 49), (16, 49),
    (42, 6), (43, 6),
    (35, 38), (36, 38),
    (1, 34), (44, 6),
]


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class TradeRouteGraph:
    def __init__(self):
        self.nodes: dict[int, tuple[float, float]] = {}  # id -> (lat, lng)
        self.adj: dict[int, list[tuple[int, float]]] = {}
        self.country_port_nodes: dict[str, int] = {}
        self._next_id = 1000

    def _add_node(self, node_id: int, lat: float, lng: float):
        self.nodes[node_id] = (lat, lng)
        if node_id not in self.adj:
            self.adj[node_id] = []
        self._next_id = max(self._next_id, node_id + 1)

    def _add_edge(self, from_id: int, to_id: int, cost: float):
        self.adj[from_id].append((to_id, cost))
        self.adj[to_id].append((from_id, cost))

    def _new_node_id(self) -> int:
        nid = self._next_id
        self._next_id += 1
        return nid

    def load_strategic_waypoints(self):
        """Load the simplified strategic maritime waypoints."""
        for wp_id, lat, lng, name in MARITIME_WAYPOINTS:
            self._add_node(wp_id, lat, lng)

        edges_added = 0
        for id_a, id_b in MARITIME_EDGES:
            if id_a in self.nodes and id_b in self.nodes:
                lat_a, lng_a = self.nodes[id_a]
                lat_b, lng_b = self.nodes[id_b]
                dist_km = haversine_km(lat_a, lng_a, lat_b, lng_b)
                cost = dist_km * COST_OCEAN_PER_KM
                self._add_edge(id_a, id_b, cost)
                edges_added += 1

        print(f"[RouteEngine] Loaded {len(MARITIME_WAYPOINTS)} strategic waypoints, {edges_added} sea edges")

    def _find_nearest_waypoint(self, lat: float, lng: float, max_dist_km: float = 8000.0) -> Optional[int]:
        """Find the nearest maritime waypoint to a given lat/lng."""
        best_id = None
        best_dist = max_dist_km
        for nid in range(1, 55):  # Only search maritime waypoints (IDs 1-54)
            if nid not in self.nodes:
                continue
            nlat, nlng = self.nodes[nid]
            dist = haversine_km(lat, lng, nlat, nlng)
            if dist < best_dist:
                best_dist = dist
                best_id = nid
        return best_id

    def add_country_ports(self, countries: list[dict]):
        """Add port node for each country, connected to nearest maritime waypoint."""
        for country in countries:
            iso3 = country["iso3"]
            lat = country["centroid_lat"]
            lng = country["centroid_lng"]

            nearest = self._find_nearest_waypoint(lat, lng)
            if nearest is None:
                continue

            port_id = self._new_node_id()
            self._add_node(port_id, lat, lng)
            self.country_port_nodes[iso3] = port_id

            nlat, nlng = self.nodes[nearest]
            dist_km = haversine_km(lat, lng, nlat, nlng)
            cost = dist_km * COST_PORT_ACCESS_PER_KM
            self._add_edge(port_id, nearest, cost)

        print(f"[RouteEngine] Added {len(self.country_port_nodes)} country port nodes")

    def add_land_borders(self):
        """Add land border edges between adjacent countries."""
        added = 0
        for iso_a, iso_b in LAND_BORDERS:
            if iso_a not in self.country_port_nodes or iso_b not in self.country_port_nodes:
                continue

            node_a = self.country_port_nodes[iso_a]
            node_b = self.country_port_nodes[iso_b]
            lat_a, lng_a = self.nodes[node_a]
            lat_b, lng_b = self.nodes[node_b]
            dist_km = haversine_km(lat_a, lng_a, lat_b, lng_b)

            pair = (iso_a, iso_b)
            pair_rev = (iso_b, iso_a)
            if pair in RAILWAY_CORRIDORS or pair_rev in RAILWAY_CORRIDORS:
                cost = dist_km * COST_RAILWAY_PER_KM
            else:
                cost = dist_km * COST_LAND_BORDER_PER_KM

            self._add_edge(node_a, node_b, cost)
            added += 1

        print(f"[RouteEngine] Added {added} land border edges")

    def dijkstra(self, start_iso3: str, end_iso3: str) -> Optional[tuple[list[int], float]]:
        """Run Dijkstra from start country to end country."""
        if start_iso3 not in self.country_port_nodes or end_iso3 not in self.country_port_nodes:
            return None

        start = self.country_port_nodes[start_iso3]
        end = self.country_port_nodes[end_iso3]

        if start == end:
            return ([start], 0.0)

        dist = {start: 0.0}
        prev: dict[int, int] = {}
        heap = [(0.0, start)]

        while heap:
            d, u = heapq.heappop(heap)
            if u == end:
                break
            if d > dist.get(u, float("inf")):
                continue
            for v, w in self.adj.get(u, []):
                nd = d + w
                if nd < dist.get(v, float("inf")):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(heap, (nd, v))

        if end not in dist:
            return None

        path = []
        node = end
        while node != start:
            path.append(node)
            if node not in prev:
                return None
            node = prev[node]
        path.append(start)
        path.reverse()

        return (path, dist[end])

    def get_path_coordinates(self, path: list[int]) -> list[tuple[float, float]]:
        """Convert path node IDs to list of (lat, lng) coordinates."""
        coords = []
        for nid in path:
            if nid in self.nodes:
                lat, lng = self.nodes[nid]
                coords.append((lat, lng))
        return coords


def build_graph(countries: list[dict]) -> TradeRouteGraph:
    """Build the complete trade route graph."""
    graph = TradeRouteGraph()
    graph.load_strategic_waypoints()
    graph.add_country_ports(countries)
    graph.add_land_borders()
    return graph
