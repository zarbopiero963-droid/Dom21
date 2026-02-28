def generate_bezier_curve(p0, p1, p2, steps):
    steps = max(1, int(steps))
    curve = []
    for t in range(steps + 1):
        t_norm = t / steps
        x = (1 - t_norm)**2 * p0[0] + 2 * (1 - t_norm) * t_norm * p1[0] + t_norm**2 * p2[0]
        y = (1 - t_norm)**2 * p0[1] + 2 * (1 - t_norm) * t_norm * p1[1] + t_norm**2 * p2[1]
        curve.append((x, y))
    return curve

def clamp_point(x, y, viewport):
    if not viewport: return int(x), int(y)
    max_w = max(1, viewport.get("width", 1920))
    max_h = max(1, viewport.get("height", 1080))
    return int(max(0, min(x, max_w - 1))), int(max(0, min(y, max_h - 1)))