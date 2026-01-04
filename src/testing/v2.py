import random
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
from matplotlib.colors import ListedColormap
from noise import pnoise2

# --- Parameters ---
HUNGER_THRESHOLD = 10          # seek food
REPRO_THRESHOLD = 15           # desire to mate

MAX_HUNGER_FOR_MATING = 5      # must be well-fed to mate
MAX_HUNGER_FOR_PREGNANCY = 8   # must stay fed during pregnancy
BIRTH_HUNGER_COST = 3          # energy cost of giving birth

N_HERBIVORES = 40
N_CARNIVORES = 20

VISION_RADIUS_HERBIVORE = 6
VISION_RADIUS_CARNIVORE = 8

WORLD_SIZE = 50
WORLD_SEED = 10

SEA_LEVEL = 0.45
BEACH_LEVEL = 0.50


# --- Environment ---
class Environment:
    def __init__(self, width, height, sea_level=SEA_LEVEL):
        self.width = width
        self.height = height

        self.heightmap = generate_perlin_terrain(width, height, seed=WORLD_SEED)
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

    def random_land_cell(self):
        while True:
            x = random.randrange(self.width)
            y = random.randrange(self.height)
            if self.grid[y][x] == 0:
                return x, y




# --- Function to generate terrain ---
def generate_perlin_terrain(width, height, scale=50, octaves=4,
                             persistence=0.5, lacunarity=2.0, seed = None):
    terrain = np.zeros((height, width))
    if seed is None:
        seed = random.randint(0,100)
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
    def __init__(self, x, y, species, hunger_limit=20, vision_radius=5):
        self.x = x
        self.y = y
        self.species = species
        self.hunger = 0
        self.hunger_limit = hunger_limit
        self.alive = True
        self.vision_radius = vision_radius

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

    def within_vision(self, x, y):
       return abs(self.x - x) <= self.vision_radius and abs(self.y - y) <= self.vision_radius


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


    def give_birth(self, env):
        if self.hunger > MAX_HUNGER_FOR_PREGNANCY:
            self.pregnant = False
            self.gestation_timer = 0
            return []

        litter_size = random.randint(1, 4)
        offspring_positions = []

        for _ in range(litter_size):
            placed = False
            for _ in range(8):  # try nearby cells first
                dx, dy = random.choice([-1, 0, 1]), random.choice([-1, 0, 1])
                x = self.x + dx
                y = self.y + dy

                if (
                    0 <= x < env.width
                    and 0 <= y < env.height
                    and env.grid[y][x] == 0
                ):
                    offspring_positions.append((x, y))
                    placed = True
                    break

            if not placed:
                # fallback to random land cell
                offspring_positions.append(env.random_land_cell())

        self.hunger += BIRTH_HUNGER_COST
        self.pregnant = False
        self.gestation_timer = 0
        return offspring_positions


    
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
        super().__init__(x, y, "herbivore", vision_radius=VISION_RADIUS_HERBIVORE)

    def step(self, env, others):
        super().step(env, others)

        # --- Perception ---
        visible_plants = [
            p for p in env.plants if self.within_vision(*p)
        ]

        visible_mates = [
            a for a in others
            if (
                a.alive
                and a.species == self.species
                and a.sex != self.sex
                and self.within_vision(a.x, a.y)
            )
        ]

        # --- Movement decision ---
        if self.hunger >= HUNGER_THRESHOLD and visible_plants:
            self.move_towards(visible_plants, env)

        elif self.repro_drive >= REPRO_THRESHOLD and visible_mates:
            mate_positions = [(a.x, a.y) for a in visible_mates]
            self.move_towards(mate_positions, env)

        else:
            self.move_randomly(env)

        # --- Eat ---
        if (self.x, self.y) in env.plants:
            env.plants.remove((self.x, self.y))
            self.hunger = 0

        self.try_to_mate(others)




class Carnivore(Animal):
    def __init__(self, x, y):
        super().__init__(x, y, "carnivore", vision_radius=VISION_RADIUS_CARNIVORE)

    def step(self, env, others):
        super().step(env, others)

        # --- Perception ---
        visible_prey = [
            a for a in others
            if (
                isinstance(a, Herbivore)
                and a.alive
                and self.within_vision(a.x, a.y)
            )
        ]

        visible_mates = [
            a for a in others
            if (
                a.alive
                and a.species == self.species
                and a.sex != self.sex
                and self.within_vision(a.x, a.y)
            )
        ]

        # --- Movement decision ---
        if self.hunger >= HUNGER_THRESHOLD and visible_prey:
            prey_positions = [(a.x, a.y) for a in visible_prey]
            self.move_towards(prey_positions, env)

        elif self.repro_drive >= REPRO_THRESHOLD and visible_mates:
            mate_positions = [(a.x, a.y) for a in visible_mates]
            self.move_towards(mate_positions, env)

        else:
            self.move_randomly(env)

        # --- Eat ---
        for other in visible_prey:
            if (other.x, other.y) == (self.x, self.y):
                other.alive = False
                self.hunger = 0
                break

        self.try_to_mate(others)





# --- Simulation ---
class Simulation:
    def __init__(self, width=20, height=20, n_herb=20, n_carn=12):
        self.env = Environment(width, height)

        self.animals = []

        # Spawn herbivores on land
        for _ in range(n_herb):
            x, y = self.env.random_land_cell()
            self.animals.append(Herbivore(x, y))

        # Spawn carnivores on land
        for _ in range(n_carn):
            x, y = self.env.random_land_cell()
            self.animals.append(Carnivore(x, y))

        self.time = 0
        self.history = {
            "herbivores": [],
            "carnivores": []
        }


    def step(self):
        new_animals = []

        for animal in list(self.animals):
            if animal.alive:
                animal.step(self.env, self.animals)

                if animal.pregnant:
                    animal.gestation_timer -= 1
                    if animal.gestation_timer <= 0:
                        births = animal.give_birth(self.env)
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

        for a in self.animals:
            assert self.env.grid[a.y][a.x] == 0, "Animal in water!"
            

# --- Visualization ---
sim = Simulation(width=WORLD_SIZE, height=WORLD_SIZE, n_carn=N_CARNIVORES, n_herb=N_HERBIVORES)

fig, (ax_map, ax_pop) = plt.subplots(1, 2, figsize=(20, 10), gridspec_kw={'wspace': 0.4})
plt.tight_layout()


def plot_group(cls, sex, color, marker, label):
    xs = [a.x for a in sim.animals if isinstance(a, cls) and a.alive and a.sex == sex]
    ys = [a.y for a in sim.animals if isinstance(a, cls) and a.alive and a.sex == sex]
    ax_map.scatter(xs, ys, c=color, marker=marker, label=label)


def update(frame):
    sim.step()

    # Clear plots
    ax_map.clear()
    ax_pop.clear()

    # Terrain
    heightmap = sim.env.heightmap
    terrain = np.zeros_like(heightmap)
    terrain[heightmap < SEA_LEVEL] = 0
    terrain[(heightmap >= SEA_LEVEL) & (heightmap < BEACH_LEVEL)] = 1
    terrain[heightmap >= BEACH_LEVEL] = 2

    terrain_cmap = ListedColormap(["#4a90e2", "#f2d16b", "#7cb342"])

    ax_map.imshow(terrain, cmap=terrain_cmap, origin="lower")

    # Plants
    if sim.env.plants:
        px, py = zip(*sim.env.plants)
        ax_map.scatter(px, py, c="#1b5e20", marker=".", label="Plants")


    # Draw animals
    plot_group(Herbivore, "F", "orange", "o", "Herbivore ♀")
    plot_group(Herbivore, "M", "orange", "D", "Herbivore ♂")
    plot_group(Carnivore, "F", "red", "o", "Carnivore ♀")
    plot_group(Carnivore, "M", "red", "D", "Carnivore ♂")

    ax_map.set_title(f"Step {sim.time-1}")
    ax_map.legend(
        loc="upper left",
        bbox_to_anchor=(1.02, 1),
        borderaxespad=0,
        fontsize=8,
        frameon=False
    )

    # Plot populations
    ax_pop.plot(sim.history["herbivores"], label="herbivores", color="orange")
    ax_pop.plot(sim.history["carnivores"], label="carnivores", color="red")
    ax_pop.set_title("Population over time")
    ax_pop.legend(
        loc="upper left",
        bbox_to_anchor=(1.02, 1),
        borderaxespad=0,
        fontsize=8,
        frameon=False
    )

ani = animation.FuncAnimation(fig, update, frames=200, interval=100, repeat=False)
plt.show()
