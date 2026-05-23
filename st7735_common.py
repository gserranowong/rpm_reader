# Shared color helpers and layout constants for ST7735.

from vec2 import Vec2

# TFTRotations and TFTRGB are bits to set on MADCTL (rotation / color layout).
TFTRotations = [0x00, 0x60, 0xC0, 0xA0]
TFTBGR = 0x08
TFTRGB = 0x00


def clamp(aValue, aMin, aMax):
    return max(aMin, min(aMax, aValue))


def TFTColor(aR, aG, aB):
    """16-bit RGB565 from R,G,B 0–255 (assumes RGB order; wrong for BGR panels)."""
    return ((aR & 0xF8) << 8) | ((aG & 0xFC) << 3) | (aB >> 3)


ScreenSize = Vec2(80, 160)
