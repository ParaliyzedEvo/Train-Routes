import re
import networkx as nx
from collections import deque

def find_odd_degree_vertices(graph):
    return [node for node, degree in graph.degree() if degree % 2 == 1]

def find_eulerian_paths(graph):
    odd_degree_vertices = find_odd_degree_vertices(graph)
    print("Odd-degree vertices:", odd_degree_vertices)
    journeys = []
    used_edges = set()
    used_routes = set()

    # Pair up odd-degree vertices and build journeys
    while len(odd_degree_vertices) >= 2:
        start = odd_degree_vertices.pop()
        end = odd_degree_vertices.pop()

        subgraph = graph.copy()
        for u, v in list(graph.edges()):
            if all(route in used_routes for route in graph[u][v]['routes']):
                subgraph.remove_edge(u, v)

        try:
            path = nx.shortest_path(subgraph, start, end)
        except nx.NetworkXNoPath:
            continue  # Skip if no path exists

        journey = []
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            if not graph.has_edge(u, v):
                continue
            for route in graph[u][v]['routes']:
                if route not in used_routes:
                    journey.append((u, v, route))
                    used_routes.add(route)
                    break
        if journey:
            journeys.append(journey)

    # Add any remaining unused routes as standalone journeys
    for u, v in graph.edges():
        for route in graph[u][v]['routes']:
            if route not in used_routes:
                journeys.append([(u, v, route)])
                used_routes.add(route)

    return journeys

def load_routes_from_file(filename):
    routes = []
    route_descriptions = {}
    route_times = {}

    pattern = r"(.+?)\s*<>\s*(.+?)\s*\((R\d+)\)\s*(\d+)\s*min.*\|\s*(.+)"  # Now captures minutes too

    with open(filename, 'r', encoding="utf-8") as file:
        for line in file:
            match = re.search(pattern, line.strip())
            if match:
                start, end, route, minutes, description = match.groups()
                routes.append((start.strip(), end.strip(), route.strip()))

                route_descriptions[route.strip()] = description.strip()
                route_times[route.strip()] = int(minutes)  # Save the duration

    return routes, route_descriptions, route_times
    
def main():
    filename = input("Enter the name of the route file to load (e.g., my_routes.txt): ").strip()
    try:
        routes, route_descriptions, route_times = load_routes_from_file(filename)  # Now also getting descriptions
        print("Loaded Routes:", routes)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found. Please check the filename and try again.")
        return
    
    graph = nx.Graph()
    for u, v, route in routes:
        if graph.has_edge(u, v):
            graph[u][v]['routes'].append(route)  # Append new route if edge already exists
        else:
            graph.add_edge(u, v, routes=[route])  # Initialize with a list

    journeys = find_eulerian_paths(graph)

    for i, journey in enumerate(journeys, 1):
        print(f"\nJourney {i}\n")
        total_time = 0
        route_ids = []

        for u, v, route in journey:
            description = route_descriptions.get(route, "Unknown Route")
            reverse_note = " (reverse direction)" if (v, u, route) in journey else ""
            print(f"    {u} → {v} ({route}) | {description}{reverse_note}")
            route_ids.append(route)
            total_time += route_times.get(route, 0)

        print(f"\n    Routes used: {', '.join(route_ids)}")
        print(f"    Total time: {total_time} min\n")

if __name__ == "__main__":
    main()
