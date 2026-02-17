import base64

with open('site_atual.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx = html.find('src="data:image')
if idx == -1:
    print('Base64 nao encontrado!')
else:
    start = html.find('base64,', idx) + 7
    end = html.find('"', start)
    b64 = html[start:end]
    print(f'Base64 tem {len(b64)} caracteres')
    with open('logo_do_site.jpg', 'wb') as f:
        f.write(base64.b64decode(b64))
    print('Salvo em logo_do_site.jpg - abra esse arquivo!')
