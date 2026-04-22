import argparse

import pyvista as pv

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - depends on runtime env
    yaml = None

LAYER_PITCH = 1.2
STUD_HEIGHT = 0.2
BRICK_BODY_HEIGHT = LAYER_PITCH - STUD_HEIGHT
STUD_RADIUS = 0.3
CONTACT_EPS = 1e-3
SCENE_BOUNDS = (0, 8, 0, 8, 0, 4)
POSITION_SCALE = 50.0
ALLOWED_ROTATIONS = {0, 90}


def brick_dimensions(block_type):
    """Extract brick dimensions from a type name like 'brick_4x2'."""
    parts = block_type.split("_")
    if len(parts) < 2 or "x" not in parts[-1]:
        raise ValueError(f"Unsupported block type: {block_type}")

    width_str, depth_str = parts[-1].split("x", maxsplit=1)
    return int(width_str), int(depth_str)


def scaled_pos_to_grid(pos):
    """Scale YAML position coordinates to stud/layer grid coordinates."""
    if len(pos) != 3:
        raise ValueError(f"Position must contain 3 values, got: {pos}")

    x_raw, y_raw, z_raw = pos
    x = int(round(float(x_raw) * POSITION_SCALE))
    y = int(round(float(y_raw) * POSITION_SCALE))
    z_layer = int(round(float(z_raw) * POSITION_SCALE))
    return x, y, z_layer


def parse_rotation_degrees(rotation):
    """Parse a block rotation and return z-rotation in degrees (0 or 90)."""
    if rotation is None:
        return 0

    # Support both scalar rotations and [x, y, z] vectors.
    if isinstance(rotation, (int, float)):
        z_rotation = int(round(float(rotation)))
    else:
        if not isinstance(rotation, (list, tuple)) or len(rotation) != 3:
            raise ValueError(
                "Rotation must be a number or a 3-value list like [0, 0, 90]."
            )

        x_rot = int(round(float(rotation[0])))
        y_rot = int(round(float(rotation[1])))
        z_rotation = int(round(float(rotation[2])))

        if x_rot != 0 or y_rot != 0:
            raise ValueError(
                "Only z-axis rotation is supported; x and y rotation must be 0."
            )

    if z_rotation not in ALLOWED_ROTATIONS:
        raise ValueError(f"Unsupported rotation: {z_rotation}. Allowed: 0 or 90.")

    return z_rotation


def load_bricks_from_yaml(yaml_path):
    """Load bricks from YAML and convert them to internal brick tuples."""
    if yaml is None:
        raise RuntimeError("PyYAML is required. Install dependencies and retry.")

    with open(yaml_path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    blocks = data.get("blocks", [])
    bricks = []

    for block in blocks:
        block_type = block["type"]
        color = block["color"]
        pos = block["pos"]
        rotation = block.get("rotation")

        width, depth = brick_dimensions(block_type)
        z_rotation = parse_rotation_degrees(rotation)
        if z_rotation == 90:
            width, depth = depth, width
        x0, y0, z_layer = scaled_pos_to_grid(pos)
        bricks.append((x0, y0, z_layer, width, depth, color))

    return bricks


def scene_bounds_for_bricks(bricks):
    """Compute plotting bounds that enclose all bricks with a small margin."""
    if not bricks:
        return SCENE_BOUNDS

    xmin = min(x0 for x0, _, _, _, _, _ in bricks)
    xmax = max(x0 + width for x0, _, _, width, _, _ in bricks)
    ymin = min(y0 for _, y0, _, _, _, _ in bricks)
    ymax = max(y0 + depth for _, y0, _, _, depth, _ in bricks)
    zmax_layer = max(z_layer for _, _, z_layer, _, _, _ in bricks)

    margin = 1
    return (
        xmin - margin,
        xmax + margin,
        ymin - margin,
        ymax + margin,
        0,
        zmax_layer + 2,
    )


def brick_cells(brick):
    """Return all stud-cell coordinates occupied by a brick footprint."""
    x0, y0, _, width, depth, _ = brick
    return {(x0 + i, y0 + j) for i in range(width) for j in range(depth)}


def covered_cells_by_layer(bricks):
    """For each brick, return stud cells that are covered by a brick one layer above."""
    cells_per_brick = [brick_cells(brick) for brick in bricks]
    result = []

    for _, _, z_layer, _, _, _ in bricks:
        covered = set()
        for idx_above, (_, _, z_above, _, _, _) in enumerate(bricks):
            if z_above == z_layer + 1:
                covered |= cells_per_brick[idx_above]
        result.append(covered)

    return result


def add_selected_plane_grids(plotter, bounds, color="black"):
    """Draw grid lines only on bottom XY and rear XZ/YZ planes."""
    xmin, xmax, ymin, ymax, zmin, zmax = bounds

    # Bottom XY plane (z = zmin)
    for x in range(int(xmin), int(xmax) + 1):
        line = pv.Line((x, ymin, zmin), (x, ymax, zmin))
        plotter.add_mesh(line, color=color, line_width=1)
    for y in range(int(ymin), int(ymax) + 1):
        line = pv.Line((xmin, y, zmin), (xmax, y, zmin))
        plotter.add_mesh(line, color=color, line_width=1)

    # Rear XZ plane (y = ymax)
    for x in range(int(xmin), int(xmax) + 1):
        line = pv.Line((x, ymax, zmin), (x, ymax, zmax))
        plotter.add_mesh(line, color=color, line_width=1)
    for z in range(int(zmin), int(zmax) + 1):
        line = pv.Line((xmin, ymax, z), (xmax, ymax, z))
        plotter.add_mesh(line, color=color, line_width=1)

    # Rear YZ plane (x = xmin)
    for y in range(int(ymin), int(ymax) + 1):
        line = pv.Line((xmin, y, zmin), (xmin, y, zmax))
        plotter.add_mesh(line, color=color, line_width=1)
    for z in range(int(zmin), int(zmax) + 1):
        line = pv.Line((xmin, ymin, z), (xmin, ymax, z))
        plotter.add_mesh(line, color=color, line_width=1)


def draw_brick(plotter, x0, y0, z_layer, width, depth, color, hidden_stud_cells=None):
    """
    Draws a Lego brick on the provided PyVista plotter.

    Parameters:
    - plotter: The PyVista plotter
    - x0, y0: Starting coordinates in stud-units
    - z_layer: Layer index (0 is ground, 1 is the first stacked layer, etc.)
    - width, depth: Brick dimensions in studs (e.g., 2, 4 for a 2x4 brick)
    - color: Hex color or matplotlib color string
    """
    # Bodies touch directly between layers; studs interlock into the brick above.
    z0 = z_layer * BRICK_BODY_HEIGHT - z_layer * CONTACT_EPS
    if hidden_stud_cells is None:
        hidden_stud_cells = set()

    # Draw the brick body as a closed mesh.
    body = pv.Box(
        bounds=(
            x0,
            x0 + width,
            y0,
            y0 + depth,
            z0,
            z0 + BRICK_BODY_HEIGHT,
        )
    )
    plotter.add_mesh(
        body,
        color=color,
        show_edges=True,
        edge_color="black",
        smooth_shading=False,
        lighting=False,
    )

    # Draw cylindrical studs on the top face.
    for i in range(width):
        for j in range(depth):
            cell = (x0 + i, y0 + j)
            if cell in hidden_stud_cells:
                continue

            cx = x0 + i + 0.5
            cy = y0 + j + 0.5
            stud = pv.Cylinder(
                center=(cx, cy, z0 + BRICK_BODY_HEIGHT + STUD_HEIGHT / 2.0),
                direction=(0.0, 0.0, 1.0),
                radius=STUD_RADIUS,
                height=STUD_HEIGHT,
                resolution=48,
                capping=True,
            )
            plotter.add_mesh(
                stud,
                color=color,
                show_edges=True,
                edge_color="black",
                smooth_shading=False,
                lighting=False,
            )


def main():
    parser = argparse.ArgumentParser(description="Render LEGO configuration from YAML.")
    parser.add_argument("input", help="Path to YAML input file")
    parser.add_argument(
        "--output",
        default="lego_config.png",
        help="Path to output image (default: lego_config.png)",
    )
    args = parser.parse_args()

    plotter = pv.Plotter(off_screen=True, window_size=[1200, 900])
    plotter.set_background("white")

    # Brick layout: (x, y, z_layer, width, depth, color)
    bricks = load_bricks_from_yaml(args.input)
    scene_bounds = scene_bounds_for_bricks(bricks)

    covered_cells = covered_cells_by_layer(bricks)
    for brick, hidden_studs in zip(bricks, covered_cells):
        draw_brick(plotter, *brick, hidden_stud_cells=hidden_studs)

    plotter.show_bounds(
        bounds=scene_bounds,
        location="outer",
        all_edges=False,
        xtitle="x (studs)",
        ytitle="y (studs)",
        ztitle="z (layers)",
        color="black",
    )
    add_selected_plane_grids(plotter, scene_bounds, color="black")

    plotter.camera_position = [
        (12.5, -7.5, 8.5),
        (3.0, 4.0, 1.2),
        (0.0, 0.0, 1.0),
    ]
    plotter.reset_camera(bounds=scene_bounds)
    plotter.camera.zoom(0.9)

    plotter.screenshot(args.output)
    plotter.close()


if __name__ == "__main__":
    main()
