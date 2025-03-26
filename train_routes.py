import re
import networkx as nx

def load_routes_from_file(filename):
    routes = []
    route_descriptions = {}
    route_times = {}

    pattern = r"(.+?)\s*<>\s*(.+?)\s*\((R\d+)\)\s*(\d+)\s*min.*\|\s*(.+)"

    with open(filename, 'r', encoding="utf-8") as file:
        for line in file:
            match = re.search(pattern, line.strip())
            if match:
                start, end, route, minutes, description = match.groups()
                routes.append((start.strip(), end.strip(), route.strip()))
                routes.append((end.strip(), start.strip(), route.strip()))  # Add reverse route
                
                route_descriptions[route.strip()] = description.strip()
                route_times[route.strip()] = int(minutes)

    return routes, route_descriptions, route_times

def build_journeys(graph, routes, route_times):
    all_used_routes = set()
    journeys = []
    reverse_lookup = {}
    
    for u1, v1, r1 in routes:
        for u2, v2, r2 in routes:
            if u1 == v2 and v1 == u2 and r1 != r2:
                reverse_lookup[r1] = r2

    for start, end, route in routes:
        if route in all_used_routes:
            continue

        journey = [(start, end, route)]
        all_used_routes.add(route)
        current_node = end

        while True:
            found_next = False
            for neighbor in graph.successors(current_node):
                for next_route in graph[current_node][neighbor]["routes"]:
                    if next_route not in all_used_routes:
                        journey.append((current_node, neighbor, next_route))
                        all_used_routes.add(next_route)
                        current_node = neighbor
                        found_next = True
                        break
                if found_next:
                    break
            if not found_next:
                break

        journeys.append(journey)
    
    return merge_journeys(journeys, route_times)

def merge_journeys(journeys, route_times):
    optimized_journeys = []
    while journeys:
        journey = journeys.pop(0)
        merged = False
        for i, other in enumerate(optimized_journeys):
            if any(stop in [x[:2] for x in other] for stop in [x[:2] for x in journey]):
                optimized_journeys[i].extend(journey)
                merged = True
                break
        if not merged:
            optimized_journeys.append(journey)
    return optimized_journeys

def main():
    filename = input("Enter the name of the route file to load (e.g., my_routes.txt): ").strip()
    try:
        routes, route_descriptions, route_times = load_routes_from_file(filename)
        print("Loaded Routes:", routes)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found. Please check the filename and try again.")
        return

    graph = nx.DiGraph()
    for u, v, route in routes:
        if graph.has_edge(u, v):
            graph[u][v]['routes'].append(route)
        else:
            graph.add_edge(u, v, routes=[route])

    journeys = build_journeys(graph, routes, route_times)

    for i, journey in enumerate(journeys, 1):
        print(f"\nJourney {i}\n")
        total_time = sum(route_times.get(route, 0) for _, _, route in journey)
        route_ids = [route for _, _, route in journey]
        
        for u, v, route in journey:
            description = route_descriptions.get(route, "Unknown Route")
            print(f"    {u} → {v} ({route}) | {description}")
        
        print(f"\n    Routes used: {', '.join(route_ids)}")
        print(f"    Total time: {total_time} min\n")

if __name__ == "__main__":
    main()