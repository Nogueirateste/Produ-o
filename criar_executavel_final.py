import os
import sys
import subprocess
import shutil

def main():
    print("Iniciando a criação do executável do Análise de Produtividade de Manobristas")
    print("===========================================================================")

    # Verificar se PyInstaller está instalado
    try:
        import PyInstaller
        print("✓ PyInstaller está instalado.")
    except ImportError:
        print("✗ PyInstaller não encontrado. Instalando...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller instalado com sucesso.")

    # Verificar outras dependências
    dependencias = ["streamlit", "pandas", "openpyxl"]
    for dep in dependencias:
        try:
            __import__(dep)
            print(f"✓ {dep} está instalado.")
        except ImportError:
            print(f"✗ {dep} não encontrado. Instalando...")
            subprocess.run([sys.executable, "-m", "pip", "install", dep])
            print(f"✓ {dep} instalado com sucesso.")

    # Criar funcionarios.csv vazio se não existir
    if not os.path.exists("funcionarios.csv"):
        with open("funcionarios.csv", "w", encoding="utf-8") as f:
            f.write("matricula,nome,tipo,ativo\n")
        print("✓ Arquivo de banco de dados vazio criado.")
    else:
        print("✓ Arquivo de banco de dados encontrado.")

    # Limpar diretórios antigos
    for dir_name in ['dist', 'build']:
        if os.path.exists(dir_name):
            print(f"Removendo diretório {dir_name} antigo...")
            shutil.rmtree(dir_name)
    
    # Remover .spec antigo se existir
    spec_file = "AnaliseProdutividadeManobristas.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)
    
    print("\nConstruindo o executável...")
    
    # Caminho para o ícone (se existir)
    icon_path = ""
    if os.path.exists("generated-icon.png"):
        icon_path = "--icon=generated-icon.png"
    
    # Comando para executar o PyInstaller
    comando = [
        sys.executable, 
        "-m", 
        "PyInstaller",
        "app_launcher.py",  # Ponto de entrada que contém todos os arquivos embutidos
        "--onefile",
        "--name=AnaliseProdutividadeManobristas",
        # Importações ocultas mínimas necessárias
        "--hidden-import=streamlit",
        "--hidden-import=pandas",
        "--hidden-import=openpyxl",
        "--hidden-import=numpy",
        "--hidden-import=matplotlib",
        "--hidden-import=plotly",
        "--hidden-import=plotly.graph_objects",
        "--hidden-import=plotly.express",
        # Coleções de módulos
        "--collect-all=streamlit",
        "--collect-all=plotly",
        "--collect-all=matplotlib",
        # Adicionar funcionarios.csv para ser extraído no diretório raiz
        "--add-data=funcionarios.csv;."
    ]
    
    # Adicionar ícone se existir
    if icon_path:
        comando.append(icon_path)
    
    # Executar o comando
    try:
        print("Gerando executável (isso pode levar alguns minutos)...")
        subprocess.run(comando, check=True)
        
        # Copiar o arquivo .bat para a pasta dist
        shutil.copy2("iniciar_aplicacao.bat", "dist/")
        
        print("\n✓ Executável criado com sucesso!")
        print("Os arquivos estão na pasta 'dist':")
        print("1. AnaliseProdutividadeManobristas.exe")
        print("2. iniciar_aplicacao.bat")
        
        print("\n===========================================================================")
        print("                         INSTRUÇÕES IMPORTANTES")
        print("===========================================================================")
        print("1. Copie AMBOS os arquivos da pasta 'dist' para o computador de destino:")
        print("   - AnaliseProdutividadeManobristas.exe")
        print("   - iniciar_aplicacao.bat")
        print("\n2. MUITO IMPORTANTE: Para iniciar a aplicação, sempre execute o arquivo")
        print("   'iniciar_aplicacao.bat' com duplo clique, NÃO execute o arquivo .exe diretamente!")
        print("\n3. Uma janela de comando se abrirá seguida de uma janela do navegador")
        print("   Se o navegador não abrir automaticamente, acesse: http://localhost:8501")
        print("\n4. NÃO feche a janela de comando enquanto estiver usando a aplicação!")
        print("   Para encerrar a aplicação, feche a janela de comando.")
        print("\n5. Para cadastrar funcionários, use a aba 'Gerenciar Funcionários' no menu lateral.")
        print("===========================================================================")
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Erro ao criar o executável: {e}")
        print("Por favor, verifique as mensagens de erro acima e tente novamente.")

if __name__ == "__main__":
    main()