import qrcode
url = 'Isft38.Edu.ar'
qr = qrcode.QRCode(version = 1, box_size=10,border=1)
qr.add_data(url)
qr.make(fit=True)

img=qr.make_image(fill='black', back_color='white')
img.save('.\static\Isft38.png')
