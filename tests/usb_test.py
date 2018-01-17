import usb
busses = usb.busses()
for bus in busses:
	devices=bus.devices
	for dev in devices:
		print("Device:", dev.filename)
		print(" idVendor: %d (%s)", dev.idVendor,hex(dev.idVendor))
		print(" idProduct: %d (%s)", dev.idProduct,hex(dev.idProduct))
