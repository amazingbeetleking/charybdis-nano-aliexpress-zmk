"""
fix_combos.py — автоматически разносит перекрывающиеся комбо.
Читает физические позиции клавиш из info.json,
вычисляет центры комбо, находит перекрытия и добавляет вертикальные смещения.
"""
import json
import yaml
import sys

LAYOUT_NAME = "charybdis_5col_layout"
OVERLAP_THRESHOLD = 0.5  # минимальное расстояние между центрами комбо (в key units)
SLIDE_STEP = 0.75        # шаг горизонтального смещения между перекрывающимися комбо

def load_key_positions(info_path, layout_name):
    with open(info_path) as f:
        info = json.load(f)
    layout = info["layouts"][layout_name]["layout"]
    return [(k["x"], k["y"]) for k in layout]

def combo_centroid(key_indices, positions):
    xs = [positions[i][0] for i in key_indices]
    ys = [positions[i][1] for i in key_indices]
    return sum(xs) / len(xs), sum(ys) / len(ys)

def find_overlapping_groups(combos, positions):
    """Группирует комбо с близкими центрами."""
    centroids = []
    for combo in combos:
        cx, cy = combo_centroid(combo["p"], positions)
        centroids.append((cx, cy))

    groups = []
    assigned = [False] * len(combos)

    for i in range(len(combos)):
        if assigned[i]:
            continue
        group = [i]
        assigned[i] = True
        for j in range(i + 1, len(combos)):
            if assigned[j]:
                continue
            dx = abs(centroids[i][0] - centroids[j][0])
            dy = abs(centroids[i][1] - centroids[j][1])
            if dx < OVERLAP_THRESHOLD and dy < OVERLAP_THRESHOLD:
                group.append(j)
                assigned[j] = True
        if len(group) > 1:
            groups.append(group)

    return groups

def apply_offsets(yaml_path, combos, groups):
    """Вставляет o: {y: ...} в YAML файл, сохраняя формат."""
    # Собираем нужные смещения: combo_index -> offset
    offsets_map = {}
    for group in groups:
        n = len(group)
        for rank, idx in enumerate(group):
            offset = round((rank - (n - 1) / 2) * SLIDE_STEP, 2)
            combo_keys = combos[idx]["p"]
            offsets_map[tuple(combo_keys)] = offset

    if not offsets_map:
        return

    with open(yaml_path) as f:
        lines = f.readlines()

    result = []
    current_combo_keys = None
    for line in lines:
        result.append(line)
        stripped = line.strip()

        # Определяем начало комбо: "- p: [x, y]"
        if stripped.startswith("- p: ["):
            try:
                keys_str = stripped.split("[")[1].split("]")[0]
                keys = tuple(int(k.strip()) for k in keys_str.split(","))
                if keys in offsets_map:
                    current_combo_keys = keys
                else:
                    current_combo_keys = None
            except (ValueError, IndexError):
                current_combo_keys = None

        # После строки l: вставляем смещение
        if current_combo_keys and stripped.startswith("l:"):
            offset = offsets_map[current_combo_keys]
            result.append(f"  s: {offset}\n")
            current_combo_keys = None

    with open(yaml_path, "w") as f:
        f.writelines(result)

def main():
    info_path = sys.argv[1] if len(sys.argv) > 1 else "config/info.json"
    yaml_path = sys.argv[2] if len(sys.argv) > 2 else "keymap-drawer/charybdis.yaml"
    layout_name = sys.argv[3] if len(sys.argv) > 3 else LAYOUT_NAME

    positions = load_key_positions(info_path, layout_name)

    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    combos = data.get("combos", [])
    if not combos:
        return

    groups = find_overlapping_groups(combos, positions)
    if groups:
        apply_offsets(yaml_path, combos, groups)
        for group in groups:
            keys_list = [combos[i]["p"] for i in group]
            print(f"  Fixed overlap: {keys_list}")
    else:
        print("  No overlapping combos found")

if __name__ == "__main__":
    main()
