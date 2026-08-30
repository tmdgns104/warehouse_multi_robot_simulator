"""Pygame visualization for the simulation engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import pygame

from .map import CellType, Position
from .simulation import Simulation

CELL_SIZE = 36
MAP_MARGIN = 18
PANEL_WIDTH = 350
HEADER_HEIGHT = 72
FOOTER_HEIGHT = 18
FPS = 60
TICK_MS = 300

BACKGROUND = (20, 25, 34)
FREE = (238, 241, 245)
WALL = (49, 58, 72)
SHELF = (151, 101, 54)
STATION = (70, 156, 119)
GRID = (205, 211, 220)
TEXT = (232, 237, 244)
MUTED = (166, 177, 192)
PATH = (88, 166, 255)
ROBOT_COLORS = [(231, 76, 91), (59, 130, 246), (245, 158, 11), (168, 85, 247)]


@dataclass
class Button:
    label: str
    rect: pygame.Rect
    color: Tuple[int, int, int]

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        pygame.draw.rect(surface, self.color, self.rect, border_radius=7)
        rendered = font.render(self.label, True, (255, 255, 255))
        surface.blit(rendered, rendered.get_rect(center=self.rect.center))


class WarehouseUI:
    def __init__(self, simulation: Simulation) -> None:
        pygame.init()
        self.simulation = simulation
        map_width = simulation.warehouse.width * CELL_SIZE
        map_height = simulation.warehouse.height * CELL_SIZE
        self.map_origin = (MAP_MARGIN, HEADER_HEIGHT)
        self.panel_x = MAP_MARGIN * 2 + map_width
        self.size = (
            self.panel_x + PANEL_WIDTH,
            HEADER_HEIGHT + map_height + FOOTER_HEIGHT,
        )
        self.screen = pygame.display.set_mode(self.size)
        pygame.display.set_caption("Warehouse Multi-Robot Simulator V1")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 17)
        self.small_font = pygame.font.SysFont("arial", 14)
        self.title_font = pygame.font.SysFont("arial", 25, bold=True)
        self.robot_font = pygame.font.SysFont("arial", 18, bold=True)
        self.selected_robot_id: Optional[int] = None
        self.last_tick_time = pygame.time.get_ticks()
        self.buttons = self._make_buttons()

    def _make_buttons(self):
        return [
            Button("Start", pygame.Rect(400, 18, 95, 38), (39, 151, 96)),
            Button("Pause", pygame.Rect(505, 18, 95, 38), (210, 139, 37)),
            Button("Reset", pygame.Rect(610, 18, 95, 38), (190, 67, 78)),
        ]

    def _cell_rect(self, position: Position) -> pygame.Rect:
        x, y = position
        return pygame.Rect(
            self.map_origin[0] + x * CELL_SIZE,
            self.map_origin[1] + y * CELL_SIZE,
            CELL_SIZE,
            CELL_SIZE,
        )

    def _mouse_cell(self, point: Tuple[int, int]) -> Optional[Position]:
        x = (point[0] - self.map_origin[0]) // CELL_SIZE
        y = (point[1] - self.map_origin[1]) // CELL_SIZE
        position = (x, y)
        return position if self.simulation.warehouse.in_bounds(position) else None

    def _handle_click(self, point: Tuple[int, int]) -> None:
        if self.buttons[0].rect.collidepoint(point):
            self.simulation.start()
            return
        if self.buttons[1].rect.collidepoint(point):
            self.simulation.pause()
            return
        if self.buttons[2].rect.collidepoint(point):
            self.selected_robot_id = None
            self.simulation.reset()
            return

        cell = self._mouse_cell(point)
        if cell is None:
            return
        clicked_robot = next(
            (robot for robot in self.simulation.robots if robot.position == cell), None
        )
        if clicked_robot is not None:
            self.selected_robot_id = clicked_robot.id
            self.simulation.log(f"Robot {clicked_robot.id} selected; click a goal cell")
        elif self.selected_robot_id is not None:
            if self.simulation.assign_goal(self.selected_robot_id, cell):
                self.simulation.log(
                    f"Robot {self.selected_robot_id} goal changed to {cell}"
                )

    def _draw_header(self) -> None:
        title = self.title_font.render("Warehouse Multi-Robot Simulator", True, TEXT)
        self.screen.blit(title, (MAP_MARGIN, 20))
        for button in self.buttons:
            button.draw(self.screen, self.font)

    def _draw_map(self) -> None:
        colors = {
            CellType.FREE: FREE,
            CellType.WALL: WALL,
            CellType.SHELF: SHELF,
            CellType.STATION: STATION,
        }
        warehouse = self.simulation.warehouse
        for y in range(warehouse.height):
            for x in range(warehouse.width):
                rect = self._cell_rect((x, y))
                pygame.draw.rect(self.screen, colors[warehouse.cell((x, y))], rect)
                pygame.draw.rect(self.screen, GRID, rect, 1)

        for robot in self.simulation.robots:
            color = ROBOT_COLORS[(robot.id - 1) % len(ROBOT_COLORS)]
            if robot.goal is not None:
                goal_rect = self._cell_rect(robot.goal).inflate(-12, -12)
                pygame.draw.rect(self.screen, color, goal_rect, 3, border_radius=4)
            for position in robot.path:
                center = self._cell_rect(position).center
                pygame.draw.circle(self.screen, color, center, 4)

        for robot in self.simulation.robots:
            rect = self._cell_rect(robot.position)
            color = ROBOT_COLORS[(robot.id - 1) % len(ROBOT_COLORS)]
            pygame.draw.circle(self.screen, color, rect.center, CELL_SIZE // 2 - 4)
            if robot.id == self.selected_robot_id:
                pygame.draw.circle(self.screen, (255, 255, 255), rect.center, CELL_SIZE // 2 - 1, 3)
            label = self.robot_font.render(str(robot.id), True, (255, 255, 255))
            self.screen.blit(label, label.get_rect(center=rect.center))

    def _draw_panel(self) -> None:
        x = self.panel_x
        pygame.draw.rect(
            self.screen,
            (30, 37, 49),
            pygame.Rect(x, HEADER_HEIGHT, PANEL_WIDTH - MAP_MARGIN, self.size[1] - HEADER_HEIGHT - FOOTER_HEIGHT),
            border_radius=8,
        )
        status = "RUNNING" if self.simulation.running else "PAUSED"
        self.screen.blit(self.title_font.render(f"{status}  |  Tick {self.simulation.tick_count}", True, TEXT), (x + 18, HEADER_HEIGHT + 16))
        self.screen.blit(self.small_font.render("Click robot -> click free cell to change goal", True, MUTED), (x + 18, HEADER_HEIGHT + 50))

        y = HEADER_HEIGHT + 86
        for robot in self.simulation.robots:
            color = ROBOT_COLORS[(robot.id - 1) % len(ROBOT_COLORS)]
            pygame.draw.circle(self.screen, color, (x + 28, y + 10), 8)
            line = f"Robot {robot.id}  {robot.state.value}"
            self.screen.blit(self.font.render(line, True, TEXT), (x + 45, y))
            details = f"pos {robot.position}  goal {robot.goal}  wait {robot.waiting_count}"
            self.screen.blit(self.small_font.render(details, True, MUTED), (x + 45, y + 24))
            y += 60

        self.screen.blit(self.font.render("Event Log", True, TEXT), (x + 18, y + 5))
        y += 34
        for event in self.simulation.events[-10:]:
            short = event if len(event) <= 42 else event[:39] + "..."
            self.screen.blit(self.small_font.render(short, True, MUTED), (x + 18, y))
            y += 20

        legend_y = self.size[1] - 58
        legend = "Brown Shelf   Dark Wall   Green Station   Dots Path"
        self.screen.blit(self.small_font.render(legend, True, MUTED), (x + 18, legend_y))

    def draw(self) -> None:
        self.screen.fill(BACKGROUND)
        self._draw_header()
        self._draw_map()
        self._draw_panel()
        pygame.display.flip()

    def run(self) -> None:
        active = True
        while active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    active = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    if self.simulation.running:
                        self.simulation.pause()
                    else:
                        self.simulation.start()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_click(event.pos)

            now = pygame.time.get_ticks()
            if self.simulation.running and now - self.last_tick_time >= TICK_MS:
                self.simulation.tick()
                self.last_tick_time = now
                if self.simulation.all_arrived:
                    self.simulation.pause()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()
