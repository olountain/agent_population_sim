import random
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
from noise import pnoise2

# --- Parameters ---
HUNGER_THRESHOLD = 10          # seek food
REPRO_THRESHOLD = 15           # desire to mate

MAX_HUNGER_FOR_MATING = 5      # must be well-fed to mate
MAX_HUNGER_FOR_PREGNANCY = 8   # must stay fed during pregnancy
BIRTH_HUNGER_COST = 3          # energy cost of giving birth

N_HERBIVORES = 30
N_CARNIVORES = 12

WORLD_SIZE = 50

# --- Environment ---
class Environment:
    def __init__(self, width, height, sea_level=0.45):
        self.width = width
        self.height = height

        self.heightmap = generate_perlin_terrain(width, height)
        self.grid = (self.heightmap < sea_level).astype(int)  
        # 0 = land, 1 = water

        self.plants = set()
        self.spawn_plants()

    def spawn_plants(self, density=0.05):
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] == 0 and np.random.rand() < density:
                    self.plants.add((x, y))

    def regenerate_plants(self, occupied, prob=0.01, attempts=50):
        for _ in range(attempts):
            x = random.randrange(self.width)
            y = random.randrange(self.height)

            if (
                self.grid[y][x] == 0
                and (x, y) not in occupied
                and (x, y) not in self.plants
                and random.random() < prob
            ):
                self.plants.add((x, y))



# --- Function to generate terrain ---
def generate_perlin_terrain(width, height, scale=50, octaves=4,
                             persistence=0.5, lacunarity=2.0, seed=0):
    terrain = np.zeros((height, width))
    for y in range(height):
        for x in range(width):
            terrain[y][x] = pnoise2(
                x / scale,
                y / scale,
                octaves=octaves,
                persistence=persistence,
                lacunarity=lacunarity,
                repeatx=1024,
                repeaty=1024,
                base=seed
            )

    # Normalize to 0–1
    terrain = (terrain - terrain.min()) / (terrain.max() - terrain.min())
    return terrain

# --- Animals ---
class Animal:
    def __init__(self, x, y, species, hunger_limit=20):
        self.x = x
        self.y = y
        self.species = species
        self.hunger = 0
        self.hunger_limit = hunger_limit
        self.alive = True

        # Reproduction
        self.sex = random.choice(["M", "F"])
        self.repro_drive = 0
        self.pregnant = False
        self.gestation_timer = 0

    def move_randomly(self, env):
        dx, dy = random.choice([-1, 0, 1]), random.choice([-1, 0, 1])
        nx = max(0, min(env.width - 1, self.x + dx))
        ny = max(0, min(env.height - 1, self.y + dy))
        if env.grid[ny][nx] == 0:
            self.x, self.y = nx, ny

    def step(self, env, others):
        self.move_randomly(env)
        self.hunger += 1
        self.repro_drive += 1

        if self.hunger > self.hunger_limit:
            self.alive = False

        if self.pregnant and self.hunger > MAX_HUNGER_FOR_PREGNANCY:
            # Pregnancy fails
            self.pregnant = False
            self.gestation_timer = 0

    def try_to_mate(self, others):
        if self.sex != "F" or self.pregnant:
            return

        # Must want to reproduce
        if self.repro_drive < REPRO_THRESHOLD:
            return

        # Must be well-fed
        if self.hunger > MAX_HUNGER_FOR_MATING:
            return

        for other in others:
            if (
                other.alive
                and other.species == self.species
                and other.sex == "M"
                and other.hunger <= MAX_HUNGER_FOR_MATING
                and abs(other.x - self.x) <= 1
                and abs(other.y - self.y) <= 1
            ):
                self.pregnant = True
                self.gestation_timer = 5
                self.repro_drive = 0
                break


    def give_birth(self):
        # Must be sufficiently fed to give birth
        if self.hunger > MAX_HUNGER_FOR_PREGNANCY:
            self.pregnant = False
            self.gestation_timer = 0
            return []

        litter_size = random.randint(1, 4)
        offspring = []

        for _ in range(litter_size):
            dx, dy = random.choice([-1, 0, 1]), random.choice([-1, 0, 1])
            ox = self.x + dx
            oy = self.y + dy
            offspring.append((ox, oy))

        # Energy cost of birth
        self.hunger += BIRTH_HUNGER_COST

        self.pregnant = False
        self.gestation_timer = 0
        return offspring

    
    def move_towards(self, target_positions, env):
        if not target_positions:
            self.move_randomly(env)
            return

        # Find nearest target
        nearest = min(target_positions, key=lambda t: (t[0]-self.x)**2 + (t[1]-self.y)**2)
        tx, ty = nearest

        dx = np.sign(tx - self.x)
        dy = np.sign(ty - self.y)

        # New position
        nx = max(0, min(env.width-1, self.x + dx))
        ny = max(0, min(env.height-1, self.y + dy))

        if env.grid[ny][nx] == 0:  # only move on land
            self.x, self.y = nx, ny
        else:
            self.move_randomly(env)




class Herbivore(Animal):
    def __init__(self, x, y):
        super().__init__(x, y, "herbivore")

    def step(self, env, others):
        super().step(env, others)

        # --- Determine movement target ---
        # 1. Hunger
        if self.hunger >= HUNGER_THRESHOLD and env.plants:
            self.move_towards(env.plants, env)
        # 2. Reproduction
        elif self.repro_drive >= REPRO_THRESHOLD:
            mates = [
                a for a in others
                if a.alive and a.species == self.species and a.sex != self.sex
            ]
            positions = [(a.x, a.y) for a in mates]
            self.move_towards(positions, env)
        # 3. Random
        else:
            self.move_randomly(env)

        # --- Eat plants if on the same cell ---
        if (self.x, self.y) in env.plants:
            env.plants.remove((self.x, self.y))
            self.hunger = 0

        # --- Try to mate ---
        self.try_to_mate(others)




class Carnivore(Animal):
    def __init__(self, x, y):
        super().__init__(x, y, "carnivore")

    def step(self, env, others):
        # Increase hunger, repro drive, etc.
        super().step(env, others)

        # --- Movement decision ---
        # 1. Hunt if hungry
        if self.hunger >= HUNGER_THRESHOLD:
            prey_positions = [
                (a.x, a.y)
                for a in others
                if isinstance(a, Herbivore) and a.alive
            ]
            self.move_towards(prey_positions, env)

        # 2. Seek mate if reproductively motivated
        elif self.repro_drive >= REPRO_THRESHOLD:
            mates = [
                a for a in others
                if (
                    a.alive
                    and a.species == self.species
                    and a.sex != self.sex
                )
            ]
            mate_positions = [(a.x, a.y) for a in mates]
            self.move_towards(mate_positions, env)

        # 3. Otherwise wander
        else:
            self.move_randomly(env)

        # --- Eat herbivore if present ---
        for other in others:
            if (
                isinstance(other, Herbivore)
                and other.alive
                and (other.x, other.y) == (self.x, self.y)
            ):
                other.alive = False
                self.hunger = 0
                break

        # --- Attempt mating ---
        self.try_to_mate(others)




# --- Simulation ---
class Simulation:
    def __init__(self, width=20, height=20, n_herb=20, n_carn=12):
        self.env = Environment(width, height)
        self.animals = [Herbivore(random.randrange(width), random.randrange(height)) for _ in range(n_herb)]
        self.animals += [Carnivore(random.randrange(width), random.randrange(height)) for _ in range(n_carn)]
        self.time = 0
        self.history = {"herbivores": [], "carnivores": []}

    def step(self):
        new_animals = []

        for animal in list(self.animals):
            if animal.alive:
                animal.step(self.env, self.animals)

                if animal.pregnant:
                    animal.gestation_timer -= 1
                    if animal.gestation_timer <= 0:
                        births = animal.give_birth()
                        for x, y in births:
                            if animal.species == "herbivore":
                                new_animals.append(Herbivore(x, y))
                            else:
                                new_animals.append(Carnivore(x, y))
            else:
                self.animals.remove(animal)

        self.animals.extend(new_animals)

        occupied = {(a.x, a.y) for a in self.animals if a.alive}
        self.env.regenerate_plants(occupied)

        self.time += 1

        # Log stats
        herb_count = sum(isinstance(a, Herbivore) for a in self.animals if a.alive)
        carn_count = sum(isinstance(a, Carnivore) for a in self.animals if a.alive)
        births = getattr(self, "births_this_step", 0)

        self.history["herbivores"].append(herb_count)
        self.history["carnivores"].append(carn_count)
        self.history.setdefault("births", []).append(births)


# --- Visualization ---
sim = Simulation(width=WORLD_SIZE, height=WORLD_SIZE, n_carn=N_CARNIVORES, n_herb=N_HERBIVORES)

fig, (ax_map, ax_pop) = plt.subplots(1, 2, figsize=(10, 5))

def update(frame):
    sim.step()

    # Clear plots
    ax_map.clear()
    ax_pop.clear()

    # Draw environment
    ax_map.imshow(sim.env.grid, cmap="Blues", alpha=0.3)
    px, py = zip(*sim.env.plants) if sim.env.plants else ([], [])
    ax_map.scatter(px, py, c="green", marker=".", label="plants")

    # Draw animals
    hx = [a.x for a in sim.animals if isinstance(a, Herbivore) and a.alive]
    hy = [a.y for a in sim.animals if isinstance(a, Herbivore) and a.alive]
    cx = [a.x for a in sim.animals if isinstance(a, Carnivore) and a.alive]
    cy = [a.y for a in sim.animals if isinstance(a, Carnivore) and a.alive]
    ax_map.scatter(hx, hy, c="orange", label="herbivores")
    ax_map.scatter(cx, cy, c="red", label="carnivores")
    ax_map.set_title(f"Step {sim.time-1}")
    ax_map.legend(loc="upper right")

    # Plot populations
    ax_pop.plot(sim.history["herbivores"], label="herbivores", color="orange")
    ax_pop.plot(sim.history["carnivores"], label="carnivores", color="red")
    ax_pop.set_title("Population over time")
    ax_pop.legend()

ani = animation.FuncAnimation(fig, update, frames=200, interval=100, repeat=False)
plt.show()
