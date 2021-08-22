from time import sleep
from enum import Enum

import napari
import numpy as np
import psygnal
from napari.qt.threading import thread_worker

BOARD_SIZE = 14
INITIAL_SNAKE_LENGTH = 4


class Direction(Enum):
    UP = (-1, 0)
    DOWN = (1, 0)
    LEFT = (0, -1)
    RIGHT = (0, 1)


class Snake:
    board_update = psygnal.Signal()
    nom = psygnal.Signal()

    def __init__(self):
        self.length = INITIAL_SNAKE_LENGTH
        self.direction = Direction.DOWN

        self.board = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=int)
        start_position = self._random_empty_board_position
        self._head_position = start_position
        self.board[start_position] = 1
        self.tail = self.board.copy()
        self.food = np.zeros_like(self.board)
        self.food[self._random_empty_board_position] = 1

    def update(self):
        self._head_position = self._next_head_position
        if self.on_food:
            self.length += 1
            self._update_food()
            self.nom.emit()

        self.tail[self.tail > 0] += 1
        self.tail[self.tail > self.length] = 0
        self.tail[self._head_position] = 1
        self.board = self.tail > 0
        self.board_update.emit()

    def _update_food(self):
        self.food = np.zeros_like(self.food)
        self.food[self._random_empty_board_position] = 1

    @property
    def direction(self):
        """not synchronised with velocity"""
        return self._direction

    @direction.setter
    def direction(self, value: Direction):
        self._velocity_ = value.value
        self._direction = value

    @property
    def about_to_self_collide(self):
        if self._next_board_value == 1:
            return True
        else:
            return False

    @property
    def on_food(self):
        if self.food[self._head_position] == 1:
            return True
        else:
            return False

    @property
    def _head_position(self):
        return self._head_position_

    @_head_position.setter
    def _head_position(self, value):
        self._head_position_ = tuple(value)

    @property
    def _velocity(self):
        return self._velocity_

    @property
    def _random_empty_board_position(self):
        idx = np.where(self.board == 0)
        n_idx = len(idx[0])
        random_idx = np.random.randint(0, n_idx - 1, 1)
        return int(idx[0][random_idx]), int(idx[1][random_idx])

    @property
    def _next_head_position(self):
        next_position = np.array(self._head_position) + np.array(self._velocity)
        next_position[next_position > (BOARD_SIZE - 1)] = 0
        next_position[next_position < 0] = BOARD_SIZE - 1
        return tuple(next_position)

    @property
    def _next_board_value(self):
        return int(self.board[self._next_head_position])


viewer = napari.Viewer()
snake = Snake()

outline = np.ones((BOARD_SIZE + 2, BOARD_SIZE + 2))
outline[1:-1, 1:-1] = 0

outline_layer = viewer.add_image(outline, blending='additive', colormap='blue', translate=(-1, -1))
board_layer = viewer.add_image(snake.board, blending='additive')
food_layer = viewer.add_image(snake.food, blending='additive', colormap='red')
viewer.text_overlay.visible = True


@snake.board_update.connect
def on_board_update():
    viewer.text_overlay.text = f'Score: {snake.length - INITIAL_SNAKE_LENGTH}'
    board_layer.data = snake.board
    food_layer.data = snake.food


@snake.nom.connect
def nom():
    print('nom')
    viewer.text_overlay.text = 'nom nom nom'


@viewer.bind_key('w')
def up(event=None):
    snake.direction = Direction.UP


@viewer.bind_key('s')
def down(event=None):
    snake.direction = Direction.DOWN


@viewer.bind_key('a')
def left(event=None):
    snake.direction = Direction.LEFT


@viewer.bind_key('d')
def right(event=None):
    snake.direction = Direction.RIGHT


@thread_worker(connect={"yielded": snake.update})
def update_in_background():
    while True:
        sleep(1/10)
        if snake.about_to_self_collide:
            print('game over!')
            sleep(1)
            snake.__init__()
        yield

worker = update_in_background()
napari.run()
