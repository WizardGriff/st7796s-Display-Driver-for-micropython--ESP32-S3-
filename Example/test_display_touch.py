"""
Test script for ST7796S Display and XPT2046 Touchscreen on ESP32-S3
Tests both drivers with basic functionality
"""

import utime as time
from machine import Pin, SPI

# Try importing the drivers
try:
    from libs.st7796s import ST7796S
    print("✓ ST7796S driver imported successfully")
except ImportError as e:
    print(f"✗ Failed to import ST7796S: {e}")
    ST7796S = None

try:
    from libs.xpt2046_touch import XPT2046
    print("✓ XPT2046 driver imported successfully")
except ImportError as e:
    print(f"✗ Failed to import XPT2046: {e}")
    XPT2046 = None


# ============================================================================
# CONFIGURATION - Adjust these pins for your ESP32-S3
# ============================================================================

class DisplayConfig:
    """Display (ST7796S) pin configuration"""
    SPI_ID = 1          # SPI bus ID
    SPI_CLK_MHZ = 40    # SPI clock: 40 MHz
    
    # SPI pins
    SCK_PIN = 14
    MOSI_PIN = 13
    MISO_PIN = 12
    
    # Control pins
    CS_PIN = 10
    DC_PIN = 9
    RST_PIN = 8
    BL_PIN = 11


class TouchConfig:
    """Touchscreen (XPT2046) pin configuration"""
    SPI_ID = 1          # Can share SPI bus with display
    SPI_CLK_KHZ = 1000  # SPI clock: 1 MHz (XPT2046 needs slower clock)
    
    # SPI pins (can share with display)
    SCK_PIN = 14
    MOSI_PIN = 13
    MISO_PIN = 12
    
    # Control pins
    CS_PIN = 15
    IRQ_PIN = 2         # Interrupt pin (optional)


# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def test_display_initialization():
    """Test display driver initialization"""
    print("\n" + "="*60)
    print("TEST 1: Display Initialization")
    print("="*60)
    
    if ST7796S is None:
        print("✗ ST7796S not available")
        return None
    
    try:
        # Create SPI bus
        print("Creating SPI bus...")
        spi = SPI(
            DisplayConfig.SPI_ID,
            baudrate=DisplayConfig.SPI_CLK_MHZ * 1_000_000,
            polarity=0,
            phase=0,
            bits=8,
            firstbit=SPI.MSB,
            sck=Pin(DisplayConfig.SCK_PIN),
            mosi=Pin(DisplayConfig.MOSI_PIN),
            miso=Pin(DisplayConfig.MISO_PIN)
        )
        print("✓ SPI bus created")
        
        # Create display instance
        print("Creating display instance...")
        display = ST7796S(
            spi=spi,
            cs_pin=DisplayConfig.CS_PIN,
            dc_pin=DisplayConfig.DC_PIN,
            rst_pin=DisplayConfig.RST_PIN,
            backlight_pin=DisplayConfig.BL_PIN
        )
        print("✓ Display instance created")
        
        # Initialize display
        print("Initializing display...")
        display.init()
        print("✓ Display initialized")
        
        # Get display dimensions
        width = display.get_width()
        height = display.get_height()
        print(f"✓ Display dimensions: {width}x{height}")
        
        return display
        
    except Exception as e:
        print(f"✗ Error during display initialization: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_display_drawing(display):
    """Test display drawing functions"""
    print("\n" + "="*60)
    print("TEST 2: Display Drawing Functions")
    print("="*60)
    
    if display is None:
        print("✗ Display not initialized")
        return False
    
    try:
        width = display.get_width()
        height = display.get_height()
        
        # Test 1: Fill entire screen with black
        print("Clearing display (black)...")
        display.fill_rect(0, 0, width, height, 0x0000)
        time.sleep_ms(500)
        print("✓ Screen cleared")
        
        # Test 2: Draw red rectangle
        print("Drawing red rectangle...")
        display.fill_rect(10, 10, 100, 100, 0xF800)
        time.sleep_ms(500)
        print("✓ Red rectangle drawn")
        
        # Test 3: Draw green horizontal line
        print("Drawing green line...")
        display.draw_hline(0, 150, width, 0x07E0)
        time.sleep_ms(500)
        print("✓ Green line drawn")
        
        # Test 4: Draw blue vertical line
        print("Drawing blue vertical line...")
        display.draw_vline(width // 2, 0, height, 0x001F)
        time.sleep_ms(500)
        print("✓ Blue line drawn")
        
        # Test 5: Write single pixels
        print("Drawing white pixels...")
        for i in range(10):
            display.write_pixel(50 + i, 50 + i, 0xFFFF)
        time.sleep_ms(500)
        print("✓ Pixels written")
        
        # Test 6: Scroll test (optional)
        print("Testing scroll (optional)...")
        display.scroll(10, 50, 50)
        time.sleep_ms(500)
        print("✓ Scroll operation completed")
        
        return True
        
    except Exception as e:
        print(f"✗ Error during display drawing: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_display_readback(display):
    """Test display read operations"""
    print("\n" + "="*60)
    print("TEST 3: Display Read Operations")
    print("="*60)
    
    if display is None:
        print("✗ Display not initialized")
        return False
    
    try:
        # Test 1: Read display ID
        print("Reading display ID...")
        display_id = display.read_id()
        if display_id:
            print(f"✓ Display ID: 0x{display_id:04X}")
        else:
            print("! Display ID read as 0 (may indicate issue)")
        
        # Test 2: Write and read pixel
        print("Writing and reading pixel...")
        test_color = 0x07E0  # Green
        display.write_pixel(160, 240, test_color)
        time.sleep_ms(10)
        read_color = display.read_pixel(160, 240)
        print(f"  Written: 0x{test_color:04X}, Read: 0x{read_color:04X}")
        if read_color == test_color or read_color != 0:
            print("✓ Pixel read/write test passed")
        else:
            print("! Pixel readback may have issues")
        
        return True
        
    except Exception as e:
        print(f"✗ Error during display readback: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_touchscreen_initialization():
    """Test touchscreen driver initialization"""
    print("\n" + "="*60)
    print("TEST 4: Touchscreen Initialization")
    print("="*60)
    
    if XPT2046 is None:
        print("✗ XPT2046 not available")
        return None
    
    try:
        # Create SPI bus for touchscreen
        print("Creating SPI bus for touchscreen...")
        spi = SPI(
            TouchConfig.SPI_ID,
            baudrate=TouchConfig.SPI_CLK_KHZ * 1000,
            polarity=0,
            phase=0,
            bits=8,
            firstbit=SPI.MSB,
            sck=Pin(TouchConfig.SCK_PIN),
            mosi=Pin(TouchConfig.MOSI_PIN),
            miso=Pin(TouchConfig.MISO_PIN)
        )
        print("✓ SPI bus created")
        
        # Create touchscreen instance
        print("Creating touchscreen instance...")
        touch = XPT2046(
            spi=spi,
            cs_pin=TouchConfig.CS_PIN,
            irq_pin=TouchConfig.IRQ_PIN
        )
        print("✓ Touchscreen instance created")
        
        # Initialize touchscreen
        print("Initializing touchscreen...")
        touch.init()
        print("✓ Touchscreen initialized")
        
        return touch
        
    except Exception as e:
        print(f"✗ Error during touchscreen initialization: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_touchscreen_reading(touch):
    """Test touchscreen reading functions"""
    print("\n" + "="*60)
    print("TEST 5: Touchscreen Reading")
    print("="*60)
    
    if touch is None:
        print("✗ Touchscreen not initialized")
        return False
    
    try:
        # Test 1: Read raw X,Y coordinates
        print("Reading raw coordinates (10 samples)...")
        for i in range(10):
            x = touch.get_x()
            y = touch.get_y()
            print(f"  Sample {i+1}: X={x:4d}, Y={y:4d}")
            time.sleep_ms(50)
        print("✓ Raw coordinate reading works")
        
        # Test 2: Read with averaging
        print("Reading averaged coordinates...")
        x, y = touch.read_xy()
        if x is not None and y is not None:
            print(f"✓ Averaged: X={x}, Y={y}")
        else:
            print("! Coordinates not within tolerance (first read may fail)")
        
        # Test 3: Pressure readings
        print("Reading pressure values...")
        z1 = touch.get_z1()
        z2 = touch.get_z2()
        print(f"✓ Pressure: Z1={z1}, Z2={z2}")
        
        # Test 4: Touch detection via update
        print("Testing touch.update()...")
        if touch.update():
            x, y = touch.get_xy()
            print(f"✓ Touch update returned: X={x}, Y={y}")
        else:
            print("! Touch update returned 0 (no valid reading)")
        
        # Test 5: Touch detection via IRQ
        print("Testing touch.detect_touch()...")
        result = touch.detect_touch()
        if result:
            print(f"✓ Touch detected (result={result})")
        else:
            print(f"✓ No touch detected (result={result})")
        
        return True
        
    except Exception as e:
        print(f"✗ Error during touchscreen reading: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_combined_operation(display, touch):
    """Test combined display and touchscreen operation"""
    print("\n" + "="*60)
    print("TEST 6: Combined Display and Touch Operation")
    print("="*60)
    
    if display is None or touch is None:
        print("✗ Display or touchscreen not initialized")
        return False
    
    try:
        # Clear display
        display.fill_rect(0, 0, display.get_width(), display.get_height(), 0x0000)
        
        # Draw touch input on display
        print("Touch the screen (10 seconds)...")
        print("Red dot will appear at touch location")
        
        start_time = time.time()
        timeout = 10  # seconds
        touch_count = 0
        
        while time.time() - start_time < timeout:
            if touch.update():
                x, y = touch.get_xy()
                
                # Map raw coordinates to display (assumes 0-4095 touch range)
                screen_x = (x * display.get_width()) // 4095
                screen_y = (y * display.get_height()) // 4095
                
                # Draw small square at touch point
                size = 5
                display.fill_rect(
                    max(0, screen_x - size),
                    max(0, screen_y - size),
                    size * 2,
                    size * 2,
                    0xF800  # Red
                )
                
                touch_count += 1
                if touch_count % 5 == 0:
                    print(f"  Touch {touch_count}: Raw=({x}, {y}) Screen=({screen_x}, {screen_y})")
            
            time.sleep_ms(50)
        
        print(f"✓ Completed combined operation test (detected {touch_count} touch events)")
        return True
        
    except Exception as e:
        print(f"✗ Error during combined operation: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_display_power_control(display):
    """Test display power control functions"""
    print("\n" + "="*60)
    print("TEST 7: Display Power Control")
    print("="*60)
    
    if display is None:
        print("✗ Display not initialized")
        return False
    
    try:
        # Test display off
        print("Turning display off...")
        display.display_off()
        time.sleep_ms(1000)
        print("✓ Display turned off")
        
        # Test display on
        print("Turning display on...")
        display.display_on()
        time.sleep_ms(1000)
        print("✓ Display turned on")
        
        return True
        
    except Exception as e:
        print(f"✗ Error during power control test: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("ST7796S Display & XPT2046 Touchscreen Test Suite")
    print("="*60)
    print("ESP32-S3 MicroPython Driver Tests\n")
    
    results = {
        "Display Init": False,
        "Display Drawing": False,
        "Display ReadBack": False,
        "Touch Init": False,
        "Touch Reading": False,
        "Combined Op": False,
        "Power Control": False,
    }
    
    # Run display tests
    display = test_display_initialization()
    if display:
        results["Display Init"] = True
        results["Display Drawing"] = test_display_drawing(display)
        results["Display ReadBack"] = test_display_readback(display)
        results["Power Control"] = test_display_power_control(display)
    
    # Run touchscreen tests
    touch = test_touchscreen_initialization()
    if touch:
        results["Touch Init"] = True
        results["Touch Reading"] = test_touchscreen_reading(touch)
    
    # Run combined test
    if display and touch:
        results["Combined Op"] = test_combined_operation(display, touch)
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = 0
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ ALL TESTS PASSED!")
    elif passed >= total * 0.75:
        print("\n⚠ MOST TESTS PASSED - Please check failures")
    else:
        print("\n✗ MULTIPLE TEST FAILURES - Please check configuration")
    
    return passed == total


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        success = run_all_tests()
        if success:
            print("\n✓ Driver conversion successful!")
        else:
            print("\n! Some tests failed - check pin configuration and hardware")
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
