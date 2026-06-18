Digital I/O (``col.io.dio``)
============================

Colosseum exposes bench digital I/O through ``col.io.dio``. Use ``driver = sim`` for offline runs and CI, or ``driver = ftdi-ft232h`` for FT232H-class USB GPIO adapters (Adafruit FT232H breakout, etc.).

Configuration
-------------

Example simulated DIO for smoke tests::

   [[io.dio]]
   dio_id = 1
   driver = sim
   port_lines = 8
   direction = 0xFF

Example FT232H on a lab bench (requires ``pip install colosseum[io]``)::

   [[io.dio]]
   dio_id = 1
   driver = ftdi-ft232h
   resource = ftdi://ftdi:232h/1
   port_lines = 8
   direction = 0x0F

``port_lines`` is ``8`` for ADBUS (default) or ``16`` for ADBUS+ACBUS. ``direction`` is a bitmask where ``1`` means output and ``0`` means input.

API usage
---------

Configure direction, drive outputs, and record readbacks as measurements::

   col.io.dio.configure(dio_id=1, direction=0x0F)
   col.io.dio.write_port(dio_id=1, value=0b1010)
   value = col.io.dio.read_port(dio_id=1, key="port_a")
   col.io.dio.write_pin(dio_id=1, line=0, value=True)
   level = col.io.dio.read_pin(dio_id=1, line=0, key="reset")

``read_port`` and ``read_pin`` require ``key=`` and persist measurement rows under domain ``equipment`` in ``execution.sqlite``. ``write_port``, ``write_pin``, and ``configure`` are ``@command`` APIs (optional ``key=``).

Platform notes
--------------

**Linux:** install ``libusb`` (distribution package) so pyftdi can open the device.

**Windows:** install the WinUSB driver for the FT232H (for example with Zadig) so pyftdi can claim the interface. USB serial drivers alone are not sufficient for MPSSE GPIO.

Reserved / experimental surfaces
--------------------------------

I2C and SPI (``col.io.i2c``, ``col.io.spi``) share the same plugin lifecycle but remain
reserved for NI USB-845x until that driver is implemented. They are exposed for API
compatibility and fail immediately with explicit ``IoNotImplementedError`` messages.
FT232H MPSSE I2C/SPI may be added later on the same URL.

See also :doc:`platform_notes` and :doc:`configuration`.
