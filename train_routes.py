import os
import re
from collections import defaultdict, deque

class Route:
    def __init__(self, start, end, code, duration, stops, tag=None):
        self.start = start
        self.end = end
        self.code = code
        self.duration = duration
        self.stops = stops
        self.tag = tag

    def __repr__(self):
        return f"{self.code}: {self.start} <> {self.end} ({self.duration} minutes, {self.stops} stops{f' | {self.tag}' if self.tag else ''})"

    def other_end(self, station):
        return self.end if station == self.start else self.start

def parse_route_line(line):
    match = re.match(r"(.+?) <> (.+?) \((R\d{3})\) (\d+) min, (\d+) stops(?: \| (.+))?", line.strip())
    if match:
        start, end, code, duration, stops, tag = match.groups()
        return Route(start.strip(), end.strip(), code.strip(), int(duration), int(stops), tag.strip() if tag else None)
    return None

def load_routes_from_file():
    txt_files = [f for f in os.listdir('.') if f.endswith('.txt')]
    if txt_files:
        print("Available route files:")
        for idx, fname in enumerate(txt_files, 1):
            print(f"{idx}. {fname}")
        choice = input("Enter the number of the file to use or type the filename directly: ").strip()
        filename = txt_files[int(choice)-1] if choice.isdigit() and 0 < int(choice) <= len(txt_files) else choice
    else:
        filename = input("No .txt files found. Please enter the full path to a routes file: ").strip()

    try:
        with open(filename, 'r') as f:
            return [parse_route_line(line) for line in f if line.strip()]
    except FileNotFoundError:
        print("File not found. Exiting.")
        exit()

def build_graph(routes):
    graph = defaultdict(list)
    edge_map = {}
    for route in routes:
        graph[route.start].append((route.end, route.code))
        graph[route.end].append((route.start, route.code))
        edge_map[(route.start, route.end)] = route
        edge_map[(route.end, route.start)] = route
    return graph, edge_map

def find_components(graph):
    visited = set()
    components = []

    for node in graph:
        if node not in visited:
            queue = deque([node])
            component = set()
            while queue:
                current = queue.popleft()
                if current not in visited:
                    visited.add(current)
                    component.add(current)
                    queue.extend(neigh for neigh, _ in graph[current])
            components.append(component)
    return components

def find_odd_vertices(graph, component):
    return [v for v in component if len(graph[v]) % 2 == 1]

def find_journeys(component, graph, edge_map):
    used_edges = set()
    journeys = []

    def dfs(u, journey):
        for v, code in graph[u]:
            edge = tuple(sorted((u, v)))
            if edge not in used_edges:
                used_edges.add(edge)
                dfs(v, journey)
                journey.append((u, v))

    for start in component:
        for v, _ in graph[start]:
            edge = tuple(sorted((start, v)))
            if edge not in used_edges:
                path = []
                dfs(start, path)
                if path:
                    path.reverse()
                    journeys.append(path)

    return journeys

def display_journeys(journeys, edge_map):
    total_time = 0
    for i, journey in enumerate(journeys, 1):
        print(f"\nJourney {i}:")
        print("Routes:")
        journey_time = 0
        used = set()
        for a, b in journey:
            route = edge_map.get((a, b)) or edge_map.get((b, a))
            if route and route.code not in used:
                used.add(route.code)
                tag = f" | {route.tag}" if route.tag else ""
                print(f"• {route.code}: {route.start} <> {route.end} ({route.duration} minutes, {route.stops} stops{tag})")
                journey_time += route.duration

        print("\nSuggested Sequence:")
        if journey:
            sequence = [journey[0][0]]
            for a, b in journey:
                if sequence[-1] == a:
                    sequence.append(b)
                else:
                    sequence.append(a)
            for i in range(len(sequence)-1):
                route = edge_map.get((sequence[i], sequence[i+1])) or edge_map.get((sequence[i+1], sequence[i]))
                tag = f" | {route.tag}" if route.tag else ""
                print(f"– From {sequence[i]}, take {route.code} to {sequence[i+1]}{tag}.")

        print(f"\nTotal Time: {journey_time} minutes")
        total_time += journey_time

    print(f"\nTotal Time Across All Journeys: {total_time} minutes")

def main():
    routes = load_routes_from_file()
    graph, edge_map = build_graph(routes)
    components = find_components(graph)

    print(f"\nNumber of connected components: {len(components)}")
    total_min_journeys = 0
    all_journeys = []

    for i, component in enumerate(components, 1):
        odd_vertices = find_odd_vertices(graph, component)
        print(f"\nAnalyzing Component {i}:")
        if not odd_vertices:
            print("This component has an Eulerian circuit. Minimum journeys: 1")
            journeys = find_journeys(component, graph, edge_map)
        else:
            print("This component does not have an Eulerian path or circuit.")
            print(f"Number of vertices with odd degree: {len(odd_vertices)}")
            print(f"Minimum number of journeys needed for this component: {len(odd_vertices)//2}")
            journeys = find_journeys(component, graph, edge_map)
            print("The graph has vertices with odd degrees, indicating multiple journeys are needed.")
            print(f"Odd-degree vertices: {odd_vertices}")

        total_min_journeys += max(1, len(odd_vertices) // 2)
        all_journeys.extend(journeys)

    print(f"\nTotal minimum journeys needed: {total_min_journeys}")
    display_journeys(all_journeys, edge_map)

if __name__ == "__main__":
    main()
