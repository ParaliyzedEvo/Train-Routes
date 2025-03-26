import re
import json
import networkx as nx

def load_routes_from_txt(filename):
    routes = []
    route_descriptions = {}
    route_times = {}

    express_pattern = r"(.+?)\s*<>\s*(.+?)\s*\((R\d+)\)\s*(\d+)\s*min.*\|\s*(.+)"
    connect_pattern = r"(.+?)\s*<>\s*(.+?)\s*\((R\d+)\)\s*(\d+)\s*min.*"

    with open(filename, 'r', encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            express_match = re.search(express_pattern, line)
            connect_match = re.search(connect_pattern, line)

            if express_match:
                start, end, route, minutes, description = express_match.groups()
                description = description.strip()
            elif connect_match:
                start, end, route, minutes = connect_match.groups()
                description = ""
            else:
                continue

            routes.append((start.strip(), end.strip(), route.strip()))
            routes.append((end.strip(), start.strip(), route.strip()))

            route_descriptions[route.strip()] = description
            route_times[route.strip()] = int(minutes)

    return routes, route_descriptions, route_times

def load_routes_from_json(filename):
    with open(filename, 'r', encoding="utf-8") as file:
        data = json.load(file)

    routes = []
    route_descriptions = {}
    route_times = {}

    for route in data["routes"]:
        start, end, route_id, minutes = route["start"], route["end"], route["id"], route["time"]
        description = route.get("description", "")

        routes.append((start, end, route_id))
        routes.append((end, start, route_id))

        route_descriptions[route_id] = description
        route_times[route_id] = minutes

    return routes, route_descriptions, route_times

def build_journeys(graph, routes, route_times):
    all_used_routes = set()
    journeys = []

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

    return journeys

def save_journeys_to_file(journeys, route_descriptions, route_times, journey_type):
    filename = f"{journey_type}_journeys"

    save_format = input("\nDo you want to save as TXT or JSON? (txt/json): ").strip().lower()
    if save_format == "json":
        filename += ".json"
        data = []
        for i, journey in enumerate(journeys, 1):
            journey_data = {
                "journey_number": i,
                "total_time": sum(route_times.get(route, 0) for _, _, route in journey),
                "routes_used": [route for _, _, route in journey],
                "steps": [
                    {
                        "from": u,
                        "to": v,
                        "route": route,
                        "description": route_descriptions.get(route, "")
                    }
                    for u, v, route in journey
                ]
            }
            data.append(journey_data)

        with open(filename, 'w', encoding="utf-8") as file:
            json.dump(data, file, indent=4)
    else:
        filename += ".txt"
        with open(filename, 'w', encoding="utf-8") as file:
            for i, journey in enumerate(journeys, 1):
                total_time = sum(route_times.get(route, 0) for _, _, route in journey)
                file.write(f"Journey {i}\n\n")
                for u, v, route in journey:
                    description = route_descriptions.get(route, "")
                    if description:
                        file.write(f"    {u} → {v} ({route}) | {description}\n")
                    else:
                        file.write(f"    {u} → {v} ({route})\n")
                file.write(f"\n    Routes used: {', '.join(route for _, _, route in journey)}\n")
                file.write(f"    Total time: {total_time} min\n\n")

    print(f"\nJourneys saved to {filename}")

def main():
    while True:
        filename = input("\nEnter the name of the route file to load (TXT or JSON): ").strip()
        if filename.endswith(".json"):
            try:
                routes, route_descriptions, route_times = load_routes_from_json(filename)
            except FileNotFoundError:
                print(f"\nError: File '{filename}' not found. Please check the filename and try again.")
                continue
        else:
            try:
                routes, route_descriptions, route_times = load_routes_from_txt(filename)
            except FileNotFoundError:
                print(f"\nError: File '{filename}' not found. Please check the filename and try again.")
                continue

        # print("Loaded Routes:", routes)

        graph = nx.DiGraph()
        for u, v, route in routes:
            if graph.has_edge(u, v):
                graph[u][v]['routes'].append(route)
            else:
                graph.add_edge(u, v, routes=[route])

        journeys = build_journeys(graph, routes, route_times)
        journey_type = "express" if any(route_descriptions[route] for _, _, route in routes) else "connect"

        for i, journey in enumerate(journeys, 1):
            print(f"\nJourney {i}\n")
            total_time = sum(route_times.get(route, 0) for _, _, route in journey)
            route_ids = [route for _, _, route in journey]

            for u, v, route in journey:
                description = route_descriptions.get(route, "")
                if description:
                    print(f"    {u} → {v} ({route}) | {description}")
                else:
                    print(f"    {u} → {v} ({route})")

            print(f"\n    Routes used: {', '.join(route_ids)}")
            print(f"    Total time: {total_time} min\n")

        save_choice = input("Do you want to save the journeys? (yes/no): ").strip().lower()
        if save_choice == "yes" or "y":
            save_journeys_to_file(journeys, route_descriptions, route_times, journey_type)

        another_set = input("\nDo you want to load another set of routes? (yes/no): ").strip().lower()
        if another_set != "yes" or "y":
            print("\nExiting program.")
            break

if __name__ == "__main__":
    main()