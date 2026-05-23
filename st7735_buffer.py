# Full-screen RGB565 RAM buffer; call render() after drawing. render() swaps each pixel's bytes for SPI
# (MicroPython FrameBuffer uses little-endian RGB565 in RAM; ST7735 expects high byte first on the wire),
# then swaps back so the buffer stays consistent for further drawing.
#
# By default render() sends only the bounding box of pixels touched since the last render() (dirty rectangle).
# Use render(full=True) to push the entire buffer, or invalidate() after drawing via self.framebuffer.
#
# If you call ST7735Driver methods such as _writedata on a TFT instance, you bypass RAM; use invalidate()
# then render() if you need the buffer and panel aligned again.

import framebuf

from st7735_common import clamp


def _swap_rgb565_byte_pairs(buf):
    """FrameBuffer RGB565 is little-endian in RAM; ST7735 expects high byte first on SPI."""
    mv = memoryview(buf)
    n = len(mv)
    for i in range(0, n - 1, 2):
        mv[i], mv[i + 1] = mv[i + 1], mv[i]


class ST7735ScreenBufferMixin:
    """Allocates a FrameBuffer the size of the logical screen (self._size)."""

    def _ensure_screen_buffer(self):
        w = int(self._size[0])
        h = int(self._size[1])
        dims = (w, h)
        if getattr(self, "_screen_buf", None) is not None and getattr(self, "_screen_dims", None) == dims:
            return
        self._screen_buf = bytearray(w * h * 2)
        self._fb = framebuf.FrameBuffer(self._screen_buf, w, h, framebuf.RGB565)
        self._screen_dims = dims
        # New backing store: panel may be stale until first render
        self._dirty_rect = (0, 0, w - 1, h - 1)

    def _mark_dirty_inclusive(self, x0, y0, x1, y1):
        """Expand the dirty region to include the inclusive pixel rectangle (clipped to the screen)."""
        self._ensure_screen_buffer()
        w, h = self._screen_dims
        x0 = clamp(int(x0), 0, w - 1)
        y0 = clamp(int(y0), 0, h - 1)
        x1 = clamp(int(x1), 0, w - 1)
        y1 = clamp(int(y1), 0, h - 1)
        if x0 > x1 or y0 > y1:
            return
        d = getattr(self, "_dirty_rect", None)
        if d is None:
            self._dirty_rect = (x0, y0, x1, y1)
        else:
            self._dirty_rect = (
                min(d[0], x0),
                min(d[1], y0),
                max(d[2], x1),
                max(d[3], y1),
            )

    def invalidate(self):
        """Mark the whole screen dirty (e.g. after using self.framebuffer directly)."""
        self._ensure_screen_buffer()
        w, h = self._screen_dims
        self._dirty_rect = (0, 0, w - 1, h - 1)

    @property
    def framebuffer(self):
        """Physical FrameBuffer (same layout as the panel); x 0..W-1, y 0..H-1 in device pixels."""
        self._ensure_screen_buffer()
        return self._fb

    def render(self, full=False):
        """Push RAM to the ST7735. Call after drawing.

        With full=False (default), only the dirty rectangle (union of all changes since the last render)
        is sent. With full=True, the entire buffer is sent. If nothing is dirty, render() does nothing
        unless full=True.
        """
        self._ensure_screen_buffer()
        w, h = self._screen_dims
        buf = self._screen_buf
        if full:
            self._setwindowloc((0, 0), (w - 1, h - 1))
            _swap_rgb565_byte_pairs(buf)
            try:
                self._writedata(buf)
            finally:
                _swap_rgb565_byte_pairs(buf)
            self._dirty_rect = None
            return
        d = getattr(self, "_dirty_rect", None)
        if d is None:
            return
        x0, y0, x1, y1 = d
        rw = x1 - x0 + 1
        rh = y1 - y0 + 1
        self._setwindowloc((x0, y0), (x1, y1))
        if rw * rh * 2 == len(buf):
            _swap_rgb565_byte_pairs(buf)
            try:
                self._writedata(buf)
            finally:
                _swap_rgb565_byte_pairs(buf)
        else:
            sub = bytearray(rw * rh * 2)
            o = 0
            mv = memoryview(buf)
            sw = w
            row_len = rw * 2
            for y in range(y0, y1 + 1):
                row_start = (y * sw + x0) * 2
                sub[o : o + row_len] = mv[row_start : row_start + row_len]
                o += row_len
            _swap_rgb565_byte_pairs(sub)
            self._writedata(sub)
        self._dirty_rect = None
