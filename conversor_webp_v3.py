#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Conversão Automática de Imagens para WebP
Sistema Imobiliária - Otimização de Imagens

Versão 3.0 - Com detecção automática do campo de imagens no banco
"""

import os
import sys
import sqlite3
import shutil
from PIL import Image
from datetime import datetime
from pathlib import Path
import glob

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

# Caminho do banco de dados (ajuste se necessário)
CAMINHO_USUARIO = r"C:\Users\anton\Documents\SistemaImobiliaria\Sistema Imobiliario"
if os.path.exists(CAMINHO_USUARIO):
    PASTA_ATUAL = CAMINHO_USUARIO
else:
    PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))

# Detecta automaticamente o banco de dados
def detectar_banco_dados():
    """Detecta automaticamente o arquivo de banco de dados SQLite"""
    # Lista de possíveis nomes
    possiveis_nomes = [
        "sistema_imobiliaria.db",
        "imobiliaria.db",
        "imoveis.db",
        "database.db",
        "db.db"
    ]
    
    # Procura pelos nomes conhecidos
    for nome in possiveis_nomes:
        caminho = os.path.join(PASTA_ATUAL, nome)
        if os.path.exists(caminho):
            return caminho
    
    # Se não encontrou, procura por qualquer arquivo .db
    arquivos_db = glob.glob(os.path.join(PASTA_ATUAL, "*.db"))
    if arquivos_db:
        # Retorna o primeiro encontrado
        return arquivos_db[0]
    
    return None

def detectar_campo_imagens(db_path):
    """
    Detecta automaticamente o nome do campo que armazena as imagens
    
    Returns:
        tuple: (nome_tabela, nome_campo) ou (None, None) se não encontrar
    """
    if not db_path or not os.path.exists(db_path):
        return None, None
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Lista todas as tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tabelas = [row[0] for row in cursor.fetchall()]
        
        # Possíveis nomes de campos
        possiveis_campos = [
            'imagens', 'fotos', 'lista_imagens', 'paths_imagens',
            'arquivos', 'files', 'images', 'photos', 'img',
            'imagem', 'foto', 'arquivo_imagem', 'path_imagem'
        ]
        
        # Procura em cada tabela
        for tabela in tabelas:
            try:
                cursor.execute(f"PRAGMA table_info({tabela})")
                colunas = [row[1] for row in cursor.fetchall()]
                
                # Verifica se algum campo conhecido existe
                for campo in possiveis_campos:
                    if campo in colunas:
                        conn.close()
                        return tabela, campo
                
                # Se não encontrou nos nomes conhecidos, procura campos que contenham "imag" ou "foto"
                for coluna in colunas:
                    if 'imag' in coluna.lower() or 'foto' in coluna.lower() or 'image' in coluna.lower():
                        conn.close()
                        return tabela, coluna
                        
            except Exception as e:
                continue
        
        conn.close()
        return None, None
        
    except Exception as e:
        print(f"Erro ao detectar campo de imagens: {e}")
        return None, None

DB_NOME = detectar_banco_dados()
TABELA_IMAGENS, CAMPO_IMAGENS = detectar_campo_imagens(DB_NOME) if DB_NOME else (None, None)

PASTA_IMAGENS = os.path.join(PASTA_ATUAL, "db_imagens")
PASTA_BACKUP = os.path.join(PASTA_ATUAL, "backup_imagens_originais")

# Configurações de conversão
QUALIDADE_WEBP = 85  # Qualidade de 1-100 (85 é um bom balanço)
FORMATOS_SUPORTADOS = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif']
BACKUP_ORIGINAIS = True  # Se True, cria backup das imagens originais
MODO_DEBUG = True  # Mostra mensagens detalhadas

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def criar_pasta_backup():
    """Cria pasta de backup se não existir"""
    if BACKUP_ORIGINAIS and not os.path.exists(PASTA_BACKUP):
        os.makedirs(PASTA_BACKUP)
        print(f"✅ Pasta de backup criada: {PASTA_BACKUP}")
    return PASTA_BACKUP

def verificar_ambiente():
    """Verifica se o ambiente está correto para execução"""
    erros = []
    avisos = []
    
    # Verifica banco de dados
    if not DB_NOME:
        avisos.append("⚠️  Nenhum banco de dados SQLite encontrado na pasta")
        avisos.append(f"   Pasta verificada: {PASTA_ATUAL}")
        avisos.append("")
        avisos.append("   💡 O script ainda pode converter as imagens, mas não atualizará o banco.")
    elif not os.path.exists(DB_NOME):
        avisos.append(f"⚠️  Banco de dados não acessível: {DB_NOME}")
    else:
        print(f"✅ Banco de dados encontrado: {os.path.basename(DB_NOME)}")
        
        if TABELA_IMAGENS and CAMPO_IMAGENS:
            print(f"✅ Campo de imagens detectado: {TABELA_IMAGENS}.{CAMPO_IMAGENS}")
        else:
            avisos.append("⚠️  Campo de imagens não detectado automaticamente")
            avisos.append("   O banco de dados não será atualizado")
    
    # Verifica pasta de imagens
    if not os.path.exists(PASTA_IMAGENS):
        erros.append(f"❌ Pasta de imagens não encontrada: {PASTA_IMAGENS}")
        erros.append(f"   Certifique-se de que a pasta 'db_imagens' existe")
    else:
        # Conta quantas imagens existem
        total_arquivos = len([f for f in os.listdir(PASTA_IMAGENS) if os.path.isfile(os.path.join(PASTA_IMAGENS, f))])
        print(f"✅ Pasta de imagens encontrada com {total_arquivos} arquivo(s)")
    
    # Verifica Pillow
    try:
        from PIL import Image
        print("✅ Biblioteca Pillow instalada")
    except ImportError:
        erros.append("❌ Biblioteca Pillow não instalada. Execute: pip install Pillow")
    
    if avisos:
        print("\n" + "\n".join(avisos))
    
    if erros:
        print("\n" + "\n".join(erros))
        return False
    
    return True

def listar_imagens_nao_webp():
    """Lista todas as imagens que não estão em formato WebP"""
    imagens_converter = []
    
    if not os.path.exists(PASTA_IMAGENS):
        print(f"⚠️  Pasta de imagens não existe: {PASTA_IMAGENS}")
        return []
    
    for arquivo in os.listdir(PASTA_IMAGENS):
        caminho_completo = os.path.join(PASTA_IMAGENS, arquivo)
        
        # Ignora diretórios
        if os.path.isdir(caminho_completo):
            continue
        
        # Verifica extensão
        _, extensao = os.path.splitext(arquivo)
        extensao_lower = extensao.lower()
        
        if extensao_lower in FORMATOS_SUPORTADOS:
            imagens_converter.append({
                'nome': arquivo,
                'caminho': caminho_completo,
                'extensao': extensao_lower,
                'tamanho': os.path.getsize(caminho_completo)
            })
    
    return imagens_converter

def converter_para_webp(caminho_origem, qualidade=QUALIDADE_WEBP):
    """
    Converte uma imagem para formato WebP
    
    Args:
        caminho_origem: Caminho completo da imagem original
        qualidade: Qualidade da compressão (1-100)
    
    Returns:
        dict com informações da conversão ou None em caso de erro
    """
    try:
        # Abre a imagem
        img = Image.open(caminho_origem)
        
        # Converte RGBA para RGB se necessário (WebP não suporta transparência em alguns casos)
        if img.mode == 'RGBA':
            # Cria um fundo branco
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # 3 é o canal alpha
            img = background
        elif img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        
        # Define nome do arquivo WebP
        nome_arquivo, _ = os.path.splitext(os.path.basename(caminho_origem))
        nome_webp = f"{nome_arquivo}.webp"
        caminho_webp = os.path.join(PASTA_IMAGENS, nome_webp)
        
        # Verifica se já existe
        if os.path.exists(caminho_webp):
            nome_webp = f"{nome_arquivo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webp"
            caminho_webp = os.path.join(PASTA_IMAGENS, nome_webp)
        
        # Salva em WebP
        tamanho_original = os.path.getsize(caminho_origem)
        img.save(caminho_webp, 'WEBP', quality=qualidade, method=6)
        tamanho_webp = os.path.getsize(caminho_webp)
        
        # Calcula economia
        economia_bytes = tamanho_original - tamanho_webp
        economia_percent = (economia_bytes / tamanho_original) * 100 if tamanho_original > 0 else 0
        
        return {
            'sucesso': True,
            'original': caminho_origem,
            'webp': caminho_webp,
            'nome_webp': nome_webp,
            'tamanho_original': tamanho_original,
            'tamanho_webp': tamanho_webp,
            'economia_bytes': economia_bytes,
            'economia_percent': economia_percent
        }
        
    except Exception as e:
        return {
            'sucesso': False,
            'original': caminho_origem,
            'erro': str(e)
        }

def fazer_backup(caminho_arquivo):
    """Cria backup do arquivo original"""
    if not BACKUP_ORIGINAIS:
        return None
    
    try:
        nome_arquivo = os.path.basename(caminho_arquivo)
        caminho_backup = os.path.join(PASTA_BACKUP, nome_arquivo)
        
        # Se já existe, adiciona timestamp
        if os.path.exists(caminho_backup):
            nome, ext = os.path.splitext(nome_arquivo)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_arquivo = f"{nome}_{timestamp}{ext}"
            caminho_backup = os.path.join(PASTA_BACKUP, nome_arquivo)
        
        shutil.copy2(caminho_arquivo, caminho_backup)
        return caminho_backup
        
    except Exception as e:
        print(f"⚠️  Erro ao criar backup de {nome_arquivo}: {e}")
        return None

def atualizar_banco_dados(caminho_original, nome_webp):
    """
    Atualiza o banco de dados substituindo referências da imagem antiga pela nova
    
    Args:
        caminho_original: Caminho completo da imagem original
        nome_webp: Nome do novo arquivo WebP
    
    Returns:
        int: Número de registros atualizados
    """
    if not DB_NOME or not os.path.exists(DB_NOME):
        return 0
    
    if not TABELA_IMAGENS or not CAMPO_IMAGENS:
        return 0
    
    try:
        nome_original = os.path.basename(caminho_original)
        
        conn = sqlite3.connect(DB_NOME)
        cursor = conn.cursor()
        
        # Atualiza o campo detectado
        query = f"""
            UPDATE {TABELA_IMAGENS} 
            SET {CAMPO_IMAGENS} = REPLACE({CAMPO_IMAGENS}, ?, ?)
            WHERE {CAMPO_IMAGENS} LIKE ?
        """
        
        cursor.execute(query, (nome_original, nome_webp, f'%{nome_original}%'))
        
        registros_atualizados = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return registros_atualizados
        
    except Exception as e:
        print(f"⚠️  Erro ao atualizar banco de dados: {e}")
        return 0

def formatar_tamanho(bytes):
    """Formata tamanho em bytes para formato legível"""
    for unidade in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unidade}"
        bytes /= 1024.0
    return f"{bytes:.2f} TB"

# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def converter_todas_imagens():
    """Converte todas as imagens para WebP e atualiza o banco de dados"""
    
    print("=" * 70)
    print("🔄 CONVERSÃO AUTOMÁTICA DE IMAGENS PARA WEBP")
    print("=" * 70)
    print()
    
    # Verifica ambiente
    if not verificar_ambiente():
        return
    
    # Cria backup se necessário
    if BACKUP_ORIGINAIS:
        criar_pasta_backup()
    
    # Lista imagens para converter
    print("\n📂 Buscando imagens para converter...")
    imagens = listar_imagens_nao_webp()
    
    if not imagens:
        print("✅ Nenhuma imagem encontrada para conversão. Todas já estão em WebP!")
        return
    
    print(f"📊 Encontradas {len(imagens)} imagens para converter")
    print()
    
    # Pergunta confirmação
    resposta = input("Deseja continuar com a conversão? (S/N): ").strip().upper()
    if resposta != 'S':
        print("❌ Conversão cancelada pelo usuário.")
        return
    
    print()
    
    # Estatísticas
    total_imagens = len(imagens)
    convertidas = 0
    erros = 0
    economia_total = 0
    registros_atualizados_total = 0
    
    # Processa cada imagem
    for i, img_info in enumerate(imagens, 1):
        print(f"[{i}/{total_imagens}] Processando: {img_info['nome']}")
        
        # Faz backup
        backup_path = None
        if BACKUP_ORIGINAIS:
            backup_path = fazer_backup(img_info['caminho'])
            if MODO_DEBUG and backup_path:
                print(f"  ✅ Backup criado: {os.path.basename(backup_path)}")
        
        # Converte para WebP
        resultado = converter_para_webp(img_info['caminho'])
        
        if resultado['sucesso']:
            convertidas += 1
            economia_total += resultado['economia_bytes']
            
            if MODO_DEBUG:
                print(f"  ✅ Convertido: {resultado['nome_webp']}")
                print(f"     Original: {formatar_tamanho(resultado['tamanho_original'])}")
                print(f"     WebP: {formatar_tamanho(resultado['tamanho_webp'])}")
                print(f"     Economia: {formatar_tamanho(resultado['economia_bytes'])} ({resultado['economia_percent']:.1f}%)")
            
            # Atualiza banco de dados
            if TABELA_IMAGENS and CAMPO_IMAGENS:
                registros = atualizar_banco_dados(img_info['caminho'], resultado['nome_webp'])
                registros_atualizados_total += registros
                
                if MODO_DEBUG and registros > 0:
                    print(f"  📝 Banco atualizado: {registros} registro(s)")
            
            # Remove arquivo original (apenas se backup foi criado com sucesso)
            if BACKUP_ORIGINAIS and backup_path:
                try:
                    os.remove(img_info['caminho'])
                    if MODO_DEBUG:
                        print(f"  🗑️  Original removido (backup salvo)")
                except Exception as e:
                    print(f"  ⚠️  Não foi possível remover original: {e}")
        else:
            erros += 1
            print(f"  ❌ Erro: {resultado['erro']}")
        
        print()
    
    # Relatório final
    print("=" * 70)
    print("📊 RELATÓRIO FINAL DA CONVERSÃO")
    print("=" * 70)
    print(f"Total de imagens processadas: {total_imagens}")
    print(f"✅ Convertidas com sucesso: {convertidas}")
    print(f"❌ Erros: {erros}")
    print(f"💾 Economia total de espaço: {formatar_tamanho(economia_total)}")
    
    if TABELA_IMAGENS and CAMPO_IMAGENS:
        print(f"📝 Registros no banco atualizados: {registros_atualizados_total}")
    else:
        print(f"⚠️  Campo de imagens não detectado - referências não atualizadas")
        print(f"   💡 Você precisará atualizar manualmente ou informar o nome do campo")
    
    if BACKUP_ORIGINAIS:
        print(f"🔒 Backup das originais em: {PASTA_BACKUP}")
    
    print("=" * 70)
    print()
    
    if convertidas > 0:
        print("✅ Conversão concluída com sucesso!")
        print("💡 Dica: As imagens WebP são mais leves e carregam mais rápido no site.")
        
        if not TABELA_IMAGENS or not CAMPO_IMAGENS:
            print("\n⚠️  ATENÇÃO: O banco de dados não foi atualizado automaticamente.")
            print("   Execute a opção [6] do menu para atualizar manualmente.")
    else:
        print("⚠️  Nenhuma imagem foi convertida.")

# ============================================================================
# FUNÇÕES ADICIONAIS
# ============================================================================

def converter_imagem_unica(caminho_imagem):
    """
    Converte uma única imagem para WebP
    Útil para integração com o sistema principal
    """
    if not os.path.exists(caminho_imagem):
        print(f"❌ Arquivo não encontrado: {caminho_imagem}")
        return None
    
    _, ext = os.path.splitext(caminho_imagem)
    if ext.lower() not in FORMATOS_SUPORTADOS:
        print(f"⚠️  Formato não suportado: {ext}")
        return None
    
    # Faz backup
    if BACKUP_ORIGINAIS:
        criar_pasta_backup()
        fazer_backup(caminho_imagem)
    
    # Converte
    resultado = converter_para_webp(caminho_imagem)
    
    if resultado['sucesso']:
        # Atualiza banco
        if TABELA_IMAGENS and CAMPO_IMAGENS:
            atualizar_banco_dados(caminho_imagem, resultado['nome_webp'])
        
        # Remove original
        if BACKUP_ORIGINAIS:
            try:
                os.remove(caminho_imagem)
            except Exception as e:
                print(f"⚠️  Não foi possível remover original: {e}")
        
        return resultado['caminho_webp']
    
    return None

def listar_estatisticas():
    """Mostra estatísticas das imagens no sistema"""
    print("=" * 70)
    print("📊 ESTATÍSTICAS DE IMAGENS")
    print("=" * 70)
    print()
    
    if not os.path.exists(PASTA_IMAGENS):
        print("❌ Pasta de imagens não encontrada")
        return
    
    total_arquivos = 0
    total_webp = 0
    total_outros = 0
    tamanho_total = 0
    tamanho_webp = 0
    tamanho_outros = 0
    
    for arquivo in os.listdir(PASTA_IMAGENS):
        caminho = os.path.join(PASTA_IMAGENS, arquivo)
        if os.path.isfile(caminho):
            total_arquivos += 1
            tamanho_arquivo = os.path.getsize(caminho)
            tamanho_total += tamanho_arquivo
            
            _, ext = os.path.splitext(arquivo)
            if ext.lower() == '.webp':
                total_webp += 1
                tamanho_webp += tamanho_arquivo
            elif ext.lower() in FORMATOS_SUPORTADOS:
                total_outros += 1
                tamanho_outros += tamanho_arquivo
    
    print(f"📁 Pasta: {PASTA_IMAGENS}")
    print(f"📊 Total de arquivos: {total_arquivos}")
    print(f"✅ Imagens WebP: {total_webp} ({formatar_tamanho(tamanho_webp)})")
    print(f"📷 Outras imagens: {total_outros} ({formatar_tamanho(tamanho_outros)})")
    print(f"💾 Tamanho total: {formatar_tamanho(tamanho_total)}")
    
    if DB_NOME:
        print(f"🗄️  Banco de dados: {os.path.basename(DB_NOME)}")
        if TABELA_IMAGENS and CAMPO_IMAGENS:
            print(f"📝 Campo de imagens: {TABELA_IMAGENS}.{CAMPO_IMAGENS}")
        else:
            print(f"⚠️  Campo de imagens: Não detectado")
    else:
        print(f"⚠️  Banco de dados: Não encontrado")
    
    print()
    
    if total_outros > 0:
        percentual = (total_outros / total_arquivos) * 100 if total_arquivos > 0 else 0
        economia_estimada = tamanho_outros * 0.4  # Estimativa conservadora de 40% de economia
        print(f"⚠️  {percentual:.1f}% das imagens ainda podem ser convertidas para WebP")
        print(f"💡 Economia estimada: {formatar_tamanho(economia_estimada)}")
    else:
        print("✅ Todas as imagens estão em formato WebP!")
    
    print("=" * 70)

def listar_bancos_disponiveis():
    """Lista todos os bancos de dados SQLite disponíveis na pasta"""
    print("\n🔍 Procurando bancos de dados SQLite...")
    arquivos_db = glob.glob(os.path.join(PASTA_ATUAL, "*.db"))
    
    if not arquivos_db:
        print("❌ Nenhum arquivo .db encontrado na pasta")
        print(f"   Pasta verificada: {PASTA_ATUAL}")
        return None
    
    print(f"\n📊 Encontrados {len(arquivos_db)} arquivo(s) .db:\n")
    for i, db in enumerate(arquivos_db, 1):
        nome = os.path.basename(db)
        tamanho = os.path.getsize(db)
        print(f"  [{i}] {nome} ({formatar_tamanho(tamanho)})")
        
        # Tenta detectar o campo de imagens
        tabela, campo = detectar_campo_imagens(db)
        if tabela and campo:
            print(f"      ✅ Campo detectado: {tabela}.{campo}")
        else:
            print(f"      ⚠️  Campo de imagens não detectado")
    
    return arquivos_db

def atualizar_banco_manualmente():
    """Permite ao usuário atualizar o banco de dados manualmente"""
    print("\n" + "=" * 70)
    print("🔧 ATUALIZAÇÃO MANUAL DO BANCO DE DADOS")
    print("=" * 70)
    print()
    
    if not DB_NOME:
        print("❌ Nenhum banco de dados encontrado")
        return
    
    print(f"📁 Banco de dados: {os.path.basename(DB_NOME)}")
    print()
    
    # Lista tabelas disponíveis
    try:
        conn = sqlite3.connect(DB_NOME)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tabelas = [row[0] for row in cursor.fetchall()]
        
        print("📊 Tabelas disponíveis:")
        for i, tabela in enumerate(tabelas, 1):
            print(f"  [{i}] {tabela}")
        
        print()
        tabela_escolhida = input("Digite o nome da tabela (ou número): ").strip()
        
        # Se digitou número, converte
        if tabela_escolhida.isdigit():
            idx = int(tabela_escolhida) - 1
            if 0 <= idx < len(tabelas):
                tabela_escolhida = tabelas[idx]
        
        # Verifica se a tabela existe
        if tabela_escolhida not in tabelas:
            print(f"❌ Tabela '{tabela_escolhida}' não encontrada")
            conn.close()
            return
        
        # Lista campos da tabela
        cursor.execute(f"PRAGMA table_info({tabela_escolhida})")
        campos = [row[1] for row in cursor.fetchall()]
        
        print(f"\n📝 Campos da tabela '{tabela_escolhida}':")
        for i, campo in enumerate(campos, 1):
            print(f"  [{i}] {campo}")
        
        print()
        campo_escolhido = input("Digite o nome do campo de imagens (ou número): ").strip()
        
        # Se digitou número, converte
        if campo_escolhido.isdigit():
            idx = int(campo_escolhido) - 1
            if 0 <= idx < len(campos):
                campo_escolhido = campos[idx]
        
        # Verifica se o campo existe
        if campo_escolhido not in campos:
            print(f"❌ Campo '{campo_escolhido}' não encontrado")
            conn.close()
            return
        
        conn.close()
        
        # Agora atualiza todas as referências
        print(f"\n🔄 Atualizando {tabela_escolhida}.{campo_escolhido}...")
        
        total_atualizados = 0
        
        # Procura todos os pares de imagem original -> webp
        for arquivo in os.listdir(PASTA_IMAGENS):
            if arquivo.endswith('.webp'):
                # Remove .webp e procura possíveis originais
                base = arquivo[:-5]  # Remove .webp
                
                for ext in FORMATOS_SUPORTADOS:
                    original = base + ext
                    caminho_original = os.path.join(PASTA_IMAGENS, original)
                    
                    # Se o original não existe mais (foi removido), tenta atualizar
                    if not os.path.exists(caminho_original):
                        try:
                            conn = sqlite3.connect(DB_NOME)
                            cursor = conn.cursor()
                            
                            query = f"""
                                UPDATE {tabela_escolhida}
                                SET {campo_escolhido} = REPLACE({campo_escolhido}, ?, ?)
                                WHERE {campo_escolhido} LIKE ?
                            """
                            
                            cursor.execute(query, (original, arquivo, f'%{original}%'))
                            
                            if cursor.rowcount > 0:
                                total_atualizados += cursor.rowcount
                                print(f"  ✅ {original} → {arquivo} ({cursor.rowcount} registro(s))")
                            
                            conn.commit()
                            conn.close()
                            
                        except Exception as e:
                            print(f"  ⚠️  Erro ao atualizar {original}: {e}")
        
        print(f"\n✅ Total de registros atualizados: {total_atualizados}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")

# ============================================================================
# MENU INTERATIVO
# ============================================================================

def menu_principal():
    """Menu interativo para o usuário"""
    while True:
        print("\n" + "=" * 70)
        print("🖼️  CONVERSOR DE IMAGENS PARA WEBP - SISTEMA IMOBILIÁRIA")
        print("=" * 70)
        print("\n[1] Converter todas as imagens para WebP")
        print("[2] Mostrar estatísticas das imagens")
        print("[3] Converter uma imagem específica")
        print("[4] Configurações e informações")
        print("[5] Listar bancos de dados disponíveis")
        print("[6] Atualizar banco de dados manualmente")
        print("[0] Sair")
        print()
        
        opcao = input("Escolha uma opção: ").strip()
        
        if opcao == "1":
            print()
            converter_todas_imagens()
            input("\nPressione ENTER para continuar...")
            
        elif opcao == "2":
            print()
            listar_estatisticas()
            input("\nPressione ENTER para continuar...")
            
        elif opcao == "3":
            print()
            caminho = input("Digite o caminho completo da imagem: ").strip()
            resultado = converter_imagem_unica(caminho)
            if resultado:
                print(f"✅ Imagem convertida: {resultado}")
            input("\nPressione ENTER para continuar...")
            
        elif opcao == "4":
            print("\n" + "=" * 70)
            print("📝 CONFIGURAÇÕES E INFORMAÇÕES")
            print("=" * 70)
            print(f"\n📁 Pasta do sistema: {PASTA_ATUAL}")
            print(f"🖼️  Pasta de imagens: {PASTA_IMAGENS}")
            if DB_NOME:
                print(f"🗄️  Banco de dados: {os.path.basename(DB_NOME)}")
                if TABELA_IMAGENS and CAMPO_IMAGENS:
                    print(f"📝 Campo detectado: {TABELA_IMAGENS}.{CAMPO_IMAGENS}")
                else:
                    print(f"⚠️  Campo de imagens: Não detectado")
            else:
                print(f"⚠️  Banco de dados: Não encontrado")
            print(f"🔒 Pasta de backup: {PASTA_BACKUP}")
            print(f"\n⚙️  Qualidade WebP: {QUALIDADE_WEBP}")
            print(f"💾 Backup de originais: {'Sim' if BACKUP_ORIGINAIS else 'Não'}")
            print(f"🐛 Modo debug: {'Sim' if MODO_DEBUG else 'Não'}")
            print(f"📋 Formatos suportados: {', '.join(FORMATOS_SUPORTADOS)}")
            input("\nPressione ENTER para continuar...")
            
        elif opcao == "5":
            listar_bancos_disponiveis()
            input("\nPressione ENTER para continuar...")
            
        elif opcao == "6":
            atualizar_banco_manualmente()
            input("\nPressione ENTER para continuar...")
            
        elif opcao == "0":
            print("\n👋 Até logo!")
            break
        
        else:
            print("\n❌ Opção inválida!")
            input("Pressione ENTER para continuar...")

# ============================================================================
# EXECUÇÃO
# ============================================================================

if __name__ == "__main__":
    # Se executado diretamente, mostra o menu
    if len(sys.argv) == 1:
        menu_principal()
    
    # Se chamado com argumentos, executa conversão direta
    elif len(sys.argv) == 2 and sys.argv[1] == "--auto":
        converter_todas_imagens()
    
    elif len(sys.argv) == 2 and sys.argv[1] == "--stats":
        listar_estatisticas()
    
    else:
        print("Uso:")
        print("  python conversor_webp.py           # Menu interativo")
        print("  python conversor_webp.py --auto    # Conversão automática")
        print("  python conversor_webp.py --stats   # Mostra estatísticas")
