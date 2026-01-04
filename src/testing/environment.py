import random

# --- Environment ---
class Environment:
    def __init__(self, width, height, plant_density=0.1):
        self.width = width
        self.height = height
        # 0 = land, 1 = water
        self.grid = [[random.choice([0, 0, 0, 1]) for _ in range(width)] for _ in range(height)]
        self.plants = {(x, y) for x in range(width) for y in range(height)
                       if self.grid[y][x] == 0 and random.random() < plant_density}

    def regenerate_plants(self, prob=0.01):
        """Small chance for plants to regrow on land cells"""
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] == 0 and random.random() < prob:
                    self.plants.add((x, y))