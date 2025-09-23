from time import sleep_ms

def tja1103_config(mdio, phy):
    if phy.name != "NXP TJA-1103" or not phy.clause45:
        return

    sleep_ms(1000)
    print(f"\n=== Configuring {phy.name} (0x{phy.addr:02X}) ===")

    try:
        a = phy.addr
        dev = 0x1E  # Common Clause 45 device type

        # Example: Soft reset + enable link training (modify per real use)
        mdio.write45(a, dev, 0x0000, 0x8000)  # Software reset
        mdio.write45(a, dev, 0x0009, 0x0100)  # Enable LT or similar

        print("NXP TJA-1103 config complete.\n")

    except Exception as e:
        print("ERROR during NXP config:", e)