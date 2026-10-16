import spidev
import gpiod
from gpiod.line import Direction, Value, Edge
from typing import Iterable
import time


class LoRaSpi():

    SPI_SPEED = 8000000

    def __init__(self, bus: int, cs: int, speed: int = SPI_SPEED):
        self.bus = bus
        self.cs = cs
        self.speed = speed

    def transfer(self, buf: Iterable) -> tuple:
        spi = spidev.SpiDev()
        spi.open(self.bus, self.cs)
        spi.lsbfirst = False
        spi.mode = 0
        spi.max_speed_hz = self.speed
        ret = spi.xfer2(buf)
        spi.close()
        return ret


class LoRaGpio:

    LOW = Value.INACTIVE
    HIGH = Value.ACTIVE

    def __init__(self, chip: int, offset: int):
        self.chip = "/dev/gpiochip" + str(chip)
        self.offset = offset
        self.seqno = 0

    def output(self, value: Value):
        with gpiod.request_lines(
            self.chip,
            consumer="LoRaGpio",
            config={self.offset: gpiod.LineSettings(direction=Direction.OUTPUT)}
        ) as request:
            request.set_value(self.offset, value)

    def input(self):
        with gpiod.request_lines(
            self.chip,
            consumer="LoRaGpio",
            config={self.offset: gpiod.LineSettings(direction=Direction.INPUT)}
        ) as request:
            return request.get_value(self.offset)

    def monitor(self, callback, timeout: float = 0):
        # Monitor this line for rising edges and invoke callback() for
        # each edge.
        #
        # timeout == 0 (the default; this is the mode the SX126x driver
        # uses): persistent monitor - the line is requested once and
        # every edge is delivered to the callback until the thread
        # dies. The SX126x driver runs exactly one such thread for the
        # lifetime of the radio (see SX126x._ensureMonitor()). The old
        # scheme - spawning a short-lived monitor thread for every
        # request()/listen()/endPacket() and joining it at the start of
        # the next operation - was racy: an edge arriving while the old
        # thread was being joined was consumed (and dropped) by the
        # stale thread, and a stale monitor with a near-infinite
        # timeout could wedge the join for hours.
        #
        # timeout > 0 (legacy one-shot): stop after the first edge or
        # when the timeout elapses.        
        t = time.time()
        with gpiod.request_lines(
            self.chip,
            consumer="LoRaGpio",
            config={self.offset: gpiod.LineSettings(edge_detection=Edge.RISING)}
        ) as request:
           while True:
                if timeout > 0 and (time.time() - t) >= timeout:
                    return
                if timeout > 0:
                    # unblock periodically so the deadline above is
                    # honoured (read_edge_events() alone blocks until
                    # the next edge); fall back to a plain blocking
                    # read on gpiod builds without wait_edge_events()
                    if hasattr(request, "wait_edge_events"):
                        if not request.wait_edge_events(0.25):
                            continue            
                for event in request.read_edge_events():
                    callback()
                    if timeout > 0:
                        return

class BaseLoRa :

    def begin(self):
        raise NotImplementedError

    def end(self):
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError

    def beginPacket(self):
        raise NotImplementedError

    def endPacket(self, timeout: int)-> bool:
        raise NotImplementedError

    def write(self, data, length: int):
        raise NotImplementedError

    def request(self, timeout: int)-> bool:
        raise NotImplementedError

    def available(self):
        raise NotImplementedError

    def read(self, length: int):
        raise NotImplementedError

    def wait(self, timeout: int)-> bool:
        raise NotImplementedError

    def status(self):
        raise NotImplementedError
