import pyvista as pv

LAYER_PITCH = 1.2
STUD_HEIGHT = 0.2
BRICK_BODY_HEIGHT = LAYER_PITCH - STUD_HEIGHT
STUD_RADIUS = 0.3
CONTACT_EPS = 1e-3
SCENE_BOUNDS = (0, 8, 0, 8, 0, 4)


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
    plotter = pv.Plotter(off_screen=True, window_size=(1200, 900))
    plotter.set_background("white")

    # Brick layout: (x, y, z_layer, width, depth, color)
    bricks = [
        (2, 2, 0, 2, 4, "#F5C242"),  # Yellow base brick (2x4)
        (2, 4, 1, 2, 2, "#64A1D8"),  # Blue middle brick (2x2)
        (2, 4, 2, 2, 2, "#5EBB76"),  # Green top brick (2x2)
    ]

    covered_cells = covered_cells_by_layer(bricks)
    for brick, hidden_studs in zip(bricks, covered_cells):
        draw_brick(plotter, *brick, hidden_stud_cells=hidden_studs)

    plotter.show_bounds(
        bounds=SCENE_BOUNDS,
        location="outer",
        all_edges=False,
        xtitle="x (studs)",
        ytitle="y (studs)",
        ztitle="z (layers)",
        color="black",
    )
    add_selected_plane_grids(plotter, SCENE_BOUNDS, color="black")

    plotter.camera_position = [
        (12.5, -7.5, 8.5),
        (3.0, 4.0, 1.2),
        (0.0, 0.0, 1.0),
    ]
    plotter.reset_camera(bounds=SCENE_BOUNDS)
    plotter.camera.zoom(0.9)

    plotter.screenshot("lego_config.png")
    plotter.close()


if __name__ == "__main__":
    main()
