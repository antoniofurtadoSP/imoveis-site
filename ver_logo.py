import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx = html.find('src="data:image')
if idx != -1:
    print('Logo em Base64:')
    print(html[idx+5:idx+60])
else:
    logos = re.findall(r'src="([^"]*logo[^"]*)"', html)
    print('Logo como arquivo:', logos)
