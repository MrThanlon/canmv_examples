# Sensor Vertical Flip Example
#
# This example shows off vertically flipping the image in hardware
# from the camera sensor.

import sensor, image, time

sensor.reset()                      # Reset and initialize the sensor.
sensor.set_pixformat(sensor.RGB565) # Set pixel format to RGB565 (or GRAYSCALE)
sensor.set_framesize(sensor.QVGA)   # Set frame size to QVGA (320x240)
sensor.skip_frames(time = 2000)     # Wait for settings take effect.
clock = time.clock()                # Create a clock object to track the FPS.

# Change this to False to undo the flip.
sensor.set_vflip(True)

while(True):
    clock.tick()                    # Update the FPS clock.
    img = sensor.snapshot()         # Take a picture and return the image.
    print(clock.fps())              # Note: CanMV Cam runs about half as fast when connected
                                    # to the IDE. The FPS should increase once disconnected.
