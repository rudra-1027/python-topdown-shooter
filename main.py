# ── MOBILE / PC CONFIG ───────────────────────────────────────────────────────
# Comment out the PC block and uncomment the mobile block to build for mobile.

# -- PC --
# from kivy.config import Config
# Config.set('graphics', 'width',  '1280')
# Config.set('graphics', 'height', '720')

# -- MOBILE (uncomment below, comment out PC block above) --
from kivy.config import Config

# ── GLOBAL SCALE FACTOR (must match kv file) ─────────────────────────────────
# 0.70 = compact mobile  |  0.80 = normal mobile  |  1.0 = PC original size
S = 0.70

import json
import hashlib
SECRET = "TeenSurvivor2026"
import os
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.animation import Animation
from kivy.uix.floatlayout import FloatLayout
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty, ListProperty, StringProperty, ObjectProperty
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.graphics import (
    Rectangle, Color, Line, RoundedRectangle, Ellipse,
    StencilPush, StencilUse, StencilUnUse, StencilPop
)
from kivy.core.audio import SoundLoader
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics.texture import Texture
from kivy.graphics import PushMatrix, PopMatrix, Translate
from pytmx import TiledMap

import math
import random

# Config.set("graphics", "resizable", False)


# ── HELPERS ───────────────────────────────────────────────────────────────────
def sdp(x):
    """Scaled dp — equivalent to dp(x) * S in the KV file."""
    return dp(x) * S

def ssp(x):
    """Scaled sp — equivalent to sp(x) * S in the KV file."""
    return sp(x) * S


class Game(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # PC only — comment out for mobile
        # Window.size = (1280, 720)

        Window.bind(on_key_down=self.on_key_down)
        Window.bind(on_key_up=self.on_key_up)
        Window.clearcolor = (0.1, 0.35, 0.55, 1)

        self.keys_pressed = set()
        self.gameState = "playing"
        self.world_layer = FloatLayout()
        self.ground_layer = FloatLayout()
        self.game_layer = FloatLayout()
        self.ground_layer.size_hint = (None, None)
        self.game_layer.size_hint = (None, None)
        self.ui_layer = GameUI()
        self.overlay_layer = FloatLayout()

        self.overlay_layer.size_hint = (None, None)
        self.overlay_layer.size = (0, 0)

        self.gs = Sound()
        self.gs.game_music.loop = True
        if self.gs.game_music.state != "play":
            self.gs.game_music.play()

        self.player = Player()

        # ── Joysticks — sized with sdp() ──────────────────────────────────────
        joy_size = (sdp(150), sdp(150))   # matches <Joystick> size: dp(150)*S

        self.joystick = JoyStick(
            size_hint=(None, None),
            size=joy_size,
            pos_hint={"x": 0.05, "y": 0.05}
        )
        self.AttackJoystick = AttackJoystick(
            size_hint=(None, None),
            size=joy_size,
            pos_hint={"right": 0.95, "y": 0.05}
        )
        self.AttackJoystick.pos = (Window.width - sdp(160), sdp(20))
        self.player.gun = Gun(owner=self.player)

        self.weapon_menu = RadialWeaponMenu(size_hint=(1, 1), opacity=0, disabled=True)

        self.game_layer.add_widget(self.player)
        self.game_layer.add_widget(self.player.gun)
        self.ui_layer.add_widget(self.AttackJoystick)
        self.ui_layer.add_widget(self.joystick)

        self.player.center = self.center

        # ── PlayerHealthBar — sized with sdp() ───────────────────────────────
        hbar_w = min(sdp(260), Window.width * 0.52)
        hbar_h = sdp(80)
        self.player.healthBar = PlayerHealthBar(
            max_health=self.player.max_health,
            health=self.player.health,
            size_hint=(None, None),
            size=(hbar_w, hbar_h),
            pos_hint={"x": 0.02, "top": 0.98}
        )
        self.ui_layer.add_widget(self.player.healthBar)

        self.player.guns = {
            "assualt": {"damage": 25, "range": 800, "magazine": 30, "ammo": 30, "rate": 0.5, "reload": 1.5}
        }
        self.player.speed = 8
        self.powerUps = []
        self.powerUp_type = {
            1: {"type": "health",         "size": sdp(28), "color": [0, 1, 0, 1],     "symbol": "+"},
            2: {"type": "sheild",         "size": sdp(28), "color": [0, 0.6, 1, 1],   "symbol": "S"},
            3: {"type": "damage_booster", "size": sdp(28), "color": [1, 0, 0, 1],     "symbol": "D"},
            4: {"type": "nuke",           "size": sdp(28), "color": [1, 0.5, 0, 1],   "symbol": "N"},
            5: {"type": "freeze",         "size": sdp(28), "color": [0.5, 0.8, 1, 1], "symbol": "F"},
        }
        self.gunList = [
            {"name": "Gun: Shotgun", "type": "shotgun", "min_wave": 2},
            {"name": "Gun: machine", "type": "machine", "min_wave": 4},
            {"name": "Gun: sniper",  "type": "sniper",  "min_wave": 6},
        ]
        self.upgrades = [
            {"target": "player", "name": "Regen +1",      "type": "regen",      "value": 1,  "count": 0},
            {"target": "player", "name": "Max Health +20", "type": "max_health", "value": 20, "count": 0},
            {"target": "player", "name": "Heal 25",        "type": "health",     "value": 25, "count": 0},
        ]
        self.ak_icon      = CoreImage("gameAsset/gun/ak.png").texture
        self.machine_icon = CoreImage("gameAsset/gun/machine.png").texture
        self.sniper_icon  = CoreImage("gameAsset/gun/sniper.png").texture
        self.shotgun_icon = CoreImage("gameAsset/gun/shotgun.png").texture

        # enemy / state
        self.enemies = []
        self.attacks = []
        self.Enemyattacks = []
        self.remove_attack = []
        self.remove_enemyAttack = []
        self.remove_enemy = []
        self.remove_powerup = []
        self.obstacles = []
        self.ground = []
        self.counter = 0
        self.game_over_shown = False
        self.bossWave = False
        self.bossAlive = 0
        self.maxBoss = 1
        self.wave = ""
        self.wave_count = 0
        self.enemies_per_wave = 0
        self.spawn_point = [(7000, 1400), (5000, 1400), (2000, 1700), (800, 700)]

        self.enemy       = Clock.schedule_interval(self.spawnEnemy, 8)
        self.powerUp     = Clock.schedule_interval(self.spawnPowerUp, 8)
        self.regen_event = Clock.schedule_interval(self.playerRegen, 5)
        self.game_update = Clock.schedule_interval(self.update, 1 / 60)

        self.add_widget(self.world_layer)
        self.world_layer.add_widget(self.ground_layer)
        self.world_layer.add_widget(self.game_layer)
        self.add_widget(self.overlay_layer)
        self.add_widget(self.ui_layer)
        self.add_widget(self.weapon_menu)

        with self.world_layer.canvas.before:
            PushMatrix()
            self.camera_translate = Translate(0, 0)
        with self.world_layer.canvas.after:
            PopMatrix()

        self.ui_layer.game    = self
        self.overlay_layer.game = self
        self.game_layer.game  = self

        self.loadMap("gameAsset/maps/map4.tmx")
        self.hit = self.load_sheet(
            CoreImage("gameAsset/effects/NEw pack blood/4_100x100px.png").texture,
            100, 100, 6, 2
        )

    # ── save / load (unchanged logic, kept intact) ───────────────────────────
    def save_stats(self):
        old_score = 0
        old_wave  = 0
        if os.path.exists("stats.dat"):
            with open("stats.dat", "r") as f:
                stats = json.load(f)
            old_score = stats.get("high_score", 0)
            old_wave  = stats.get("highest_wave", 0)
        with open("stats.dat", "w") as f:
            json.dump({
                "high_score":   max(old_score, self.player.score),
                "highest_wave": max(old_wave, self.wave_count)
            }, f)

    def save_game(self):
        data = {
            "score":       self.player.score,
            "wave":        self.wave_count,
            "guns":        self.player.guns,
            "current_gun": self.player.gun.current,
            "health":      self.player.health,
            "max_health":  self.player.max_health,
            "regen":       self.player.regen,
            "upgrades":    self.player.gun.assault_upgrade,
            "speed":       self.player.speed,
            "counter":     self.counter,
            "bossWave":    self.bossWave,
            "bossAlive":   self.bossAlive,
            "maxBoss":     self.maxBoss,
        }
        raw      = json.dumps(data, sort_keys=True)
        checksum = hashlib.sha256((raw + SECRET).encode()).hexdigest()
        with open("save.dat", "w") as f:
            json.dump({"data": data, "checksum": checksum}, f)

    def load_game(self):
        if not os.path.exists("save.dat"):
            return False
        with open("save.dat", "r") as f:
            save_data = json.load(f)
        if (
            not isinstance(save_data, dict)
            or "data" not in save_data
            or "checksum" not in save_data
            or not save_data["data"]
        ):
            return False
        raw      = json.dumps(save_data["data"], sort_keys=True)
        expected = hashlib.sha256((raw + SECRET).encode()).hexdigest()
        if expected != save_data["checksum"]:
            return False
        data = save_data["data"]
        self.player.score      = data["score"]
        self.wave_count        = data["wave"]
        self.player.guns       = data["guns"]
        self.player.gun.current = data["current_gun"]
        self.player.health     = data["health"]
        self.player.max_health = data["max_health"]
        self.player.healthBar.health     = self.player.health
        self.player.healthBar.max_health = self.player.max_health
        self.player.regen      = data["regen"]
        saved_upgrades         = data.get("upgrades", [])
        for saved in saved_upgrades:
            for upgrade in self.player.gun.assault_upgrade:
                if (
                    upgrade["type"]   == saved["type"]
                    and upgrade["target"] == saved["target"]
                    and upgrade.get("gun") == saved.get("gun")
                ):
                    upgrade["count"] = saved["count"]
        self.rebuild_upgrade_pool()
        return True

    def rebuild_upgrade_pool(self):
        self.upgrades.clear()
        for upgrade in self.player.gun.assault_upgrade:
            if (
                self.wave_count >= upgrade["min_wave"]
                and upgrade["gun"] in self.player.guns
                and upgrade["count"] < upgrade["max_stack"]
            ):
                self.upgrades.append(upgrade)

    # ── keyboard ─────────────────────────────────────────────────────────────
    def on_key_down(self, window, key, scancode, codepoint, modifiers):
        self.keys_pressed.add(key)
        if key == 32:
            if not hasattr(self.player, "attack") and self.gameState == "playing":
                self.AttackJoystick.shooting = True
                self.player.attack = Clock.schedule_interval(
                    self.spawnAtttck,
                    self.player.guns[self.player.gun.current]["rate"]
                )

    def on_key_up(self, window, key, scancode):
        if key in self.keys_pressed:
            self.keys_pressed.remove(key)
        if key == 32:
            if hasattr(self.player, "attack"):
                self.player.attack.cancel()
                del self.player.attack
                self.AttackJoystick.shooting = False

    def update_joystick_from_keyboard(self):
        vx, vy = 0, 0
        if 97  in self.keys_pressed: vx -= 1
        if 100 in self.keys_pressed: vx += 1
        if 119 in self.keys_pressed: vy += 1
        if 115 in self.keys_pressed: vy -= 1
        length = (vx**2 + vy**2) ** 0.5
        if length > 0:
            vx /= length
            vy /= length
        if length > 0:
            self.joystick.vector = (vx, vy)
        else:
            if not self.joystick.active:
                self.joystick.vector = (0, 0)

    def play_click(self):
        self.gs.button_click.stop()
        self.gs.button_click.play()

    def play_click2(self):
        self.gs.button_click2.stop()
        self.gs.button_click2.play()

    def enable_darkness(self):
        if hasattr(self, "dark_overlay"):
            return
        self.dark_overlay = DarknessOverlay(radius=sdp(220))
        self.dark_overlay.size = Window.size
        self.dark_overlay.pos  = (0, 0)
        self.ui_layer.add_widget(self.dark_overlay)
        px = self.player.center_x + self.camera_translate.x
        py = self.player.center_y + self.camera_translate.y
        self.dark_overlay.update_light(px, py)

    def disable_darkness(self):
        if hasattr(self, "dark_overlay"):
            self.ui_layer.remove_widget(self.dark_overlay)
            del self.dark_overlay

    def update_camera(self):
        camera_x = self.player.center_x - Window.width  / 2
        camera_y = self.player.center_y - Window.height / 2
        max_x = self.max_world_x - Window.width
        max_y = self.max_world_y - Window.height
        camera_x = max(self.min_world_x, min(camera_x, max_x))
        camera_y = max(self.min_world_y, min(camera_y, max_y))
        self.camera_translate.x = -camera_x
        self.camera_translate.y = -camera_y
        if hasattr(self, "dark_overlay"):
            self.dark_overlay.size = Window.size
            actual_camera_x = -self.camera_translate.x
            actual_camera_y = -self.camera_translate.y
            player_screen_x = self.player.center_x - actual_camera_x
            player_screen_y = self.player.center_y - actual_camera_y
            self.dark_overlay.update_light(player_screen_x, player_screen_y)

    def loadMap(self, tmx_path):
        if not os.path.isabs(tmx_path):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            tmx_path = os.path.join(base_dir, tmx_path)
        tmx_data       = TiledMap(tmx_path)
        self.tmx_data  = tmx_data
        MAP_SCALE      = 0.4
        tile_w         = tmx_data.tilewidth  * MAP_SCALE
        tile_h         = tmx_data.tileheight * MAP_SCALE
        ground_row_step   = tile_h - 175
        obstacle_row_step = tile_h - 168
        self.ground_layer.canvas.clear()
        self.obstacle_rects = []
        texture_cache = {}

        def get_texture(gid):
            if gid in texture_cache:
                return texture_cache[gid]
            try:
                image_info = tmx_data.images[gid]
                if image_info is None:
                    return None
                image_path = image_info[0] if isinstance(image_info, tuple) else image_info
                texture = CoreImage(image_path).texture
                texture_cache[gid] = texture
                return texture
            except Exception as e:
                print("Texture load error:", gid, e)
                return None

        def get_draw_pos(x, y, tex_w, tex_h, row_step):
            draw_x = x * tile_w
            draw_y = y * row_step
            if y % 2 == 1:
                draw_x += tile_w / 2
            draw_x -= (tex_w - tile_w) / 2
            draw_y -= (tex_h - tile_h)
            return draw_x, draw_y

        min_x, min_y =  float("inf"),  float("inf")
        max_x, max_y = float("-inf"), float("-inf")

        for layer in tmx_data.visible_layers:
            if not hasattr(layer, "data"):
                continue
            is_obs    = layer.name and layer.name.lower() == "obstacles"
            row_step  = obstacle_row_step if is_obs else ground_row_step
            for x, y, gid in layer:
                if gid == 0:
                    continue
                texture = get_texture(gid)
                if texture is None:
                    continue
                tex_w = texture.width  * MAP_SCALE
                tex_h = texture.height * MAP_SCALE
                draw_x, draw_y = get_draw_pos(x, y, tex_w, tex_h, row_step)
                min_x = min(min_x, draw_x)
                min_y = min(min_y, draw_y)
                max_x = max(max_x, draw_x + tex_w)
                max_y = max(max_y, draw_y + tex_h)

        self.world_w = max_x - min_x
        self.world_h = max_y - min_y
        self.ground_layer.size = (self.world_w, self.world_h)
        self.game_layer.size   = (self.world_w, self.world_h)
        offset_x = -min_x
        offset_y = -min_y
        self.offset_x = offset_x
        self.offset_y = offset_y
        margin_x = tile_w * 0.5
        margin_y = tile_h * 0.5
        self.min_world_x = margin_x + 50
        self.min_world_y = margin_y + 50
        self.max_world_x = self.world_w - margin_x
        self.max_world_y = self.world_h - margin_y

        with self.ground_layer.canvas:
            for layer in tmx_data.visible_layers:
                if not hasattr(layer, "data"):
                    continue
                is_obstacle_layer = layer.name and layer.name.lower() == "obstacles"
                row_step = obstacle_row_step if is_obstacle_layer else ground_row_step
                for x, y, gid in layer:
                    if gid == 0:
                        continue
                    texture = get_texture(gid)
                    if texture is None:
                        continue
                    tex_w = texture.width  * MAP_SCALE
                    tex_h = texture.height * MAP_SCALE
                    draw_x, draw_y = get_draw_pos(x, y, tex_w, tex_h, row_step)
                    draw_x += offset_x
                    draw_y += offset_y
                    Rectangle(texture=texture, pos=(draw_x, draw_y), size=(tex_w, tex_h))
                    if is_obstacle_layer:
                        self.obstacle_rects.append((draw_x, draw_y, tex_w, tex_h))

        print("Map Loaded Successfully")

    def rect_blocked(self, x, y, w, h):
        for ox, oy, ow, oh in self.obstacle_rects:
            if x < ox + ow and x + w > ox and y < oy + oh and y + h > oy:
                return True
        return False

    def rect_overlap(self, x1, y1, w1, h1, x2, y2, w2, h2):
        return (x1 < x2 + w2 and x1 + w1 > x2 and y1 < y2 + h2 and y1 + h1 > y2)

    def enemy_colloison(self, enemy, new_x, new_y):
        return self.rect_blocked(
            new_x + enemy.hitbox_offset_x,
            new_y + enemy.hitbox_offset_y,
            enemy.hitbox_w,
            enemy.hitbox_h
        )

    def show_game_over(self):
        from kivy.graphics import Color as KColor, RoundedRectangle as KRR, Line as KLine

        self.ui_layer.ids.pause_button.opacity   = 0
        self.ui_layer.ids.pause_button.disabled  = True
        self.ui_layer.ids.weapon_button.opacity  = 0
        self.ui_layer.ids.weapon_button.disabled = True
        self.ui_layer.ids.gun_ui.opacity         = 0
        self.ui_layer.ids.gun_ui.disabled        = True
        self.ui_layer.ids.top_hud.opacity        = 0
        self.ui_layer.ids.top_hud.disabled       = True
        self.player.healthBar.opacity            = 0
        self.player.healthBar.disabled           = True
        self.joystick.opacity                    = 0
        self.joystick.disabled                   = True
        self.AttackJoystick.opacity              = 0
        self.AttackJoystick.disabled             = True

        root    = FloatLayout(size_hint=(1, 1))
        overlay = Widget(size_hint=(1, 1))
        with overlay.canvas:
            KColor(rgba=(0, 0, 0, 0.75))
            overlay._rect = Rectangle(pos=overlay.pos, size=overlay.size)
        def _upd_overlay(w, *_):
            w._rect.pos  = w.pos
            w._rect.size = w.size
        overlay.bind(pos=_upd_overlay, size=_upd_overlay)
        root.add_widget(overlay)

        panel = BoxLayout(
            orientation='vertical',
            size_hint=(None, 1),
            width=min(sdp(340), Window.width * 0.88),
            pos_hint={'x': 0, 'y': 0},
            spacing=sdp(8),
            padding=[sdp(28), sdp(36), sdp(28), sdp(28)],
        )
        with panel.canvas.before:
            KColor(rgba=(0.04, 0.04, 0.08, 0.93))
            panel._bg     = Rectangle(pos=panel.pos, size=panel.size)
            KColor(rgba=(0.85, 0.25, 0.25, 0.5))
            panel._border = Rectangle(pos=(panel.right - dp(2), panel.y), size=(dp(2), panel.height))
            KColor(rgba=(0.85, 0.25, 0.25, 1))
            panel._top    = Rectangle(pos=(panel.x, panel.top - dp(4)), size=(panel.width, dp(4)))
        def _upd_panel(w, *_):
            w._bg.pos     = w.pos
            w._bg.size    = w.size
            w._border.pos  = (w.right - dp(2), w.y)
            w._border.size = (dp(2), w.height)
            w._top.pos    = (w.x, w.top - dp(4))
            w._top.size   = (w.width, dp(4))
        panel.bind(pos=_upd_panel, size=_upd_panel)

        def make_label(text, font_size, color, height, halign='left', bold=False):
            lbl = Label(
                text=text, font_size=ssp(font_size), bold=bold, color=color,
                size_hint_y=None, height=sdp(height),
                halign=halign, valign='middle',
            )
            lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            return lbl

        panel.add_widget(make_label('LAST TEEN STANDING', 11, (0.85, 0.25, 0.25, 1), 20, bold=True))
        panel.add_widget(make_label('GAME OVER',           28, (0.91, 0.9,  0.96, 1), 42, bold=True))

        div = Widget(size_hint_y=None, height=dp(1))
        with div.canvas:
            KColor(rgba=(1, 1, 1, 0.07))
            div._r = Rectangle(pos=div.pos, size=div.size)
        div.bind(pos=lambda w, _: setattr(w._r, 'pos', w.pos),
                 size=lambda w, _: setattr(w._r, 'size', w.size))
        panel.add_widget(div)
        panel.add_widget(Widget(size_hint_y=None, height=sdp(6)))

        stats_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=sdp(64), spacing=sdp(6))
        for label_txt, value_txt in [("WAVE", str(self.wave_count)), ("SCORE", str(self.player.score))]:
            stat_box = BoxLayout(orientation='vertical')
            with stat_box.canvas.before:
                KColor(rgba=(1, 1, 1, 0.03))
                stat_box._bg = KRR(pos=stat_box.pos, size=stat_box.size, radius=[sdp(6)])
            def _upd_stat(w, *_): w._bg.pos = w.pos; w._bg.size = w.size
            stat_box.bind(pos=_upd_stat, size=_upd_stat)
            val_lbl = Label(text=value_txt, font_size=ssp(20), bold=True,
                            color=(0.85, 0.8, 1, 1), halign='center')
            val_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            key_lbl = Label(text=label_txt, font_size=ssp(9), bold=True,
                            color=(0.5, 0.45, 0.65, 1), size_hint_y=None, height=sdp(18), halign='center')
            key_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            stat_box.add_widget(val_lbl)
            stat_box.add_widget(key_lbl)
            stats_row.add_widget(stat_box)
        panel.add_widget(stats_row)
        panel.add_widget(Widget(size_hint_y=None, height=sdp(14)))

        def _make_primary_btn(text):
            btn = Button(
                text=text, size_hint_y=None, height=sdp(54),
                font_size=ssp(14), bold=True,
                background_normal='', background_color=(0, 0, 0, 0),
                color=(0.15, 0.12, 0.05, 1),
            )
            with btn.canvas.before:
                KColor(rgba=(0.91, 0.75, 0.29, 1))
                btn._bg    = KRR(pos=btn.pos, size=btn.size, radius=[sdp(8)])
                KColor(rgba=(1, 1, 1, 0.12))
                btn._shine = KRR(pos=(btn.x + sdp(4), btn.top - sdp(10)),
                                 size=(btn.width - sdp(8), sdp(8)), radius=[sdp(6)])
            def _upd(w, *_):
                w._bg.pos    = w.pos;  w._bg.size   = w.size
                w._shine.pos = (w.x + sdp(4), w.top - sdp(10))
                w._shine.size = (w.width - sdp(8), sdp(8))
            btn.bind(pos=_upd, size=_upd)
            return btn

        def _make_danger_btn(text):
            btn = Button(
                text=text, size_hint_y=None, height=sdp(54),
                font_size=ssp(14), bold=True,
                background_normal='', background_color=(0, 0, 0, 0),
                color=(0.90, 0.38, 0.38, 1),
            )
            with btn.canvas.before:
                KColor(rgba=(0.18, 0.07, 0.07, 1))
                btn._bg  = KRR(pos=btn.pos, size=btn.size, radius=[sdp(8)])
                KColor(rgba=(0.80, 0.22, 0.22, 0.25))
                btn._bdr = KLine(rounded_rectangle=(btn.x, btn.y, btn.width, btn.height, sdp(8)), width=dp(1))
            def _upd(w, *_):
                w._bg.pos  = w.pos; w._bg.size = w.size
                w._bdr.rounded_rectangle = (w.x, w.y, w.width, w.height, sdp(8))
            btn.bind(pos=_upd, size=_upd)
            return btn

        restart_btn = _make_primary_btn('RESTART')
        def on_restart(instance):
            self.play_click()
            self.ui_layer.remove_widget(self._game_over_root)
            app = App.get_running_app()
            app.root.clear_widgets()
            game = Game()
            if hasattr(self, 'main_menu'):
                game.main_menu = self.main_menu
            app.root.add_widget(game)
        restart_btn.bind(on_release=on_restart)
        panel.add_widget(restart_btn)

        quit_btn = _make_danger_btn('QUIT TO MENU')
        def on_quit(instance):
            self.play_click()
            app = App.get_running_app()
            app.root.clear_widgets()
            app.root.add_widget(MainMenu())
            if self.gs.menu_music.state != "play":
                self.gs.menu_music.play()
        quit_btn.bind(on_release=on_quit)
        panel.add_widget(quit_btn)

        panel.add_widget(Widget())
        footer = make_label('v1.0.0  ·  BETTER LUCK NEXT TIME', 9, (0.25, 0.22, 0.32, 1), 18)
        panel.add_widget(footer)
        root.add_widget(panel)
        self._game_over_root = root
        self.ui_layer.add_widget(root)

    def pause(self):
        if self.gameState != "playing":
            return
        self.gameState = "pause"
        if hasattr(self, "dark_overlay"):
            self.disable_darkness()
        if self.gs.menu_music.state != "play":
            self.gs.menu_music.play()
        if self.gs.game_music.state == "play":
            self.gs.game_music.stop()
        self.ui_layer.ids.pause_menu.opacity  = 1
        self.ui_layer.ids.pause_menu.disabled = False
        self.ui_layer.ids.pause_button.opacity   = 0;  self.ui_layer.ids.pause_button.disabled  = True
        self.ui_layer.ids.weapon_button.opacity  = 0;  self.ui_layer.ids.weapon_button.disabled = True
        self.ui_layer.ids.gun_ui.opacity         = 0;  self.ui_layer.ids.gun_ui.disabled        = True
        self.ui_layer.ids.top_hud.opacity        = 0;  self.ui_layer.ids.top_hud.disabled       = True
        self.player.healthBar.opacity = 0;  self.player.healthBar.disabled = True
        self.joystick.opacity = 0;          self.joystick.disabled = True
        self.AttackJoystick.opacity = 0;    self.AttackJoystick.disabled = True
        self.ui_layer.ids.stat_wave.text  = str(self.wave_count)
        self.ui_layer.ids.stat_score.text = str(self.player.score)

    def quit_to_menu(self):
        app = App.get_running_app()
        app.root_layout.clear_widgets()
        app.root_layout.add_widget(MainMenu())

    def resume(self):
        self.gameState = "playing"
        if self.gs.menu_music.state == "play":
            self.gs.menu_music.stop()
        if self.gs.game_music.state != "play":
            self.gs.game_music.play()
        self.ui_layer.ids.pause_menu.opacity  = 0
        self.ui_layer.ids.pause_menu.disabled = True
        self.ui_layer.ids.pause_button.opacity   = 1;  self.ui_layer.ids.pause_button.disabled  = False
        self.ui_layer.ids.weapon_button.opacity  = 1;  self.ui_layer.ids.weapon_button.disabled = False
        self.ui_layer.ids.gun_ui.opacity         = 1;  self.ui_layer.ids.gun_ui.disabled        = False
        self.ui_layer.ids.top_hud.opacity        = 1;  self.ui_layer.ids.top_hud.disabled       = False
        self.player.healthBar.opacity = 1;  self.player.healthBar.disabled = False
        self.joystick.opacity = 1;          self.joystick.disabled = False
        self.AttackJoystick.opacity = 1;    self.AttackJoystick.disabled = False

    def restart(self):
        app = App.get_running_app()
        app.root.clear_widgets()
        if self.gs.menu_music.state == "play":
            self.gs.menu_music.stop()
        game = Game()
        with open("save.dat", "w") as f:
            json.dump({}, f)
        if hasattr(self, 'main_menu'):
            game.main_menu = self.main_menu
        app.root.add_widget(game)

    def playerRegen(self, dt):
        if self.gameState != "playing":
            return
        if self.player.health < self.player.max_health:
            self.player.health += self.player.regen

    def show_menu(self):
        self.gs.levelup.play()
        self.gameState    = "pause"
        self.unlocked_gun = None
        for gun in self.gunList:
            if self.wave_count == gun["min_wave"]:
                self.player.guns[gun["type"]] = self.player.gun.gunData[gun["type"]]
                self.unlocked_gun = gun
        for upgrade in self.player.gun.assault_upgrade:
            if self.wave_count >= upgrade["min_wave"] and upgrade not in self.upgrades and upgrade["gun"] in self.player.guns:
                self.upgrades.append(upgrade)
            if upgrade["count"] >= upgrade["max_stack"] and upgrade in self.upgrades:
                self.upgrades.remove(upgrade)
        self.upgrade_panel = UpgradePanel()
        if self.unlocked_gun:
            self._show_gun_unlock_screen()
        else:
            self._show_upgrade_cards()

    def _show_gun_unlock_screen(self):
        from kivy.graphics import Color as KColor, RoundedRectangle as KRR, Line as KLine, Rectangle as KRect
        panel   = self.upgrade_panel
        box     = panel.ids.upgrade_box
        box.clear_widgets()
        inner_box       = box.parent
        inner_box.size  = (sdp(520), sdp(480))
        GUN_NAME  = {"shotgun": "SHOTGUN", "machine": "MACHINE GUN", "sniper": "SNIPER RIFLE", "assualt": "ASSAULT RIFLE"}
        GUN_DESC  = {"shotgun": "Close-range devastation", "machine": "Rapid suppression fire",
                     "sniper": "Extreme long-range damage", "assualt": "Balanced automatic rifle"}
        gun_type  = self.unlocked_gun["type"]
        gun_name  = GUN_NAME.get(gun_type, gun_type.upper())
        gun_desc  = GUN_DESC.get(gun_type, "New weapon unlocked!")
        card = BoxLayout(orientation="vertical", spacing=sdp(10),
                         padding=[sdp(28), sdp(20), sdp(28), sdp(20)], size_hint=(1, 1))
        with card.canvas.before:
            KColor(rgba=(0.16, 0.12, 0.04, 1))
            card._bg     = KRR(pos=card.pos, size=card.size, radius=[sdp(16)])
            KColor(rgba=(0.91, 0.75, 0.29, 0.55))
            card._border = KLine(rounded_rectangle=(card.x, card.y, card.width, card.height, sdp(16)), width=dp(1.5))
        def update_card(w, *_):
            w._bg.pos = w.pos; w._bg.size = w.size
            w._border.rounded_rectangle = (w.x, w.y, w.width, w.height, sdp(16))
        card.bind(pos=update_card, size=update_card)

        for txt, fs, col, ht, bold in [
            ("NEW WEAPON UNLOCKED", 18, (0.91, 0.75, 0.29, 1), 30, True),
            (gun_name,              26, (1, 1, 1, 1),           40, True),
            (gun_desc,              13, (0.8, 0.8, 0.8, 1),     25, False),
        ]:
            lbl = Label(text=txt, font_size=ssp(fs), bold=bold, color=col,
                        size_hint_y=None, height=sdp(ht), halign="center", valign="middle")
            lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
            card.add_widget(lbl)
        card.add_widget(Widget())

        gun_data = self.player.guns[gun_type]
        stats    = BoxLayout(spacing=sdp(10), size_hint_y=None, height=sdp(70))
        for title_txt, value in [("DMG", gun_data.get("damage", "-")), ("MAG", gun_data.get("magazine", "-")),
                                  ("RNG", gun_data.get("range",  "-")), ("RLD", gun_data.get("reload",  "-"))]:
            stat_box = BoxLayout(orientation="vertical")
            with stat_box.canvas.before:
                KColor(rgba=(1, 1, 1, 0.04))
                stat_box._bg = KRR(pos=stat_box.pos, size=stat_box.size, radius=[sdp(8)])
            def _upd_stat(w, *_): w._bg.pos = w.pos; w._bg.size = w.size
            stat_box.bind(pos=_upd_stat, size=_upd_stat)
            for t, fs, col in [(str(value), 18, (0.91, 0.75, 0.29, 1)), (title_txt, 10, (0.7, 0.7, 0.7, 1))]:
                l = Label(text=t, font_size=ssp(fs), bold=(fs==18), color=col, halign="center", valign="middle")
                l.bind(size=lambda w, s: setattr(w, "text_size", s))
                stat_box.add_widget(l)
            stats.add_widget(stat_box)
        card.add_widget(stats)
        card.add_widget(Widget(size_hint_y=None, height=sdp(8)))

        cont_btn = Button(text="CONTINUE", size_hint=(1, None), height=sdp(46),
                          background_normal="", background_color=(0, 0, 0, 0),
                          color=(0.15, 0.12, 0.04, 1), bold=True)
        with cont_btn.canvas.before:
            KColor(rgba=(0.91, 0.75, 0.29, 1))
            cont_btn._bg = KRR(pos=cont_btn.pos, size=cont_btn.size, radius=[sdp(10)])
        def update_btn(w, *_): w._bg.pos = w.pos; w._bg.size = w.size
        cont_btn.bind(pos=update_btn, size=update_btn)
        def on_continue(instance):
            self.play_click(); box.clear_widgets(); self._show_upgrade_cards()
        cont_btn.bind(on_release=on_continue)
        card.add_widget(cont_btn)
        box.add_widget(card)
        if panel.parent is None:
            self.ui_layer.add_widget(panel)

    def _show_upgrade_cards(self):
        from kivy.graphics import Color as KColor, RoundedRectangle as KRR, Line as KLine
        box       = self.upgrade_panel.ids.upgrade_box
        box.clear_widgets()
        inner_box = box.parent
        inner_box.size = (min(sdp(600), Window.width * 0.95), min(sdp(340), Window.height * 0.55))

        player_upgrades = [u for u in self.upgrades if u["target"] == "player"]
        gun_upgrades    = [u for u in self.upgrades if u["target"] == "gun"]
        if len(player_upgrades) >= 1 and len(gun_upgrades) >= 2:
            choices = random.sample(player_upgrades, 1) + random.sample(gun_upgrades, 2)
        else:
            choices = random.sample(self.upgrades, min(3, len(self.upgrades)))

        TYPE_STYLE = {
            "damage":     {"color": (1, 0.24, 0.24, 1),  "bg": (0.20, 0.04, 0.04, 0.9), "icon": "gameAsset/icon/damage.png"},
            "max_health": {"color": (0, 1, 0.60, 1),     "bg": (0.03, 0.16, 0.10, 0.9), "icon": "gameAsset/icon/max_health.png"},
            "health":     {"color": (0, 1, 0.60, 1),     "bg": (0.03, 0.16, 0.10, 0.9), "icon": "gameAsset/effects/health.png"},
            "regen":      {"color": (0, 0.85, 0.55, 1),  "bg": (0.02, 0.14, 0.09, 0.9), "icon": "gameAsset/icon/regen.png"},
            "magazine":   {"color": (1, 0.80, 0.15, 1),  "bg": (0.16, 0.12, 0.02, 0.9), "icon": "gameAsset/icon/magazine.png"},
            "reload":     {"color": (0.40, 0.70, 1, 1),  "bg": (0.04, 0.08, 0.18, 0.9), "icon": "gameAsset/icon/reload.png"},
            "range":      {"color": (0.70, 0.50, 1, 1),  "bg": (0.10, 0.06, 0.18, 0.9), "icon": "gameAsset/icon/range.png"},
        }
        for upgrade in choices:
            style = TYPE_STYLE.get(upgrade["type"], {"color": (0.7,0.7,0.7,1), "bg": (0.1,0.1,0.1,0.9), "icon": ""})
            ic, bc, col    = style["icon"], style["bg"], style["color"]
            target_label   = upgrade.get("gun", upgrade.get("target", "")).upper()
            card = BoxLayout(orientation="vertical", spacing=sdp(6),
                             padding=[sdp(14), sdp(12), sdp(14), sdp(12)], size_hint=(1, 1))
            with card.canvas.before:
                KColor(rgba=bc)
                card._bg     = KRR(pos=card.pos, size=card.size, radius=[sdp(13)])
                KColor(rgba=(col[0], col[1], col[2], 0.18))
                card._border = KLine(rounded_rectangle=(card.x, card.y, card.width, card.height, sdp(13)), width=dp(1.3))
            def _update_card_canvas(widget, *_):
                widget._bg.pos  = widget.pos; widget._bg.size = widget.size
                widget._border.rounded_rectangle = (widget.x, widget.y, widget.width, widget.height, sdp(13))
            card.bind(pos=_update_card_canvas, size=_update_card_canvas)

            card.add_widget(Image(source=ic, size_hint=(None, None), size=(sdp(120), sdp(120)),
                                  pos_hint={"center_x": 0.5}, allow_stretch=True, keep_ratio=True))

            for txt, fs, c, ht, bold in [
                (upgrade["name"], 13, (0.88, 0.93, 1, 0.95), 24, True),
                (target_label,    9,  (col[0], col[1], col[2], 0.65), 16, True),
            ]:
                l = Label(text=txt, font_size=ssp(fs), bold=bold, color=c,
                          size_hint_y=None, height=sdp(ht), halign="center", valign="middle")
                l.bind(size=lambda w, s: setattr(w, "text_size", s))
                card.add_widget(l)
            card.add_widget(Widget())

            sel_btn = Button(text="SELECT", font_size=ssp(12), bold=True,
                             size_hint=(1, None), height=sdp(38),
                             background_normal="", background_color=(0, 0, 0, 0),
                             color=(col[0], col[1], col[2], 1))
            with sel_btn.canvas.before:
                KColor(rgba=(col[0]*0.25, col[1]*0.25, col[2]*0.25, 0.6))
                sel_btn._bg  = KRR(pos=sel_btn.pos, size=sel_btn.size, radius=[sdp(9)])
                KColor(rgba=(col[0], col[1], col[2], 0.45))
                sel_btn._bdr = KLine(rounded_rectangle=(sel_btn.x, sel_btn.y, sel_btn.width, sel_btn.height, sdp(9)), width=dp(1.2))
            def _upd_sel(w, *_):
                w._bg.pos  = w.pos; w._bg.size = w.size
                w._bdr.rounded_rectangle = (w.x, w.y, w.width, w.height, sdp(9))
            sel_btn.bind(pos=_upd_sel, size=_upd_sel)
            def onclick(instance, up=upgrade):
                self.apply_upgrade(up)
                self.ui_layer.remove_widget(self.upgrade_panel)
                self.gameState = "playing"
            sel_btn.bind(on_press=onclick)
            card.add_widget(sel_btn)
            box.add_widget(card)

        if self.upgrade_panel.parent is None:
            self.ui_layer.add_widget(self.upgrade_panel)

    def reset(self, dt):
        self.player.gun.switch = True

    def changeWeapon(self, weapon):
        if not self.player.gun.switch:
            return
        if self.player.gun.reloading:
            return
        if self.player.gun.current == weapon:
            return
        self.player.gun.switch  = False
        self.player.gun.current = weapon
        self.ui_layer.update()
        Clock.schedule_once(self.reset, self.player.gun.cooldown)

    def apply_upgrade(self, upgrade):
        self.play_click2()
        type_   = upgrade["type"]
        value   = upgrade["value"]
        target  = upgrade["target"]
        upgrade["count"] += 1
        if type_ == "max_health":
            self.player.max_health += value
            self.player.healthBar.max_health += value
            self.player.health = min(self.player.health + value, self.player.max_health)
        elif target == "gun":
            gun = upgrade["gun"]
            self.player.guns[gun][type_] += value
            if type_ == "reload":
                self.player.guns[gun]["reload"] = max(0.3, self.player.guns[gun]["reload"])
            self.ui_layer.update()
        elif target == "player" and type_ != "health":
            if hasattr(self.player, type_):
                setattr(self.player, type_, getattr(self.player, type_) + value)
        elif type_ == "health":
            self.player.health = min(self.player.max_health, self.player.health + value)

    def apply_powerUp(self, power):
        self.gs.collectable.stop()
        self.gs.collectable.play()
        if power.type == "health":
            self.player.health = min(self.player.health + 10, self.player.max_health)
        elif power.type == "sheild":
            self.player.sheild = True
            Clock.schedule_once(lambda dt: setattr(self.player, "sheild", False), 3)
        elif power.type == "freeze":
            self.player.freeze = True
            self.player.freeze_multiplier = 0.3
            Clock.schedule_once(lambda dt: setattr(self.player, "freeze_multiplier", 1), 4)
            Clock.schedule_once(lambda dt: setattr(self.player, "freeze", False), 4)
        elif power.type == "damage_booster":
            self.player.damage_booster = True
            self.player.damage_multiplier = 1.5
            Clock.schedule_once(lambda dt: setattr(self.player, "damage_multiplier", 1), 5)
            Clock.schedule_once(lambda dt: setattr(self.player, "damage_booster", False), 5)
        elif power.type == "nuke":
            nukeEffect = Effect(frame=self.player.nuke_effect, pos=(power.x - sdp(250), power.y - sdp(180)))
            nukeEffect.size = (sdp(500), sdp(500))
            self.player.nuked = True
            Clock.schedule_once(lambda dt: setattr(self.player, "nuked", False), 3)
            self.game_layer.add_widget(nukeEffect)
            for enemy in self.enemies[:]:
                enemy.health -= 50
                if enemy.health <= 0:
                    enemy.health = 0
                    if enemy not in self.remove_enemy:
                        self.remove_enemy.append(enemy)

    def spawnPowerUp(self, dt):
        if self.gameState != "playing":
            return
        num    = random.randint(1, 5)
        powerUp = PowerUp()
        powerUp.type    = self.powerUp_type[num]["type"]
        powerUp.texture = powerUp.orb[powerUp.type]
        sz = self.powerUp_type[num]["size"]
        powerUp.size = (sz, sz)
        for _ in range(20):
            rand_x = random.uniform(self.player.x - self.player.entity_spawn_radius,
                                    self.player.x + self.player.entity_spawn_radius)
            rand_y = random.uniform(self.player.y - self.player.entity_spawn_radius,
                                    self.player.y + self.player.entity_spawn_radius)
            rand_x = max(self.min_world_x, min(rand_x, self.max_world_x - powerUp.width))
            rand_y = max(self.min_world_y, min(rand_y, self.max_world_y - powerUp.height))
            if not self.rect_blocked(rand_x, rand_y, powerUp.width, powerUp.height):
                powerUp.pos = (rand_x, rand_y)
                break
        else:
            return
        self.game_layer.add_widget(powerUp)
        self.powerUps.append(powerUp)
        Clock.schedule_once(lambda dt: self.despawnPowerUp(powerUp), 10)

    def despawnPowerUp(self, powerUp):
        if powerUp.parent:
            self.game_layer.remove_widget(powerUp)
            self.powerUps.remove(powerUp)

    def spawnAtttck(self, dt):
        if self.player.gun.reloading:
            return
        if self.player.guns[self.player.gun.current]["ammo"] <= 0:
            return
        self.player.guns[self.player.gun.current]["ammo"] -= 1
        self.gs.gun_sound[self.player.gun.current]["shoot"].stop()
        self.gs.gun_sound[self.player.gun.current]["shoot"].play()
        self.ui_layer.update()
        dx, dy    = self.AttackJoystick.vector
        if dx == 0 and dy == 0:
            dx, dy = 0, 1
        direction = (dx, dy)
        self.player.update_direction(dx, dy)
        self.player.set_state("attack_" + self.player.facing)
        attack = Attack(direction=direction)
        attack.damage   = self.player.guns[self.player.gun.current]["damage"]
        attack.center   = self.player.gun.center
        attack.start_x  = attack.center_x
        attack.start_y  = attack.center_y
        attack.texture  = attack.player
        self.spawn_effect_gun_shoot(self.player, attack)
        self.game_layer.add_widget(attack)
        self.attacks.append(attack)
        if self.player.gun.current == "shotgun":
            attack2 = Attack(direction=(dx + 0.45, dy))
            attack2.damage  = self.player.guns[self.player.gun.current]["damage"]
            attack2.center  = self.player.gun.center
            attack2.start_x = attack2.center_x
            attack2.start_y = attack2.center_y
            attack2.texture = attack2.player
            self.game_layer.add_widget(attack2)
            self.attacks.append(attack2)

    def spawnEnemyAttack(self, enemy, dt):
        dx = self.player.center_x - enemy.center_x
        dy = self.player.center_y - enemy.center_y
        direction = (dx, dy) if (dx, dy) != (0, 0) else (0, 1)
        Enemyattack = Attack(direction=direction)
        Enemyattack.size    = (sdp(30), sdp(30))
        Enemyattack.damage  = enemy.damage
        Enemyattack.center  = enemy.center
        Enemyattack.start_x = Enemyattack.center_x
        Enemyattack.start_y = Enemyattack.center_y
        Enemyattack.range   = enemy.attack_range
        Enemyattack.texture = Enemyattack.enemy
        enemy.projectile_spawned = True
        self.game_layer.add_widget(Enemyattack)
        self.Enemyattacks.append(Enemyattack)

    def wave_data(self):
        self.save_game()
        self.wave_count += 1
        self.show_wave_text(self.wave_count)
        self.enemies_per_wave = 4 + self.wave_count * 2
        self.maxBoss = 1 + self.wave_count // 3

    def load_sheet(self, texture, frame_w, frame_h, cols, rows):
        frames = []
        for row in range(rows):
            for col in range(cols):
                x = col * frame_w
                y = texture.height - (row + 1) * frame_h
                subtexture = texture.get_region(x, y, frame_w, frame_h)
                frames.append(subtexture)
        return frames

    def spawn_effect_enemy_hit(self, entity):
        effect = Effect(frame=self.hit, pos=(entity.center_x - sdp(40), entity.center_y - sdp(40)))
        self.game_layer.add_widget(effect)

    def spawn_effect_gun_shoot(self, entity, attack):
        if   entity.facing == "up":    pos = (attack.start_x - sdp(45), attack.start_y - sdp(5))
        elif entity.facing == "down":  pos = (attack.start_x - sdp(40), attack.start_y - sdp(75))
        elif entity.facing == "left":  pos = (attack.start_x - sdp(85), attack.start_y - sdp(30))
        elif entity.facing == "right": pos = (attack.start_x - sdp(20), attack.start_y - sdp(40))
        else:                          pos = (attack.start_x - sdp(40), attack.start_y - sdp(40))
        effect = Effect(frame=entity.shoot_effect[entity.facing], pos=pos)
        self.game_layer.add_widget(effect)

    def spawnEnemy(self, dt):
        if self.gameState != "playing":
            return
        if self.counter == 0 and len(self.enemies) == 0:
            self.wave_data()
        self.counter += 1
        if self.counter == self.enemies_per_wave and self.bossWave == False:
            self.bossWave  = True
            self.bossAlive = self.maxBoss
            for i in range(self.maxBoss):
                self.enemy = self.spawnBoss()
        if self.counter < self.enemies_per_wave:
            enemy = Enemy()
            enemy.role = "melee"
            enemy.boss = False
            enemy.type = {
                1: {"size": sdp(180), "health": 75,  "speed": 7, "damage": 8},
                2: {"size": sdp(180), "health": 125, "speed": 6, "damage": 18},
            }
            num  = random.randint(1, 2)
            snum = random.randint(0, 3)
            enemy.attackDelay = max(1.0, 2.0 - self.wave_count * 0.1)
            sz = enemy.type[num]["size"]
            enemy.size    = (sz, sz)
            enemy.health  = enemy.type[num]["health"] + self.wave_count * 25
            enemy.speed   = enemy.type[num]["speed"]
            enemy.damage  = enemy.type[num]["damage"] + self.wave_count * 2

            if self.wave_count > 0 and random.random() < 0.40:
                enemy.attackDelay = max(3.0, 5.0 - self.wave_count * 0.2)
                enemy.role        = "ranged"
                enemy.minDist     = sdp(300)
                enemy.maxDist     = sdp(420)

            if self.wave_count > 0 and random.random() < 0.35:
                sz = sdp(100)
                enemy.size    = (sz, sz)
                enemy.attackDelay = max(2.0, 3.0 - self.wave_count * 0.2)
                enemy.role        = "poisoner"
                enemy.poison_time = min(5 + self.wave_count * 0.3, 10)
                enemy.poison_damage = 5
                enemy.hitbox_w          = sdp(55); enemy.hitbox_h          = sdp(45)
                enemy.hitbox_offset_x   = sdp(30); enemy.hitbox_offset_y   = sdp(15)
                enemy.damage_hitbox_w   = sdp(80); enemy.damage_hitbox_h   = sdp(60)
                enemy.damage_hitbox_offset_x = sdp(20); enemy.damage_hitbox_offset_y = sdp(20)

            if self.wave_count >= 2 and random.random() < min(0.25 + self.wave_count * 0.015, 0.40):
                sz = sdp(220)
                enemy.size    = (sz, sz)
                enemy.role    = "elite"
                enemy.health += 50
                enemy.damage *= 1.5
                enemy.speed   = 7.5
                enemy.hitbox_w          = sdp(60); enemy.hitbox_h          = sdp(30)
                enemy.hitbox_offset_x   = sdp(120); enemy.hitbox_offset_y  = sdp(80)
                enemy.damage_hitbox_w   = sdp(100); enemy.damage_hitbox_h  = sdp(120)
                enemy.damage_hitbox_offset_x = sdp(60); enemy.damage_hitbox_offset_y = sdp(60)

            enemy.pos         = self.spawn_point[snum]
            enemy.max_health  = enemy.health
            enemy.healthBar   = HealthBar(max_health=enemy.max_health, health=enemy.health)
            self.game_layer.add_widget(enemy.healthBar)
            self.game_layer.add_widget(enemy)
            self.enemies.append(enemy)

    def apply_poison(self, enemy, dt):
        if not self.player.poisoned or self.gameState != "playing":
            return
        self.player.health -= enemy.poison_damage

    def stop_poison(self, dt):
        self.player.poisoned = False
        if hasattr(self.player, "poison_event"):
            self.player.poison_event.cancel()

    def poison(self, enemy):
        if self.player.poisoned or self.player.sheild or self.gameState != "playing":
            return
        self.player.poisoned     = True
        self.player.poison_event = Clock.schedule_interval(lambda dt: self.apply_poison(enemy, dt), 1)
        Clock.schedule_once(self.stop_poison, enemy.poison_time)

    def enemyHit(self, enemy, damage):
        enemy.color = (2, 2, 2, 1)
        dmg = DamageNumber(text=str(damage), pos=(enemy.center_x, enemy.center_y))
        self.game_layer.add_widget(dmg)
        self.spawn_effect_enemy_hit(enemy)
        Clock.schedule_once(lambda dt: self.resetEnemyFlash(enemy, dmg), 0.1)

    def resetEnemyFlash(self, enemy, dmg):
        enemy.color = (1, 1, 1, 1)
        self.game_layer.remove_widget(dmg)

    def enemyDeathAnimation(self, enemy):
        if enemy.health <= 0 and not enemy.death:
            enemy.set_state("death", enemy.role)
            Clock.schedule_once(lambda dt: self.enemyDeath(enemy), 0.7)

    def enemyDeath(self, enemy):
        if enemy.death:
            return
        if enemy.health <= 0:
            enemy.death = True
            if enemy.isAttack:
                enemy.isAttack = False
            self.game_layer.remove_widget(enemy)
            if hasattr(enemy, "healthBar"):
                self.game_layer.remove_widget(enemy.healthBar)
            self.enemies.remove(enemy)
            if not self.bossWave:
                self.player.score += 1
            if self.bossWave and enemy.boss:
                self.bossAlive -= 1
                self.player.score += 10
            play_dialouge = enemy.boss or random.random() < 0.3
            if play_dialouge:
                dia = random.choice(self.gs.enemy_clear)
                for s in self.gs.enemy_clear:
                    if s and s.state == "play":
                        s.stop()
                dia.play()
            if self.counter >= self.enemies_per_wave and self.bossAlive == 0 and len(self.enemies) == 0:
                self.bossWave = False
                self.counter  = 0

    def enemyAttack(self, enemy, dt):
        enemy.set_state("attack_" + enemy.facing, enemy.role)
        if enemy.frame_index == 7 and enemy.role in ("melee", "elite"):
            enemy.attack_timer = 0
            enemy.isAttack     = False
            if not self.player.sheild:
                self.player.health -= enemy.damage
        if enemy.frame_index == 7 and enemy.role == "boss":
            enemy.attack_timer = 0
            enemy.isAttack     = False
            if not self.player.sheild:
                if random.random() < 0.25:
                    dia = random.choice(self.gs.boss)
                    for s in self.gs.boss:
                        if s and s.state == "play": s.stop()
                    dia.play()
                if random.random() < 0.75:
                    self.enable_darkness()
                    Clock.schedule_once(lambda dt: self.disable_darkness(), 7)
                self.player.health -= enemy.damage
        if enemy.frame_index == 16 and enemy.role == "poisoner":
            enemy.attack_timer = 0
            enemy.isAttack     = False
            if not self.player.sheild:
                self.player.health -= enemy.damage
                self.poison(enemy)

    def spawnBoss(self):
        if Window.width <= 0 or Window.height <= 0:
            return
        enemy = Enemy()
        enemy.role = "boss"
        enemy.boss = True
        enemy.type = {
            1: {"name": "boss", "size": sdp(300), "health": 500,  "speed": 7, "damage": 25},
            2: {"name": "boss", "size": sdp(320), "health": 750,  "speed": 6, "damage": 30},
        }
        num  = random.randint(1, 2)
        snum = random.randint(0, 3)
        sz            = enemy.type[num]["size"]
        enemy.size    = (sz, sz)
        self.bossWave = True
        enemy.health  = enemy.type[num]["health"] + self.wave_count * 150
        enemy.max_health = enemy.health
        enemy.healthBar  = HealthBar(max_health=enemy.max_health, health=enemy.health)
        enemy.speed   = enemy.type[num]["speed"]
        enemy.damage  = enemy.type[num]["damage"] + self.wave_count * 6
        enemy.attackDelay = max(1.5, 2.5 - self.wave_count * 0.2)
        enemy.hitbox_w          = sdp(60);  enemy.hitbox_h          = sdp(30)
        enemy.hitbox_offset_x   = sdp(120); enemy.hitbox_offset_y   = sdp(80)
        enemy.damage_hitbox_w   = sdp(100); enemy.damage_hitbox_h   = sdp(120)
        enemy.damage_hitbox_offset_x = sdp(100); enemy.damage_hitbox_offset_y = sdp(80)
        enemy.pos = self.spawn_point[snum]
        self.game_layer.add_widget(enemy)
        self.game_layer.add_widget(enemy.healthBar)
        self.enemies.append(enemy)

    def show_wave_text(self, wave):
        self.wave_label = Label(
            text=f"[b]WAVE {wave}[/b]", markup=True,
            font_size=ssp(80), color=(0.92, 0.82, 0.58, 0),
            size_hint=(1, 1), pos_hint={"center_x": 0.5, "center_y": 0.5}
        )
        self.ui_layer.add_widget(self.wave_label)
        anim = (Animation(color=(0.92, 0.82, 0.58, 1), duration=0.4) +
                Animation(duration=1.2) +
                Animation(color=(0.92, 0.82, 0.58, 0), duration=0.4))
        anim.start(self.wave_label)
        Clock.schedule_once(lambda dt: self.ui_layer.remove_widget(self.wave_label), 2)
        Clock.schedule_once(lambda dt: self.show_menu(), 3)

    def show_status(self):
        bar = self.player.healthBar
        if   self.player.poisoned:       bar.status_text = "Poisoned";        bar.status_color = [0.43, 0.81, 0.43, 1]
        elif self.player.nuked:          bar.status_text = "antivirus spreaded"; bar.status_color = [0.30, 0.70, 1.0, 1]
        elif self.player.sheild:         bar.status_text = "Shielded";         bar.status_color = [0.30, 0.70, 1.0, 1]
        elif self.player.freeze:         bar.status_text = "Enemies Frozen";   bar.status_color = [0.55, 0.90, 1.0, 1]
        elif self.player.damage_booster: bar.status_text = "Damage Boosted";   bar.status_color = [1.0,  0.55, 0.10, 1]
        else:                            bar.status_text = "No status effect"; bar.status_color = [1, 1, 1, 0.35]

    def update(self, dt):
        if self.gameState != "playing":
            return
        self.ui_layer.ids.wave_label.text  = str(self.wave_count)
        self.ui_layer.ids.score_label.text = str(self.player.score)
        self.update_joystick_from_keyboard()
        self.update_camera()
        self.show_status()

        self.player.hitbox_debug.rectangle = (
            self.player.x + self.player.hitbox_offset_x, self.player.y + self.player.hitbox_offset_y,
            self.player.hitbox_w, self.player.hitbox_h)
        self.player.damage_hitbox_debug.rectangle = (
            self.player.x + self.player.damage_hitbox_offset_x, self.player.y + self.player.damage_hitbox_offset_y,
            self.player.damage_hitbox_w, self.player.damage_hitbox_h)

        if self.player.guns[self.player.gun.current]["ammo"] <= 0 and not self.player.gun.reloading:
            if hasattr(self.player, "attack"):
                self.player.attack.cancel()
                del self.player.attack
            if hasattr(self, "AttackJoystick"):
                self.AttackJoystick.shooting = False
            self.player.gun.startReload()

        vx, vy = self.joystick.vector
        if not self.AttackJoystick.shooting:
            self.player.update_direction(vx, vy)
            if vx == 0 and vy == 0:
                self.player.set_state("idle_" + self.player.facing)
            else:
                self.player.set_state("run_" + self.player.facing)

        mov_x = self.player.x + vx * self.player.speed
        mov_y = self.player.y + vy * self.player.speed
        if not self.rect_blocked(mov_x + self.player.hitbox_offset_x, self.player.y + self.player.hitbox_offset_y, self.player.hitbox_w, self.player.hitbox_h):
            self.player.x = mov_x
        if not self.rect_blocked(self.player.x + self.player.hitbox_offset_x, mov_y + self.player.hitbox_offset_y, self.player.hitbox_w, self.player.hitbox_h):
            self.player.y = mov_y
        self.player.x = max(self.min_world_x, min(self.player.x, self.max_world_x - self.player.width))
        self.player.y = max(self.min_world_y, min(self.player.y, self.max_world_y - self.player.height))
        self.player.gun.update(vector=self.AttackJoystick.vector)
        self.player.healthBar.health = self.player.health

        if self.player.health <= 0:
            if not self.game_over_shown:
                self.game_over_shown = True
                self.gameState = "gameover"
                if self.gs.game_over.state != "play":
                    self.gs.game_over.play()
                if self.gs.game_music.state == "play":
                    self.gs.game_music.stop()
                with open("save.dat", "w") as f:
                    json.dump({}, f)
                self.save_stats()
                self.show_game_over()
            return

        for powers in self.powerUps:
            if self.rect_overlap(self.player.x, self.player.y,
                                 self.player.damage_hitbox_w + self.player.damage_hitbox_offset_x,
                                 self.player.damage_hitbox_h + self.player.damage_hitbox_offset_y,
                                 powers.x, powers.y, powers.width, powers.height):
                self.remove_powerup.append(powers)
                self.apply_powerUp(powers)

        for attack in self.attacks:
            attack.x += attack.vx * attack.speed
            attack.y += attack.vy * attack.speed
            attack.rdx = attack.center_x - attack.start_x
            attack.rdy = attack.center_y - attack.start_y
            distance   = math.hypot(attack.rdx, attack.rdy)
            if attack.y > self.world_h or distance > self.player.guns[self.player.gun.current]["range"]:
                self.remove_attack.append(attack)
            if self.rect_blocked(attack.x, attack.y, attack.attack_w, attack.attack_h):
                self.remove_attack.append(attack)
            for enemy in self.enemies:
                if self.rect_overlap(attack.x, attack.y, attack.attack_w, attack.attack_h,
                                     enemy.x + enemy.damage_hitbox_offset_x, enemy.y + enemy.damage_hitbox_offset_y,
                                     enemy.damage_hitbox_w, enemy.damage_hitbox_h):
                    enemy.health -= attack.damage * self.player.damage_multiplier
                    self.enemyHit(enemy, attack.damage * self.player.damage_multiplier)
                    self.remove_attack.append(attack)
                    if enemy.health <= 0:
                        enemy.health = 0
                        if enemy not in self.remove_enemy:
                            self.remove_enemy.append(enemy)
                    break

        for attack in self.Enemyattacks:
            attack.x += attack.vx * attack.speed
            attack.y += attack.vy * attack.speed
            attack.rdx = attack.center_x - attack.start_x
            attack.rdy = attack.center_y - attack.start_y
            distance   = math.hypot(attack.rdx, attack.rdy)
            if distance > attack.range:
                self.remove_enemyAttack.append(attack)
                continue
            if self.rect_blocked(attack.x, attack.y, attack.attack_w, attack.attack_h):
                self.remove_enemyAttack.append(attack)
            if self.rect_overlap(attack.x, attack.y, attack.attack_w, attack.attack_h,
                                 self.player.x + self.player.damage_hitbox_offset_x,
                                 self.player.y + self.player.damage_hitbox_offset_y,
                                 self.player.damage_hitbox_w, self.player.damage_hitbox_h):
                self.player.health -= attack.damage
                self.remove_enemyAttack.append(attack)

        for enemy in self.enemies:
            if enemy.state == "death":
                continue
            enemy.hitbox_debug.rectangle = (
                enemy.x + enemy.hitbox_offset_x, enemy.y + enemy.hitbox_offset_y,
                enemy.hitbox_w, enemy.hitbox_h)
            enemy.damage_hitbox_debug.rectangle = (
                enemy.x + enemy.damage_hitbox_offset_x, enemy.y + enemy.damage_hitbox_offset_y,
                enemy.damage_hitbox_w, enemy.damage_hitbox_h)

            px, py = self.player.center
            ex, ey = enemy.center
            dx = px - ex; dy = py - ey
            if not enemy.isAttack:
                enemy.update_direction(dx, dy)
                enemy.set_state("run_" + enemy.facing, enemy.role)
            enemy_distance = math.sqrt(dx**2 + dy**2)
            if enemy_distance > 0:
                enemy_x = dx / (enemy_distance + 0.0001)
                enemy_y = dy / (enemy_distance + 0.0001)
                effective_speed = enemy.speed * self.player.freeze_multiplier
                if enemy.role != "ranged":
                    if not self.rect_overlap(
                        enemy.x + enemy.damage_hitbox_offset_x, enemy.y + enemy.damage_hitbox_offset_y,
                        enemy.damage_hitbox_w, enemy.damage_hitbox_h,
                        self.player.x + self.player.damage_hitbox_offset_x, self.player.y + self.player.damage_hitbox_offset_y,
                        self.player.damage_hitbox_w, self.player.damage_hitbox_h
                    ):
                        step = effective_speed
                        ene_mov_x = enemy.x + enemy_x * step
                        ene_mov_y = enemy.y + enemy_y * step
                        if not self.enemy_colloison(enemy, ene_mov_x, enemy.y):
                            enemy.x = ene_mov_x
                        if not self.enemy_colloison(enemy, enemy.x, ene_mov_y):
                            enemy.y = ene_mov_y
                if enemy.role == "ranged":
                    enemy.attack_timer += dt
                    if enemy.attack_timer > enemy.attackDelay:
                        enemy.isAttack = True
                        enemy.set_state("attack_" + enemy.facing, enemy.role)
                        enemy.projectile_spawned = False
                        if enemy.frame_index == 7 and not enemy.projectile_spawned:
                            self.spawnEnemyAttack(enemy, dt)
                            enemy.attack_timer = 0
                            enemy.isAttack     = False
                    if enemy_distance < enemy.minDist:
                        ene_mov_x = enemy.x - enemy_x * enemy.speed
                        ene_mov_y = enemy.y - enemy_y * enemy.speed
                        if not self.enemy_colloison(enemy, ene_mov_x, enemy.y): enemy.x = ene_mov_x
                        if not self.enemy_colloison(enemy, enemy.x, ene_mov_y): enemy.y = ene_mov_y
                    if enemy_distance > enemy.maxDist:
                        ene_mov_x = enemy.x + enemy_x * enemy.speed
                        ene_mov_y = enemy.y + enemy_y * enemy.speed
                        if not self.enemy_colloison(enemy, ene_mov_x, enemy.y): enemy.x = ene_mov_x
                        if not self.enemy_colloison(enemy, enemy.x, ene_mov_y): enemy.y = ene_mov_y

            if hasattr(enemy, "healthBar"):
                enemy.health = max(0, enemy.health)
                enemy.healthBar.health = enemy.health
                enemy.healthBar.pos = (
                    enemy.x + enemy.damage_hitbox_offset_x + enemy.damage_hitbox_w / 2 - enemy.healthBar.width / 2,
                    enemy.y + enemy.damage_hitbox_offset_y + enemy.damage_hitbox_h + sdp(15)
                )

            if self.rect_overlap(enemy.x + enemy.damage_hitbox_offset_x, enemy.y + enemy.damage_hitbox_offset_y,
                                 enemy.damage_hitbox_w, enemy.damage_hitbox_h,
                                 self.player.x + self.player.damage_hitbox_offset_x,
                                 self.player.y + self.player.damage_hitbox_offset_y,
                                 self.player.damage_hitbox_w, self.player.damage_hitbox_h):
                if enemy.role in ("melee", "elite", "boss", "poisoner"):
                    enemy.attack_timer += dt
                    enemy.isAttack = True
                    if enemy.attack_timer > enemy.attackDelay:
                        self.enemyAttack(enemy, dt)
            else:
                if enemy.role in ("melee", "elite", "boss", "poisoner"):
                    enemy.attack_timer = 0
                if enemy.role in ("melee", "elite", "boss", "poisoner") and enemy.isAttack:
                    enemy.isAttack = False

        if self.remove_enemy:
            for entity in self.remove_enemy:
                if entity in self.enemies:
                    self.enemyDeathAnimation(entity)
            self.remove_enemy.clear()
        if self.remove_attack:
            for entity in self.remove_attack:
                if entity in self.attacks:
                    self.attacks.remove(entity)
                if entity.parent:
                    self.game_layer.remove_widget(entity)
            self.remove_attack.clear()
        if self.remove_powerup:
            for entity in self.remove_powerup:
                self.powerUps.remove(entity)
                self.game_layer.remove_widget(entity)
            self.remove_powerup.clear()
        if self.remove_enemyAttack:
            for entity in self.remove_enemyAttack:
                self.Enemyattacks.remove(entity)
                self.game_layer.remove_widget(entity)
            self.remove_enemyAttack.clear()


# ── JOYSTICK ──────────────────────────────────────────────────────────────────
class JoyStick(Widget):
    knob_x = NumericProperty(0)
    knob_y = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # radius scales with widget size (size is already sdp(150))
        self.radius       = self.width / 2 * 0.8
        self.radius_knob  = self.width * 0.17
        self.active       = False
        self.vector       = (0, 0)
        self.touch        = None
        self.bind(center=self._reset_knob, size=self._on_size)

    def _on_size(self, *args):
        self.radius      = self.width / 2 * 0.8
        self.radius_knob = self.width * 0.17

    def _reset_knob(self, *args):
        self.knob_x = self.center_x
        self.knob_y = self.center_y

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        self.touch  = touch
        self.active = True
        return True

    def on_touch_move(self, touch):
        if touch != self.touch:
            return False
        if self.parent.game.gameState != "playing":
            return False
        dx = touch.x - self.center_x
        dy = touch.y - self.center_y
        distance = math.sqrt(dx**2 + dy**2)
        if distance > self.radius:
            dx = dx / distance * self.radius
            dy = dy / distance * self.radius
        self.vector = (dx / self.radius, dy / self.radius)
        self.knob_x = self.center_x + dx
        self.knob_y = self.center_y + dy
        return True

    def on_touch_up(self, touch):
        if touch != self.touch:
            return False
        self.touch  = None
        self.active = False
        self.vector = (0, 0)
        self.knob_x = self.center_x
        self.knob_y = self.center_y
        return True


class AttackJoystick(Widget):
    knob_x = NumericProperty(0)
    knob_y = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.radius      = self.width / 2 * 0.8
        self.knob_radius = self.width * 0.17
        self.vector      = (0, 0)
        self.shooting    = False
        self.touch       = None
        self.bind(center=self._reset_knob, size=self._on_size)

    def _on_size(self, *args):
        self.radius      = self.width / 2 * 0.8
        self.knob_radius = self.width * 0.17

    def _reset_knob(self, *args):
        self.knob_x = self.center_x
        self.knob_y = self.center_y

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        self.touch = touch
        return True

    def on_touch_move(self, touch):
        if touch != self.touch:
            return False
        if self.parent.game.gameState != "playing":
            return False
        if not self.parent.game.player.gun.reloading:
            self.parent.game.player.speed = 5.5
        dx = touch.x - self.center_x
        dy = touch.y - self.center_y
        distance = math.sqrt(dx**2 + dy**2)
        if distance > self.radius:
            dx = dx / distance * self.radius
            dy = dy / distance * self.radius
        self.vector = (dx / self.radius, dy / self.radius)
        self.knob_x = self.center_x + dx
        self.knob_y = self.center_y + dy
        if not self.shooting:
            self.shooting = True
            self.parent.game.player.attack = Clock.schedule_interval(
                self.parent.game.spawnAtttck,
                self.parent.game.player.guns[self.parent.game.player.gun.current]["rate"]
            )
        return True

    def on_touch_up(self, touch):
        if touch != self.touch:
            return False
        self.touch   = None
        self.vector  = (0, 0)
        self.knob_x  = self.center_x
        self.knob_y  = self.center_y
        if not self.parent.game.player.gun.reloading:
            self.parent.game.player.speed = 8
        if self.shooting:
            self.parent.game.player.attack.cancel()
            del self.parent.game.player.attack
            self.shooting = False
        return True


class DamageNumber(Label):
    pass


class Gun(Widget):
    angle = NumericProperty(0)

    def __init__(self, owner, **kwargs):
        super().__init__(**kwargs)
        self.type     = "assualt"
        self.current  = "assualt"
        self.owner    = owner
        self.opacity  = 0
        self.size     = (sdp(34), sdp(12))
        self.offset   = (sdp(20), 0)
        self.angle    = 0
        self.switch   = True
        self.cooldown = 5
        self.reloading = False
        self.gunData = {
            "assualt": {"damage": 25, "range": 800,  "magazine": 30, "ammo": 30, "rate": 0.5,  "reload": 1.5},
            "sniper":  {"damage": 50, "range": 1400, "magazine":  7, "ammo":  7, "rate": 1.2,  "reload": 2.5},
            "shotgun": {"damage": 30, "range": 350,  "magazine":  2, "ammo":  2, "rate": 0.9,  "reload": 2.0},
            "machine": {"damage": 20, "range": 700,  "magazine": 25, "ammo": 25, "rate": 0.15, "reload": 2.2},
        }
        self.assault_upgrade = [
            {"target":"gun","gun":"assualt","name":"Assault Damage++",          "type":"damage",  "value":5,     "min_wave":1,"max_stack":4,"count":0},
            {"target":"gun","gun":"assualt","name":"Assault Extended Magazine",  "type":"magazine","value":5,     "min_wave":2,"max_stack":3,"count":0},
            {"target":"gun","gun":"assualt","name":"Assault Fast Reload",        "type":"reload",  "value":-0.2,  "min_wave":2,"max_stack":3,"count":0},
            {"target":"gun","gun":"assualt","name":"Assault Extended Range",     "type":"range",   "value":80,    "min_wave":2,"max_stack":3,"count":0},
            {"target":"gun","gun":"shotgun","name":"Shotgun Damage++",           "type":"damage",  "value":10,    "min_wave":3,"max_stack":4,"count":0},
            {"target":"gun","gun":"shotgun","name":"Shotgun Extended Shell",     "type":"magazine","value":1,     "min_wave":3,"max_stack":3,"count":0},
            {"target":"gun","gun":"shotgun","name":"Shotgun Quick Pump",         "type":"reload",  "value":-0.2,  "min_wave":4,"max_stack":3,"count":0},
            {"target":"gun","gun":"shotgun","name":"Shotgun Extended Range",     "type":"range",   "value":50,    "min_wave":4,"max_stack":2,"count":0},
            {"target":"gun","gun":"sniper", "name":"Sniper Extended Magazine",   "type":"magazine","value":2,     "min_wave":7,"max_stack":3,"count":0},
            {"target":"gun","gun":"sniper", "name":"Sniper Fast Reload",         "type":"reload",  "value":-0.25, "min_wave":8,"max_stack":3,"count":0},
            {"target":"gun","gun":"sniper", "name":"Sniper Extended Range",      "type":"range",   "value":150,   "min_wave":8,"max_stack":2,"count":0},
            {"target":"gun","gun":"sniper", "name":"Sniper Damage++",            "type":"damage",  "value":15,    "min_wave":7,"max_stack":4,"count":0},
            {"target":"gun","gun":"machine","name":"Machine Damage++",           "type":"damage",  "value":4,     "min_wave":5,"max_stack":4,"count":0},
            {"target":"gun","gun":"machine","name":"Machine Extended Magazine",  "type":"magazine","value":8,     "min_wave":5,"max_stack":3,"count":0},
            {"target":"gun","gun":"machine","name":"Machine Fast Reload",        "type":"reload",  "value":-0.18, "min_wave":6,"max_stack":3,"count":0},
            {"target":"gun","gun":"machine","name":"Machine Extended Range",     "type":"range",   "value":60,    "min_wave":6,"max_stack":2,"count":0},
        ]

    def reload(self, dt):
        self.reloading = False
        game = self.parent.game
        if game.AttackJoystick.shooting:
            game.player.speed = 5.5
        else:
            game.player.speed = 8
        game.player.guns[game.player.gun.current]["ammo"] = game.player.guns[game.player.gun.current]["magazine"]
        game.ui_layer.update()

    def startReload(self):
        if self.reloading:
            return
        self.reloading = True
        game = self.parent.game
        game.player.speed = 4
        Clock.schedule_once(game.player.gun.reload,
                            game.player.guns[game.player.gun.current]["reload"])
        game.gs.gun_sound[game.player.gun.current]["reload"].stop()
        game.gs.gun_sound[game.player.gun.current]["reload"].play()

    def update(self, vector):
        self.center = self.owner.center
        dx, dy = vector
        length = math.sqrt(dx**2 + dy**2)
        if dx == 0 and dy == 0:
            return
        self.angle = math.degrees(math.atan2(dy, dx))
        dx /= length; dy /= length
        self.center_x = self.owner.center_x + dx * self.offset[0]
        self.center_y = self.owner.center_y + dy * self.offset[1]


class PowerUp(Widget):
    color   = ListProperty([1, 1, 1, 1])
    symbol  = StringProperty("")
    texture = ObjectProperty(None)
    orb = {
        "health":         CoreImage("gameAsset/effects/health.png").texture,
        "damage_booster": CoreImage("gameAsset/effects/damage.png").texture,
        "sheild":         CoreImage("gameAsset/effects/sheild.png").texture,
        "freeze":         CoreImage("gameAsset/effects/time.png").texture,
        "nuke":           CoreImage("gameAsset/effects/nuke4.png").texture,
    }


class Effect(Widget):
    texture = ObjectProperty(None)

    def __init__(self, frame, **kwargs):
        super().__init__(**kwargs)
        self.frames      = frame
        self.frame_index = 0
        self.texture     = self.frames[self.frame_index]
        # ── Effect widget inherits size from caller; scale it ──────────────
        if "size" not in kwargs:
            self.size = (sdp(100), sdp(100))
        Clock.schedule_interval(self.animate, 0.05)

    def animate(self, dt):
        self.frame_index += 1
        if self.frame_index >= len(self.frames):
            if self.parent:
                self.parent.remove_widget(self)
            return False
        self.texture = self.frames[self.frame_index]


class Player(Widget):
    texture = ObjectProperty(None)
    angle   = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # ── Player widget size ────────────────────────────────────────────
        self.size = (sdp(100), sdp(100))

        self.shoot_effect = {
            "up":    self.load_sheet(CoreImage("gameAsset/effects/Sprite_Fire_Shots_Shot_A_000-0.png").texture,       256, 256, 4, 1),
            "right": self.load_sheet(CoreImage("gameAsset/effects/Sprite_Fire_Shots_Shot_A_000-0_right.png").texture, 256, 256, 1, 4),
            "left":  self.load_sheet(CoreImage("gameAsset/effects/Sprite_Fire_Shots_Shot_A_000-0_left.png").texture,  256, 256, 1, 4),
            "down":  self.load_sheet(CoreImage("gameAsset/effects/Sprite_Fire_Shots_Shot_A_000-0_down.png").texture,  256, 256, 4, 1),
        }
        self.nuke_effect = self.load_sheet(CoreImage("gameAsset/effects/green_smoke.png").texture, 800, 800, 10, 1)

        # ── Hitboxes — scaled ─────────────────────────────────────────────
        self.hitbox_w          = sdp(48)
        self.hitbox_h          = sdp(32)
        self.hitbox_offset_x   = (self.width  - self.hitbox_w)  / 2
        self.hitbox_offset_y   = sdp(20)
        self.damage_hitbox_w   = sdp(70)
        self.damage_hitbox_h   = sdp(80)
        self.damage_hitbox_offset_x = (self.width  - self.damage_hitbox_w) / 2
        self.damage_hitbox_offset_y = sdp(8)

        with self.canvas.after:
            Color(0, 0, 0, 0)
            self.damage_hitbox_debug = Line(rectangle=(self.x, self.y, self.damage_hitbox_w, self.damage_hitbox_h), width=1.5)
        with self.canvas.after:
            Color(0, 0, 0, 0)
            self.hitbox_debug = Line(rectangle=(self.x, self.y, self.hitbox_w, self.hitbox_h), width=1.5)

        self.entity_spawn_radius = sdp(500)
        self.damage              = 200
        self.health              = 100
        self.max_health          = 100
        self.sheild              = False
        self.freeze              = False
        self.damage_booster      = False
        self.poisoned            = False
        self.nuked               = False
        self.damage_multiplier   = 1
        self.score               = 0
        self.freeze_multiplier   = 1
        self.regen               = 0
        self.state               = "idle_up"
        self.facing              = "up"
        self.frame_index         = 0

        frame_w = 256; frame_h = 256; cols = 4; rows = 4
        self.animations = {
            "death":       self.load_sheet(CoreImage("gameAsset/Characters/Enemy/2/Death/Death_Body_000.png").texture, frame_w, frame_h, 6, rows),
            "idle_up":     self.load_sheet(CoreImage("gameAsset/idle/SW_spritesheet.png").texture,       frame_w, frame_h, cols, rows),
            "run_up":      self.load_sheet(CoreImage("gameAsset/gun_run/SW_spritesheet.png").texture,    256, 256, 3, 5),
            "attack_up":   self.load_sheet(CoreImage("gameAsset/run_shoot/SW_spritesheet.png").texture,  256, 256, 3, 7),
            "idle_down":   self.load_sheet(CoreImage("gameAsset/idle/NE_spritesheet.png").texture,       frame_w, frame_h, cols, rows),
            "run_down":    self.load_sheet(CoreImage("gameAsset/gun_run/NE_spritesheet.png").texture,    256, 256, 3, 5),
            "attack_down": self.load_sheet(CoreImage("gameAsset/run_shoot/NE_spritesheet.png").texture,  256, 256, 3, 7),
            "idle_right":  self.load_sheet(CoreImage("gameAsset/idle/SE_spritesheet.png").texture,       frame_w, frame_h, cols, rows),
            "run_right":   self.load_sheet(CoreImage("gameAsset/gun_run/SE_spritesheet.png").texture,    256, 256, 3, 5),
            "attack_right":self.load_sheet(CoreImage("gameAsset/run_shoot/SE_spritesheet.png").texture,  256, 256, 3, 7),
            "idle_left":   self.load_sheet(CoreImage("gameAsset/idle/NW_spritesheet.png").texture,       frame_w, frame_h, cols, rows),
            "run_left":    self.load_sheet(CoreImage("gameAsset/gun_run/NW_spritesheet.png").texture,    256, 256, 3, 5),
            "attack_left": self.load_sheet(CoreImage("gameAsset/run_shoot/NW_spritesheet.png").texture,  256, 256, 3, 7),
        }
        self.CurrentFrames = self.animations[self.state]
        self.texture       = self.CurrentFrames[0]
        Clock.schedule_interval(self.animate, 0.08)

    def load_sheet(self, texture, frame_w, frame_h, cols, rows):
        frames = []
        for row in range(rows):
            for col in range(cols):
                x = col * frame_w
                y = texture.height - (row + 1) * frame_h
                frames.append(texture.get_region(x, y, frame_w, frame_h))
        return frames

    def animate(self, dt):
        self.frame_index += 1
        if self.frame_index >= len(self.CurrentFrames):
            self.frame_index = 0
        self.texture = self.CurrentFrames[self.frame_index]

    def set_state(self, new_state):
        if self.state == new_state:
            return
        self.state       = new_state
        self.frame_index = 0
        self.CurrentFrames = self.animations[self.state]
        self.texture = self.CurrentFrames[0]

    def update_direction(self, vx, vy):
        if vx == 0 and vy == 0:
            self.set_state("idle_" + self.facing)
            return
        if abs(vx) > abs(vy):
            self.facing = "right" if vx > 0 else "left"
        else:
            self.facing = "up" if vy > 0 else "down"


class Enemy(Widget):
    texture = ObjectProperty(None)
    color   = ListProperty([1, 1, 1, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.death             = False
        self.isAttack          = False
        self.projectile_spawned = False
        self.attack_timer      = 0
        self.attack_range      = sdp(800)
        self.texture           = CoreImage("gameAsset/Characters/S.png").texture

        # ── Default hitboxes (scaled) ────────────────────────────────────
        self.hitbox_w          = sdp(60);  self.hitbox_h          = sdp(30)
        self.hitbox_offset_x   = sdp(60);  self.hitbox_offset_y   = sdp(55)
        self.damage_hitbox_w   = sdp(80);  self.damage_hitbox_h   = sdp(90)
        self.damage_hitbox_offset_x = sdp(50); self.damage_hitbox_offset_y = sdp(45)

        with self.canvas.after:
            Color(0, 0, 0, 0)
            self.damage_hitbox_debug = Line(rectangle=(self.x, self.y, self.damage_hitbox_w, self.damage_hitbox_h), width=1.5)
        with self.canvas.after:
            Color(0, 0, 0, 0)
            self.hitbox_debug = Line(rectangle=(self.x, self.y, self.hitbox_w, self.hitbox_h), width=1.2)

        self.frame_index = 0
        self.state       = "idle_up"
        self.facing      = "up"
        frame_w = 256; frame_h = 256
        self.role = 'melee'

        # (animations dict is identical to original — just loading textures, no size changes needed)
        self.animations = {"melee": {
            "death":        self.load_sheet(CoreImage("gameAsset/Characters/Enemy/3/x256_Spritesheets/Death1/Death1 Body 0.png").texture,   frame_w, frame_h, 6, 5),
            "idle_up":      self.load_sheet(CoreImage("gameAsset/Characters/Enemy/3/x256_Spritesheets/Idle/Idle Body 0.png").texture,        frame_w, frame_h, 4, 5),
            "run_up":       self.load_sheet(CoreImage("gameAsset/Characters/Enemy/3/x256_Spritesheets/Run/Run Body 0.png").texture,          frame_w, frame_h, 4, 5),
            "attack_up":    self.load_sheet(CoreImage("gameAsset/Characters/Enemy/3/x256_Spritesheets/Attack2/Attack2 Body 0.png").texture,  frame_w, frame_h, 4, 5),
            "idle_down":    self.load_sheet(CoreImage("gameAsset/Characters/Enemy/3/x256_Spritesheets/Idle/Idle Body 180.png").texture,      frame_w, frame_h, 4, 5),
            "run_down":     self.load_sheet(CoreImage("gameAsset/Characters/Enemy/3/x256_Spritesheets/Run/Run Body 180.png").texture,        frame_w, frame_h, 4, 5),
            "attack_down":  self.load_sheet(CoreImage("gameAsset/Characters/Enemy/3/x256_Spritesheets/Attack2/Attack2 Body 180.png").texture,frame_w, frame_h, 4, 5),
            "idle_right":   self.load_sheet(CoreImage("gameAsset/Characters/Enemy/3/x256_Spritesheets/Idle/Idle Body 090.png").texture,      frame_w, frame_h, 4, 5),
            "run_right":    self.load_sheet(CoreImage("gameAsset/Characters/Enemy/3/x256_Spritesheets/Run/Run Body 090.png").texture,        frame_w, frame_h, 4, 5),
            "attack_right": self.load_sheet(CoreImage("gameAsset/Characters/Enemy/3/x256_Spritesheets/Attack2/Attack2 Body 090.png").texture,frame_w, frame_h, 4, 5),
            "idle_left":    self.load_sheet(CoreImage("gameAsset/Characters/Enemy/3/x256_Spritesheets/Idle/Idle Body 270.png").texture,      frame_w, frame_h, 4, 5),
            "run_left":     self.load_sheet(CoreImage("gameAsset/Characters/Enemy/3/x256_Spritesheets/Run/Run Body 270.png").texture,        frame_w, frame_h, 4, 5),
            "attack_left":  self.load_sheet(CoreImage("gameAsset/Characters/Enemy/3/x256_Spritesheets/Attack2/Attack2 Body 270.png").texture,frame_w, frame_h, 4, 5),
        }, "ranged": {
            "death":        self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Death1/Death1 Body 0.png").texture,    frame_w, frame_h, 6, 5),
            "idle_up":      self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Idle/Idle Body 0.png").texture,        frame_w, frame_h, 4, 5),
            "run_up":       self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Run/Run Body 0.png").texture,          frame_w, frame_h, 4, 5),
            "attack_up":    self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Attack3/Attack3 Body 0.png").texture,  frame_w, frame_h, 6, 4),
            "idle_down":    self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Idle/Idle Body 180.png").texture,      frame_w, frame_h, 4, 5),
            "run_down":     self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Run/Run Body 180.png").texture,        frame_w, frame_h, 4, 5),
            "attack_down":  self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Attack3/Attack3 Body 180.png").texture,frame_w, frame_h, 6, 4),
            "idle_right":   self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Idle/Idle Body 090.png").texture,      frame_w, frame_h, 4, 5),
            "run_right":    self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Run/Run Body 090.png").texture,        frame_w, frame_h, 4, 5),
            "attack_right": self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Attack3/Attack3 Body 090.png").texture,frame_w, frame_h, 6, 4),
            "idle_left":    self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Idle/Idle Body 270.png").texture,      frame_w, frame_h, 4, 5),
            "run_left":     self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Run/Run Body 270.png").texture,        frame_w, frame_h, 4, 5),
            "attack_left":  self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Attack3/Attack3 Body 270.png").texture,frame_w, frame_h, 6, 4),
        }, "boss": {
            "death":        self.load_sheet(CoreImage("gameAsset/Characters/Enemy/boss2/death/up.png").texture,   frame_w, frame_h, 16, 1),
            "idle_up":      self.load_sheet(CoreImage("gameAsset/Characters/Enemy/boss2/idle/up.png").texture,    frame_w, frame_h, 20, 1),
            "run_up":       self.load_sheet(CoreImage("gameAsset/Characters/Enemy/boss2/run/up.png").texture,     frame_w, frame_h, 16, 1),
            "attack_up":    self.load_sheet(CoreImage("gameAsset/Characters/Enemy/boss2/attack/up.png").texture,  frame_w, frame_h, 20, 1),
            "idle_down":    self.load_sheet(CoreImage("gameAsset/Characters/Enemy/boss2/idle/up.png").texture,    frame_w, frame_h, 20, 1),
            "run_down":     self.load_sheet(CoreImage("gameAsset/Characters/Enemy/boss2/run/down.png").texture,   frame_w, frame_h, 16, 1),
            "attack_down":  self.load_sheet(CoreImage("gameAsset/Characters/Enemy/boss2/attack/down.png").texture,frame_w, frame_h, 20, 1),
            "idle_right":   self.load_sheet(CoreImage("gameAsset/Characters/Enemy/boss2/idle/up.png").texture,    frame_w, frame_h, 20, 1),
            "run_right":    self.load_sheet(CoreImage("gameAsset/Characters/Enemy/boss2/run/left.png").texture,   frame_w, frame_h, 16, 1),
            "attack_right": self.load_sheet(CoreImage("gameAsset/Characters/Enemy/boss2/attack/left.png").texture,frame_w, frame_h, 16, 1),
            "idle_left":    self.load_sheet(CoreImage("gameAsset/Characters/Enemy/boss2/idle/up.png").texture,    frame_w, frame_h, 20, 1),
            "run_left":     self.load_sheet(CoreImage("gameAsset/Characters/Enemy/boss2/run/right.png").texture,  frame_w, frame_h, 16, 1),
            "attack_left":  self.load_sheet(CoreImage("gameAsset/Characters/Enemy/boss2/attack/right.png").texture,frame_w,frame_h,16, 1),
        }, "elite": {
            "death":        self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Death1/Death1 Body 0.png").texture,    frame_w, frame_h, 6, 5),
            "idle_up":      self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Idle/Idle Body 0.png").texture,        frame_w, frame_h, 4, 5),
            "run_up":       self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Run/Run Body 0.png").texture,          frame_w, frame_h, 4, 5),
            "attack_up":    self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Attack3/Attack3 Body 0.png").texture,  frame_w, frame_h, 6, 4),
            "idle_down":    self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Idle/Idle Body 180.png").texture,      frame_w, frame_h, 4, 5),
            "run_down":     self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Run/Run Body 180.png").texture,        frame_w, frame_h, 4, 5),
            "attack_down":  self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Attack3/Attack3 Body 180.png").texture,frame_w, frame_h, 6, 4),
            "idle_right":   self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Idle/Idle Body 090.png").texture,      frame_w, frame_h, 4, 5),
            "run_right":    self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Run/Run Body 090.png").texture,        frame_w, frame_h, 4, 5),
            "attack_right": self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Attack3/Attack3 Body 090.png").texture,frame_w, frame_h, 6, 4),
            "idle_left":    self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Idle/Idle Body 270.png").texture,      frame_w, frame_h, 4, 5),
            "run_left":     self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Run/Run Body 270.png").texture,        frame_w, frame_h, 4, 5),
            "attack_left":  self.load_sheet(CoreImage("gameAsset/Characters/Enemy/4/x256_Spritesheets/Attack3/Attack3 Body 270.png").texture,frame_w, frame_h, 6, 4),
        }, "poisoner": {
            "death":        self.load_sheet(CoreImage("gameAsset/Characters/Enemy/5/idle/s.png").texture,    frame_w, frame_h, 21, 1),
            "idle_up":      self.load_sheet(CoreImage("gameAsset/Characters/Enemy/5/idle/n.png").texture,    frame_w, frame_h, 19, 1),
            "run_up":       self.load_sheet(CoreImage("gameAsset/Characters/Enemy/5/walk/n.png").texture,    frame_w, frame_h, 24, 1),
            "attack_up":    self.load_sheet(CoreImage("gameAsset/Characters/Enemy/5/attack/n.png").texture,  frame_w, frame_h, 44, 1),
            "idle_down":    self.load_sheet(CoreImage("gameAsset/Characters/Enemy/5/idle/s.png").texture,    frame_w, frame_h, 21, 1),
            "run_down":     self.load_sheet(CoreImage("gameAsset/Characters/Enemy/5/walk/s.png").texture,    frame_w, frame_h, 26, 1),
            "attack_down":  self.load_sheet(CoreImage("gameAsset/Characters/Enemy/5/attack/s.png").texture,  frame_w, frame_h, 6,  6),
            "idle_right":   self.load_sheet(CoreImage("gameAsset/Characters/Enemy/5/idle/e.png").texture,    frame_w, frame_h, 19, 1),
            "run_right":    self.load_sheet(CoreImage("gameAsset/Characters/Enemy/5/walk/e.png").texture,    frame_w, frame_h, 25, 1),
            "attack_right": self.load_sheet(CoreImage("gameAsset/Characters/Enemy/5/attack/e.png").texture,  frame_w, frame_h, 44, 1),
            "idle_left":    self.load_sheet(CoreImage("gameAsset/Characters/Enemy/5/idle/w.png").texture,    frame_w, frame_h, 21, 1),
            "run_left":     self.load_sheet(CoreImage("gameAsset/Characters/Enemy/5/walk/w.png").texture,    frame_w, frame_h, 26, 1),
            "attack_left":  self.load_sheet(CoreImage("gameAsset/Characters/Enemy/5/attack/w.png").texture,  frame_w, frame_h, 6,  6),
        }}

        self.currentFrames = self.animations[self.role][self.state]
        self.texture        = self.currentFrames[0]
        Clock.schedule_interval(self.animate, 0.07)

    def load_sheet(self, texture, frame_w, frame_h, cols, rows):
        frames = []
        for row in range(rows):
            for col in range(cols):
                x = col * frame_w
                y = texture.height - (row + 1) * frame_h
                frames.append(texture.get_region(x, y, frame_w, frame_h))
        return frames

    def animate(self, dt):
        self.frame_index += 1
        if self.frame_index >= len(self.currentFrames):
            self.frame_index = 0
        self.texture = self.currentFrames[self.frame_index]

    def set_state(self, new_state, role):
        if self.state == new_state:
            return
        self.state        = new_state
        self.frame_index  = 0
        self.currentFrames = self.animations[role][self.state]
        self.texture      = self.currentFrames[0]

    def update_direction(self, vx, vy):
        if vx == 0 and vy == 0:
            self.set_state("idle_" + self.facing, self.role)
            return
        if abs(vx) > abs(vy):
            self.facing = "right" if vx > 0 else "left"
        else:
            self.facing = "up" if vy > 0 else "down"


class HealthBar(Widget):
    health     = NumericProperty(100)
    max_health = NumericProperty(100)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # ── HealthBar sized with sdp() matching KV: dp(90)*S x dp(10)*S ──
        self.size = (sdp(90), sdp(10))


class PlayerHealthBar(Widget):
    health       = NumericProperty(100)
    max_health   = NumericProperty(100)
    status_text  = StringProperty("No status effect")
    status_color = ListProperty([1, 1, 1, 0.35])


class Attack(Widget):
    texture = ObjectProperty(None)
    player  = CoreImage("gameAsset/bullet/round.png").texture
    enemy   = CoreImage("gameAsset/bullet/zombie.png").texture

    def __init__(self, direction=(0, 1), **kwargs):
        super().__init__(**kwargs)
        self.texture  = CoreImage("gameAsset/bullet/round.png").texture
        # ── Bullet size scaled ────────────────────────────────────────────
        self.attack_w = sdp(10)
        self.attack_h = sdp(10)
        self.size     = (self.attack_w, self.attack_h)
        dx, dy = direction
        length = math.sqrt(dx**2 + dy**2)
        if length == 0:
            self.vx, self.vy = 0, 1
        else:
            self.vx = dx / length
            self.vy = dy / length
        self.start_x = 0
        self.start_y = 0
        self.speed   = 15
        self.damage  = 50
        self.range   = sdp(800)


class DarknessOverlay(Widget):
    def __init__(self, radius=None, **kwargs):
        super().__init__(**kwargs)
        self.radius = radius or sdp(220)
        self.size   = Window.size
        self.pos    = (0, 0)
        self._tex   = CoreImage("gameAsset/effects/darkness_overlay.png").texture
        self._iw    = 2560
        self._ih    = 1440
        self._cx    = Window.width  / 2
        self._cy    = Window.height / 2
        self._redraw()

    def update_light(self, x, y):
        self._cx = x; self._cy = y
        self._redraw()

    def _redraw(self):
        self.canvas.clear()
        cx, cy = self._cx, self._cy
        iw, ih = self._iw, self._ih
        w,  h  = Window.width, Window.height
        img_x  = cx - iw / 2
        img_y  = cy - ih / 2
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(texture=self._tex, pos=(img_x, img_y), size=(iw, ih))
            Color(0, 0, 0, 0.92)
            if img_x > 0:             Rectangle(pos=(0, 0),         size=(img_x, h))
            img_right = img_x + iw
            if img_right < w:         Rectangle(pos=(img_right, 0), size=(w - img_right, h))
            if img_y > 0:             Rectangle(pos=(img_x, 0),     size=(iw, img_y))
            img_top = img_y + ih
            if img_top < h:           Rectangle(pos=(img_x, img_top), size=(iw, h - img_top))


class GameUI(RelativeLayout):
    ammo_ratio = NumericProperty(1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.weapon_icons = {
            "assault": "gameAsset/gun/ak.png",
            "assualt": "gameAsset/gun/ak.png",
            "shotgun": "gameAsset/gun/shotgun.png",
            "sniper":  "gameAsset/gun/sniper.png",
            "machine": "gameAsset/gun/machine.png",
        }

    def update(self):
        gun     = self.parent.player.guns[self.parent.player.gun.current]
        current = self.parent.player.gun.current
        ammo    = gun['ammo']
        mag     = gun['magazine']
        self.ids.gun_text.text  = current.upper()
        self.ids.ammo_text.text = f"{ammo} / {mag}"
        self.ammo_ratio = ammo / mag if mag > 0 else 0
        self.ids.gun_icon.source = self.weapon_icons.get(current, "")


class RadialWeaponMenu(FloatLayout):

    def open_menu(self, guns, center_x, center_y):
        if not self.disabled:
            self.close_menu()
            return
        if not self.parent.player.gun.switch:
            return
        self.clear_widgets()
        self.opacity  = 1
        self.disabled = False

        scrim = Widget(size=Window.size)
        with scrim.canvas:
            Color(0, 0, 0, 0.72)
            Rectangle(pos=(0, 0), size=Window.size)
        self.add_widget(scrim)

        wheel_x = Window.width  / 2
        wheel_y = Window.height / 2

        wheel = Widget()
        with wheel.canvas:
            Color(0, 0, 0, 0.35)
            Ellipse(pos=(wheel_x - sdp(190), wheel_y - sdp(190)), size=(sdp(380), sdp(380)))
            Color(0.13, 0.13, 0.14, 0.98)
            Ellipse(pos=(wheel_x - sdp(170), wheel_y - sdp(170)), size=(sdp(340), sdp(340)))
            Color(0.07, 0.07, 0.08, 1)
            Ellipse(pos=(wheel_x - sdp(85),  wheel_y - sdp(85)),  size=(sdp(170), sdp(170)))
        self.add_widget(wheel)

        center_label = Label(
            text="[b]WEAPONS[/b]", markup=True,
            font_size=ssp(20), bold=True, color=(1, 1, 1, 1),
            size_hint=(None, None), size=(sdp(200), sdp(40)),
            pos=(wheel_x - sdp(100), wheel_y - sdp(20))
        )
        self.add_widget(center_label)

        BTN_SIZE = sdp(100)
        radius   = sdp(250)
        total    = len(guns)

        TYPE_ICON  = {"assault": self.parent.ak_icon, "assualt": self.parent.ak_icon,
                      "sniper": self.parent.sniper_icon, "shotgun": self.parent.shotgun_icon,
                      "machine": self.parent.machine_icon}
        TYPE_LABEL = {"assault": "AR", "assualt": "AR", "sniper": "SR", "shotgun": "SG", "machine": "LMG"}

        for i, gun in enumerate(guns):
            angle = math.radians((360 / total) * i - 90)
            bx    = wheel_x + math.cos(angle) * radius - BTN_SIZE / 2
            by    = wheel_y + math.sin(angle) * radius - BTN_SIZE / 2
            ammo  = self.parent.player.guns[gun]["ammo"]
            mag   = self.parent.player.guns[gun]["magazine"]
            is_current = gun == self.parent.player.gun.current

            container = RelativeLayout(size_hint=(None, None), size=(BTN_SIZE, BTN_SIZE), pos=(bx, by))
            bg = Widget(size_hint=(1, 1))
            with bg.canvas:
                Color(0, 0, 0, 0.4)
                Ellipse(pos=(-dp(4), -dp(6)), size=(BTN_SIZE, BTN_SIZE))
                Color(0.92, 0.55, 0.22, 1) if is_current else Color(0.14, 0.14, 0.15, 1)
                Ellipse(pos=(0, 0), size=(BTN_SIZE, BTN_SIZE))
                if is_current:
                    Color(1, 1, 1, 0.30)
                    Line(ellipse=(dp(2), dp(2), BTN_SIZE - dp(4), BTN_SIZE - dp(4)), width=dp(2))
                Color(1, 1, 1, 0.04)
                Ellipse(pos=(dp(8), dp(8)), size=(BTN_SIZE - dp(16), BTN_SIZE - dp(16)))
            container.add_widget(bg)

            icon_tex = TYPE_ICON.get(gun)
            if icon_tex:
                container.add_widget(Image(texture=icon_tex, size_hint=(None, None), size=(sdp(60), sdp(60)),
                                           pos_hint={"center_x": 0.5, "center_y": 0.62}, fit_mode="contain"))

            for txt, fs, col, ht, yh in [
                (TYPE_LABEL.get(gun, gun.upper()), 8, (1, 1, 1, 0.85), sdp(18), 0.20),
                (f"{ammo}/{mag}", 8, (0.91, 0.75, 0.29, 1) if is_current else (1, 1, 1, 0.55), sdp(16), 0.05),
            ]:
                l = Label(text=txt, font_size=ssp(fs), bold=True, color=col,
                          size_hint=(1, None), height=ht,
                          pos_hint={"center_x": 0.5, "y": yh}, halign="center", valign="middle")
                l.bind(size=lambda w, s: setattr(w, "text_size", s))
                container.add_widget(l)

            btn = Button(size_hint=(1, 1), background_normal="", background_down="",
                         background_color=(0, 0, 0, 0), border=(0, 0, 0, 0), text="")
            container.add_widget(btn)
            self.add_widget(container)
            btn.bind(on_release=lambda inst, g=gun: self.select_weapon(g))

    def select_weapon(self, gun):
        self.parent.play_click2()
        self.parent.changeWeapon(gun)
        self.close_menu()

    def close_menu(self):
        self.opacity  = 0
        self.disabled = True
        self.clear_widgets()

    def on_touch_down(self, touch):
        if self.disabled:
            return False
        return super().on_touch_down(touch)


class Obstacle(Widget):
    source = StringProperty("")

class Ground(Widget):
    source = StringProperty("")

class UpgradePanel(RelativeLayout):
    pass


class Sound():
    boss         = [SoundLoader.load("gameAsset/dialouge/genda.mp3"), SoundLoader.load("gameAsset/dialouge/gym.mp3")]
    enemy_clear  = [SoundLoader.load("gameAsset/dialouge/ekdum.mp3"), SoundLoader.load("gameAsset/dialouge/i_can.mp3"),
                    SoundLoader.load("gameAsset/dialouge/who_am.mp3"), SoundLoader.load("gameAsset/dialouge/game_to.mp3")]
    game_over    = SoundLoader.load("gameAsset/game_menu/game_over.mp3")
    game_music   = SoundLoader.load("gameAsset/game_menu/game_music.mp3")
    game_music.volume = 0.4
    menu_music   = SoundLoader.load("gameAsset/game_menu/menu_music.mp3")
    collectable  = SoundLoader.load("gameAsset/sound/collect.mp3")
    button_click2 = SoundLoader.load("gameAsset/sound/button3.mp3")
    button_click  = SoundLoader.load("gameAsset/sound/button2.mp3")
    button_click.volume = 0.5
    levelup      = SoundLoader.load("gameAsset/sound/levelup.mp3")
    enemy_hit    = SoundLoader.load("gameAsset/sound/hurtPlayer.mp3")
    run          = SoundLoader.load("gameAsset/sound/run.mp3")
    run.volume   = 0.01
    gun_sound = {
        "assualt": {"shoot": SoundLoader.load("gameAsset/sound/rifle.mp3"),   "reload": SoundLoader.load("gameAsset/sound/rifle_reload.mp3")},
        "shotgun": {"shoot": SoundLoader.load("gameAsset/sound/shotgun.mp3"), "reload": SoundLoader.load("gameAsset/sound/shotgun_reload.mp3")},
        "machine": {"shoot": SoundLoader.load("gameAsset/sound/machine3.mp3"),"reload": SoundLoader.load("gameAsset/sound/rifle_reload.mp3")},
        "sniper":  {"shoot": SoundLoader.load("gameAsset/sound/sniper.mp3"),  "reload": SoundLoader.load("gameAsset/sound/rifle_reload.mp3")},
    }
    gun_sound["assualt"]["shoot"].volume  = 0.15;  gun_sound["assualt"]["reload"].volume = 0.3
    gun_sound["shotgun"]["shoot"].volume  = 0.15;  gun_sound["shotgun"]["reload"].volume = 0.3
    gun_sound["sniper"]["shoot"].volume   = 0.15;  gun_sound["sniper"]["reload"].volume  = 0.3
    gun_sound["machine"]["shoot"].volume  = 0.2;   gun_sound["machine"]["reload"].volume = 0.3


class MainMenu(FloatLayout):

    def on_kv_post(self, *args):
        best_score = 0; best_wave = 0
        if os.path.exists("stats.dat"):
            with open("stats.dat", "r") as f:
                stats = json.load(f)
            best_score = stats.get("high_score", 0)
            best_wave  = stats.get("highest_wave", 0)
        self.ids.best_score_label.text = str(best_score)
        self.ids.best_wave_label.text  = str(best_wave)

    def start_new_game(self):
        Clock.schedule_once(self._launch_new_game, 0)

    def _launch_new_game(self, dt):
        app = App.get_running_app()
        app.root.clear_widgets()
        if app.gs.menu_music.state == "play":
            app.gs.menu_music.stop()
        game = Game()
        with open("save.dat", "w") as f:
            json.dump({}, f)
        game.main_menu = self
        app.root.add_widget(game)

    def continue_game(self):
        Clock.schedule_once(self._launch_continue, 0)

    def _launch_continue(self, dt):
        app = App.get_running_app()
        app.root.clear_widgets()
        if app.gs.menu_music.state == "play":
            app.gs.menu_music.stop()
        game = Game()
        game.load_game()
        game.main_menu = self
        app.root.add_widget(game)


class Escape(App):
    def build(self):
        self.root_layout = FloatLayout()
        menu = MainMenu()
        self.gs = Sound()
        if self.gs.menu_music.state != "play":
            self.gs.menu_music.play()
        self.root_layout.add_widget(menu)
        return self.root_layout

    def play_click(self):
        self.gs.button_click.stop()
        self.gs.button_click.play()


if __name__ == '__main__':
    Escape().run()
