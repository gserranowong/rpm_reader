# Low-level ST7735 SPI driver: init sequences, registers, windows, raw transfers.

import machine
import time

from st7735_common import ScreenSize, TFTRGB, TFTRotations, TFTBGR, TFTColor


class ST7735Driver:
    """Hardware-only ST7735: init, rotation, windows, raw SPI writes.

    No framebuffer or drawing primitives. For buffered drawing (RAM then render()),
    use TFT. Typical driver-only flow: init* → _setwindowloc → _writedata or _pushcolor.
    Import: from ST7735 import ST7735Driver.
    """

    NOP = 0x0
    SWRESET = 0x01
    RDDID = 0x04
    RDDST = 0x09
    SLPIN = 0x10
    SLPOUT = 0x11
    PTLON = 0x12
    NORON = 0x13
    INVOFF = 0x20
    INVON = 0x21
    DISPOFF = 0x28
    DISPON = 0x29
    CASET = 0x2A
    RASET = 0x2B
    RAMWR = 0x2C
    RAMRD = 0x2E
    VSCRDEF = 0x33
    VSCSAD = 0x37
    COLMOD = 0x3A
    MADCTL = 0x36
    FRMCTR1 = 0xB1
    FRMCTR2 = 0xB2
    FRMCTR3 = 0xB3
    INVCTR = 0xB4
    DISSET5 = 0xB6
    PWCTR1 = 0xC0
    PWCTR2 = 0xC1
    PWCTR3 = 0xC2
    PWCTR4 = 0xC3
    PWCTR5 = 0xC4
    VMCTR1 = 0xC5
    RDID1 = 0xDA
    RDID2 = 0xDB
    RDID3 = 0xDC
    RDID4 = 0xDD
    PWCTR6 = 0xFC
    GMCTRP1 = 0xE0
    GMCTRN1 = 0xE1

    BLACK = 0
    RED = TFTColor(0xFF, 0x00, 0x00)
    MAROON = TFTColor(0x80, 0x00, 0x00)
    GREEN = TFTColor(0x00, 0xFF, 0x00)
    FOREST = TFTColor(0x00, 0x80, 0x80)
    BLUE = TFTColor(0x00, 0x00, 0xFF)
    NAVY = TFTColor(0x00, 0x00, 0x80)
    CYAN = TFTColor(0x00, 0xFF, 0xFF)
    YELLOW = TFTColor(0xFF, 0xFF, 0x00)
    PURPLE = TFTColor(0xFF, 0x00, 0xFF)
    WHITE = TFTColor(0xFF, 0xFF, 0xFF)
    GRAY = TFTColor(0x80, 0x80, 0x80)
    GOLD = TFTColor(0xFF,0xD7,0x00)

    @staticmethod
    def color(aR, aG, aB):
        return TFTColor(aR, aG, aB)

    def __init__(self, spi, aDC, aReset, aCS):
        self._size = ScreenSize
        self._offset = bytearray([26, 1])
        self.rotate = 0
        self._rgb = True
        self.tfa = 0
        self.bfa = 0
        self.dc = machine.Pin(aDC, machine.Pin.OUT, machine.Pin.PULL_DOWN)
        self.reset = machine.Pin(aReset, machine.Pin.OUT, machine.Pin.PULL_DOWN)
        self.cs = machine.Pin(aCS, machine.Pin.OUT, machine.Pin.PULL_DOWN)
        self.cs(1)
        self.spi = spi
        self.colorData = bytearray(2)
        self.windowLocData = bytearray(4)

    def size(self):
        return self._size

    def on(self, aTF=True):
        cls = self.__class__
        self._writecommand(cls.DISPON if aTF else cls.DISPOFF)

    def invertcolor(self, aBool):
        cls = self.__class__
        self._writecommand(cls.INVON if aBool else cls.INVOFF)

    def rgb(self, aTF=True):
        self._rgb = aTF
        self._setMADCTL()

    def rotation(self, aRot):
        if 0 <= aRot < 4:
            rotchange = self.rotate ^ aRot
            self.rotate = aRot
            if rotchange & 1:
                self._size = (self._size[1], self._size[0])
            self._setMADCTL()

    def setvscroll(self, tfa, bfa):
        cls = self.__class__
        self._writecommand(cls.VSCRDEF)
        data2 = bytearray([0, tfa])
        self._writedata(data2)
        data2[1] = 162 - tfa - bfa
        self._writedata(data2)
        data2[1] = bfa
        self._writedata(data2)
        self.tfa = tfa
        self.bfa = bfa

    def vscroll(self, value):
        a = value + self.tfa
        if a + self.bfa > 162:
            a = 162 - self.bfa
        self._vscrolladdr(a)

    def _vscrolladdr(self, addr):
        cls = self.__class__
        self._writecommand(cls.VSCSAD)
        data2 = bytearray([addr >> 8, addr & 0xFF])
        self._writedata(data2)

    def _setwindowpoint(self, aPos):
        cls = self.__class__
        x = self._offset[0] + int(aPos[0])
        y = self._offset[1] + int(aPos[1])
        self._writecommand(cls.CASET)
        self.windowLocData[0] = self._offset[0]
        self.windowLocData[1] = x
        self.windowLocData[2] = self._offset[0]
        self.windowLocData[3] = x
        self._writedata(self.windowLocData)
        self._writecommand(cls.RASET)
        self.windowLocData[0] = self._offset[1]
        self.windowLocData[1] = y
        self.windowLocData[2] = self._offset[1]
        self.windowLocData[3] = y
        self._writedata(self.windowLocData)
        self._writecommand(cls.RAMWR)

    def _setwindowloc(self, aPos0, aPos1):
        cls = self.__class__
        self._writecommand(cls.CASET)
        self.windowLocData[0] = self._offset[0]
        self.windowLocData[1] = self._offset[0] + int(aPos0[0])
        self.windowLocData[2] = self._offset[0]
        self.windowLocData[3] = self._offset[0] + int(aPos1[0])
        self._writedata(self.windowLocData)
        self._writecommand(cls.RASET)
        self.windowLocData[0] = self._offset[1]
        self.windowLocData[1] = self._offset[1] + int(aPos0[1])
        self.windowLocData[2] = self._offset[1]
        self.windowLocData[3] = self._offset[1] + int(aPos1[1])
        self._writedata(self.windowLocData)
        self._writecommand(cls.RAMWR)

    def _writecommand(self, aCommand):
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([aCommand]))
        self.cs(1)

    def _writedata(self, aData):
        self.dc(1)
        self.cs(0)
        self.spi.write(aData)
        self.cs(1)

    def _pushcolor(self, aColor):
        """Send one RGB565 pixel (high byte first, as typical ST7735 SPI expects)."""
        self.colorData[0] = aColor >> 8
        self.colorData[1] = aColor & 0xFF
        self._writedata(self.colorData)

    def _setMADCTL(self):
        cls = self.__class__
        self._writecommand(cls.MADCTL)
        rgb = TFTRGB if self._rgb else TFTBGR
        self._writedata(bytearray([TFTRotations[self.rotate] | rgb]))

    def _reset(self):
        self.dc(0)
        self.reset(1)
        time.sleep_us(500)
        self.reset(0)
        time.sleep_us(500)
        self.reset(1)
        time.sleep_us(500)

    def initb(self):
        cls = self.__class__
        self._size = (ScreenSize[0] + 2, ScreenSize[1] + 1)
        self._reset()
        self._writecommand(cls.SWRESET)
        time.sleep_us(50)
        self._writecommand(cls.SLPOUT)
        time.sleep_us(500)
        data1 = bytearray(1)
        self._writecommand(cls.COLMOD)
        data1[0] = 0x05
        self._writedata(data1)
        time.sleep_us(10)
        data3 = bytearray([0x00, 0x06, 0x03])
        self._writecommand(cls.FRMCTR1)
        self._writedata(data3)
        time.sleep_us(10)
        self._writecommand(cls.MADCTL)
        data1[0] = 0x08
        self._writedata(data1)
        data2 = bytearray(2)
        self._writecommand(cls.DISSET5)
        data2[0] = 0x15
        data2[1] = 0x02
        self._writedata(data2)
        self._writecommand(cls.INVCTR)
        data1[0] = 0x00
        self._writedata(data1)
        self._writecommand(cls.PWCTR1)
        data2[0] = 0x02
        data2[1] = 0x70
        self._writedata(data2)
        time.sleep_us(10)
        self._writecommand(cls.PWCTR2)
        data1[0] = 0x05
        self._writedata(data1)
        self._writecommand(cls.PWCTR3)
        data2[0] = 0x01
        data2[1] = 0x02
        self._writedata(data2)
        self._writecommand(cls.VMCTR1)
        data2[0] = 0x3C
        data2[1] = 0x38
        self._writedata(data2)
        time.sleep_us(10)
        self._writecommand(cls.PWCTR6)
        data2[0] = 0x11
        data2[1] = 0x15
        self._writedata(data2)
        dataGMCTRP = bytearray(
            [
                0x02,
                0x1C,
                0x07,
                0x12,
                0x37,
                0x32,
                0x29,
                0x2D,
                0x29,
                0x25,
                0x2B,
                0x39,
                0x00,
                0x01,
                0x03,
                0x10,
            ]
        )
        self._writecommand(cls.GMCTRP1)
        self._writedata(dataGMCTRP)
        dataGMCTRN = bytearray(
            [
                0x03,
                0x1D,
                0x07,
                0x06,
                0x2E,
                0x2C,
                0x29,
                0x2D,
                0x2E,
                0x2E,
                0x37,
                0x3F,
                0x00,
                0x00,
                0x02,
                0x10,
            ]
        )
        self._writecommand(cls.GMCTRN1)
        self._writedata(dataGMCTRN)
        time.sleep_us(10)
        self._writecommand(cls.CASET)
        self.windowLocData[0] = 0x00
        self.windowLocData[1] = 2
        self.windowLocData[2] = 0x00
        self.windowLocData[3] = self._size[0] - 1
        self._writedata(self.windowLocData)
        self._writecommand(cls.RASET)
        self.windowLocData[1] = 1
        self.windowLocData[3] = self._size[1] - 1
        self._writedata(self.windowLocData)
        self._writecommand(cls.NORON)
        time.sleep_us(10)
        self._writecommand(cls.RAMWR)
        time.sleep_us(500)
        self._writecommand(cls.DISPON)
        self.cs(1)
        time.sleep_us(500)

    def initr(self):
        cls = self.__class__
        self._reset()
        self._writecommand(cls.SWRESET)
        time.sleep_us(150)
        self._writecommand(cls.SLPOUT)
        time.sleep_us(500)
        data3 = bytearray([0x01, 0x2C, 0x2D])
        self._writecommand(cls.FRMCTR1)
        self._writedata(data3)
        self._writecommand(cls.FRMCTR2)
        self._writedata(data3)
        data6 = bytearray([0x01, 0x2C, 0x2D, 0x01, 0x2C, 0x2D])
        self._writecommand(cls.FRMCTR3)
        self._writedata(data6)
        time.sleep_us(10)
        data1 = bytearray(1)
        self._writecommand(cls.INVCTR)
        data1[0] = 0x07
        self._writedata(data1)
        self._writecommand(cls.PWCTR1)
        data3[0] = 0xA2
        data3[1] = 0x02
        data3[2] = 0x84
        self._writedata(data3)
        self._writecommand(cls.PWCTR2)
        data1[0] = 0xC5
        self._writedata(data1)
        data2 = bytearray(2)
        self._writecommand(cls.PWCTR3)
        data2[0] = 0x0A
        data2[1] = 0x00
        self._writedata(data2)
        self._writecommand(cls.PWCTR4)
        data2[0] = 0x8A
        data2[1] = 0x2A
        self._writedata(data2)
        self._writecommand(cls.PWCTR5)
        data2[0] = 0x8A
        data2[1] = 0xEE
        self._writedata(data2)
        self._writecommand(cls.VMCTR1)
        data1[0] = 0x0E
        self._writedata(data1)
        self._writecommand(cls.INVOFF)
        self._writecommand(cls.MADCTL)
        data1[0] = 0xC8
        self._writedata(data1)
        self._writecommand(cls.COLMOD)
        data1[0] = 0x05
        self._writedata(data1)
        self._writecommand(cls.CASET)
        self.windowLocData[0] = 0x00
        self.windowLocData[1] = 0x00
        self.windowLocData[2] = 0x00
        self.windowLocData[3] = self._size[0] - 1
        self._writedata(self.windowLocData)
        self._writecommand(cls.RASET)
        self.windowLocData[3] = self._size[1] - 1
        self._writedata(self.windowLocData)
        dataGMCTRP = bytearray(
            [
                0x0F,
                0x1A,
                0x0F,
                0x18,
                0x2F,
                0x28,
                0x20,
                0x22,
                0x1F,
                0x1B,
                0x23,
                0x37,
                0x00,
                0x07,
                0x02,
                0x10,
            ]
        )
        self._writecommand(cls.GMCTRP1)
        self._writedata(dataGMCTRP)
        dataGMCTRN = bytearray(
            [
                0x0F,
                0x1B,
                0x0F,
                0x17,
                0x33,
                0x2C,
                0x29,
                0x2E,
                0x30,
                0x30,
                0x39,
                0x3F,
                0x00,
                0x07,
                0x03,
                0x10,
            ]
        )
        self._writecommand(cls.GMCTRN1)
        self._writedata(dataGMCTRN)
        time.sleep_us(10)
        self._writecommand(cls.DISPON)
        time.sleep_us(100)
        self._writecommand(cls.NORON)
        time.sleep_us(10)
        self.cs(1)

    def initb2(self):
        cls = self.__class__
        self._size = (ScreenSize[0] + 2, ScreenSize[1] + 1)
        self._offset[0] = 2
        self._offset[1] = 1
        self._reset()
        self._writecommand(cls.SWRESET)
        time.sleep_us(50)
        self._writecommand(cls.SLPOUT)
        time.sleep_us(500)
        data3 = bytearray([0x01, 0x2C, 0x2D])
        self._writecommand(cls.FRMCTR1)
        self._writedata(data3)
        time.sleep_us(10)
        self._writecommand(cls.FRMCTR2)
        self._writedata(data3)
        time.sleep_us(10)
        self._writecommand(cls.FRMCTR3)
        self._writedata(data3)
        time.sleep_us(10)
        self._writecommand(cls.INVCTR)
        data1 = bytearray(1)
        data1[0] = 0x07
        self._writedata(data1)
        self._writecommand(cls.PWCTR1)
        data3[0] = 0xA2
        data3[1] = 0x02
        data3[2] = 0x84
        self._writedata(data3)
        time.sleep_us(10)
        self._writecommand(cls.PWCTR2)
        data1[0] = 0xC5
        self._writedata(data1)
        self._writecommand(cls.PWCTR3)
        data2 = bytearray(2)
        data2[0] = 0x0A
        data2[1] = 0x00
        self._writedata(data2)
        self._writecommand(cls.PWCTR4)
        data2[0] = 0x8A
        data2[1] = 0x2A
        self._writedata(data2)
        self._writecommand(cls.PWCTR5)
        data2[0] = 0x8A
        data2[1] = 0xEE
        self._writedata(data2)
        self._writecommand(cls.VMCTR1)
        data1[0] = 0x0E
        self._writedata(data1)
        time.sleep_us(10)
        self._writecommand(cls.MADCTL)
        data1[0] = 0xC8
        self._writedata(data1)
        dataGMCTRP = bytearray(
            [
                0x02,
                0x1C,
                0x07,
                0x12,
                0x37,
                0x32,
                0x29,
                0x2D,
                0x29,
                0x25,
                0x2B,
                0x39,
                0x00,
                0x01,
                0x03,
                0x10,
            ]
        )
        self._writecommand(cls.GMCTRP1)
        self._writedata(dataGMCTRP)
        dataGMCTRN = bytearray(
            [
                0x03,
                0x1D,
                0x07,
                0x06,
                0x2E,
                0x2C,
                0x29,
                0x2D,
                0x2E,
                0x2E,
                0x37,
                0x3F,
                0x00,
                0x00,
                0x02,
                0x10,
            ]
        )
        self._writecommand(cls.GMCTRN1)
        self._writedata(dataGMCTRN)
        time.sleep_us(10)
        self._writecommand(cls.CASET)
        self.windowLocData[0] = 0x00
        self.windowLocData[1] = 0x02
        self.windowLocData[2] = 0x00
        self.windowLocData[3] = self._size[0] - 1
        self._writedata(self.windowLocData)
        self._writecommand(cls.RASET)
        self.windowLocData[1] = 0x01
        self.windowLocData[3] = self._size[1] - 1
        self._writedata(self.windowLocData)
        data1 = bytearray(1)
        self._writecommand(cls.COLMOD)
        data1[0] = 0x05
        self._writedata(data1)
        time.sleep_us(10)
        self._writecommand(cls.NORON)
        time.sleep_us(10)
        self._writecommand(cls.RAMWR)
        time.sleep_us(500)
        self._writecommand(cls.DISPON)
        self.cs(1)
        time.sleep_us(500)

    def initg(self):
        cls = self.__class__
        self._reset()
        self._writecommand(cls.SWRESET)
        time.sleep_us(150)
        self._writecommand(cls.SLPOUT)
        time.sleep_us(255)
        data3 = bytearray([0x01, 0x2C, 0x2D])
        self._writecommand(cls.FRMCTR1)
        self._writedata(data3)
        self._writecommand(cls.FRMCTR2)
        self._writedata(data3)
        data6 = bytearray([0x01, 0x2C, 0x2D, 0x01, 0x2C, 0x2D])
        self._writecommand(cls.FRMCTR3)
        self._writedata(data6)
        time.sleep_us(10)
        self._writecommand(cls.INVCTR)
        self._writedata(bytearray([0x07]))
        self._writecommand(cls.PWCTR1)
        data3[0] = 0xA2
        data3[1] = 0x02
        data3[2] = 0x84
        self._writedata(data3)
        self._writecommand(cls.PWCTR2)
        self._writedata(bytearray([0xC5]))
        data2 = bytearray(2)
        self._writecommand(cls.PWCTR3)
        data2[0] = 0x0A
        data2[1] = 0x00
        self._writedata(data2)
        self._writecommand(cls.PWCTR4)
        data2[0] = 0x8A
        data2[1] = 0x2A
        self._writedata(data2)
        self._writecommand(cls.PWCTR5)
        data2[0] = 0x8A
        data2[1] = 0xEE
        self._writedata(data2)
        self._writecommand(cls.VMCTR1)
        self._writedata(bytearray([0x0E]))
        self._writecommand(cls.INVOFF)
        self._setMADCTL()
        self._writecommand(cls.COLMOD)
        self._writedata(bytearray([0x05]))
        self._writecommand(cls.CASET)
        self.windowLocData[0] = 0x00
        self.windowLocData[1] = 0x01
        self.windowLocData[2] = 0x00
        self.windowLocData[3] = self._size[0] - 1
        self._writedata(self.windowLocData)
        self._writecommand(cls.RASET)
        self.windowLocData[3] = self._size[1] - 1
        self._writedata(self.windowLocData)
        dataGMCTRP = bytearray(
            [
                0x02,
                0x1C,
                0x07,
                0x12,
                0x37,
                0x32,
                0x29,
                0x2D,
                0x29,
                0x25,
                0x2B,
                0x39,
                0x00,
                0x01,
                0x03,
                0x10,
            ]
        )
        self._writecommand(cls.GMCTRP1)
        self._writedata(dataGMCTRP)
        dataGMCTRN = bytearray(
            [
                0x03,
                0x1D,
                0x07,
                0x06,
                0x2E,
                0x2C,
                0x29,
                0x2D,
                0x2E,
                0x2E,
                0x37,
                0x3F,
                0x00,
                0x00,
                0x02,
                0x10,
            ]
        )
        self._writecommand(cls.GMCTRN1)
        self._writedata(dataGMCTRN)
        self._writecommand(cls.NORON)
        time.sleep_us(10)
        self._writecommand(cls.DISPON)
        time.sleep_us(100)
        self.cs(1)
