# Drawing primitives into the physical framebuffer (see st7735_buffer.render).
# Optional render-only landscape / flip remaps logical coordinates without changing MADCTL / driver._size.

import framebuf
from math import sqrt

from st7735_common import clamp


class ST7735RenderMixin:
    """2D drawing in logical space; requires ST7735ScreenBufferMixin + ST7735Driver."""

    def set_render_landscape(self, landscape=False, flip_180=False):
        """Interpret drawing in landscape (swap logical width/height) without changing the driver.

        Does not call ``rotation()`` or alter MADCTL; the framebuffer stays ``physical_size()`` pixels.
        ``size()`` and all drawing APIs use logical (lx, ly); pixels are mapped into the physical buffer.

        If you also use ``ST7735Driver.rotation()``, you combine hardware rotation with this logical map.

        Refreshes the dirty region to full screen so the next ``render()`` updates the panel.
        """
        self._render_landscape = bool(landscape)
        self._render_flip = bool(flip_180)
        self.invalidate()

    def _render_trivial(self):
        return not getattr(self, "_render_landscape", False) and not getattr(self, "_render_flip", False)

    def logical_size(self):
        """(width, height) in user coordinates (landscape swaps vs physical)."""
        pw = int(self._size[0])
        ph = int(self._size[1])
        if getattr(self, "_render_landscape", False):
            return (ph, pw)
        return (pw, ph)

    def physical_size(self):
        """Pixel size of the framebuffer / panel (always ``driver._size``)."""
        return (int(self._size[0]), int(self._size[1]))

    def size(self):
        """Logical size for layout (respects render landscape / flip)."""
        return self.logical_size()

    def _logical_to_phys(self, lx, ly):
        """Map logical (lx, ly) to physical (px, py), or None if out of logical bounds."""
        lx, ly = int(lx), int(ly)
        lw, lh = self.logical_size()
        if not (0 <= lx < lw and 0 <= ly < lh):
            return None
        if getattr(self, "_render_flip", False):
            lx = lw - 1 - lx
            ly = lh - 1 - ly
        pw, ph = int(self._size[0]), int(self._size[1])
        if getattr(self, "_render_landscape", False):
            px = ly
            py = ph - 1 - lx
        else:
            px, py = lx, ly
        return (px, py)

    def _phys_pixel(self, lx, ly, aColor):
        t = self._logical_to_phys(lx, ly)
        if t is None:
            return
        px, py = t
        pw, ph = int(self._size[0]), int(self._size[1])
        if 0 <= px < pw and 0 <= py < ph:
            self._fb.pixel(px, py, aColor)
            self._mark_dirty_inclusive(px, py, px, py)

    def _mark_dirty_logical_rect(self, lx0, ly0, lx1, ly1):
        xa, xb = min(lx0, lx1), max(lx0, lx1)
        ya, yb = min(ly0, ly1), max(ly0, ly1)
        pxs = []
        for lx, ly in ((xa, ya), (xa, yb), (xb, ya), (xb, yb)):
            t = self._logical_to_phys(lx, ly)
            if t:
                pxs.append(t)
        if not pxs:
            return
        mix = min(p[0] for p in pxs)
        miy = min(p[1] for p in pxs)
        mxx = max(p[0] for p in pxs)
        mxy = max(p[1] for p in pxs)
        self._mark_dirty_inclusive(mix, miy, mxx, mxy)

    def pixel(self, aPos, aColor):
        self._ensure_screen_buffer()
        if self._render_trivial():
            w, h = self._screen_dims
            x, y = int(aPos[0]), int(aPos[1])
            if 0 <= x < w and 0 <= y < h:
                self._fb.pixel(x, y, aColor)
                self._mark_dirty_inclusive(x, y, x, y)
        else:
            self._phys_pixel(aPos[0], aPos[1], aColor)

    def text(self, aPos, aString, aColor, aFont, aSize=1, nowrap=False):
        if aFont is None:
            return
        if isinstance(aSize, (int, float)):
            wh = (aSize, aSize)
        else:
            wh = aSize
        px, py = aPos
        lw = self.logical_size()[0]
        width = wh[0] * aFont["Width"] + 1
        for c in aString:
            self.char((px, py), c, aColor, aFont, wh)
            px += width
            if px + width > lw:
                if nowrap:
                    break
                py += aFont["Height"] * wh[1] + 1
                px = aPos[0]

    def char(self, aPos, aChar, aColor, aFont, aSizes):
        if aFont is None:
            return
        startchar = aFont["Start"]
        endchar = aFont["End"]
        ci = ord(aChar)
        if startchar <= ci <= endchar:
            fontw = aFont["Width"]
            fonth = aFont["Height"]
            ci = (ci - startchar) * fontw
            charA = aFont["Data"][ci : ci + fontw]
            px = aPos[0]
            if aSizes[0] <= 1 and aSizes[1] <= 1:
                buf = bytearray(2 * fonth * fontw)
                for q in range(fontw):
                    c = charA[q]
                    for r in range(fonth):
                        if c & 0x01:
                            pos = 2 * (r * fontw + q)
                            buf[pos] = aColor & 0xFF
                            buf[pos + 1] = (aColor >> 8) & 0xFF
                        c >>= 1
                self.image(aPos[0], aPos[1], aPos[0] + fontw - 1, aPos[1] + fonth - 1, buf)
            else:
                for c in charA:
                    py = aPos[1]
                    for r in range(fonth):
                        if c & 0x01:
                            self.fillrect((px, py), aSizes, aColor)
                        py += aSizes[1]
                        c >>= 1
                    px += aSizes[0]

    def line(self, aStart, aEnd, aColor):
        self._ensure_screen_buffer()
        lw, lh = self.logical_size()
        x0, y0 = int(aStart[0]), int(aStart[1])
        x1, y1 = int(aEnd[0]), int(aEnd[1])
        if self._render_trivial():
            w, h = self._screen_dims
            if x0 == x1:
                pnt = aEnd if (aEnd[1] < aStart[1]) else aStart
                self.vline(pnt, abs(aEnd[1] - aStart[1]) + 1, aColor)
            elif y0 == y1:
                pnt = aEnd if aEnd[0] < aStart[0] else aStart
                self.hline(pnt, abs(aEnd[0] - aStart[0]) + 1, aColor)
            else:
                px, py = x0, y0
                ex, ey = x1, y1
                dx = ex - px
                dy = ey - py
                inx = 1 if dx > 0 else -1
                iny = 1 if dy > 0 else -1
                dx = abs(dx)
                dy = abs(dy)
                if dx >= dy:
                    dy <<= 1
                    e = dy - dx
                    dx <<= 1
                    while px != ex:
                        if 0 <= px < w and 0 <= py < h:
                            self._fb.pixel(px, py, aColor)
                        if e >= 0:
                            py += iny
                            e -= dx
                        e += dy
                        px += inx
                    self._mark_dirty_inclusive(x0, y0, x1, y1)
                else:
                    dx <<= 1
                    e = dx - dy
                    dy <<= 1
                    while py != ey:
                        if 0 <= px < w and 0 <= py < h:
                            self._fb.pixel(px, py, aColor)
                        if e >= 0:
                            px += inx
                            e -= dy
                        e += dx
                        py += iny
                    self._mark_dirty_inclusive(x0, y0, x1, y1)
            return
        if x0 == x1:
            pnt = aEnd if (aEnd[1] < aStart[1]) else aStart
            self.vline(pnt, abs(aEnd[1] - aStart[1]) + 1, aColor)
        elif y0 == y1:
            pnt = aEnd if aEnd[0] < aStart[0] else aStart
            self.hline(pnt, abs(aEnd[0] - aStart[0]) + 1, aColor)
        else:
            px, py = x0, y0
            ex, ey = x1, y1
            dx = ex - px
            dy = ey - py
            inx = 1 if dx > 0 else -1
            iny = 1 if dy > 0 else -1
            dx = abs(dx)
            dy = abs(dy)
            if dx >= dy:
                dy <<= 1
                e = dy - dx
                dx <<= 1
                while px != ex:
                    if 0 <= px < lw and 0 <= py < lh:
                        self._phys_pixel(px, py, aColor)
                    if e >= 0:
                        py += iny
                        e -= dx
                    e += dy
                    px += inx
            else:
                dx <<= 1
                e = dx - dy
                dy <<= 1
                while py != ey:
                    if 0 <= px < lw and 0 <= py < lh:
                        self._phys_pixel(px, py, aColor)
                    if e >= 0:
                        px += inx
                        e -= dy
                    e += dx
                    py += iny
            self._mark_dirty_logical_rect(x0, y0, x1, y1)

    def hline(self, aStart, aLen, aColor):
        self._ensure_screen_buffer()
        if aLen == 0:
            return
        if self._render_trivial():
            w, h = self._screen_dims
            y0 = clamp(int(aStart[1]), 0, h - 1)
            xs = int(aStart[0])
            if aLen >= 0:
                xe = xs + aLen - 1
            else:
                xe = xs
                xs = xs + aLen + 1
            xs = clamp(xs, 0, w - 1)
            xe = clamp(xe, 0, w - 1)
            if xs > xe:
                xs, xe = xe, xs
            self._fb.hline(xs, y0, xe - xs + 1, aColor)
            self._mark_dirty_inclusive(xs, y0, xe, y0)
            return
        lw, lh = self.logical_size()
        y0 = clamp(int(aStart[1]), 0, lh - 1)
        xs = int(aStart[0])
        if aLen >= 0:
            xe = xs + aLen - 1
        else:
            xe = xs
            xs = xs + aLen + 1
        xs = clamp(xs, 0, lw - 1)
        xe = clamp(xe, 0, lw - 1)
        if xs > xe:
            xs, xe = xe, xs
        for lx in range(xs, xe + 1):
            self._phys_pixel(lx, y0, aColor)
        self._mark_dirty_logical_rect(xs, y0, xe, y0)

    def vline(self, aStart, aLen, aColor):
        self._ensure_screen_buffer()
        if aLen == 0:
            return
        if self._render_trivial():
            w, h = self._screen_dims
            x0 = clamp(int(aStart[0]), 0, w - 1)
            ys = int(aStart[1])
            if aLen >= 0:
                ye = ys + aLen - 1
            else:
                ye = ys
                ys = ys + aLen + 1
            ys = clamp(ys, 0, h - 1)
            ye = clamp(ye, 0, h - 1)
            if ys > ye:
                ys, ye = ye, ys
            self._fb.vline(x0, ys, ye - ys + 1, aColor)
            self._mark_dirty_inclusive(x0, ys, x0, ye)
            return
        lw, lh = self.logical_size()
        x0 = clamp(int(aStart[0]), 0, lw - 1)
        ys = int(aStart[1])
        if aLen >= 0:
            ye = ys + aLen - 1
        else:
            ye = ys
            ys = ys + aLen + 1
        ys = clamp(ys, 0, lh - 1)
        ye = clamp(ye, 0, lh - 1)
        if ys > ye:
            ys, ye = ye, ys
        for ly in range(ys, ye + 1):
            self._phys_pixel(x0, ly, aColor)
        self._mark_dirty_logical_rect(x0, ys, x0, ye)

    def rect(self, aStart, aSize, aColor):
        self._ensure_screen_buffer()
        if self._render_trivial():
            w, h = self._screen_dims
            x = clamp(int(aStart[0]), 0, w - 1)
            y = clamp(int(aStart[1]), 0, h - 1)
            rw = max(0, int(aSize[0]))
            rh = max(0, int(aSize[1]))
            if rw == 0 or rh == 0:
                return
            rw = min(rw, w - x)
            rh = min(rh, h - y)
            if rw < 1 or rh < 1:
                return
            self._fb.rect(x, y, rw, rh, aColor)
            self._mark_dirty_inclusive(x, y, x + rw - 1, y + rh - 1)
            return
        lw, lh = self.logical_size()
        x = clamp(int(aStart[0]), 0, lw - 1)
        y = clamp(int(aStart[1]), 0, lh - 1)
        rw = max(0, int(aSize[0]))
        rh = max(0, int(aSize[1]))
        if rw == 0 or rh == 0:
            return
        rw = min(rw, lw - x)
        rh = min(rh, lh - y)
        if rw < 1 or rh < 1:
            return
        self.hline((x, y), rw, aColor)
        self.hline((x, y + rh - 1), rw, aColor)
        self.vline((x, y), rh, aColor)
        self.vline((x + rw - 1, y), rh, aColor)

    def fillrect(self, aStart, aSize, aColor):
        self._ensure_screen_buffer()
        if self._render_trivial():
            w, h = self._screen_dims
            start = (clamp(int(aStart[0]), 0, w - 1), clamp(int(aStart[1]), 0, h - 1))
            end = (
                clamp(start[0] + int(aSize[0]) - 1, 0, w - 1),
                clamp(start[1] + int(aSize[1]) - 1, 0, h - 1),
            )
            if end[0] < start[0]:
                tmp = end[0]
                end = (start[0], end[1])
                start = (tmp, start[1])
            if end[1] < start[1]:
                tmp = end[1]
                end = (end[0], start[1])
                start = (start[0], tmp)
            rw = end[0] - start[0] + 1
            rh = end[1] - start[1] + 1
            self._fb.fill_rect(start[0], start[1], rw, rh, aColor)
            self._mark_dirty_inclusive(start[0], start[1], end[0], end[1])
            return
        lw, lh = self.logical_size()
        start = (clamp(int(aStart[0]), 0, lw - 1), clamp(int(aStart[1]), 0, lh - 1))
        end = (
            clamp(start[0] + int(aSize[0]) - 1, 0, lw - 1),
            clamp(start[1] + int(aSize[1]) - 1, 0, lh - 1),
        )
        if end[0] < start[0]:
            tmp = end[0]
            end = (start[0], end[1])
            start = (tmp, start[1])
        if end[1] < start[1]:
            tmp = end[1]
            end = (end[0], start[1])
            start = (start[0], tmp)
        for ly in range(start[1], end[1] + 1):
            for lx in range(start[0], end[0] + 1):
                self._phys_pixel(lx, ly, aColor)
        self._mark_dirty_logical_rect(start[0], start[1], end[0], end[1])

    def circle(self, aPos, aRadius, aColor):
        self._ensure_screen_buffer()
        cx, cy = int(aPos[0]), int(aPos[1])
        r = int(aRadius)
        if self._render_trivial():
            self._mark_dirty_inclusive(cx - r, cy - r, cx + r, cy + r)
            fb = self._fb
            w, h = self._screen_dims
            if hasattr(fb, "ellipse"):
                try:
                    fb.ellipse(cx, cy, r, r, aColor, False)
                    return
                except TypeError:
                    pass
            xend = int(0.7071 * r) + 1
            rsq = r * r
            for x in range(xend):
                y = int(sqrt(rsq - x * x))
                for px, py in (
                    (cx + x, cy + y),
                    (cx + x, cy - y),
                    (cx - x, cy + y),
                    (cx - x, cy - y),
                    (cx + y, cy + x),
                    (cx + y, cy - x),
                    (cx - y, cy + x),
                    (cx - y, cy - x),
                ):
                    if 0 <= px < w and 0 <= py < h:
                        self._fb.pixel(px, py, aColor)
            return
        self._mark_dirty_logical_rect(cx - r, cy - r, cx + r, cy + r)
        xend = int(0.7071 * r) + 1
        rsq = r * r
        lw, lh = self.logical_size()
        for x in range(xend):
            y = int(sqrt(rsq - x * x))
            for lx, ly in (
                (cx + x, cy + y),
                (cx + x, cy - y),
                (cx - x, cy + y),
                (cx - x, cy - y),
                (cx + y, cy + x),
                (cx + y, cy - x),
                (cx - y, cy + x),
                (cx - y, cy - x),
            ):
                if 0 <= lx < lw and 0 <= ly < lh:
                    self._phys_pixel(lx, ly, aColor)

    def fillcircle(self, aPos, aRadius, aColor):
        self._ensure_screen_buffer()
        cx, cy = int(aPos[0]), int(aPos[1])
        r = int(aRadius)
        if self._render_trivial():
            self._mark_dirty_inclusive(cx - r, cy - r, cx + r, cy + r)
            fb = self._fb
            w, h = self._screen_dims
            if hasattr(fb, "ellipse"):
                try:
                    fb.ellipse(cx, cy, r, r, aColor, True)
                    return
                except TypeError:
                    pass
            rsq = r * r
            for x in range(r):
                y = int(sqrt(rsq - x * x))
                y0 = cy - y
                ye = cy + y
                y0 = clamp(y0, 0, h - 1)
                ye = clamp(ye, 0, h - 1)
                if y0 <= ye:
                    self._fb.vline(cx + x, y0, ye - y0 + 1, aColor)
                    self._fb.vline(cx - x, y0, ye - y0 + 1, aColor)
            return
        self._mark_dirty_logical_rect(cx - r, cy - r, cx + r, cy + r)
        rsq = r * r
        lw, lh = self.logical_size()
        for ly in range(cy - r, cy + r + 1):
            for lx in range(cx - r, cx + r + 1):
                if 0 <= lx < lw and 0 <= ly < lh and (lx - cx) ** 2 + (ly - cy) ** 2 <= rsq:
                    self._phys_pixel(lx, ly, aColor)

    def fill(self, aColor=None):
        self._ensure_screen_buffer()
        if aColor is None:
            aColor = self.BLACK
        self._fb.fill(aColor)
        self.invalidate()

    def image(self, x0, y0, x1, y1, data):
        self._ensure_screen_buffer()
        iw = x1 - x0 + 1
        ih = y1 - y0 + 1
        if iw <= 0 or ih <= 0:
            return
        if self._render_trivial():
            w, h = self._screen_dims
            src = framebuf.FrameBuffer(data, iw, ih, framebuf.RGB565)
            dx = clamp(x0, 0, w - 1)
            dy = clamp(y0, 0, h - 1)
            self._fb.blit(src, dx, dy)
            xa = max(0, int(x0))
            ya = max(0, int(y0))
            xb = min(w - 1, int(x0) + iw - 1)
            yb = min(h - 1, int(y0) + ih - 1)
            if xa <= xb and ya <= yb:
                self._mark_dirty_inclusive(xa, ya, xb, yb)
            return
        lw, lh = self.logical_size()
        for r in range(ih):
            for q in range(iw):
                lx = x0 + q
                ly = y0 + r
                if 0 <= lx < lw and 0 <= ly < lh:
                    pos = 2 * (r * iw + q)
                    c = data[pos] | (data[pos + 1] << 8)
                    self._phys_pixel(lx, ly, c)
        self._mark_dirty_logical_rect(x0, y0, x0 + iw - 1, y0 + ih - 1)
