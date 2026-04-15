"""
ST7796S LCD driver for MicroPython
Based on ST7796S C driver ported to MicroPython
Supports SPI interface with optional touchscreen
"""

import utime as time
import struct
from machine import Pin, SPI

# ST7796S Command Codes
ST7796S_NOP = 0x00
ST7796S_SWRESET = 0x01
ST7796S_RDDID = 0x04
ST7796S_RDDST = 0x09
ST7796S_RDMODE = 0x0A
ST7796S_RDMADCTL = 0x0B
ST7796S_RDPIXFMT = 0x0C
ST7796S_RDIMGFMT = 0x0D
ST7796S_RDSELFDIAG = 0x0F
ST7796S_SLPIN = 0x10
ST7796S_SLPOUT = 0x11
ST7796S_PTLON = 0x12
ST7796S_NORON = 0x13
ST7796S_INVOFF = 0x20
ST7796S_INVON = 0x21
ST7796S_DISPOFF = 0x28
ST7796S_DISPON = 0x29
ST7796S_CASET = 0x2A
ST7796S_PASET = 0x2B
ST7796S_RAMWR = 0x2C
ST7796S_RAMRD = 0x2E
ST7796S_PTLAR = 0x30
ST7796S_VSCRDEF = 0x33
ST7796S_MADCTL = 0x36
ST7796S_VSCRSADD = 0x37
ST7796S_PIXFMT = 0x3A
ST7796S_RGB_INTERFACE = 0xB0
ST7796S_FRMCTR1 = 0xB1
ST7796S_FRMCTR2 = 0xB2
ST7796S_FRMCTR3 = 0xB3
ST7796S_INVCTR = 0xB4
ST7796S_DFUNCTR = 0xB6
ST7796S_PWCTR1 = 0xC0
ST7796S_PWCTR2 = 0xC1
ST7796S_PWCTR3 = 0xC2
ST7796S_PWCTR4 = 0xC3
ST7796S_PWCTR5 = 0xC4
ST7796S_VMCTR1 = 0xC5
ST7796S_RDID1 = 0xDA
ST7796S_RDID2 = 0xDB
ST7796S_RDID3 = 0xDC
ST7796S_RDID4 = 0xDD
ST7796S_GMCTRP1 = 0xE0
ST7796S_GMCTRN1 = 0xE1
ST7796S_DGCTR1 = 0xE2
ST7796S_DGCTR2 = 0xE3

# Color mode definitions
ST7796S_MAD_RGB = 0x08
ST7796S_MAD_BGR = 0x00
ST7796S_MAD_VERTICAL = 0x20
ST7796S_MAD_X_LEFT = 0x00
ST7796S_MAD_X_RIGHT = 0x40
ST7796S_MAD_Y_UP = 0x80
ST7796S_MAD_Y_DOWN = 0x00

# Configuration
ST7796S_INTERFACE_MODE = 1  # SPI mode
ST7796S_ORIENTATION = 0     # 0: portrait, 1: landscape
ST7796S_COLORMODE = 0       # 0: RGB565, 1: BGR565
ST7796S_INITCLEAR = 1       # Clear on init
ST7796S_TOUCH = 1           # Enable touchscreen
ST7796S_MULTITASK_MUTEX = 0 # No mutex

# Touchscreen calibration data
TS_CINDEX = {
    0: [-76088, -83042, 151, 964366, 240, -84004, 1327176],
    1: [-76088, 240, -84004, 1327176, 83042, -151, -25236438],
    2: [-76088, 83042, -151, -25236438, -240, 84004, -37773328],
    3: [-76088, -240, 84004, -37773328, -83042, 151, 964366],
}

# Physical resolution
ST7796S_LCD_PIXEL_WIDTH = 320
ST7796S_LCD_PIXEL_HEIGHT = 480

# Derived values for orientation 0 (portrait)
if ST7796S_ORIENTATION == 0:
    ST7796S_SIZE_X = ST7796S_LCD_PIXEL_WIDTH
    ST7796S_SIZE_Y = ST7796S_LCD_PIXEL_HEIGHT
    ST7796S_MAD_DATA_RIGHT_THEN_UP = ST7796S_MAD_RGB | ST7796S_MAD_X_RIGHT | ST7796S_MAD_Y_UP
    ST7796S_MAD_DATA_RIGHT_THEN_DOWN = ST7796S_MAD_RGB | ST7796S_MAD_X_RIGHT | ST7796S_MAD_Y_DOWN
    ST7796S_MAD_DATA_RGBMODE = ST7796S_MAD_RGB | ST7796S_MAD_X_LEFT | ST7796S_MAD_Y_DOWN
elif ST7796S_ORIENTATION == 1:
    ST7796S_SIZE_X = ST7796S_LCD_PIXEL_HEIGHT
    ST7796S_SIZE_Y = ST7796S_LCD_PIXEL_WIDTH
    ST7796S_MAD_DATA_RIGHT_THEN_UP = ST7796S_MAD_RGB | ST7796S_MAD_X_RIGHT | ST7796S_MAD_Y_DOWN | ST7796S_MAD_VERTICAL
    ST7796S_MAD_DATA_RIGHT_THEN_DOWN = ST7796S_MAD_RGB | ST7796S_MAD_X_LEFT | ST7796S_MAD_Y_DOWN | ST7796S_MAD_VERTICAL
    ST7796S_MAD_DATA_RGBMODE = ST7796S_MAD_RGB | ST7796S_MAD_X_RIGHT | ST7796S_MAD_Y_DOWN


class ST7796S:
    """ST7796S LCD Display Driver"""
    
    def __init__(self, spi, cs_pin, dc_pin, rst_pin=None, backlight_pin=None):
        """
        Initialize ST7796S display
        
        Args:
            spi: SPI bus instance
            cs_pin: Chip select pin (CS)
            dc_pin: Data/Command pin (DC)
            rst_pin: Reset pin (optional)
            backlight_pin: Backlight control pin (optional)
        """
        self.spi = spi
        self.cs = Pin(cs_pin, Pin.OUT, value=1)
        self.dc = Pin(dc_pin, Pin.OUT, value=0)
        self.rst = Pin(rst_pin, Pin.OUT, value=1) if rst_pin is not None else None
        self.bl = Pin(backlight_pin, Pin.OUT, value=1) if backlight_pin is not None else None
        
        self.is_initialized = False
        self.y_start = 0
        self.y_end = 0
    
    def _reset(self):
        """Reset display"""
        if self.rst:
            self.rst.off()
            time.sleep_ms(10)
            self.rst.on()
            time.sleep_ms(120)
    
    def _write_cmd(self, cmd):
        """Write command byte"""
        self.dc.off()
        self.cs.off()
        self.spi.write(bytes([cmd]))
        self.cs.on()
    
    def _write_data(self, data):
        """Write data bytes"""
        self.dc.on()
        self.cs.off()
        if isinstance(data, int):
            self.spi.write(bytes([data]))
        else:
            self.spi.write(data)
        self.cs.on()
    
    def _write_cmd_data(self, cmd, data):
        """Write command followed by data"""
        self._write_cmd(cmd)
        self._write_data(data)
    
    def _write_data16(self, value):
        """Write 16-bit data value"""
        self._write_data(bytes([(value >> 8) & 0xFF, value & 0xFF]))
    
    def init(self):
        """Initialize the display"""
        if self.is_initialized:
            return
        
        self._reset()
        time.sleep_ms(1)
        
        self._write_cmd(ST7796S_SWRESET)
        time.sleep_ms(5)
        
        # Command Set Control - enable command 2 part I
        self._write_cmd_data(0xF0, bytes([0xC3]))
        # Command Set Control - enable command 2 part II
        self._write_cmd_data(0xF0, bytes([0x96]))
        
        self._write_cmd_data(ST7796S_MADCTL, bytes([0x68]))
        self._write_cmd_data(ST7796S_PIXFMT, bytes([0x05]))
        
        # Interface Mode Control
        self._write_cmd_data(0xB0, bytes([0x80]))
        # Display Function Control
        self._write_cmd_data(0xB6, bytes([0x20, 0x02]))
        # Blanking Porch Control
        self._write_cmd_data(0xB5, bytes([0x02, 0x03, 0x00, 0x04]))
        
        # Frame Control
        self._write_cmd_data(ST7796S_FRMCTR1, bytes([0x80, 0x10]))
        
        # Display Inversion Control
        self._write_cmd_data(ST7796S_INVCTR, bytes([0x00]))
        
        # Entry Mode Set
        self._write_cmd_data(0xB7, bytes([0xC6]))
        
        # VCOM Control
        self._write_cmd_data(ST7796S_VMCTR1, bytes([0x24]))
        self._write_cmd_data(0xE4, bytes([0x31]))
        
        # Display Output Control Adjust
        self._write_cmd_data(0xE8, bytes([0x40, 0x8A, 0x00, 0x00, 0x29, 0x19, 0xA5, 0x33]))
        
        # Power Control
        self._write_cmd_data(ST7796S_PWCTR3, bytes([0xA7]))
        
        # Positive gamma control
        self._write_cmd_data(ST7796S_GMCTRP1, bytes([0xF0, 0x09, 0x13, 0x12, 0x12, 0x2B, 0x3C, 0x44, 0x4B, 0x1B, 0x18, 0x17, 0x1D, 0x21]))
        
        # Negative gamma control
        self._write_cmd_data(ST7796S_GMCTRN1, bytes([0xF0, 0x09, 0x13, 0x0C, 0x0D, 0x27, 0x3B, 0x44, 0x4D, 0x0B, 0x17, 0x17, 0x1D, 0x21]))
        
        self._write_cmd(ST7796S_MADCTL)
        self._write_data(ST7796S_MAD_DATA_RIGHT_THEN_DOWN)
        
        # Command Set Control - disable command 2
        self._write_cmd_data(0xF0, bytes([0xC3]))
        self._write_cmd_data(0xF0, bytes([0x69]))
        
        # Display on sequence
        self._write_cmd(ST7796S_NORON)
        self._write_cmd(ST7796S_INVOFF)
        self._write_cmd(ST7796S_SLPOUT)
        time.sleep_ms(200)
        self._write_cmd(ST7796S_DISPON)
        time.sleep_ms(10)
        
        # Clear screen
        self.fill_rect(0, 0, ST7796S_SIZE_X, ST7796S_SIZE_Y, 0x0000)
        
        self.is_initialized = True
    
    def display_on(self):
        """Turn display on"""
        self._write_cmd(ST7796S_SLPOUT)
        if self.bl:
            self.bl.on()
    
    def display_off(self):
        """Turn display off"""
        if self.bl:
            self.bl.off()
        self._write_cmd(ST7796S_SLPIN)
    
    def get_width(self):
        """Get display width in current orientation"""
        return ST7796S_SIZE_X
    
    def get_height(self):
        """Get display height in current orientation"""
        return ST7796S_SIZE_Y
    
    def read_id(self):
        """Read display ID"""
        # Read 3 bytes starting from 0xD3
        self._write_cmd(0xD3)
        self.dc.on()
        self.cs.off()
        data = self.spi.read(3)
        self.cs.on()
        
        id_val = (data[0] << 16) | (data[1] << 8) | data[2]
        if id_val == 0x869400:
            return 0x9486
        return 0
    
    def set_cursor(self, x, y):
        """Set cursor position"""
        self._set_display_window(x, y, 1, 1)
    
    def write_pixel(self, x, y, color):
        """Write a single pixel"""
        self.set_cursor(x, y)
        self._write_cmd(ST7796S_RAMWR)
        self._write_data16(color)
    
    def read_pixel(self, x, y):
        """Read a single pixel"""
        self._write_cmd_data(ST7796S_PIXFMT, bytes([0x66]))  # 24-bit mode
        self.set_cursor(x, y)
        self._write_cmd(ST7796S_RAMRD)
        self.dc.on()
        self.cs.off()
        data = self.spi.read(3)
        self.cs.on()
        self._write_cmd_data(ST7796S_PIXFMT, bytes([0x55]))  # Back to 16-bit
        
        # Convert 24-bit to 16-bit RGB565
        r = (data[0] >> 3) & 0x1F
        g = ((data[1] >> 2) & 0x3F)
        b = (data[2] >> 3) & 0x1F
        return (r << 11) | (g << 5) | b
    
    def _set_display_window(self, x, y, width, height):
        """Set display window"""
        self.y_start = y
        self.y_end = y + height - 1
        
        self._write_cmd(ST7796S_CASET)
        self._write_data16(x)
        self._write_data16(x + width - 1)
        
        self._write_cmd(ST7796S_PASET)
        self._write_data16(y)
        self._write_data16(y + height - 1)
    
    def draw_hline(self, x, y, length, color):
        """Draw horizontal line"""
        self._set_display_window(x, y, length, 1)
        self._write_cmd(ST7796S_RAMWR)
        
        # Write color repeated
        color_bytes = bytes([(color >> 8) & 0xFF, color & 0xFF])
        self.dc.on()
        self.cs.off()
        for _ in range(length):
            self.spi.write(color_bytes)
        self.cs.on()
    
    def draw_vline(self, x, y, length, color):
        """Draw vertical line"""
        self._set_display_window(x, y, 1, length)
        self._write_cmd(ST7796S_RAMWR)
        
        # Write color repeated
        color_bytes = bytes([(color >> 8) & 0xFF, color & 0xFF])
        self.dc.on()
        self.cs.off()
        for _ in range(length):
            self.spi.write(color_bytes)
        self.cs.on()
    
    def fill_rect(self, x, y, width, height, color):
        """Fill rectangle with color"""
        self._set_display_window(x, y, width, height)
        self._write_cmd(ST7796S_RAMWR)
        
        # Write color repeated for all pixels
        color_bytes = bytes([(color >> 8) & 0xFF, color & 0xFF])
        self.dc.on()
        self.cs.off()
        for _ in range(width * height):
            self.spi.write(color_bytes)
        self.cs.on()
    
    def draw_image(self, x, y, width, height, image_data):
        """Draw RGB image"""
        self._set_display_window(x, y, width, height)
        self._write_cmd(ST7796S_RAMWR)
        self._write_data(image_data)
    
    def read_image(self, x, y, width, height):
        """Read RGB image from display"""
        self._set_display_window(x, y, width, height)
        self._write_cmd_data(ST7796S_PIXFMT, bytes([0x66]))  # 24-bit mode
        self._write_cmd(ST7796S_RAMRD)
        
        self.dc.on()
        self.cs.off()
        # Read 24-bit data and convert to 16-bit
        data = self.spi.read(width * height * 3)
        self.cs.on()
        
        self._write_cmd_data(ST7796S_PIXFMT, bytes([0x55]))  # Back to 16-bit
        
        result = bytearray(width * height * 2)
        for i in range(width * height):
            b_idx = i * 3
            r = (data[b_idx] >> 3) & 0x1F
            g = ((data[b_idx + 1] >> 2) & 0x3F)
            b = (data[b_idx + 2] >> 3) & 0x1F
            color = (r << 11) | (g << 5) | b
            result[i * 2] = (color >> 8) & 0xFF
            result[i * 2 + 1] = color & 0xFF
        
        return bytes(result)
    
    def scroll(self, offset, top_fix=0, bottom_fix=0):
        """Set display scroll parameters"""
        scroll_height = ST7796S_LCD_PIXEL_HEIGHT - top_fix - bottom_fix
        
        # Set scroll area
        self._write_cmd(ST7796S_VSCRDEF)
        self._write_data16(top_fix)
        self._write_data16(scroll_height)
        self._write_data16(bottom_fix)
        
        # Set scroll address
        scroll_addr = ((offset % scroll_height) + top_fix) & 0xFFFF
        self._write_cmd(ST7796S_VSCRSADD)
        self._write_data16(scroll_addr)
