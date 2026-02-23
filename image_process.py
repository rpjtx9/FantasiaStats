from PIL import Image, ImageDraw
import numpy as np
from collections import deque
from pathlib import Path

def flood_fill_transparent(arr, start_pixels, threshold=200):
    h, w = arr.shape[:2]
    visited = np.zeros((h, w), dtype=bool)
    queue = deque(start_pixels)
    for px, py in start_pixels:
        visited[py, px] = True
    while queue:
        x, y = queue.popleft()
        r, g, b = arr[y, x, 0], arr[y, x, 1], arr[y, x, 2]
        is_background = (r > threshold and g > threshold and b > threshold) or \
                        (r < 30 and g < 30 and b < 30)
        if is_background:
            arr[y, x, 3] = 0
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                nx, ny = x+dx, y+dy
                if 0 <= nx < w and 0 <= ny < h and not visited[ny, nx]:
                    visited[ny, nx] = True
                    queue.append((nx, ny))

def process_icon(input_path, output_path, radius=18):
    img = Image.open(input_path).convert("RGBA")
    arr = np.array(img)
    h, w = arr.shape[:2]
    corners = [(0,0),(w-1,0),(0,h-1),(w-1,h-1)]
    flood_fill_transparent(arr, corners)
    img = Image.fromarray(arr)
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, w-1, h-1], radius=radius, fill=255)
    result = Image.new("RGBA", img.size, (0,0,0,0))
    result.paste(img, (0,0), mask)
    result.save(output_path)
    print(f"Saved {output_path}")

Path("data/icons").mkdir(parents=True, exist_ok=True)
icons = ["beginner", "warrior", "magician", "archer", "thief", "pirate"]
for name in icons:
    process_icon(f"raw/{name}.png", f"data/icons/{name}.png")