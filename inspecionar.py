with open('site_atual.html', 'r', encoding='utf-8') as f:
    html = f.read()

print(f'Tamanho do HTML: {len(html)} caracteres')

# Procurar qualquer referencia a imagem no header/nav
idx = html.find('<header')
if idx != -1:
    print('\nTrecho do header (primeiros 500 chars):')
    print(html[idx:idx+500])
else:
    print('Header nao encontrado')

# Procurar src= no inicio do arquivo
import re
srcs = re.findall(r'src="([^"]{0,80})"', html[:5000])
print('\nPrimeiros src= encontrados:')
for s in srcs[:10]:
    print(f'  {s[:80]}')
