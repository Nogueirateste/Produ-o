import os
import sys
import PyInstaller.__main__

# Pasta onde o executável será gerado
output_folder = "dist"

# Definir argumentos para o PyInstaller
# --onefile: cria um único arquivo executável
# --windowed: não mostra a janela de console (mais limpo para o usuário)
# --name: nome do executável
# --add-data: adiciona arquivos necessários ao executável
# --hidden-import: inclui imports escondidos
# --icon: adiciona um ícone ao executável (opcional)

args = [
    "app.py",
    "--onefile",
    "--name=AnaliseProdutividadeManobristas",
    "--add-data=.streamlit;.streamlit",
    "--hidden-import=openpyxl",
    "--hidden-import=pandas",
    "--hidden-import=streamlit",
]

# Se tiver um ícone, adicione-o
if os.path.exists("generated-icon.png"):
    args.append("--icon=generated-icon.png")

# Executar o PyInstaller com os argumentos
PyInstaller.__main__.run(args)

print("\nExecutável criado com sucesso na pasta 'dist'.")
print("Execute o arquivo 'AnaliseProdutividadeManobristas' para iniciar o programa.")