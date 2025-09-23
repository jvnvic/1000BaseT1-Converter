from time import sleep_ms

def m88q2110_config(mdio, phy):
    if phy.name != "MARVELL 88Q2112" or not phy.clause45:
        return

    print(f"\n=== Initializing {phy.name} (PHY address 0x{phy.addr:02X}) ===")

    try:
        a = phy.addr

        print(">> Starting Marvell Config...")
        print(">> Disabling PMA transmit and auto-negotiation...")
        mdio.write45(a, 0x01, 0x0900, 0x4000)
        mdio.write45(a, 0x07, 0x0200, 0x0000)

        # M/S is set by HW config with DIP switch
        # print(">> Setting PHY as Master...")
        # mdio.write45(a, 0x01, 0x0834, 0x4000)

        print(">> Beginning configuration sequence...")
        mdio.write45(a, 0x03, 0xFFE4, 0x07B5)
        mdio.write45(a, 0x03, 0xFFE4, 0x06B6)

        print(">> Waiting 5 seconds...")
        sleep_ms(5000)

        print(">> Setting RGMII Receive Timing Control delay...")
        mdio.write45(a, 0x1F, 0x8001, 0x4000)
        mdio.write45(a, 0x03, 0x8000, 0x8000)
        sleep_ms(500)
        mdio.write45(a, 0x03, 0x8000, 0x0000)
        sleep_ms(200)

        print(">> Doing the rest of the config...")

        mdio.write45(a, 0x03, 0xFFDE, 0x402F)
        mdio.write45(a, 0x03, 0xFE2A, 0x3C3D)
        mdio.write45(a, 0x03, 0xFE34, 0x4040)
        mdio.write45(a, 0x03, 0xFE4B, 0x9337)
        mdio.write45(a, 0x03, 0xFE2A, 0x3C1D)
        mdio.write45(a, 0x03, 0xFE34, 0x0040)
        mdio.write45(a, 0x03, 0xFE0F, 0x0000)
        mdio.write45(a, 0x03, 0xFC00, 0x01C0)
        mdio.write45(a, 0x03, 0xFC17, 0x0425)
        mdio.write45(a, 0x03, 0xFC94, 0x5470)
        mdio.write45(a, 0x03, 0xFC95, 0x0055)
        mdio.write45(a, 0x03, 0xFC19, 0x08D8)
        mdio.write45(a, 0x03, 0xFC1A, 0x0110)
        mdio.write45(a, 0x03, 0xFC1B, 0x0A10)
        mdio.write45(a, 0x03, 0xFC3A, 0x2725)
        mdio.write45(a, 0x03, 0xFC61, 0x2627)
        mdio.write45(a, 0x03, 0xFC3B, 0x1612)
        mdio.write45(a, 0x03, 0xFC62, 0x1C12)
        mdio.write45(a, 0x03, 0xFC9D, 0x6367)
        mdio.write45(a, 0x03, 0xFC9E, 0x8060)
        mdio.write45(a, 0x03, 0xFC00, 0x01C8)
        mdio.write45(a, 0x03, 0x8000, 0x0000)
        mdio.write45(a, 0x03, 0x8016, 0x0011)
        mdio.write45(a, 0x03, 0xFDA3, 0x1800)
        mdio.write45(a, 0x03, 0xFE02, 0x00C0)
        mdio.write45(a, 0x03, 0xFFDB, 0x0010)
        mdio.write45(a, 0x03, 0xFFF3, 0x0020)
        mdio.write45(a, 0x03, 0xFE40, 0x00A6)
        mdio.write45(a, 0x03, 0xFE60, 0x0000)
        mdio.write45(a, 0x03, 0xFE2A, 0x3C3D)
        mdio.write45(a, 0x03, 0xFE4B, 0x9334)
        mdio.write45(a, 0x03, 0xFC10, 0xF600)
        mdio.write45(a, 0x03, 0xFC11, 0x073D)
        mdio.write45(a, 0x03, 0xFC12, 0x000D)
        mdio.write45(a, 0x03, 0xFC13, 0x0010)

        mdio.write45(a, 0x07, 0x8032, 0x0064)
        mdio.write45(a, 0x07, 0x8031, 0x0A01)
        mdio.write45(a, 0x07, 0x8031, 0x0C01)
        mdio.write45(a, 0x03, 0x800C, 0x0000)
        mdio.write45(a, 0x07, 0x8032, 0x0002)
        mdio.write45(a, 0x07, 0x8031, 0x0A1B)
        mdio.write45(a, 0x07, 0x8031, 0x0C1B)
        mdio.write45(a, 0x07, 0x8032, 0x0003)
        mdio.write45(a, 0x07, 0x8031, 0x0A1C)
        mdio.write45(a, 0x07, 0x8031, 0x0C1C)
        mdio.write45(a, 0x03, 0xFE04, 0x0008)

        print(">> Configuring LEDs...")
        mdio.write45(a, 0x03, 0x8013, 0x0417)
        # Set PIN output modes
        mdio.write45(a, 0x03, 0x8016, 0x0014)
        # Set LED functionality
        mdio.write45(a, 0x03, 0x8017, 0x8802)
        # Switch LED Polarity
                
        print(">> Performing soft reset sequence...")
        mdio.write45(a, 0x01, 0x0000, 0x0800)
        mdio.write45(a, 0x03, 0xFFE4, 0x000C)
        sleep_ms(1000)
        mdio.write45(a, 0x03, 0xFFE4, 0x06B6)
        mdio.write45(a, 0x01, 0x0000, 0x0000)
        sleep_ms(1000)

        print(">> Finalizing configuration...")
        mdio.write45(a, 0x03, 0xFC47, 0x0030)
        mdio.write45(a, 0x03, 0xFC47, 0x0031)
        mdio.write45(a, 0x03, 0xFC47, 0x0030)
        mdio.write45(a, 0x03, 0xFC47, 0x0000)
        mdio.write45(a, 0x03, 0xFC47, 0x0001)
        mdio.write45(a, 0x03, 0xFC47, 0x0000)
        mdio.write45(a, 0x01, 0x0900, 0x8000)
        mdio.write45(a, 0x01, 0x0900, 0x0000)
        mdio.write45(a, 0x03, 0xFFE4, 0x000C)

        print("=== 88Q2112 configuration complete ===\n")

    except Exception as e:
        print("ERROR during Marvell config:", e)