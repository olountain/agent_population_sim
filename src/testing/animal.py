import random

class Animal:
    def __init__(self, x, y, species, hunger_limit=20):
        self.x = x
        self.y = y
        self.species = species
        self.hunger = 0
        self.hunger_limit = hunger_limit
        self.alive = True

    def move_randomly(self, env):
        dx, dy = random.choice([-1, 0, 1]), random.choice([-1, 0, 1])
        new_x = max(0, min(env.width - 1, self.x + dx))
        new_y = max(0, min(env.height - 1, self.y + dy))
        # Can only move on land
        if env.grid[new_y][new_x] == 0:
            self.x, self.y = new_x, new_y

    def step(self, env, others):
        self.move_randomly(env)
        self.hunger += 1
        if self.hunger > self.hunger_limit:
            self.alive = False


class Herbivore(Animal):
    def __init__(self, x, y):
        super().__init__(x, y, "herbivore")

    def step(self, env, others):
        super().step(env, others)
        if (self.x, self.y) in env.plants:
            env.plants.remove((self.x, self.y))
            self.hunger = 0


class Carnivore(Animal):
    def __init__(self, x, y):
        super().__init__(x, y, "carnivore")

    def step(self, env, others):
        super().step(env, others)
        for other in others:
            if isinstance(other, Herbivore) and other.alive and (other.x, other.y) == (self.x, self.y):
                other.alive = False
                self.hunger = 0
                break