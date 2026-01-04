import random

class Environment:
    def __init__(self, width, height, plant_density=0.1):
        self.width = width
        self.height = height
        # 0 = land, 1 = water
        self.grid = [[random.choice([0, 1]) for _ in range(width)] for _ in range(height)]
        # Plant positions
        self.plants = {(x, y) for x in range(width) for y in range(height) if random.random() < plant_density}

class Animal:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.hunger = 0
        self.thirst = 0

    def move_randomly(self, env):
        dx, dy = random.choice([-1, 0, 1]), random.choice([-1, 0, 1])
        self.x = max(0, min(env.width-1, self.x + dx))
        self.y = max(0, min(env.height-1, self.y + dy))

class Herbivore(Animal):
    def eat(self, env):
        if (self.x, self.y) in env.plants:
            self.hunger = 0
            env.plants.remove((self.x, self.y))

# Example usage
env = Environment(10, 10)
herb = Herbivore(5, 5)

for step in range(10):
    herb.move_randomly(env)
    herb.eat(env)
    print(f"Step {step}: Herbivore at ({herb.x}, {herb.y}), Hunger: {herb.hunger}")
