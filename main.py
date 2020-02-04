import time
from math import copysign
from os import listdir
from os.path import isfile, join

import pygame
from glm import ivec2, length, vec2

ASSET_DIR = 'res/'
TEXTURES = {'entity_player_0': 'pacman_0.png',
            'entity_player_1': 'pacman_1.png',
            'entity_ghost': 'ghost.png',
            'block_wall': 'wall.png',
            'block_dot': 'dot.png',
            'block_empty': 'empty.png'}
TEXTURES = {name: ASSET_DIR + path for name, path in TEXTURES.items()}

SIZE_MODIFIER = 5

pygame.init()


class Tile:
    TEXTURE_PATH = ''
    BLOCK = False

    def __init__(self):
        self.texture = pygame.image.load(self.TEXTURE_PATH)


class Wall(Tile):
    TEXTURE_PATH = TEXTURES['block_wall']
    BLOCK = True


class Dot(Tile):
    TEXTURE_PATH = TEXTURES['block_dot']


class Empty(Tile):
    TEXTURE_PATH = TEXTURES['block_empty']


class Map:
    def __init__(self, window, filename):
        self.window = window
        self.tiles = None
        self.tex_map = None
        self.tile_size = 0
        self.tile_instances = {}
        self.dot_count = 0
        self.entities = {'player': None, 'ghost': []}

        self.finish = False
        self._parse_file(filename)
        self._draw_texture()

    def _parse_file(self, filename):
        tiles = {'X': Wall(), '*': Dot(), '0': Empty()}
        lines = open(filename).read().split('\n')
        lines = self._parse_entities(lines)
        data = [[None for _ in range(len(lines))] for _ in range(len(lines[0].split(' ')))]
        for i, line in enumerate(lines):
            line = line.split(' ')
            for j, elem in enumerate(line):
                data[j][i] = tiles[elem]
                if elem == '*':
                    self.dot_count += 1
        self.tiles = data
        self.tile_instances = tiles

    def _parse_entities(self, lines):
        for i in range(len(lines)):
            if not lines[i]:
                return lines[i + 1:]
            entity, x, y = lines[i].split(' ')
            pos = ivec2(int(x), int(y)) * SIZE_MODIFIER
            if entity == 'player':
                self.entities['player'] = Player(self, pos)
            else:
                self.entities['ghost'].append(Ghost(self, self.entities['player'], pos))

    def _draw_texture(self):
        tile_size = self.tiles[0][0].texture.get_rect()[2:]
        self.tile_size = tile_size[0]
        texture = pygame.Surface((tile_size[0] * len(self.tiles),
                                  tile_size[1] * len(self.tiles[1])))
        for i, line in enumerate(self.tiles):
            for j, elem in enumerate(line):
                texture.blit(elem.texture, (i * tile_size[0], j * tile_size[1]))
        self.tex_map = texture

    def draw_surface(self, surface, pos):
        self.window.blit(surface, pos * self.tile_size / SIZE_MODIFIER)

    def set_tile(self, pos: ivec2, tile):
        self.tiles[pos.x][pos.y] = tile
        self.tex_map.blit(tile.texture, pos * self.tile_size)

    def set_empty(self, pos: ivec2):
        if isinstance(self.tiles[pos.x][pos.y], Dot):
            self.dot_count -= 1
            self.set_tile(pos, self.tile_instances['0'])
            if not self.dot_count:
                self.finish = True


class EntityTextureManager:
    def __init__(self, tex_list, interval):
        self.textures = tex_list
        self.interval = interval
        self._curr_tex_id = 0
        self._curr_waiting = 0

    def get_texture(self):
        self._curr_waiting += 1
        if self._curr_waiting >= self.interval:
            self._curr_waiting = 0
            self._curr_tex_id += 1
            self._curr_tex_id %= len(self.textures)
        return self.textures[self._curr_tex_id]


class Entity:
    TEXTURE_PATHS = []
    TEXTURE_SWITCH_INTERVAL = 8

    def __init__(self, world, pos=ivec2(SIZE_MODIFIER)):
        self.world = world
        self.pos = pos
        self.direction = ivec2(1, 0)
        self.tex_manager = EntityTextureManager(self._load_textures(), self.TEXTURE_SWITCH_INTERVAL)

    def _load_textures(self):
        textures = []
        for path in self.TEXTURE_PATHS:
            img = pygame.image.load(path)
            # todo alpha
            textures.append(img)
        return textures

    def update(self):
        pass

    def move(self):
        new_pos = self.pos + self.direction
        new_tile_pos = new_pos / SIZE_MODIFIER
        if self.direction.x:
            if new_pos.x % SIZE_MODIFIER:
                if self.world.tiles[new_tile_pos.x][new_tile_pos.y].BLOCK or \
                        self.world.tiles[new_tile_pos.x + 1][new_tile_pos.y].BLOCK:
                    return
        elif self.direction.y:
            if new_pos.y % SIZE_MODIFIER:
                if self.world.tiles[new_tile_pos.x][new_tile_pos.y].BLOCK or \
                        self.world.tiles[new_tile_pos.x][new_tile_pos.y + 1].BLOCK:
                    return
        self.pos += self.direction

    @property
    def surface(self):
        return self.tex_manager.get_texture()


class Player(Entity):
    TEXTURE_PATHS = [TEXTURES['entity_player_0'], TEXTURES['entity_player_1']]

    def __init__(self, world, pos=ivec2(SIZE_MODIFIER)):
        super(Player, self).__init__(world, pos)
        self.tex_manager_list = [EntityTextureManager(self._rotate_textures(self.tex_manager.textures, 0),
                                                      self.TEXTURE_SWITCH_INTERVAL),
                                 EntityTextureManager(self._rotate_textures(self.tex_manager.textures, 270),
                                                      self.TEXTURE_SWITCH_INTERVAL),
                                 EntityTextureManager(self._rotate_textures(self.tex_manager.textures, 90),
                                                      self.TEXTURE_SWITCH_INTERVAL),
                                 EntityTextureManager(self._rotate_textures(self.tex_manager.textures, 180),
                                                      self.TEXTURE_SWITCH_INTERVAL)]
        self.curr_dir_texture = 1

    @staticmethod
    def _rotate_textures(textures, value):
        new_textures = []
        for tex in textures:
            new_textures.append(pygame.transform.rotate(tex, value))
        return new_textures

    @property
    def surface(self):
        return self.tex_manager_list[self.curr_dir_texture].get_texture()

    def update(self):
        self.move()
        self.world.set_empty((self.pos + SIZE_MODIFIER // 2) / SIZE_MODIFIER)

    def set_rotation(self, pressed_keys):
        if self.pos.x % SIZE_MODIFIER or self.pos.y % SIZE_MODIFIER:
            self.update()
            return

        old_direction = self.direction
        old_index = self.curr_dir_texture
        old_pos = ivec2(self.pos)

        if pressed_keys[pygame.K_w]:
            self.direction = ivec2(0, -1)
            self.curr_dir_texture = 0
        elif pressed_keys[pygame.K_a]:
            self.direction = ivec2(-1, 0)
            self.curr_dir_texture = 2
        elif pressed_keys[pygame.K_s]:
            self.direction = ivec2(0, 1)
            self.curr_dir_texture = 3
        elif pressed_keys[pygame.K_d]:
            self.direction = ivec2(1, 0)
            self.curr_dir_texture = 1
        self.update()

        if self.pos == old_pos:
            self.direction = old_direction
            self.curr_dir_texture = old_index


class Ghost(Entity):
    TEXTURE_PATHS = [TEXTURES['entity_ghost']]
    TEXTURE_SWITCH_INTERVAL = 10

    def __init__(self, world, player, pos=ivec2(15, 15) * SIZE_MODIFIER):
        super(Ghost, self).__init__(world, pos)
        self.player = player

    def move_to_player(self):
        pos_diff = self.player.pos - self.pos
        if abs(pos_diff.x) > abs(pos_diff.y):
            curr_speed = ivec2(copysign(1, pos_diff.x), 0)
        else:
            curr_speed = ivec2(0, copysign(1, pos_diff.y))
        self.direction = curr_speed

    def check_player_collides(self):
        if length(vec2(self.pos - self.player.pos)) <= 1.42:
            self.world.finish = True

    def update(self):
        self.move_to_player()
        self.move()
        self.check_player_collides()


def main():
    speed = 20
    text_offset = 40
    pygame.init()
    pygame.display.set_caption('Pacman4dumbz')
    window = pygame.display.set_mode((800, 600), pygame.DOUBLEBUF | pygame.HWSURFACE | pygame.HWACCEL)
    level = None

    # UI:
    # i am too tired to write good UI system, so
    # welcome to some shitty code
    font = pygame.font.SysFont('Arial', 20)
    _label_text_remain = font.render('Remain: ', False, (255, 255, 255))

    result_font = pygame.font.SysFont('SomeUnexistingFont', 192)
    _label_text_win = result_font.render('You WIN!', True, (30, 255, 30))
    _label_text_lose = result_font.render('You LOSE', True, (255, 30, 30))

    result_remain_font = pygame.font.SysFont('Arial', 48)
    _label_text_result_remain = None

    menu_maps_font = pygame.font.SysFont('Comic Sans MS', 48)
    _label_text_select_file = pygame.font.SysFont('SomeUnexistingFont', 64).render('Select level:', True, (50, 255, 50))
    maps = [f for f in listdir('maps/') if isfile(join('maps', f)) and f.endswith('.txt')]
    maps = [[text, menu_maps_font.render(text, True, (200, 200, 200))] for text in maps]
    curr_selected_surface = [0]
    # end UI

    def default_drawing_func():
        player = level.entities['player']
        player.set_rotation(pygame.key.get_pressed())
        window.blit(level.tex_map, (0, 0))
        level.draw_surface(player.surface, player.pos)

        for ghost in level.entities['ghost']:
            ghost.update()
            level.draw_surface(ghost.surface, ghost.pos)

        _label_number_remain = font.render(str(level.dot_count), True, (30, 255, 30))
        window.blit(_label_text_remain, (800 - _label_text_remain.get_rect()[2] - text_offset, 0))
        window.blit(_label_number_remain, (800 - text_offset, 0))
        return level

    def result_drawing_func():
        if level.dot_count:
            curr_label = _label_text_lose
        else:
            curr_label = _label_text_win
        rect = ivec2(curr_label.get_rect()[2:])
        window.blit(curr_label, (ivec2(800, 600) - rect) / 2)

        curr_label = _label_text_result_remain
        window.blit(curr_label, (ivec2(800, 600) - ivec2(curr_label.get_rect()[2:])) / 2 + ivec2(0, rect.y))
        return level

    def menu_drawing_func():
        # drawing header
        window.blit(_label_text_select_file, (400 - _label_text_select_file.get_rect()[2] // 2, 0))
        curr_height_offset = _label_text_select_file.get_rect()[3]

        # drawing list and triangle
        for i, (text, surface) in enumerate(maps):
            window.blit(surface, (400 - surface.get_rect()[2] // 2, curr_height_offset))
            if i == curr_selected_surface[0]:
                pos = ivec2(20, curr_height_offset + 5)
                pygame.draw.polygon(window, (255, 60, 60), [pos, pos + ivec2(0, 50), pos + ivec2(50, 25)])
            curr_height_offset += surface.get_rect()[3]

        if pygame.key.get_pressed()[pygame.K_DOWN]:
            curr_selected_surface[0] += 1
        if pygame.key.get_pressed()[pygame.K_UP]:
            curr_selected_surface[0] -= 1
        curr_selected_surface[0] %= len(maps)
        if pygame.key.get_pressed()[pygame.K_SPACE]:
            return Map(window, join('maps', maps[curr_selected_surface[0]][0]))

    curr_drawing_func = menu_drawing_func

    while True:
        for evt in pygame.event.get():
            if evt.type == pygame.QUIT:
                return
        window.fill(0)

        level = curr_drawing_func()
        if level is not None:
            curr_drawing_func = default_drawing_func
            if level.finish:
                curr_drawing_func = result_drawing_func
                _label_text_result_remain = result_remain_font.render('There are %s points left!' %
                                                                      (level.dot_count or 'no more'),
                                                                      True, (150, 150, 255))

        time.sleep(1 / speed)
        pygame.display.flip()


if __name__ == '__main__':
    main()
    pygame.quit()
