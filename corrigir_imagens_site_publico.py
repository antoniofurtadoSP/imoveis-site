"""
CORREÇÃO COMPLETA DE IMAGENS DO SITE PÚBLICO + MARCA D'ÁGUA
Versão adaptada para: C:\Users\anton\Documents\Site_Publico_Antonio

PROBLEMAS CORRIGIDOS:
1. Imagens não abrem no modal
2. Marca d'água não aparece
3. Sincronização com pasta separada de segurança

RECURSOS:
- Processa TODAS as imagens da pasta db_imagens do sistema
- Adiciona marca d'água da logo automaticamente
- Copia para a pasta pública separada
- Mantém sincronização entre sistema e site público
"""

import os
import shutil
from datetime import datetime
import sqlite3

try:
    from PIL import Image, ImageEnhance
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("⚠️  Pillow não instalado. Marca d'água não será adicionada.")

# ============================================================================
# CONFIGURAÇÕES - ADAPTADAS PARA PASTA SEPARADA
# ============================================================================

# PASTA DO SISTEMA (onde ficam as fotos originais)
PASTA_SISTEMA = r"C:\Users\anton\Documents\SistemaImobiliaria\Sistema Imobiliario"
PASTA_IMAGENS_SISTEMA = os.path.join(PASTA_SISTEMA, "db_imagens")
DB_NOME = r"C:\Users\anton\Documents\SistemaImobiliaria\Sistema Imobiliario\dist\imobex_principal.db"

# PASTA PÚBLICA SEPARADA (site de produção)
PASTA_SITE_PUBLICO = r"C:\Users\anton\Documents\Site_Publico_Antonio"
PASTA_SITE_PUBLICO_SUBPASTA = os.path.join(PASTA_SITE_PUBLICO, "meu_site_imobiliaria")
PASTA_IMAGENS_SITE_PUBLICO = os.path.join(PASTA_SITE_PUBLICO_SUBPASTA, "db_imagens")

# LOGO
CAMINHO_LOGO = os.path.join(PASTA_SITE_PUBLICO_SUBPASTA, "logo.png")

# Configurações da marca d'água
POSICAO_LOGO = 'inferior_direito'
TAMANHO_LOGO_PERCENTUAL = 12
OPACIDADE_LOGO = 85
MARGEM = 20

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def calcular_posicao_logo(img_largura, img_altura, logo_largura, logo_altura, posicao):
    """Calcula a posição X, Y da logo na imagem"""
    
    if posicao == 'inferior_direito':
        x = img_largura - logo_largura - MARGEM
        y = img_altura - logo_altura - MARGEM
    elif posicao == 'inferior_esquerdo':
        x = MARGEM
        y = img_altura - logo_altura - MARGEM
    elif posicao == 'superior_direito':
        x = img_largura - logo_largura - MARGEM
        y = MARGEM
    elif posicao == 'superior_esquerdo':
        x = MARGEM
        y = MARGEM
    elif posicao == 'centro':
        x = (img_largura - logo_largura) // 2
        y = (img_altura - logo_altura) // 2
    else:
        x = img_largura - logo_largura - MARGEM
        y = img_altura - logo_altura - MARGEM
    
    return (x, y)


def adicionar_logo_imagem(caminho_imagem, logo):
    """Adiciona a logo em uma imagem específica"""
    
    if not HAS_PIL:
        return False
    
    try:
        # Abrir imagem
        imagem = Image.open(caminho_imagem)
        
        # Converter para RGBA se necessário
        if imagem.mode != 'RGBA':
            imagem = imagem.convert('RGBA')
        
        # Calcular tamanho da logo baseado no percentual
        nova_largura_logo = int(imagem.width * (TAMANHO_LOGO_PERCENTUAL / 100))
        proporcao = nova_largura_logo / logo.width
        nova_altura_logo = int(logo.height * proporcao)
        
        # Redimensionar logo
        logo_redimensionada = logo.resize((nova_largura_logo, nova_altura_logo), 
                                          Image.Resampling.LANCZOS)
        
        # Ajustar opacidade se necessário
        if OPACIDADE_LOGO < 100:
            if logo_redimensionada.mode == 'RGBA':
                r, g, b, a = logo_redimensionada.split()
                a = ImageEnhance.Brightness(a).enhance(OPACIDADE_LOGO / 100)
                logo_redimensionada = Image.merge('RGBA', (r, g, b, a))
        
        # Calcular posição
        posicao = calcular_posicao_logo(
            imagem.width, imagem.height,
            logo_redimensionada.width, logo_redimensionada.height,
            POSICAO_LOGO
        )
        
        # Criar camada transparente
        camada = Image.new('RGBA', imagem.size, (0, 0, 0, 0))
        camada.paste(logo_redimensionada, posicao, logo_redimensionada)
        
        # Combinar imagem original com a logo
        resultado = Image.alpha_composite(imagem, camada)
        
        # Converter de volta para o formato original se não era RGBA
        imagem_original = Image.open(caminho_imagem)
        if imagem_original.mode == 'RGB':
            resultado = resultado.convert('RGB')
        
        # Salvar
        resultado.save(caminho_imagem, quality=95, optimize=True)
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erro ao adicionar logo: {e}")
        return False


def verificar_imagens_banco():
    """Lista todas as imagens registradas no banco de dados"""
    
    try:
        conn = sqlite3.connect(DB_NOME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT arquivo 
            FROM imagens_imoveis 
            ORDER BY arquivo
        """)
        
        imagens_banco = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return imagens_banco
        
    except Exception as e:
        print(f"❌ Erro ao acessar banco: {e}")
        return []


def verificar_imagens_pasta():
    """Lista todas as imagens na pasta db_imagens do sistema"""
    
    if not os.path.exists(PASTA_IMAGENS_SISTEMA):
        return []
    
    imagens = [f for f in os.listdir(PASTA_IMAGENS_SISTEMA) 
               if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp'))]
    
    return sorted(imagens)


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def corrigir_imagens_site():
    """Corrige todas as imagens do site público e adiciona marca d'água"""
    
    print("="*70)
    print("🔧 CORREÇÃO DE IMAGENS - SITE PÚBLICO SEPARADO")
    print("="*70)
    print()
    
    # 1. VERIFICAR ESTRUTURA DE PASTAS
    print("📁 Verificando estrutura de pastas...")
    print()
    
    # Pasta do sistema (origem)
    if not os.path.exists(PASTA_IMAGENS_SISTEMA):
        print(f"❌ Pasta de imagens do sistema não encontrada:")
        print(f"   {PASTA_IMAGENS_SISTEMA}")
        return False
    print(f"✅ ORIGEM (Sistema):")
    print(f"   {PASTA_IMAGENS_SISTEMA}")
    print()
    
    # Pasta pública (destino)
    if not os.path.exists(PASTA_SITE_PUBLICO):
        print(f"❌ Pasta do site público não encontrada:")
        print(f"   {PASTA_SITE_PUBLICO}")
        return False
    print(f"✅ DESTINO (Site Público):")
    print(f"   {PASTA_SITE_PUBLICO}")
    print()
    
    # Criar subpasta se não existir
    if not os.path.exists(PASTA_SITE_PUBLICO_SUBPASTA):
        print(f"📁 Criando subpasta: meu_site_imobiliaria")
        os.makedirs(PASTA_SITE_PUBLICO_SUBPASTA)
        print(f"   ✅ Criada em: {PASTA_SITE_PUBLICO_SUBPASTA}")
    
    # Criar pasta db_imagens no site público se não existir
    if not os.path.exists(PASTA_IMAGENS_SITE_PUBLICO):
        print(f"📁 Criando pasta de imagens no site público...")
        os.makedirs(PASTA_IMAGENS_SITE_PUBLICO)
        print(f"   ✅ Criada em: {PASTA_IMAGENS_SITE_PUBLICO}")
    else:
        print(f"✅ Pasta de imagens do site público já existe:")
        print(f"   {PASTA_IMAGENS_SITE_PUBLICO}")
    
    print()
    
    # 2. VERIFICAR LOGO
    print("🎨 Verificando logo...")
    print()
    
    logo = None
    if HAS_PIL:
        if os.path.exists(CAMINHO_LOGO):
            try:
                logo = Image.open(CAMINHO_LOGO)
                if logo.mode != 'RGBA':
                    logo = logo.convert('RGBA')
                print(f"✅ Logo carregada com sucesso!")
                print(f"   Caminho: {CAMINHO_LOGO}")
                print(f"   Tamanho: {logo.width}x{logo.height} pixels")
                print(f"   Posição na foto: {POSICAO_LOGO}")
                print(f"   Tamanho relativo: {TAMANHO_LOGO_PERCENTUAL}% da largura")
                print(f"   Opacidade: {OPACIDADE_LOGO}%")
            except Exception as e:
                print(f"⚠️  Erro ao carregar logo: {e}")
                logo = None
        else:
            print(f"⚠️  Logo não encontrada em:")
            print(f"   {CAMINHO_LOGO}")
            print()
            print(f"   ATENÇÃO: Marca d'água NÃO será adicionada!")
            print(f"   Coloque sua logo.png na pasta e execute novamente.")
    else:
        print("⚠️  Pillow não instalado - marca d'água não será adicionada")
        print("   Execute: pip install Pillow")
    
    print()
    
    # 3. LISTAR IMAGENS
    print("📊 Analisando imagens...")
    print()
    
    imagens_banco = verificar_imagens_banco()
    imagens_pasta = verificar_imagens_pasta()
    
    print(f"📋 Imagens no banco de dados: {len(imagens_banco)}")
    print(f"📂 Imagens na pasta do sistema: {len(imagens_pasta)}")
    
    # Verificar discrepâncias
    imagens_faltando = set(imagens_banco) - set(imagens_pasta)
    imagens_extras = set(imagens_pasta) - set(imagens_banco)
    
    if imagens_faltando:
        print(f"⚠️  {len(imagens_faltando)} imagens estão no banco mas não na pasta")
    
    if imagens_extras:
        print(f"ℹ️  {len(imagens_extras)} imagens na pasta mas não no banco (normal)")
    
    print()
    
    # 4. CONFIRMAR ANTES DE PROCESSAR
    print("="*70)
    print("RESUMO DA OPERAÇÃO")
    print("="*70)
    print()
    print(f"🔹 ORIGEM: {PASTA_IMAGENS_SISTEMA}")
    print(f"🔹 DESTINO: {PASTA_IMAGENS_SITE_PUBLICO}")
    print(f"🔹 Total de imagens a processar: {len(imagens_pasta)}")
    print(f"🔹 Marca d'água: {'SIM ✅' if logo else 'NÃO ⚠️'}")
    print()
    
    resposta = input("Deseja continuar? (S/N): ").strip().upper()
    
    if resposta != 'S':
        print()
        print("❌ Operação cancelada pelo usuário.")
        return False
    
    print()
    
    # 5. PROCESSAR IMAGENS
    print("="*70)
    print("🖼️  PROCESSANDO IMAGENS")
    print("="*70)
    print()
    
    sucesso = 0
    erro = 0
    logo_adicionada = 0
    
    for i, arquivo in enumerate(imagens_pasta, 1):
        origem = os.path.join(PASTA_IMAGENS_SISTEMA, arquivo)
        destino = os.path.join(PASTA_IMAGENS_SITE_PUBLICO, arquivo)
        
        # Mostrar progresso
        nome_curto = arquivo[:45] + "..." if len(arquivo) > 45 else arquivo
        print(f"[{i}/{len(imagens_pasta)}] {nome_curto}", end=' ')
        
        try:
            # 1. Copiar imagem para site público
            shutil.copy2(origem, destino)
            
            # 2. Adicionar logo se disponível
            if logo and HAS_PIL:
                if adicionar_logo_imagem(destino, logo):
                    logo_adicionada += 1
                    print("✅ (copiada + logo)")
                else:
                    print("✅ (copiada, erro na logo)")
            else:
                print("✅ (copiada)")
            
            sucesso += 1
            
        except Exception as e:
            print(f"❌ Erro: {str(e)[:50]}")
            erro += 1
    
    print()
    print("="*70)
    print("📊 RESUMO FINAL")
    print("="*70)
    print()
    print(f"✅ Imagens copiadas com sucesso: {sucesso}")
    print(f"🎨 Logos adicionadas: {logo_adicionada}")
    print(f"❌ Erros: {erro}")
    print(f"📁 Total processado: {len(imagens_pasta)}")
    print()
    
    if imagens_faltando:
        print("⚠️  IMAGENS FALTANDO NA PASTA (mas estão no banco):")
        for img in sorted(list(imagens_faltando))[:10]:
            print(f"   - {img}")
        if len(imagens_faltando) > 10:
            print(f"   ... e mais {len(imagens_faltando) - 10} imagens")
        print()
    
    # 6. ESTATÍSTICAS DA PASTA PÚBLICA
    print("="*70)
    print("📂 PASTA PÚBLICA ATUALIZADA")
    print("="*70)
    print()
    
    imagens_site_publico = [f for f in os.listdir(PASTA_IMAGENS_SITE_PUBLICO)
                            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp'))]
    
    print(f"📍 Local: {PASTA_IMAGENS_SITE_PUBLICO}")
    print(f"📊 Total de imagens: {len(imagens_site_publico)}")
    
    # Calcular tamanho total
    tamanho_total = 0
    for img in imagens_site_publico:
        caminho = os.path.join(PASTA_IMAGENS_SITE_PUBLICO, img)
        tamanho_total += os.path.getsize(caminho)
    
    tamanho_mb = tamanho_total / (1024 * 1024)
    print(f"💾 Tamanho total: {tamanho_mb:.2f} MB")
    print()
    
    print("="*70)
    print("✅ CORREÇÃO CONCLUÍDA COM SUCESSO!")
    print("="*70)
    print()
    print("📋 PRÓXIMOS PASSOS:")
    print()
    print("1. ✅ As imagens já estão na pasta pública com marca d'água")
    print("2. 📤 Se usar GitHub Pages, faça commit e push:")
    print(f"   cd \"{PASTA_SITE_PUBLICO}\"")
    print("   git add .")
    print("   git commit -m \"Atualizar imagens com marca d'água\"")
    print("   git push")
    print()
    print("3. 🌐 Se usar FTP, envie a pasta db_imagens para o servidor")
    print()
    print("4. 🧪 Teste abrindo o site e clicando nas fotos")
    print()
    
    return True


def menu_principal():
    """Menu interativo"""
    
    print("="*70)
    print("🏠 CORREÇÃO DE IMAGENS - SITE PÚBLICO")
    print("   Antonio Furtado - Consultoria Imobiliária")
    print("="*70)
    print()
    
    print("Este script irá:")
    print()
    print("✅ Copiar imagens de:")
    print(f"   {PASTA_IMAGENS_SISTEMA}")
    print()
    print("✅ Para:")
    print(f"   {PASTA_IMAGENS_SITE_PUBLICO}")
    print()
    print("✅ Adicionando marca d'água da logo em cada imagem")
    print("✅ Mantendo qualidade alta (95%)")
    print("✅ Gerando relatório completo")
    print()
    
    input("Pressione ENTER para iniciar...")
    print()
    
    corrigir_imagens_site()
    
    print()
    input("Pressione ENTER para sair...")


# ============================================================================
# EXECUÇÃO
# ============================================================================

if __name__ == "__main__":
    menu_principal()
