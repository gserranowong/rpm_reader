from ST7735 import TFT
from ST7735 import ScreenSize
from sysfont import sysfont
from sysfont import load_font
from machine import SPI,Pin
import time
import math
from vec2 import Vec2




def InitializeLCDHardware():
    spi = SPI(0, baudrate=20000000, polarity=0, phase=0, sck=Pin(2), mosi=Pin(3), miso=None)
    tft=TFT(spi,0,1,5)
    tft.set_render_landscape(True)
    tft.initr()
    tft.invertcolor(True)
    tft.rgb(False)
    return tft



class Tools:

    def __init__(self):
        
        self.tft = InitializeLCDHardware()

        self.leds = [ Pin(n, Pin.OUT) for n in [22,26,27,28,21] ]
        self.sensor = Pin(20, Pin.IN)
        self.rpm_input = self.sensor.value()
        self.enable = False
        self.start = time.ticks_ms() # get millisecond counter
        self.delta = 0
        self.writer = LCDScreenWriter(self.tft)
       
        
        def handle_sensor_change(pin):
            if self.enable:
                current_time = time.ticks_ms()
                self.delta = time.ticks_diff(current_time, self.start)
                self.start = current_time
                self.rpm_input = pin.value()
                self.leds[0].toggle()
            else:
                self.rmp_input = False
            
        self.sensor.irq(
                trigger=Pin.IRQ_FALLING,  # detect both edges
                handler=handle_sensor_change
            )
    def all_off(self):
        for l in self.leds:
                l.off()
                
    def all_on(self):
       for l in self.leds:
                l.on()
    def enable_sensor(self, enable=True):
        self.enable = enable

class LCDScreenWriter:
    
    def __init__(self, tft: TFT):
        self.tft = tft
        self.font = load_font("Tiny5-Regular.8x8")

    
    def write(self,s):
        midPoint = ScreenSize.trans() / 2

        self.tft.fill(TFT.WHITE)
        self.tft.text(midPoint-Vec2(50,10), s, TFT.GOLD, self.font, 2)
        self.tft.render()
        
def __main__():
    
    
    with open("goldenlumy.logo", "rb") as f:
        data = f.read()    
    
    
    def init_lcd(tools):
        tools.writer.write("Golden Lumy")

    
    tools = Tools()
    init_lcd(tools)
    
    time.sleep(1)
    
    tools.enable_sensor()
    
    while True:
        
        time.sleep_ms(300)
        rpm = (1000.0/tools.delta)*60 if tools.delta != 0 else 0
        tools.writer.write(f"D: {tools.delta} ms RPM: {int(rpm)}")

