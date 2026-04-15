"""
XPT2046 Touchscreen Driver for MicroPython
Based on XPT2046 C driver ported to MicroPython
Supports SPI interface for touch input
"""

import utime as time
from machine import Pin, SPI

# SPI Commands
READ_X = 0xD0
READ_Y = 0x90
READ_Z1 = 0xB0
READ_Z2 = 0xC0
READ_TEMP1 = 0x80
READ_TEMP2 = 0xF0
CMD_POWER_DOWN = 0x00
CMD_POWER_UP = 0x01

# Configuration
TOUCH_SPI = 0  # 0 = Software SPI, 1-6 = Hardware SPI
TOUCH_SPI_MODE = 0  # 0 = Full duplex, 1 = Half duplex
TOUCH_SPI_SPD_WRITE = 0
TOUCH_SPI_SPD_READ = 0

# Touch detection parameters
TOUCHMINPRESSRC = 8192
TOUCHMAXPRESSRC = 4096
TOUCHMINPRESTRG = 0
TOUCHMAXPRESTRG = 255
TOUCH_FILTER = 8
COORD_ERR_RANGE = 10
UPDATE_Z_PRESSURE = 0

# Touchscreen calibration coefficients (orientation 0)
TS_CALIBRATION_COEFFS = [-76088, -83042, 151, 964366, 240, -84004, 1327176]


class XPT2046:
    """XPT2046 Touchscreen Driver"""
    
    def __init__(self, spi, cs_pin, irq_pin=None, clk_pin=None, mosi_pin=None, miso_pin=None):
        """
        Initialize XPT2046 touchscreen
        
        Args:
            spi: SPI bus instance (for hardware SPI mode)
            cs_pin: Chip select pin number
            irq_pin: Interrupt pin number (active low)
            clk_pin: Clock pin (for software SPI)
            mosi_pin: MOSI pin (for software SPI)
            miso_pin: MISO pin (for software SPI)
        """
        self.spi = spi
        self.cs = Pin(cs_pin, Pin.OUT, value=1)
        self.irq = Pin(irq_pin, Pin.IN) if irq_pin is not None else None
        
        # For software SPI
        self.clk = Pin(clk_pin, Pin.OUT, value=0) if clk_pin is not None else None
        self.mosi = Pin(mosi_pin, Pin.OUT, value=0) if mosi_pin is not None else None
        self.miso = Pin(miso_pin, Pin.IN) if miso_pin is not None else None
        
        # Global touch coordinates and pressure
        self.tx = 0
        self.ty = 0
        self.tz = 0
        
        self.is_initialized = False
    
    def init(self):
        """Initialize touchscreen"""
        if self.is_initialized:
            return
        
        # Calibration coefficients
        self.cal_coeffs = TS_CALIBRATION_COEFFS.copy()
        
        self.is_initialized = True
    
    def _software_spi_write_bit(self, bit):
        """Write a single bit via software SPI"""
        self.mosi.value(bit & 1)
        time.sleep_us(1)
        self.clk.on()
        time.sleep_us(1)
        self.clk.off()
        time.sleep_us(1)
    
    def _software_spi_read_bit(self):
        """Read a single bit via software SPI"""
        self.clk.on()
        time.sleep_us(1)
        bit = self.miso.value()
        time.sleep_us(1)
        self.clk.off()
        time.sleep_us(1)
        return bit
    
    def _software_spi_write_byte(self, byte):
        """Write a byte via software SPI"""
        for i in range(7, -1, -1):
            self._software_spi_write_bit((byte >> i) & 1)
    
    def _software_spi_read_byte(self):
        """Read a byte via software SPI"""
        byte = 0
        for i in range(8):
            byte = (byte << 1) | self._software_spi_read_bit()
        return byte
    
    def _spi_write(self, data):
        """Write data via SPI"""
        if TOUCH_SPI == 0 and self.mosi is not None:
            # Software SPI
            for byte in data:
                self._software_spi_write_byte(byte)
        else:
            # Hardware SPI
            self.spi.write(data)
    
    def _spi_read(self, size):
        """Read data via SPI"""
        if TOUCH_SPI == 0 and self.miso is not None:
            # Software SPI - read bytes
            data = bytearray(size)
            for i in range(size):
                data[i] = self._software_spi_read_byte()
            return bytes(data)
        else:
            # Hardware SPI
            return self.spi.read(size)
    
    def _read_cmd_12bit(self, cmd):
        """Read 12-bit value from command"""
        self.cs.off()
        time.sleep_us(10)
        
        self._spi_write(bytes([cmd]))
        
        # Read 2 bytes
        rx_data = self._spi_read(2)
        
        time.sleep_us(10)
        self.cs.on()
        
        # Convert to 12-bit value
        value = (rx_data[0] << 5) | (rx_data[1] >> 3)
        return value
    
    def get_x(self):
        """Read X coordinate"""
        return self._read_cmd_12bit(READ_X)
    
    def get_y(self):
        """Read Y coordinate"""
        return self._read_cmd_12bit(READ_Y)
    
    def get_z1(self):
        """Read Z1 pressure"""
        return self._read_cmd_12bit(READ_Z1)
    
    def get_z2(self):
        """Read Z2 pressure"""
        return self._read_cmd_12bit(READ_Z2)
    
    def update_z(self):
        """Update Z-coefficient (pressure reading)"""
        z1 = self.get_z1()
        z2 = self.get_z2()
        x = self.get_x()
        
        if z1 > 0:
            # Z-coefficient calculation
            self.tz = x * ((z2 // z1) - 1)
        else:
            self.tz = 0
    
    def read_xy(self):
        """
        Read X,Y coordinates twice and verify consistency
        Returns tuple (x, y) or (None, None) if readings don't match
        """
        x1 = self.get_x()
        y1 = self.get_y()
        x2 = self.get_x()
        y2 = self.get_y()
        
        # Check if readings are within acceptable range
        x_valid = (x2 <= x1 and x1 < x2 + COORD_ERR_RANGE) or \
                  (x1 <= x2 and x2 < x1 + COORD_ERR_RANGE)
        y_valid = (y2 <= y1 and y1 < y2 + COORD_ERR_RANGE) or \
                  (y1 <= y2 and y2 < y1 + COORD_ERR_RANGE)
        
        if x_valid and y_valid:
            x = (x1 + x2) // 2
            y = (y1 + y2) // 2
            return (x, y)
        else:
            return (None, None)
    
    def get_xy(self):
        """Get last read X,Y coordinates"""
        return (self.tx, self.ty)
    
    def get_z(self):
        """Get last read Z pressure"""
        return self.tz
    
    def update(self):
        """
        Update touch detection
        Returns 1 if touch detected and reading is valid, 0 otherwise
        """
        x, y = self.read_xy()
        if x is not None and y is not None:
            self.tx = x
            self.ty = y
            if UPDATE_Z_PRESSURE:
                self.update_z()
            return 1
        return 0
    
    def detect_touch(self):
        """
        Detect if touch is present
        Returns 1 if touch detected, 0 otherwise
        """
        if self.irq is None:
            return 1  # Assume touch if no IRQ pin
        
        # IRQ is active low
        if self.irq.value():
            return 0  # No touch
        
        # Touch detected
        if UPDATE_Z_PRESSURE:
            self.update_z()
        
        return 1
    
    def calibrate(self, reference_points=None):
        """
        Calibrate touchscreen using reference points
        reference_points: list of tuples [(touch_x, touch_y, screen_x, screen_y), ...]
        """
        if reference_points is None or len(reference_points) < 3:
            # Use default calibration
            return
        
        # This is a simplified calibration - in production use proper calibration algorithm
        # For now, we'll store the points and calculate linear transformation
        self.cal_points = reference_points
    
    def get_calibrated_xy(self):
        """Get calibrated X,Y coordinates"""
        # For now, return raw values
        # Implement proper calibration transformation here if needed
        return (self.tx, self.ty)


class TouchCalibration:
    """Simple touch screen calibration helper"""
    
    @staticmethod
    def apply_calibration(raw_x, raw_y, coefficients):
        """
        Apply calibration coefficients to raw touch coordinates
        Using affine transformation: X' = a*X + b*Y + c, Y' = d*X + e*Y + f
        
        Args:
            raw_x: Raw X coordinate
            raw_y: Raw Y coordinate
            coefficients: Calibration coefficients [a, b, c, d, e, f, ...]
        
        Returns:
            Tuple (calibrated_x, calibrated_y)
        """
        if len(coefficients) < 7:
            return (raw_x, raw_y)
        
        a, b, c, d, e, f, g = coefficients[0:7]
        
        # Apply affine transformation
        cal_x = (a * raw_x + b * raw_y + c) // g if g != 0 else raw_x
        cal_y = (d * raw_x + e * raw_y + f) // g if g != 0 else raw_y
        
        return (cal_x, cal_y)
    
    @staticmethod
    def create_calibration_points():
        """Create standard calibration points for testing"""
        # 4-point calibration: top-left, top-right, bottom-left, bottom-right
        # Each tuple: (touch_x, touch_y, screen_x, screen_y)
        return [
            (50, 50, 20, 20),
            (1000, 50, 300, 20),
            (50, 950, 20, 460),
            (1000, 950, 300, 460),
        ]
