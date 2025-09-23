from time import ticks_ms, ticks_diff, sleep_ms
from PicoMDIO import MDIO
from machine import Pin
import sys
import select
import machine

from m88q2110_config import m88q2110_config
from rtl8221b_config import rtl8221b_config
from tja1103_config import tja1103_config



led_onboard = Pin(22, Pin.OUT)

marvell_reset = Pin(8, Pin.OUT)

realtek_reset = Pin(6, Pin.OUT)

mdio = MDIO()

DEVICE_INFO = {
    "DEVICE": "DOLPHIN 1000BASE-T1",
    "CONTROLLER": "RP2350",
    "SOFTWARE VERSION": "V1.0",
    "SPEED": "1000 Mbit/s",
    "FUNCTION": "Reset"
}

DEVICE_ORDER = [
    "DEVICE",
    "CONTROLLER",
    "SOFTWARE VERSION",
    "SPEED",
    "FUNCTION"
]


class Phy:
    def __init__(self, addr, clause45=False, phy_id=None):
        self.addr = addr
        self.clause45 = clause45
        self.phy_id = phy_id
        self.c_id = None
        self.name = None
        self.functions = []
        self.configured = False

        self._identify_by_address()

    def _identify_by_address(self):
        # Extend with more PHYs as needed
        known_phys = {
            0x00: {
                "c_id": 0,
                "name": "REALTEK 8221B",
                "functions": ["Reset", "Switch Speed"]
            },
            0x01: {
                "c_id": 1,
                "name": "MARVELL 88Q2112",
                "functions": ["Reset", "Compliance Test", "Switch Speed", "Switch M/S"]
            },
            0x02: {
                "c_id": 2,
                "name": "unknown-02",
                "functions": ["Reset"]
            },
            0x03: {
                "c_id": 3,
                "name": "unknown-03",
                "functions": ["Reset"]
                
            },
            0x04: {
                "c_id": 4,
                "name": "MARVELL MVQ3244",
                "functions": ["Reset"]
                
            },
            0x05: {
                "c_id": 5,
                "name": "REALTEK 8221B",
                "functions": ["Reset", "Switch Speed"]
            },            
            0x06: {
                "c_id": 6,
                "name": "NXP TJA-1103",
                "functions": ["Reset"]
            },
        }


        info = known_phys.get(self.addr)
        if info:
            self.c_id = info["c_id"]
            self.name = info["name"]
            self.functions = info["functions"]

    def __str__(self):
        proto = "Clause-45" if self.clause45 else "Clause-22"
        lines = [f"PHY addr=0x{self.addr:02X}  ({proto})"]
        if self.c_id is not None:
            lines.append(f"  C_ID: {self.c_id}")
        if self.name:
            lines.append(f"  PHY: {self.name}")
        if self.functions:
            lines.append(f"  FUNCTIONS: {', '.join(self.functions)}")
        if self.phy_id is not None:
            lines.append(f"  ID=0x{self.phy_id:04X}")
        return "\n".join(lines)


def print_serial_status(phys):
    print("INFO")
    for key in DEVICE_ORDER:
        print(f"{key}: {DEVICE_INFO[key]}")

    for i, phy in enumerate(phys, start=1):
        name = phy.name if phy.name else "Unknown PHY"
        print(f"PHY{i}: 0x{phy.addr:02X} - {name}")
        if phy.functions:
            print(f"FUNCTION: {', '.join(phy.functions)}")

    print("END")

def process_command(cmd, phys):

    s = cmd.strip()

    # ---- device-level commands ----
    if s == "DEV_RESET" or s == "DEV_RESET\r":
        # optional: let the host see the ACK before the USB/serial drops
        print(">>> ACK: resetting device…")
        led_onboard.off()
        realtek_reset.off()
        marvell_reset.off()
        sleep_ms(100)
        machine.reset()      # hard reset of the RP2350
        return
    
    elif s == "0x00_RESET" or s == "0x05_RESET":
        print(">>> ACK: resetting REALTEK…")
        realtek_reset.off()
        sleep_ms(200)
        realtek_reset.on()
        # mdio.write22(0x00, 0x00, 0x8000)

        # reconfigure matching PHYs
        for p in phys:
            if p.addr in (0x00, 0x05):
                p.configured = False 
                configure_phy(p)

    elif s == "0x01_RESET":
        print(">>> ACK: resetting MARVELL…")
        marvell_reset.off()
        sleep_ms(200)
        marvell_reset.on()

        # reconfigure matching PHYs
        for p in phys:
            if p.addr == 0x01:
                p.configured = False
                configure_phy(p)

    elif s == "0x01_SWITCH_SPEED":
        # Bit 0: 1 = 1000, 0 = 100
        try:
            phy, dev, reg = 0x01, 0x01, 0x834
            mask = 0x0001
            old = mdio.read45(phy, dev, reg)
            new = old ^ mask
            mdio.write45(phy, dev, reg, new)
            rb = mdio.read45(phy, dev, reg)
            print(">>> Switching Marvell Speed (100 <-> 1000)")
        except Exception as e:
            print(f"ERR: speed toggle failed: {e}")

    elif s == "0x01_SWITCH_M/S":
        # Bit 14: 1 = Master, 0 = Slave
        try:
            phy, dev, reg = 0x01, 0x01, 0x834
            mask = 0x4000
            old = mdio.read45(phy, dev, reg)
            new = old ^ mask
            mdio.write45(phy, dev, reg, new)
            rb = mdio.read45(phy, dev, reg)
            print(">>> Switching Marvell Master/Slave")
        except Exception as e:
            print(f"ERR: master/slave toggle failed: {e}")

    elif s == "0x00_SWITCH_SPEED" or s == "0x05_SWITCH_SPEED":
        try:
            phy_addr = int(s.split('_')[0], 16)  # "0x00" or "0x05"
        except Exception:
            phy_addr = 0x00 if "0x00" in s else 0x05
        _realtek_switch_speed_clause22(phy_addr)



    parts = cmd.strip().split('_')

    if not parts:
        print("ERR: Empty command")
        return

    action = parts[0]

    if action == "WRITE":
        if len(parts) == 4:
            _, phy_str, reg_str, data_str = parts
            dev_type = None
        elif len(parts) == 5:
            _, phy_str, dev_str, reg_str, data_str = parts
            dev_type = int(dev_str, 16)
        else:
            print("ERR: WRITE format: WRITE_<PHY>_<REG>_<DATA> or WRITE_<PHY>_<DEV>_<REG>_<DATA>")
            return

        try:
            phy_addr = int(phy_str, 16)
            reg = int(reg_str, 16)
            data = int(data_str, 16)
        except ValueError:
            print("ERR: Invalid number format")
            return

        matching_phy = next((p for p in phys if p.addr == phy_addr), None)

        try:
            if matching_phy and matching_phy.clause45:
                dev = dev_type if dev_type is not None else 0x01
                mdio.write45(phy_addr, dev, reg, data)
                read_val = mdio.read45(phy_addr, dev, reg)
                print(f"WRITE Clause-45  PHY=0x{phy_addr:02X} DEV=0x{dev:02X} REG=0x{reg:04X} DATA=0x{data:04X}")
                print(f"READBACK         PHY=0x{phy_addr:02X} DEV=0x{dev:02X} REG=0x{reg:04X} DATA=0x{read_val:04X}")
            else:
                mdio.write22(phy_addr, reg, data)
                read_val = mdio.read22(phy_addr, reg)
                print(f"WRITE Clause-22  PHY=0x{phy_addr:02X} REG=0x{reg:02X} DATA=0x{data:04X}")
                print(f"READBACK         PHY=0x{phy_addr:02X} REG=0x{reg:02X} DATA=0x{read_val:04X}")
        except Exception as e:
            print(f"ERR: MDIO write failed: {e}")


    elif action == "READ":
        if len(parts) == 3:
            _, phy_str, reg_str = parts
            dev_type = None
        elif len(parts) == 4:
            _, phy_str, dev_str, reg_str = parts
            dev_type = int(dev_str, 16)
        else:
            print("ERR: READ format: READ_<PHY>_<REG> or READ_<PHY>_<DEV>_<REG>")
            return

        try:
            phy_addr = int(phy_str, 16)
            reg = int(reg_str, 16)
        except ValueError:
            print("ERR: Invalid number format")
            return

        matching_phy = next((p for p in phys if p.addr == phy_addr), None)

        try:
            if matching_phy and matching_phy.clause45:
                dev = dev_type if dev_type is not None else 0x01
                val = mdio.read45(phy_addr, dev, reg)
                print(f"READ Clause-45  PHY=0x{phy_addr:02X} DEV=0x{dev:02X} REG=0x{reg:04X} DATA=0x{val:04X}")
            else:
                val = mdio.read22(phy_addr, reg)
                print(f"READ Clause-22  PHY=0x{phy_addr:02X} REG=0x{reg:02X} DATA=0x{val:04X}")
        except Exception as e:
            print(f"ERR: MDIO read failed: {e}")

def _realtek_switch_speed_clause22(phy_addr):
    # Clause-22, REG 0x000
    # Bit 13 & 6: speed (10=1000, 01=100)
    # Bit 12: autoneg enable (force to 0)
    # Bit 8: duplex (force to 1)
    try:
        reg = 0x000
        old = mdio.read22(phy_addr, reg)

        b13 = (old >> 13) & 1
        b06 = (old >> 6) & 1

        # Toggle between 1000 <-> 100
        if b13 == 1 and b06 == 0:
            # 1000 -> 100 (01)
            tgt_b13, tgt_b06 = 0, 1
        elif b13 == 0 and b06 == 1:
            # 100 -> 1000 (10)
            tgt_b13, tgt_b06 = 1, 0
        else:
            # unknown -> default to 1000 (10)
            tgt_b13, tgt_b06 = 1, 0

        # Clear bits 13, 12, and 6; set new speed; force bit 8 = 1; force bit 12 = 0
        clear_mask = (1 << 13) | (1 << 12) | (1 << 6)
        new = (old & ~clear_mask) | (tgt_b13 << 13) | (tgt_b06 << 6) | (1 << 8)

        mdio.write22(phy_addr, reg, new)
        rb = mdio.read22(phy_addr, reg)

        f13 = (rb >> 13) & 1
        f06 = (rb >> 6) & 1
        speed = "1000" if (f13 == 1 and f06 == 0) else ("100" if (f13 == 0 and f06 == 1) else "UNKNOWN")
        duplex = "FULL" if ((rb >> 8) & 1) else "HALF"
        an = "OFF" if (((rb >> 12) & 1) == 0) else "ON"

        print(f">>> Realtek 0x{phy_addr:02X} SWITCH_SPEED")
        print(f"    REG 0x{reg:04X}: 0x{old:04X} -> 0x{rb:04X}")
        print(f"    Now: {speed} Mbit/s, {duplex}-DUPLEX, AN={an}")
    except Exception as e:
        print(f"ERR: Realtek speed switch failed on PHY 0x{phy_addr:02X}: {e}")



def marvell_compliance_100():
    mdio.write45(0x01, 0x01, 0x836, 0x2000)
    mdio.write45(0x01, 0x01, 0x836, 0x4000)
    mdio.write45(0x01, 0x01, 0x834, 0xC001)
    mdio.write45(0x01, 0x01, 0x836, 0x2000)
    mdio.write45(0x01, 0x01, 0x834, 0xC000)
    return

def marvell_compliance_1000():
    mdio.write45(0x01, 0x01, 0x904, 0x0000)
    mdio.write45(0x01, 0x01, 0x904, 0x4000)
    mdio.write45(0x01, 0x01, 0x904, 0x8000)
    mdio.write45(0x01, 0x01, 0x904, 0xA000)
    mdio.write45(0x01, 0x01, 0x904, 0xC000)
    mdio.write45(0x01, 0x01, 0x904, 0xE000)
    return


DEBUG_SCAN = False

def _present_c45(phy_addr):
    try:
        id1 = mdio.read45(phy_addr, 1, 2)   # PMA/PMD Device 1, ID1
        id2 = mdio.read45(phy_addr, 1, 3)   # PMA/PMD Device 1, ID2
        if DEBUG_SCAN:
            print(f"[DBG] C45 probe addr=0x{phy_addr:02X} ID1=0x{id1:04X} ID2=0x{id2:04X}")
        # Treat valid if either word looks non-trivial
        return (id1 not in (0x0000, 0xFFFF)) or (id2 not in (0x0000, 0xFFFF)), id1
    except Exception as e:
        if DEBUG_SCAN:
            print(f"[DBG] C45 probe error addr=0x{phy_addr:02X}: {e}")
        return False, None

def _present_c22(phy_addr):
    try:
        id1 = mdio.read22(phy_addr, 2)  # PHYIDR1
        id2 = mdio.read22(phy_addr, 3)  # PHYIDR2
        if DEBUG_SCAN:
            print(f"[DBG] C22 probe addr=0x{phy_addr:02X} ID1=0x{id1:04X} ID2=0x{id2:04X}")
        # Valid if either word looks non-trivial
        return (id1 not in (0x0000, 0xFFFF)) or (id2 not in (0x0000, 0xFFFF)), id1
    except Exception as e:
        if DEBUG_SCAN:
            print(f"[DBG] C22 probe error addr=0x{phy_addr:02X}: {e}")
        return False, None

def configure_phy(p):
    if p.configured:
        return

    # Ensure both flags exist and stay consistent
    if not hasattr(p, "clause22"):
        p.clause22 = not p.clause45
    else:
        # keep them in sync if something set only one
        p.clause22 = bool(p.clause22)
        p.clause45 = not p.clause22

    if p.name == "MARVELL 88Q2112":
        m88q2110_config(mdio, p)
    elif p.name == "NXP TJA-1103":
        tja1103_config(mdio, p)
    elif p.name == "REALTEK 8221B":
        rtl8221b_config(mdio, p)

    p.configured = True

def scan_phys(existing_phys):
    updated_phys = []

    for phy_addr in range(32):
        p = next((x for x in existing_phys if x.addr == phy_addr), None)

        # 1) Probe Clause-45
        c45_ok, id1_c45 = _present_c45(phy_addr)
        if c45_ok:
            if p is None:
                p = Phy(addr=phy_addr, clause45=True, phy_id=id1_c45)
            else:
                p.clause45 = True
                p.phy_id = id1_c45
            updated_phys.append(p)          # <- ensure it’s tracked even if config fails
            configure_phy(p)
            if DEBUG_SCAN:
                print(f"[DBG] Detected C45 PHY @0x{phy_addr:02X}: {p}")
            continue  # skip C22 if C45 worked

        # 2) Probe Clause-22 (fallback or native)
        c22_ok, id1_c22 = _present_c22(phy_addr)
        if c22_ok:
            if p is None:
                p = Phy(addr=phy_addr, clause45=False, phy_id=id1_c22)
            else:
                p.clause45 = False
                p.phy_id = id1_c22
            updated_phys.append(p)          # <- ensure it’s tracked even if config fails
            configure_phy(p)
            if DEBUG_SCAN:
                print(f"[DBG] Detected C22 PHY @0x{phy_addr:02X}: {p}")

    return updated_phys


def sync_realtek_speed_from_c45(src_phy=0x01, realtek_phy=0x00, dev=0x01, reg=0x000):
    """
    Read speed from a Clause-45 PHY (src_phy) and apply it to a Realtek Clause-22 PHY (realtek_phy).
    Mapping (bits 13 & 6):
      10 -> 1000 Mbit/s
      01 -> 100 Mbit/s
    Behavior:
      - If Realtek already matches, do nothing.
      - If Realtek is at the opposite valid speed, call the existing toggle:
          _realtek_switch_speed_clause22(realtek_phy)
      - If Realtek is in an unknown state, force the desired bits directly.
    """
    try:
        # 1) Read desired speed from Clause-45 source
        v = mdio.read45(src_phy, dev, reg)
        d13 = (v >> 13) & 1
        d06 = (v >> 6)  & 1

        if d13 == 1 and d06 == 0:
            desired_pair = (1, 0)
            desired_str = "1000"
        elif d13 == 0 and d06 == 1:
            desired_pair = (0, 1)
            desired_str = "100"
        else:
            print("ERR: Desired speed from C45 is unknown (bits 13/6 not 10 or 01).")
            return

        # 2) Read current Realtek setting (Clause-22, REG 0x000)
        r = mdio.read22(realtek_phy, 0x000)
        r13 = (r >> 13) & 1
        r06 = (r >> 6)  & 1
        current_pair = (r13, r06)

        if current_pair == desired_pair:
            # print(f">>> Realtek 0x{realtek_phy:02X} already at {desired_str} Mbit/s")
            return

        # 3) If Realtek is at a valid opposite speed, just toggle using the existing function
        if current_pair in ((1, 0), (0, 1)):
            _realtek_switch_speed_clause22(realtek_phy)
        else:
            # Unknown state: force the bits directly
            clear_mask = (1 << 13) | (1 << 12) | (1 << 6)   # clear speed + AN
            new_val = (r & ~clear_mask) \
                      | (desired_pair[0] << 13) \
                      | (desired_pair[1] << 6) \
                      | (1 << 8)  # force FULL duplex
            mdio.write22(realtek_phy, 0x000, new_val)

        # 4) Verify
        rb = mdio.read22(realtek_phy, 0x000)
        f13 = (rb >> 13) & 1
        f06 = (rb >> 6)  & 1
        final_pair = (f13, f06)
        final_speed = "1000" if final_pair == (1, 0) else ("100" if final_pair == (0, 1) else "UNKNOWN")
        status = "OK" if final_pair == desired_pair else "FAILED"
        print(f">>> Sync Realtek 0x{realtek_phy:02X} to {desired_str} Mbit/s -> {final_speed} ({status})")

    except Exception as e:
        print(f"ERR: sync_realtek_speed_from_c45 failed: {e}")




# Timers
last_scan = 0
last_print = 0
scan_interval = 1000
print_interval = 3000
phy_list = []

while True:
    now = ticks_ms()

    led_onboard.on()

    marvell_reset.on()

    realtek_reset.on()

    if ticks_diff(now, last_scan) >= scan_interval:
        phy_list = scan_phys(phy_list)
        sync_realtek_speed_from_c45()
        last_scan = now

    if ticks_diff(now, last_print) >= print_interval:
        if any(p.configured for p in phy_list):
            print_serial_status(phy_list)
            
        else:
            print("No configured PHYs detected yet.")
            led_onboard.off()
        last_print = now

    sleep_ms(1)  # Yield to allow REPL access

        # Check for serial input
    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        line = sys.stdin.readline()
        process_command(line, phy_list)