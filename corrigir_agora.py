import os
import re

# Pasta onde estão os arquivos HTML
pasta_site = r'C:\Users\anton\Documents\Site_Publico_Antonio'

print("--- INICIANDO CORREÇÃO DE LINKS DO SITE ---")

# Extensões que vamos procurar
padrao = re.compile(r'\.(jpg|jpeg|png)', re.IGNORECASE)

cont_arquivos = 0
cont_trocas = 0

for nome_arquivo in os.listdir(pasta_site):
    if nome_arquivo.endswith(".html") or nome_arquivo == "style.css":
        caminho_completo = os.path.join(pasta_site, nome_arquivo)
        
        with open(caminho_completo, 'r', encoding='utf-8', errors='ignore') as f:
            conteudo = f.read()

        if padrao.search(conteudo):
            # Troca as extensões para .webp
            novo_conteudo = padrao.sub('.webp', conteudo)
            
            with open(caminho_completo, 'w', encoding='utf-8') as f:
                f.write(novo_conteudo)
            
            print(f"✅ Atualizado: {nome_arquivo}")
            cont_arquivos += 1
            cont_trocas += 1

print(f"\n--- FIM ---")
print(f"Arquivos modificados: {cont_arquivos}")
if cont_arquivos == 0:
    print("Nenhuma referência antiga foi encontrada ou os arquivos já estavam em WebP.")