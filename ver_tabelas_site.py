import sqlite3

try:
    conn = sqlite3.connect('banco_imobiliaria.db')
    cursor = conn.cursor()
    
    # Lista todas as tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabelas = cursor.fetchall()
    
    print("\n--- TABELAS ENCONTRADAS NO SITE PÚBLICO ---")
    for t in tabelas:
        print(f"Tabela: {t[0]}")
        # Para cada tabela, mostra as colunas
        cursor.execute(f"PRAGMA table_info({t[0]})")
        colunas = [col[1] for col in cursor.fetchall()]
        print(f"   Colunas: {colunas}")
    
    conn.close()
except Exception as e:
    print(f"Erro: {e}")