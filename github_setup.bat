@echo off
echo Configurando GitHub...

:: Criar diretório temporário
mkdir temp_git
cd temp_git

:: Inicializar Git
git init
git config --global user.name "YourGitHubName"
git config --global user.email "your.email@example.com"

:: Adicionar repositório remoto
git remote add origin https://github.com/Nogueirateste/Produ-o.git

:: Copiar arquivos
echo Copiando arquivos...
copy ..\*.py .
copy ..\*.csv .
copy ..\*.bat .
copy ..\*.toml .
mkdir attached_assets
copy ..\attached_assets\*.* attached_assets\

:: Adicionar arquivos ao Git
git add .

:: Fazer commit
git commit -m "Initial commit: Projeto de Análise de Produção de Manobristas"

:: Configurar token
:: Substitua TOKEN_AQUI pelo seu token pessoal do GitHub
set GH_TOKEN=TOKEN_AQUI

:: Push usando token
git push -u https://%GH_TOKEN%@github.com/Nogueirateste/Produ-o.git main

echo Concluído!
pause