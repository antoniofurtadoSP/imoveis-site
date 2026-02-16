import os
import re

pasta_site = os.getcwd()
print(f"--- INICIANDO CORREÇÃO PROFUNDA EM: {pasta_site} ---")

padrao = re.compile(r'\.(jpg|jpeg|png)', re.IGNORECASE)
arquivos_totais = 0

for raiz, pastas, arquivos in os.walk(pasta_site):
    for nome_arquivo in arquivos:
        if nome_arquivo.lower().endswith((".html", ".js", ".css")):
            caminho_completo = os.path.join(raiz, nome_arquivo)
            try:
                with open(caminho_completo, 'r', encoding='utf-8', errors='ignore') as f:
                    conteudo = f.read()
                if padrao.search(conteudo):
                    novo_conteudo = padrao.sub('.webp', conteudo)
                    with open(caminho_completo, 'w', encoding='utf-8') as f:
                        f.write(novo_conteudo)
                    relativo = os.path.relpath(caminho_completo, pasta_site)
                    print(f"✅ Atualizado: {relativo}")
                    arquivos_totais += 1
            except Exception as e:
                print(f"❌ Erro em {nome_arquivo}: {e}")

print(f"\n--- FIM: {arquivos_totais} arquivos corrigidos ---")
