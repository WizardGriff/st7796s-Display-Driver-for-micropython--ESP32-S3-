"""
ST7796S Display and XPT2046 Touchscreen Driver - MicroPython Conversion Guide
Converted from C drivers for ESP32-S3 with MicroPython

Usage Example:
"""

# Example usage of ST7796S and XPT2046 drivers

from machine import Pin, SPI
from libs.st7796s import ST7796S
from libs.xpt2046_touch import XPT2046
import time

# ============================================================================
# Display (ST7796S) Initialization and Usage
# ============================================================================

# Configure SPI bus (adjust pins for your ESP32-S3)
# SPI0 or SPI1 depending on your hardware configuration
spi_display = SPI(
    1,
    baudrate=40_000_000,  # 40 MHz for display
    polarity=0,
    phase=0,
    bits=8,
    firstbit=SPI.MSB,
    sck=Pin(14),      # SCK pin - adjust as needed
    mosi=Pin(13),     # MOSI pin - adjust as needed
    miso=Pin(12)      # MISO pin - adjust as needed
)

# Display control pins
display = ST7796S(
    spi=spi_display,
    cs_pin=10,        # CS pin
    dc_pin=9,         # DC (Data/Command) pin
    rst_pin=8,        # RST (Reset) pin - optional
    backlight_pin=11  # Backlight control pin - optional
)

# Initialize display
display.init()

# Display operations
display.display_on()
width = display.get_width()    # Get 320
height = display.get_height()  # Get 480

# Fill screen with black
display.fill_rect(0, 0, width, height, 0x0000)

# Fill rectangle with red
display.fill_rect(10, 10, 100, 100, 0xF800)

# Draw horizontal line in green
display.draw_hline(0, 50, 100, 0x07E0)

# Draw vertical line in blue
display.draw_vline(100, 0, 200, 0x001F)

# Write single pixel in white
display.write_pixel(160, 240, 0xFFFF)

# Read single pixel
color = display.read_pixel(160, 240)

# Draw image (assuming you have 320x480 RGB565 data)
# image_data = bytearray(320 * 480 * 2)  # RGB565 format
# display.draw_image(0, 0, 320, 480, image_data)

# Turn off display
display.display_off()

# ============================================================================
# Touchscreen (XPT2046) Initialization and Usage
# ============================================================================

# Configure SPI bus for touchscreen (can be same or different from display)
# For touchscreen, use lower speed: ~1-2 MHz
spi_touch = SPI(
    1,
    baudrate=1_000_000,  # 1 MHz for touchscreen
    polarity=0,
    phase=0,
    bits=8,
    firstbit=SPI.MSB,
    sck=Pin(14),    # SCK pin
    mosi=Pin(13),   # MOSI pin
    miso=Pin(12)    # MISO pin
)

# Initialize touchscreen
touch = XPT2046(
    spi=spi_touch,
    cs_pin=15,      # Touch CS pin
    irq_pin=2,      # Touch IRQ pin (interrupt) - optional
    clk_pin=14,     # For software SPI mode
    mosi_pin=13,    # For software SPI mode
    miso_pin=12     # For software SPI mode
)

touch.init()

# Touch detection and reading
while True:
    # Method 1: Detect touch via IRQ pin
    if touch.detect_touch():
        # Read and average coordinates twice for stability
        x, y = touch.get_xy()
        z = touch.get_z()  # Pressure reading
        
        print(f"Touch detected - X: {x}, Y: {y}, Pressure: {z}")
    
    # Method 2: Direct update with validation
    if touch.update():
        x, y = touch.get_xy()
        print(f"Touch valid - X: {x}, Y: {y}")
    
    time.sleep_ms(50)

# ============================================================================
# Combined Display and Touchscreen Example
# ============================================================================

def draw_filled_circle(display, cx, cy, radius, color):
    """Draw a filled circle (helper function)"""
    for y in range(-radius, radius + 1):
        for x in range(-radius, radius + 1):
            if x*x + y*y <= radius*radius:
                display.write_pixel(cx + x, cy + y, color)

def touch_draw_example():
    """Example: Draw on display where user touches"""
    # Clear display
    display.fill_rect(0, 0, display.get_width(), display.get_height(), 0x0000)
    
    while True:
        # Check for touch
        if touch.detect_touch():
            # Update touch coordinates
            if touch.update():
                x, y = touch.get_xy()
                
                # Map touch coordinates to display coordinates
                # (This requires calibration for actual hardware)
                # For this example, assuming 1:1 mapping
                screen_x = (x * display.get_width()) // 4095
                screen_y = (y * display.get_height()) // 4095
                
                # Draw small circle at touch point
                draw_filled_circle(display, screen_x, screen_y, 5, 0xF800)
                
                print(f"Drawing at: {screen_x}, {screen_y}")

# ============================================================================
# Display and Touch Information Functions
# ============================================================================

def print_display_info():
    """Print display information"""
    print(f"Display Width: {display.get_width()}")
    print(f"Display Height: {display.get_height()}")
    display_id = display.read_id()
    print(f"Display ID: {display_id}")

def read_touch_sample():
    """Read single touch sample"""
    # Read raw coordinates
    x_raw = touch.get_x()
    y_raw = touch.get_y()
    z1 = touch.get_z1()
    z2 = touch.get_z2()
    
    print(f"Raw X: {x_raw}, Raw Y: {y_raw}")
    print(f"Pressure Z1: {z1}, Z2: {z2}")
    
    # Read averaged coordinates
    if touch.update():
        x, y = touch.get_xy()
        print(f"Averaged X: {x}, Y: {y}")

# ============================================================================
# ERROR HANDLING AND NOTES
# ============================================================================

"""
IMPORTANT NOTES:

1. Pin Configuration:
   - Adjust pins (SCK, MOSI, MISO, CS, DC, RST) according to your ESP32-S3
   - You can find pin assignments in your specific board documentation
   
2. SPI Bus Speed:
   - Display: 20-40 MHz typically works well
   - Touchscreen: 0.5-2 MHz (slower clock required for XPT2046)
   
3. Touch Calibration:
   - Raw touch coordinates range: 0-4095
   - Must be calibrated/mapped to display coordinates
   - Calibration depends on touch controller orientation
   
4. Hardware Considerations:
   - Ensure proper power supply for both display and touchscreen
   - Add pull-up resistors if needed for CS pins
   - Use appropriate cable shielding for SPI signals
   
5. Performance:
   - Display drawing operations are blocking
   - Consider double-buffering for animation
   - Touchscreen reads are relatively fast at 1 MHz
   
6. Color Format:
   - Colors are in RGB565 format: (R:5bits G:6bits B:5bits)
   - Example: 0xF800 = Red, 0x07E0 = Green, 0x001F = Blue
   - White: 0xFFFF, Black: 0x0000

TROUBLESHOOTING:

- If display shows no image:
  * Check CS, DC pin connections
  * Verify SPI speed is not too high (try 10MHz)
  * Ensure RST pin is properly pulsed
  
- If touchscreen not responding:
  * Check CS and IRQ pin connections
  * Verify SPI speed is < 2 MHz for XPT2046
  * Test with direct coordinate reads
  
- For calibration issues:
  * Implement a proper calibration routine
  * Store calibration coefficients in flash
  * Use 3-5 point calibration for accuracy
"""

# ============================================================================
# Integration with your existing code
# ============================================================================

"""
To integrate these drivers with your existing C++ code patterns:

1. Replace C structures with Python classes
2. Use properties instead of getters/setters
3. Handle hardware abstraction through machine module
4. Adapt interrupts using micropython IRQ callbacks

Example integration pattern:

from libs.st7796s import ST7796S
from libs.xpt2046_touch import XPT2046

# In your main initialization
def init_display_system():
    # ... SPI configuration ...
    display = ST7796S(spi, cs, dc, rst, bl)
    touch = XPT2046(spi, cs, irq)
    display.init()
    touch.init()
    return display, touch

# In your main loop
def main_loop():
    while True:
        # Handle touch
        if touch.detect_touch():
            x, y = touch.get_xy()
            # Process touch input
        
        # Update display
        # Your display updates here
        
        time.sleep_ms(16)  # ~60 FPS
"""
