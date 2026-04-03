import can

# Maak een busverbinding
with can.Bus(interface='socketcan', channel='can0', bitrate=500000) as bus:
    # Stuur een bericht
    msg = can.Message(arbitration_id=0x123, data=[1, 2, 3, 4], is_extended_id=True)
    try:
        bus.send(msg)
        print(f"Bericht verzonden op {bus.channel_info}")
    except can.CanError:
        print("Bericht kon niet worden verzonden")   