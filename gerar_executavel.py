import PyInstaller.__main__
import os
import sys
import shutil
import subprocess

print("Iniciando a criação do executável...")

# Limpar diretórios antigos se existirem
for dir_name in ['dist', 'build']:
    if os.path.exists(dir_name):
        print(f"Removendo diretório antigo: {dir_name}")
        shutil.rmtree(dir_name)

# Garantir que a pasta .streamlit existe
os.makedirs('.streamlit', exist_ok=True)

# Certificar-se de que o arquivo de configuração do Streamlit existe
config_file = os.path.join('.streamlit', 'config.toml')
if not os.path.exists(config_file):
    with open(config_file, 'w') as f:
        f.write("""[server]
headless = true
address = "0.0.0.0"
port = 5000
""")

# Configurar argumentos do PyInstaller
pyinstaller_args = [
    'app.py',
    '--onefile',
    '--name=AnaliseProdutividadeManobristas',
    '--hidden-import=streamlit',
    '--hidden-import=pandas',
    '--hidden-import=openpyxl',
    '--collect-all=streamlit',
    '--add-data=.streamlit;.streamlit',
]

# Se houver um ícone, usá-lo
if os.path.exists('generated-icon.png'):
    pyinstaller_args.append('--icon=generated-icon.png')

# Executar o PyInstaller
print("\nExecutando PyInstaller para criar o executável...")
PyInstaller.__main__.run(pyinstaller_args)

print("\n===================================================")
print("Executável criado com sucesso!")
print("O arquivo executável está na pasta 'dist' com o nome 'AnaliseProdutividadeManobristas.exe'")
print("Para usar o programa:")
print("1. Copie o arquivo 'AnaliseProdutividadeManobristas.exe' para seu computador")
print("2. Execute o arquivo com duplo clique")
print("3. Selecione os arquivos Excel quando solicitado")
print("===================================================")