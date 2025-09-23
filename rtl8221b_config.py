from time import sleep_ms

def rtl8221b_config(mdio, phy):
    if phy.name != "REALTEK 8221B" or not phy.clause22:
        return
    
    print(f"\n=== Configuring {phy.name} (0x{phy.addr:02X}) ===")

    try:
        a = phy.addr

        print(">> Starting Realtek Config...")
        # Clause 22 example: write to BMCR (reg 0) to enable AN + restart
        mdio.write22(a, 0x00, 0x1200)

        print(">> LED Config")

        print(">> Switch page to LED register...")
        mdio.write22(a, 0x1F, 0x0D04)

        print(">> Set LED IEEE Mode...")
        mdio.write22(a, 0x11, 0x6009)

        print(">> Set LED functionality...")
        mdio.write22(a, 0x10, 0x6D68)

        print(">> Switch page to standard register...")
        mdio.write22(a, 0x1F, 0x0A42)

        print("REALTEK 8221B config complete.\n")

    except Exception as e:
        print("ERROR during REALTEK config:", e)
