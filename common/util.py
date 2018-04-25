import uuid

def get_mac_address():
    mac=uuid.UUID(int = uuid.getnode()).hex[-12:].upper()
    return ":".join([mac[e:e+2] for e in range(0,11,2)])

if __name__ == '__main__':
	print(get_mac_address())