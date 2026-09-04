import re
import json
import random
import networkx as nx

def parse_route_line(line):
    match = re.match(
        r"^(.+?)\s*<>\s*(.+?)\s*\((R\d+)\)\s*(\d+)\s*min(?:,\s*\d+\s*stops)?(?:\s*\|\s*(.+))?$",
        line
    )
    if not match:
        return None
    start, end, route, minutes, description = match.groups()
    return start.strip(), end.strip(), route.strip(), int(minutes), (description or "").strip()

def load_routes_from_txt(filename):
    # Auto-detects two formats
    classes = {}
    route_descriptions = {}
    route_times = {}
    current_class = "Journeys"

    with open(filename, 'r', encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line:
                continue

            parsed = parse_route_line(line)
            if parsed:
                start, end, route, minutes, description = parsed
                route_descriptions[route] = description
                route_times[route] = minutes
                classes.setdefault(current_class, [])
                classes[current_class].append((start, end, route))
                classes[current_class].append((end, start, route))
                continue

            if line.endswith(":"):
                current_class = line[:-1].strip()

    return classes, route_descriptions, route_times

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

    return {"Journeys": routes}, route_descriptions, route_times

def classify_route_type(description):
    if not description:
        return None  # ambiguous - blank description could be waterline or connect
    if re.search(r"shuttle", description, re.IGNORECASE):
        return "waterline"
    if re.search(r"semi-fast", description, re.IGNORECASE):
        return "connect"
    if re.search(r"\(E\)|\(S\)", description, re.IGNORECASE) or re.search(r"Via T\(\d+-\d+\)", description, re.IGNORECASE):
        return "airlink"
    if re.search(r"clockwise", description, re.IGNORECASE):
        return "metro"
    return "express"

_BALANCE_TRIALS = 2000

def _decompose_component_once(subgraph, rng):
    # shuffle edge insertion order (varies traversal order)
    working = nx.MultiGraph()
    edge_list = list(subgraph.edges(keys=True, data=True))
    rng.shuffle(edge_list)
    for u, v, k, d in edge_list:
        working.add_edge(u, v, key=k, **d)

    odd_nodes = [n for n, d in working.degree() if d % 2 == 1]
    rng.shuffle(odd_nodes)
    for i in range(0, len(odd_nodes) - 1, 2):
        u, v = odd_nodes[i], odd_nodes[i + 1]
        working.add_edge(u, v, route="__virtual__")

    has_virtual = len(odd_nodes) > 0
    start_node = odd_nodes[0] if has_virtual else next(iter(working.nodes))
    circuit = list(nx.eulerian_circuit(working, source=start_node, keys=True))

    if has_virtual:
        first_virtual_idx = next(
            i for i, (u, v, k) in enumerate(circuit)
            if working.get_edge_data(u, v, k)["route"] == "__virtual__"
        )
        circuit = circuit[first_virtual_idx + 1:] + circuit[:first_virtual_idx + 1]

    trails = []
    current_trail = []
    for u, v, key in circuit:
        route = working.get_edge_data(u, v, key)["route"]
        if route == "__virtual__":
            if current_trail:
                trails.append(current_trail)
                current_trail = []
            continue
        current_trail.append((u, v, route))
    if current_trail:
        trails.append(current_trail)

    return trails


def _decompose_component(subgraph, route_times, trial_count):
    odd_count = sum(1 for _, d in subgraph.degree() if d % 2 == 1)
    actual_trials = 1 if odd_count <= 2 else trial_count

    rng = random.Random(0)
    best_trails = None
    best_spread = None
    for _ in range(actual_trials):
        trails = _decompose_component_once(subgraph, rng)
        totals = [sum(route_times.get(r, 0) for _, _, r in t) for t in trails]
        spread = max(totals) - min(totals)
        if best_spread is None or spread < best_spread:
            best_spread = spread
            best_trails = trails

    return best_trails


def build_journeys(routes, route_times, trial_count=_BALANCE_TRIALS):
    undirected = nx.MultiGraph()
    seen_routes = set()
    for u, v, route in routes:
        if route in seen_routes:
            continue
        seen_routes.add(route)
        undirected.add_edge(u, v, key=route, route=route)

    journeys = []
    for component_nodes in nx.connected_components(undirected):
        subgraph = undirected.subgraph(component_nodes)
        if subgraph.number_of_edges() == 0:
            continue
        journeys.extend(_decompose_component(subgraph, route_times, trial_count))

    return journeys

def _json_str(value):
    return json.dumps(value, ensure_ascii=False)

def _format_journey_json(journey, indent):
    pad = " " * indent
    pad2 = " " * (indent + 4)
    pad3 = " " * (indent + 8)
    segments_lines = ",\n".join(f"{pad3}{_json_str(s)}" for s in journey["segments"])
    routes_inline = ", ".join(_json_str(r) for r in journey["routes_used"])
    return (
        f"{pad}{{\n"
        f"{pad2}\"segments\": [\n{segments_lines}\n{pad2}],\n"
        f"{pad2}\"routes_used\": [{routes_inline}],\n"
        f"{pad2}\"total_time_min\": {journey['total_time_min']}\n"
        f"{pad}}}"
    )

def _format_all_journeys_json(data):
    lines = ["{"]
    class_names = list(data.keys())
    for ci, class_name in enumerate(class_names):
        journeys = data[class_name]
        class_comma = "," if ci < len(class_names) - 1 else ""
        if not journeys:
            lines.append(f"    {_json_str(class_name)}: []{class_comma}")
            continue
        lines.append(f"    {_json_str(class_name)}: [")
        for ji, journey in enumerate(journeys):
            journey_comma = "," if ji < len(journeys) - 1 else ""
            lines.append(_format_journey_json(journey, 8) + journey_comma)
        lines.append(f"    ]{class_comma}")
    lines.append("}")
    return "\n".join(lines)

def save_journeys_to_file(all_class_journeys, route_descriptions, route_times, journey_type):
    filename = f"{journey_type}_journeys"

    save_format = ""
    while save_format not in ["txt", "json", "t", "j"]:
        save_format = input("\nDo you want to save as TXT or JSON? (txt/json): ").strip().lower()
        if save_format not in ["txt", "json", "t", "j"]:
            print("\nError: Please enter 'txt' or 'json'.")

    if save_format == "t":
        save_format = "txt"
    elif save_format == "j":
        save_format = "json"

    filename += f".{save_format}"

    if save_format == "json":
        data = {}
        for class_name, journeys in all_class_journeys.items():
            class_data = []
            for journey in journeys:
                segments = []
                routes_used = []
                total_time = 0

                for u, v, route in journey:
                    description = route_descriptions.get(route, "")
                    segments.append(f"{u} → {v} ({route})" + (f" | {description}" if description else ""))
                    routes_used.append(route)
                    total_time += route_times.get(route, 0)

                class_data.append({
                    "segments": segments,
                    "routes_used": routes_used,
                    "total_time_min": total_time
                })
            data[class_name] = class_data

        with open(filename, 'w', encoding="utf-8") as file:
            file.write(_format_all_journeys_json(data))
    elif save_format == "txt":
        with open(filename, 'w', encoding="utf-8") as file:
            for class_name, journeys in all_class_journeys.items():
                file.write(f"{class_name}\n\n")
                for i, journey in enumerate(journeys, 1):
                    total_time = sum(route_times.get(route, 0) for _, _, route in journey)
                    file.write(f"Journey {i}\n\n")
                    for u, v, route in journey:
                        description = route_descriptions.get(route, "")
                        file.write(f"    {u} → {v} ({route}) | {description}\n" if description else f"    {u} → {v} ({route})\n")
                    file.write(f"\n    Routes used: {', '.join(route for _, _, route in journey)}\n")
                    file.write(f"    Total time: {total_time} min\n\n")

    print(f"\nJourneys saved to {filename}")

def main():
    trial_input = input(
        f"\nEnter number of balancing trials per route group (default {_BALANCE_TRIALS}, press Enter to use default): "
    ).strip()
    if trial_input:
        try:
            balance_trials = int(trial_input)
            if balance_trials < 1:
                raise ValueError
        except ValueError:
            print(f"\nInvalid number, using default of {_BALANCE_TRIALS}.")
            balance_trials = _BALANCE_TRIALS
    else:
        balance_trials = _BALANCE_TRIALS

    while True:
        filename = input("\nEnter the name of the route file to load (TXT or JSON): ").strip()
        if filename.endswith(".json"):
            try:
                classes, route_descriptions, route_times = load_routes_from_json(filename)
            except FileNotFoundError:
                print(f"\nError: File '{filename}' not found. Please check the filename and try again.")
                continue
        else:
            try:
                classes, route_descriptions, route_times = load_routes_from_txt(filename)
            except FileNotFoundError:
                print(f"\nError: File '{filename}' not found. Please check the filename and try again.")
                continue

        all_class_journeys = {}
        for class_name, routes in classes.items():
            all_class_journeys[class_name] = build_journeys(routes, route_times, balance_trials)

        classified = [classify_route_type(desc) for desc in route_descriptions.values()]
        types_present = {t for t in classified if t}
        has_ambiguous = None in classified
        # blank descriptions can't be told apart from waterline/connect
        if has_ambiguous and not ({"waterline", "connect"} & types_present):
            types_present.add("connect-wl")

        type_priority = ["connect-wl", "waterline", "connect", "airlink", "metro", "express"]
        journey_type = "-".join(t for t in type_priority if t in types_present)

        for class_name, journeys in all_class_journeys.items():
            print(f"\n{class_name}\n")
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

        while True:
            save_choice = input("Do you want to save the journeys? (yes/no): ").strip().lower()
            if save_choice in ["yes", "y"]:
                save_journeys_to_file(all_class_journeys, route_descriptions, route_times, journey_type)
                break
            elif save_choice in ["no", "n"]:
                break
            else:
                print("\nError: Please enter 'yes' or 'no'.\n")

        while True:
            another_set = input("\nDo you want to load another set of routes? (yes/no): ").strip().lower()
            if another_set in ["no", "n"]:
                print("\nkk bye!!!")
                return
            elif another_set in ["yes", "y"]:
                break
            else:
                print("\nError: Please enter 'yes' or 'no'.")

if __name__ == "__main__":
    main()