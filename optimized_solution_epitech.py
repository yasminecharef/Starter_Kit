import json, math, random, copy

def b_max(b):
    return max(b['populationPeakHours'], b['populationOffPeakHours'], b['populationNight'])

def sum_triplet(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

def sub_triplet(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def fits_cap(load, cap):
    return max(load) <= cap


def precompute_neighbors(buildings):
    n = len(buildings)
    neigh = {100: [[] for _ in range(n)],
             150: [[] for _ in range(n)],
             400: [[] for _ in range(n)]}

    for i in range(n):
        xi, yi = buildings[i]['x'], buildings[i]['y']
        for j in range(i + 1, n):
            dx = xi - buildings[j]['x']
            dy = yi - buildings[j]['y']
            d = math.hypot(dx, dy)
            if d <= 400:
                neigh[400][i].append(j)
                neigh[400][j].append(i)
                if d <= 150:
                    neigh[150][i].append(j)
                    neigh[150][j].append(i)
                    if d <= 100:
                        neigh[100][i].append(j)
                        neigh[100][j].append(i)
    return neigh

def greedy_random_solution_optimized(dataset, loads, neigh, RCL_SIZE):
    buildings = dataset['buildings']
    n = len(buildings)
    covered = set()
    antennas = []

    # === Density (>3500) ===
    for i, b in enumerate(buildings):
        if b_max(b) > 3500 and i not in covered:
            cap, rng = 5000, 150
            cluster = [i]
            load = loads[i]
            covered.add(i)

            for j in sorted(neigh[150][i], key=lambda x: b_max(buildings[x])):
                if j in covered:
                    continue
                new_load = sum_triplet(load, loads[j])
                if fits_cap(new_load, cap):
                    cluster.append(j)
                    covered.add(j)
                    load = new_load

            antennas.append({
                'id': len(antennas), 'type': 'Density',
                'x': b['x'], 'y': b['y'],
                'buildings_idx': cluster, 'current_load': load
            })

    # === MaxRange ===
    medium = [i for i in range(n) if i not in covered and 800 < b_max(buildings[i]) <= 3500]
    medium.sort(key=lambda i: b_max(buildings[i]), reverse=True)

    while medium:
        i = random.choice(medium[:RCL_SIZE])
        medium.remove(i)
        covered.add(i)

        cluster = [i]
        load = loads[i]

        for j in sorted(neigh[400][i], key=lambda x: b_max(buildings[x])):
            if j in covered:
                continue
            new_load = sum_triplet(load, loads[j])
            if fits_cap(new_load, 3500):
                cluster.append(j)
                covered.add(j)
                load = new_load
                if j in medium:
                    medium.remove(j)

        antennas.append({
            'id': len(antennas), 'type': 'MaxRange',
            'x': buildings[i]['x'], 'y': buildings[i]['y'],
            'buildings_idx': cluster, 'current_load': load
        })

    # === Spot ===
    remaining = [i for i in range(n) if i not in covered]
    remaining.sort(key=lambda i: b_max(buildings[i]), reverse=True)

    while remaining:
        i = random.choice(remaining[:RCL_SIZE])
        remaining.remove(i)
        covered.add(i)

        cluster = [i]
        load = loads[i]

        for j in sorted(neigh[100][i], key=lambda x: b_max(buildings[x])):
            if j in covered:
                continue
            new_load = sum_triplet(load, loads[j])
            if fits_cap(new_load, 800):
                cluster.append(j)
                covered.add(j)
                load = new_load
                if j in remaining:
                    remaining.remove(j)

        antennas.append({
            'id': len(antennas), 'type': 'Spot',
            'x': buildings[i]['x'], 'y': buildings[i]['y'],
            'buildings_idx': cluster, 'current_load': load
        })

    return antennas

def local_search_spot_removal(solution, buildings, loads, neigh):
    CAP = {'Density': 5000, 'MaxRange': 3500, 'Spot': 800}
    RNG = {'Density': 150,  'MaxRange': 400,  'Spot': 100}

    improved = True
    while improved:
        improved = False

        for spot in list(solution):
            if spot['type'] != 'Spot':
                continue

            # Tentative de redistribution
            assignments = {}  # b_idx -> target_ant
            temp_loads = {}   # ant_id -> load

            feasible = True

            for b_idx in spot['buildings_idx']:
                placed = False

                for ant in solution:
                    if ant is spot:
                        continue

                    ant_cap = CAP[ant['type']]
                    ant_rng = RNG[ant['type']]

                    # 🔒 test spatial CORRECT : centre antenne
                    dx = ant['x'] - buildings[b_idx]['x']
                    dy = ant['y'] - buildings[b_idx]['y']
                    if dx*dx + dy*dy > ant_rng * ant_rng:
                        continue

                    cur_load = temp_loads.get(id(ant), ant['current_load'])
                    new_load = sum_triplet(cur_load, loads[b_idx])

                    if fits_cap(new_load, ant_cap):
                        temp_loads[id(ant)] = new_load
                        assignments[b_idx] = ant
                        placed = True
                        break

                if not placed:
                    feasible = False
                    break

            # ✅ Appliquer uniquement si TOUT est faisable
            if feasible:
                for b_idx, ant in assignments.items():
                    ant['buildings_idx'].append(b_idx)
                for ant in solution:
                    if id(ant) in temp_loads:
                        ant['current_load'] = temp_loads[id(ant)]

                solution.remove(spot)
                improved = True
                break  # restart loop

    return solution


def local_search_exchange(solution, buildings, loads, neigh):
    CAP = {'Density': 5000, 'MaxRange': 3500}
    RNG = {'Density': 150,  'MaxRange': 400}

    for ant in list(solution):
        if ant['type'] == 'Spot':
            continue
        for other in list(solution):
            if other is ant or other['type'] == 'Spot':
                continue
            for b_idx in list(other['buildings_idx']):
                # quick range check using precomputed neighbors of the anchor building
                anchor = ant['buildings_idx'][0] if ant['buildings_idx'] else None
                if anchor is None or (b_idx != anchor and b_idx not in neigh[RNG[ant['type']]][anchor]):
                    continue
                new_load = sum_triplet(ant['current_load'], loads[b_idx])
                if fits_cap(new_load, CAP[ant['type']]):
                    ant['buildings_idx'].append(b_idx)
                    ant['current_load'] = new_load
                    other['buildings_idx'].remove(b_idx)
                    other['current_load'] = sub_triplet(other['current_load'], loads[b_idx])
            if not other['buildings_idx']:
                solution.remove(other)
    return solution


def grasp_solver(dataset_txt, max_iterations=20, RCL_SIZE=10):
    dataset = json.loads(dataset_txt)
    buildings = dataset['buildings']
    loads = [(b['populationPeakHours'], b['populationOffPeakHours'], b['populationNight']) for b in buildings]

    neigh = precompute_neighbors(buildings)

    best = None
    best_n = float('inf')
    patience = 8
    since_improvement = 0

    def merge_spots_into_maxrange(solution):
        # Merge clusters of >=3 Spot antennas into one MaxRange if it reduces cost
        def weighted_barycenter(idx_list):
            sx = sy = sw = 0.0
            for idx in idx_list:
                w = float(b_max(buildings[idx]))
                sx += buildings[idx]['x'] * w
                sy += buildings[idx]['y'] * w
                sw += w
            if sw == 0:
                return None
            return (sx / sw, sy / sw)

        def nearest_building_to(x, y, idx_list):
            best_idx, best_d = None, float('inf')
            for idx in idx_list:
                d = math.hypot(buildings[idx]['x'] - x, buildings[idx]['y'] - y)
                if d < best_d:
                    best_d = d
                    best_idx = idx
            return best_idx

        improved = True
        current = copy.deepcopy(solution)
        while improved:
            improved = False
            spots = [ant for ant in current if ant['type'] == 'Spot']
            if len(spots) < 3:
                break
            used = set()
            new_solution = [ant for ant in current if ant['type'] != 'Spot']
            any_cluster = False

            for s in spots:
                if s['id'] in used:
                    continue
                # Nearby candidate spots by center distance threshold
                cands = []
                for t in spots:
                    if t['id'] == s['id'] or t['id'] in used:
                        continue
                    if math.hypot(s['x'] - t['x'], s['y'] - t['y']) <= 600:
                        cands.append(t)
                # Build cluster greedily
                cluster_spots = [s]
                union_buildings = list(s['buildings_idx'])
                union_load = (0, 0, 0)
                for idx in union_buildings:
                    union_load = sum_triplet(union_load, loads[idx])
                changed = True
                while changed and cands:
                    changed = False
                    cands.sort(key=lambda t: math.hypot(s['x'] - t['x'], s['y'] - t['y']))
                    for t in list(cands):
                        tmp_buildings = list(dict.fromkeys(union_buildings + t['buildings_idx']))
                        tmp_load = union_load
                        for idx in t['buildings_idx']:
                            tmp_load = sum_triplet(tmp_load, loads[idx])
                        if max(tmp_load) > 3500:
                            continue
                        bc = weighted_barycenter(tmp_buildings)
                        if bc is None:
                            continue
                        cx, cy = bc
                        center_idx = nearest_building_to(cx, cy, tmp_buildings)
                        if center_idx is None:
                            continue
                        # range check via precomputed neighbors
                        ok = True
                        nbrs400 = set(neigh[400][center_idx])
                        for idx in tmp_buildings:
                            if idx != center_idx and idx not in nbrs400:
                                ok = False
                                break
                        if not ok:
                            continue
                        # Accept addition
                        cluster_spots.append(t)
                        union_buildings = tmp_buildings
                        union_load = tmp_load
                        cands.remove(t)
                        changed = True
                # If enough spots and cost decreases, create a MaxRange
                if len(cluster_spots) >= 3 and 40000 < 15000 * len(cluster_spots):
                    bc = weighted_barycenter(union_buildings)
                    if bc is None:
                        continue
                    cx, cy = bc
                    center_idx = nearest_building_to(cx, cy, union_buildings)
                    if center_idx is None:
                        continue
                    # Ensure range again
                    ok = True
                    nbrs400 = set(neigh[400][center_idx])
                    for idx in union_buildings:
                        if idx != center_idx and idx not in nbrs400:
                            ok = False
                            break
                    if not ok:
                        continue
                    # Mark used and add new MaxRange antenna
                    for t in cluster_spots:
                        used.add(t['id'])
                    new_solution.append({
                        'id': max([ant['id'] for ant in current], default=-1) + 1,
                        'type': 'MaxRange',
                        'x': buildings[center_idx]['x'],
                        'y': buildings[center_idx]['y'],
                        'buildings_idx': union_buildings,
                        'current_load': union_load
                    })
                    any_cluster = True
            # Append all unused spots
            for s in spots:
                if s['id'] not in used:
                    new_solution.append(s)
            if any_cluster:
                current = new_solution
                improved = True
            else:
                break
        return current

    for _ in range(max_iterations):
        sol = greedy_random_solution_optimized(dataset, loads, neigh, RCL_SIZE)
        sol = local_search_spot_removal(sol, buildings, loads, neigh)
        sol = local_search_exchange(sol, buildings, loads, neigh)
        sol = merge_spots_into_maxrange(sol)
        # Sanitize: ensure unique coverage by preferring cheaper antennas
        type_cost = {'Spot': 15000, 'Density': 30000, 'MaxRange': 40000}
        seen = set()
        sanitized = []
        for ant in sorted(sol, key=lambda a: type_cost.get(a['type'], 999999)):
            kept = []
            for b_idx in ant['buildings_idx']:
                if b_idx in seen:
                    continue
                kept.append(b_idx)
                seen.add(b_idx)
            if kept:
                load = (0, 0, 0)
                for idx in kept:
                    load = sum_triplet(load, loads[idx])
                ant['buildings_idx'] = kept
                ant['current_load'] = load
                sanitized.append(ant)
        sol = sanitized

        if len(sol) < best_n:
            best_n = len(sol)
            best = sol
            since_improvement = 0
        else:
            since_improvement += 1
            if since_improvement >= patience:
                break

    return json.dumps([
        {
            'id': i,
            'type': a['type'],
            'x': a['x'],
            'y': a['y'],
            'buildings': [buildings[j]['id'] for j in a['buildings_idx']]
        }
        for i, a in enumerate(best)
    ])


def greedy_random_solution(dataset_txt):
    # Increase iterations modestly; early-stop will cap time
    return grasp_solver(dataset_txt, max_iterations=80, RCL_SIZE=10)
