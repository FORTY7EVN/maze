"""Procedural sound effects for Sapphire Dash."""

import math
import random
import pygame


class AudioManager:
    """Builds and plays the game's small synthesized sound palette."""

    def __init__(self):
        try:
            self.sounds = {
                "deadend": self._make_tone(110, 120, "square", 0.25),
                "undo": self._make_tone(320, 40, "sine", 0.18),
                "hint": self._make_tone(580, 180, "sine", 0.20),
                "levelup": self._make_tone(750, 240, "sine", 0.25),
            }
            self.enabled = True
        except Exception:
            self.sounds = {}
            self.enabled = False

    @staticmethod
    def _make_tone(freq, duration_ms, wave_type="sine", volume=0.25):
        sample_rate = 44100
        n_samples = int(sample_rate * (duration_ms / 1000.0))
        buffer = bytearray(n_samples * 2)
        for index in range(n_samples):
            time = index / sample_rate
            if wave_type == "sine":
                value = math.sin(2.0 * math.pi * freq * time)
            elif wave_type == "noise":
                value = random.uniform(-1.0, 1.0)
            else:
                value = 1.0 if (
                    index // (sample_rate // max(1, int(freq)))) % 2 == 0 else -1.0
            value *= max(0.0, 1.0 - index / n_samples) * volume
            buffer[index * 2:index * 2 +
                   2] = int(value * 32767).to_bytes(2, "little", signed=True)
        return pygame.mixer.Sound(bytes(buffer))

    def play(self, name):
        if self.enabled and name in self.sounds:
            self.sounds[name].play()

    def play_glide(self, streak):
        if not self.enabled:
            return
        frequency = min(590.0, 290.0 + streak * 7.5)
        duration = max(14, int(24 - min(8, streak * 0.3)))
        self._make_tone(frequency, duration, "sine", 0.15).play()
