import subprocess
import sys
import time
from importlib.metadata import distributions

# --------- Definitionen ---------

TIC = 1

B1_FREQ = 1.0
B1_AN = 1
B1_AUS = 1

B2_FREQ = 1.0
B2_AN = 1
B2_AUS = 1

B3_FREQ = 3.0
B3_AN = 1
B3_AUS = 1

# --------------------------------

print("MESA.py: Checking for required packages")

required = {'pygame'}
installed = {dist.metadata['Name'].lower() for dist in distributions()}
missing = required - installed

if missing:
    print("MESA.py: Installing required packages", missing)
    python = sys.executable
    subprocess.check_call([python, '-m', 'pip', 'install', *missing])

print("MESA.py: Required packages installed")

import pygame

window_open = False


class Module:
    def __init__(self, mesa=None, index=0, name="Module", background_color=(255, 255, 255)):
        self.mesa = mesa
        self.index = index
        self.name = name
        self.background_color = background_color
        self.font = pygame.font.Font(None, 15 * self.mesa.virtual_screen_scale)
        self.byte_1_port = ""
        self.byte_2_port = ""
        self.last_byte_1 = None
        self.last_byte_2 = None
        self.last_mouse_click = None
        self.surface = pygame.Surface((self.mesa.module_width, self.mesa.module_height))

    def draw(self, byte_1, byte_2, update_byte_1, update_byte_2, mouse_pos, click):
        if byte_1 == self.last_byte_1 and byte_2 == self.last_byte_2 and self.last_mouse_click == (mouse_pos, click):
            self.mesa.screen.blit(self.surface, (0, self.mesa.module_height * self.index))
            return

        self.last_byte_1 = byte_1
        self.last_byte_2 = byte_2
        self.last_mouse_click = (mouse_pos, click)

        self.redraw(byte_1, byte_2, update_byte_1, update_byte_2, mouse_pos, click)
        self.mesa.screen.blit(self.surface, (0, self.mesa.module_height * self.index))

    def redraw(self, byte_1, byte_2, update_byte_1, update_byte_2, mouse_pos, click):
        module_rect = (0, 0, self.mesa.module_width, self.mesa.module_height)
        pygame.draw.rect(self.surface, self.background_color, module_rect)
        pygame.draw.rect(self.surface, (0, 0, 0), module_rect, 1 * self.mesa.virtual_screen_scale)

        text = self.font.render(self.name, True, (0, 0, 0))
        self.surface.blit(text, (5, 5 * self.mesa.virtual_screen_scale))

        if self.index == 0:
            self.byte_1_port = "P2"
            self.byte_2_port = "P3"
        elif self.index == 1:
            self.byte_1_port = "P1"
            self.byte_2_port = "P5"
        elif self.index == 2:
            self.byte_1_port = "P6"
            self.byte_2_port = "P7"

        text = self.font.render(self.byte_2_port, True, (0, 0, 0))
        self.surface.blit(text, (5, self.mesa.module_height - 20 * self.mesa.virtual_screen_scale))
        text = self.font.render(self.byte_1_port, True, (0, 0, 0))
        self.surface.blit(text, (5, self.mesa.module_height - 40 * self.mesa.virtual_screen_scale))


class MM20(Module):
    LED_ON = (255, 84, 84)
    LED_OFF = (122, 40, 40)
    BUTTON_ON = (59, 217, 90)
    BUTTON_OFF = (29, 107, 44)
    BUTTON_BACKGROUND = (50, 50, 50)

    def __init__(self, mesa=None, index=0):
        super().__init__(mesa, index, "MM20")

    def redraw(self, byte_1, byte_2, update_byte_1, update_byte_2, mouse_pos, click):
        super().redraw(byte_1, byte_2, update_byte_1, update_byte_2, mouse_pos, click)

        offset_y = 0
        offset_to_top = self.mesa.module_height / 3
        led_radius = self.mesa.module_width / 16 - 10 * self.mesa.virtual_screen_scale
        led_spacing = self.mesa.module_width / 8
        led_offset = self.mesa.module_width / 16

        for i in range(8):
            led_center = (led_offset + i * led_spacing, offset_y + offset_to_top)
            led_color = self.LED_ON if byte_1 & (1 << (7 - i)) else self.LED_OFF
            pygame.draw.circle(self.surface, led_color, led_center, led_radius)

        offset_to_leds = self.mesa.module_height / 3 * 2
        button_radius = led_radius
        button_ring_padding = 5 * self.mesa.virtual_screen_scale
        button_spacing = led_spacing
        button_offset = led_offset

        for i in range(8):
            button_center = (button_offset + i * button_spacing, offset_y + offset_to_leds)
            button_color = self.BUTTON_ON if byte_2 & (1 << (7 - i)) else self.BUTTON_OFF

            button_rect = pygame.Rect(button_center[0] - button_radius, button_center[1] - button_radius,
                                      button_radius * 2, button_radius * 2)
            pygame.draw.rect(self.surface, self.BUTTON_BACKGROUND, button_rect, border_radius=5)
            pygame.draw.circle(self.surface, button_color, button_center, button_radius - button_ring_padding)

            module_mouse_pos = (mouse_pos[0], mouse_pos[1] - self.mesa.module_height * self.index)
            if button_rect.collidepoint(module_mouse_pos) and click:
                byte_2 ^= (1 << (7 - i))
                update_byte_2(byte_2)
                break


class Matrix(Module):
    matrix_size = (8, 8)
    LED_ON = (255, 84, 84)
    LED_OFF = (122, 42, 42)

    def __init__(self, mesa=None, index=0, led_color=(255, 84, 84)):
        super().__init__(mesa, index, "Matrix")
        self.matrix = [[0 for _ in range(self.matrix_size[0])] for _ in range(self.matrix_size[1])]
        self.LED_ON = led_color
        self.LED_OFF = (led_color[0] // 3, led_color[1] // 3, led_color[2] // 3)

    def redraw(self, byte_1, byte_2, update_byte_1, update_byte_2, mouse_pos, click):
        super().redraw(byte_1, byte_2, update_byte_1, update_byte_2, mouse_pos, click)

        row = byte_1 & 0x0f
        enable_input = (byte_1 & 0x10) == 0x10
        enable_output = (byte_1 & 0x20) == 0x20

        if enable_input:
            self.matrix[row] = [byte_2 & (1 << (7 - i)) != 0 for i in range(8)]

        if not enable_output:
            self.redraw_matrix()
        else:
            self.redraw_matrix(self.matrix)

    def redraw_matrix(self, matrix=None):
        side = min(self.mesa.module_width, self.mesa.module_height) - 10
        led_size = side / self.matrix_size[0]
        padding = 0.05 * led_size
        offset_x = (self.mesa.module_width - side) / 2
        offset_y = (self.mesa.module_height - side) / 2

        for i in range(self.matrix_size[0]):
            for j in range(self.matrix_size[1]):
                led_color = (self.LED_ON if matrix[j][i] else self.LED_OFF) if matrix else self.LED_OFF
                pygame.draw.rect(self.surface, led_color,
                                 (offset_x + i * led_size + padding, offset_y + j * led_size + padding,
                                  led_size - 2 * padding, led_size - 2 * padding),
                                 border_radius=2)


class MESA:
    P2 = 0xff
    P3 = 0xff
    module_1: Module = None
    P1 = 0xff
    P5 = 0xff
    module_2: Module = None
    P6 = 0xff
    P7 = 0xff
    module_3: Module = None
    screen = None
    clock = None
    module_width = 0
    module_height = 0
    draw_tick = 100
    virtual_screen_scale = 2
    delta_time = 0

    prev_time = time.time_ns()

    def __init__(self):
        global window_open
        if window_open:
            raise Exception("MESA window already open")

        window_open = True
        pygame.init()

        display_info = pygame.display.Info()
        height = display_info.current_h
        window_height = 9 / 10 * height
        window_width = window_height / 3 * 1.5

        self.module_width = window_width * self.virtual_screen_scale
        self.module_height = window_height * self.virtual_screen_scale / 3

        self.screen = pygame.Surface(
            (window_width * self.virtual_screen_scale, window_height * self.virtual_screen_scale))
        self.actual_screen = pygame.display.set_mode((window_width, window_height))

        self.clock = pygame.time.Clock()
        self.screen.fill((255, 255, 255))

        self.module_1 = MM20(self, 0)
        self.module_2 = MM20(self, 1)
        self.module_3 = MM20(self, 2)

        self.update_modules()

        pygame.display.flip()
        self.base_title = "MESA"
        pygame.display.set_caption(self.base_title)

    def update_modules(self, mouse_pos=(0, 0), click=0):
        def update_byte_1_1(new_1):
            self.P2 = new_1

        def update_byte_1_2(new_2):
            self.P3 = new_2

        def update_byte_2_1(new_1):
            self.P1 = new_1

        def update_byte_2_2(new_2):
            self.P5 = new_2

        def update_byte_3_1(new_1):
            self.P6 = new_1

        def update_byte_3_2(new_2):
            self.P7 = new_2

        self.module_1.draw(self.P2, self.P3, update_byte_1_1, update_byte_1_2, mouse_pos, click)
        self.module_2.draw(self.P1, self.P5, update_byte_2_1, update_byte_2_2, mouse_pos, click)
        self.module_3.draw(self.P6, self.P7, update_byte_3_1, update_byte_3_2, mouse_pos, click)

    def update(self):
        mouse_pos = (0, 0)
        click = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                mouse_pos = (mouse_pos[0] * self.virtual_screen_scale, mouse_pos[1] * self.virtual_screen_scale)
                click = event.button

        self.screen.fill((255, 255, 255))
        self.update_modules(mouse_pos, click)

        scaled_surface = pygame.transform.smoothscale(self.screen,
                                                      (self.actual_screen.get_width(), self.actual_screen.get_height()))
        self.actual_screen.blit(scaled_surface, (0, 0))

        pygame.display.flip()

        fps = self.clock.get_fps()
        pygame.display.set_caption(f"{self.base_title} - FPS: {fps:.2f}")

        self.delta_time = self.clock.tick(240) / 1000  # delta_time in seconds

        return self.delta_time

    # waits for a certain amount of cycles (1 cycle = 1ms)
    # it first waits the remaining time of the current cycle and then waits the remaining cycles
    def wait_cycle(self, cycles):
        zyklus_update()
        while cycles > 0:
            self.wait_remaining()
            cycles -= 1

    def wait_remaining(self):
        self.update()

        current = time.time_ns()
        diff = (current - self.prev_time) / 1_000_000_000
        self.prev_time = current

        remaining = max(0, (TIC / 1000) - diff)
        time.sleep(remaining)


AN = "AN"
AUS = "AUS"
POS_FLANKE = "POS_FLANKE"
NEG_FLANKE = "NEG_FLANKE"
ERROR = "ERROR"
INVALID_INDEX = 255

B1 = 1
B2 = 2
B3 = 3

# Global variables
previous_btn_reads = [0] * 8
current_btn_reads = [0] * 8
blink_counters = [0] * 8
previous_blink_freq = [0] * 8


# Function to update stored button states
def zyklus_update():
    global previous_btn_reads, current_btn_reads
    previous_btn_reads = current_btn_reads[:]


# Function to read the current button state and compare it with the previous state
def read(btn_mask):
    global previous_btn_reads, current_btn_reads
    btns = [0] * 8
    current = (mesa.P3 & btn_mask) == btn_mask

    mask_to_index(btn_mask, btns)
    btn = btns[0]

    if btn == INVALID_INDEX:
        return ERROR

    current_btn_reads[btn] = current

    if previous_btn_reads[btn] != current and current == 1:
        return POS_FLANKE

    if previous_btn_reads[btn] != current and current == 0:
        return NEG_FLANKE

    if current == 1:
        return AN
    else:
        return AUS


# Function for LED blinking
def blinken(led_mask, id):
    global blink_counters, previous_blink_freq

    if id == B1:
        frequenz = B1_FREQ
        an = B1_AN
        aus = B1_AUS
    elif id == B2:
        frequenz = B2_FREQ
        an = B2_AN
        aus = B2_AUS
    elif id == B3:
        frequenz = B3_FREQ
        an = B3_AN
        aus = B3_AUS
    else:
        return

    gesammt = an + aus
    leds = [0] * 8
    mask_to_index(led_mask, leds)
    current = (mesa.P2 & led_mask) == led_mask
    periode = 1000.0 / frequenz

    if leds[0] == INVALID_INDEX:
        return

    if id != previous_blink_freq[leds[0]]:
        blink_counters[leds[0]] = 0
        previous_blink_freq[leds[0]] = id

    if an == 0:
        mesa.P2 &= ~led_mask
        return
    elif aus == 0:
        mesa.P2 |= led_mask
        return

    if current == 1 and blink_counters[leds[0]] <= 0:
        aus_tics = int((periode * aus) / gesammt)
        blink_counters[leds[0]] = aus_tics
        mesa.P2 &= ~led_mask
    elif current == 0 and blink_counters[leds[0]] <= 0:
        an_tics = int((periode * an) / gesammt)
        blink_counters[leds[0]] = an_tics
        mesa.P2 |= led_mask

    blink_counters[leds[0]] -= mesa.delta_time * 1000  # Adjusting blink counter based on delta_time


# Function to convert mask to index
def mask_to_index(mask, indices):
    for i in range(8):
        indices[i] = INVALID_INDEX

    i = 0

    if mask & 0x01:
        indices[i] = 0
        i += 1

    if mask & 0x02:
        indices[i] = 1
        i += 1

    if mask & 0x04:
        indices[i] = 2
        i += 1

    if mask & 0x08:
        indices[i] = 3
        i += 1

    if mask & 0x10:
        indices[i] = 4
        i += 1

    if mask & 0x20:
        indices[i] = 5
        i += 1

    if mask & 0x40:
        indices[i] = 6
        i += 1

    if mask & 0x80:
        indices[i] = 7
        i += 1


# Function to convert Gray code to decimal
def gray_to_decimal(gray):
    decimal = gray
    while gray >> 1:
        decimal ^= gray
    return decimal


# Function to convert decimal to Gray code
def decimal_to_gray(decimal):
    return decimal ^ (decimal >> 1)


mesa = MESA()
