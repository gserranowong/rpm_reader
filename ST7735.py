# ST7735 1.8" TFT (Sainsmart-style) — public API.
# Implementation: st7735_driver (SPI + init), st7735_buffer (framebuffer), st7735_render (primitives + optional logical landscape).
#
# TFT draws into an RGB565 buffer; call render() after changes. Use set_render_landscape(True) for horizontal
# layout in software only (does not change MADCTL / driver.rotation). self.framebuffer uses physical coordinates.
# After drawing via self.framebuffer, call invalidate() then render().

from st7735_buffer import ST7735ScreenBufferMixin
from st7735_common import TFTColor, clamp, ScreenSize, TFTRGB, TFTRotations, TFTBGR
from st7735_driver import ST7735Driver
from st7735_render import ST7735RenderMixin

__all__ = [
    "ST7735Driver",
    "TFT",
    "TFTColor",
    "clamp",
    "ScreenSize",
    "TFTRGB",
    "TFTRotations",
    "TFTBGR",
    "maker",
    "makeb",
    "makeg",
]


class TFT(ST7735Driver, ST7735ScreenBufferMixin, ST7735RenderMixin):
    """Hardware driver + framebuffer; use render() after drawing."""

    pass


def maker():
    t = TFT(1, "X1", "X2")
    print("Initializing")
    t.initr()
    t.fill(0)
    t.render()
    return t


def makeb():
    t = TFT(1, "X1", "X2")
    print("Initializing")
    t.initb()
    t.fill(0)
    t.render()
    return t


def makeg():
    t = TFT(1, "X1", "X2")
    print("Initializing")
    t.initg()
    t.fill(0)
    t.render()
    return t
