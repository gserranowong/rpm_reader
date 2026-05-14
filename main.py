from ST7735 import TFT
from sysfont import sysfont
from machine import SPI,Pin
import time
import math


def initLCD():
    spi = SPI(0, baudrate=20000000, polarity=0, phase=0, sck=Pin(2), mosi=Pin(3), miso=None)
    tft=TFT(spi,0,1,5)
    tft.initr()
    tft.invertcolor(True)
    tft.rgb(False)
    return tft




class Tools:

    def __init__(self):
        
        self.tft = initLCD()

        self.leds = [ Pin(n, Pin.OUT) for n in [22,26,27,28,21] ]
        self.sensor = Pin(20, Pin.IN)
        
        def handle_sensor_change(pin):
            self.leds[0].value(pin.value())
        self.sensor.irq(
            trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING,  # detect both edges
            handler=handle_sensor_change
        )

    def all_off(self):
        for l in self.leds:
                l.off()
                
    def all_on(self):
       for l in self.leds:
                l.on()     

tools = Tools()
