import re
from collections import defaultdict, deque

class Route:
    def __init__(self, route_id, start, end, duration, stops, description):
        self.route_id = route_id
        self.start = start
        self.end = end
        self.duration = duration
        self.stops = stops
        self.description = description.strip()

    def __repr__(self):
        return f"{self.route_id}: {self.start} <> {self.end} ({self.duration} minutes, {self.stops} stops{' | ' + self.description if self.description else ''})"

    def endpoints(self):
        return self.start, self.end

def parse_routes(route_lines):
    routes = []
    pattern = re.compile(r"(.+?) <> (.+?) \((R\d+)\) (\d+) min, (\d+) stops(?: \| (.+))?")
    for line in route_lines:
        match = pattern.match(line)
        if match:
            start, end, route_id, duration, stops, description = match.groups()
            route = Route(route_id, start.strip(), end.strip(), int(duration), int(stops), description or "")
            routes.append(route)
    return routes

def build_graph(routes):
    graph = defaultdict(list)
    for route in routes:
        graph[route.start].append((route.end, route))
        graph[route.end].append((route.start, route))
    return graph

def find_odd_degree_vertices(graph):
    return [node for node in graph if len(graph[node]) % 2 == 1]

def find_connected_components(graph):
    visited = set()
    components = []

    def dfs(node, component):
        stack = [node]
        while stack:
            current = stack.pop()
            if current not in visited:
                visited.add(current)
                component.add(current)
                for neighbor in graph[current]:
                    if neighbor not in visited:
                        stack.append(neighbor)

    for node in graph:
        if node not in visited:
            component = set()
            dfs(node, component)
            components.append(component)

    return components

def extract_component_routes(component_nodes, graph):
    seen = set()
    component_routes = []
    for node in component_nodes:
        for neighbor, route in graph[node]:
            route_key = tuple(sorted([route.start, route.end, route.route_id]))
            if route_key not in seen:
                seen.add(route_key)
                component_routes.append(route)
    return component_routes

def build_subgraph(component_nodes, routes):
    subgraph = defaultdict(list)
    for route in routes:
        if route.start in component_nodes and route.end in component_nodes:
            subgraph[route.start].append((route.end, route))
            subgraph[route.end].append((route.start, route))
    return subgraph

def find_eulerian_path_or_pairs(graph, component_routes):
    used = set()
    paths = []
    
    def dfs_path(start):
        stack = [start]
        path = []
        while stack:
            node = stack[-1]
            if graph[node]:
                neighbor, route = graph[node].pop()
                if route.route_id in used:
                    continue
                used.add(route.route_id)
                stack.append(neighbor)
                path.append(route)
            else:
                stack.pop()
        return path

    odd_vertices = find_odd_degree_vertices(graph)
    while len(odd_vertices) > 1:
        start = odd_vertices.pop()
        end = odd_vertices.pop()
        path = dfs_path(start)
        if path:
            paths.append(path)
    
    remaining_routes = [r for r in component_routes if r.route_id not in used]
    while remaining_routes:
        start = remaining_routes[0].start
        path = dfs_path(start)
        if path:
            paths.append(path)
        remaining_routes = [r for r in component_routes if r.route_id not in used]
    
    return paths

def format_journey(journey_num, path):
    output = [f"Journey {journey_num}:", "Routes:"]
    total_time = 0
    for route in path:
        desc = f" | {route.description}" if route.description else ""
        output.append(f"• {route.route_id}: {route.start} <> {route.end} ({route.duration} minutes, {route.stops} stops{desc})")
        total_time += route.duration

    sequence = ["\nSuggested Sequence:"]
    if path:
        sequence.append(f"– From {path[0].start}, take {path[0].route_id} to {path[0].end}{f' | {path[0].description}' if path[0].description else ''}.")
        for prev, curr in zip(path, path[1:]):
            sequence.append(f"– From {curr.start}, take {curr.route_id} to {curr.end}{f' | {curr.description}' if curr.description else ''}.")

    output.extend(sequence)
    output.append(f"\nTotal Time: {total_time} minutes\n")
    return "\n".join(output)

def generate_journeys(route_lines):
    routes = parse_routes(route_lines)
    graph = build_graph(routes)
    route_graph = defaultdict(set)
    for route in routes:
        route_graph[route.start].add(route.end)
        route_graph[route.end].add(route.start)
    
    components = find_connected_components(route_graph)
    all_journeys = []

    for component_nodes in components:
        component_routes = extract_component_routes(component_nodes, graph)
        subgraph = build_subgraph(component_nodes, component_routes)
        paths = find_eulerian_path_or_pairs(subgraph, component_routes)
        all_journeys.extend(paths)

    total_time = 0
    for idx, journey in enumerate(all_journeys, start=1):
        output = format_journey(idx, journey)
        print(output)
        total_time += sum(route.duration for route in journey)

    print(f"Total Time Across All Journeys: {total_time} minutes")
    print(f"Number of journeys created: {len(all_journeys)}")

if __name__ == "__main__":
    filename = input("Enter the name of the route file to load (e.g., my_routes.txt): ").strip()
    try:
        with open(filename, encoding="utf-8") as f:
            input_routes = [line.strip() for line in f if line.strip()]
        generate_journeys(input_routes)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found. Please check the filename and try again.")