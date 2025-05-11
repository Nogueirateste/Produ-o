@echo off
echo ============================================================
echo  Analise de Producao de Manobristas - Iniciando aplicacao
echo ============================================================
echo.

REM Verifica se o executavel existe
if not exist "AnaliseProdutividadeManobristas.exe" (
    echo ERRO: O arquivo AnaliseProdutividadeManobristas.exe nao foi encontrado!
    echo Certifique-se de que este batch esta no mesmo diretorio do executavel.
    echo.
    pause
    exit /b 1
)

echo Iniciando a aplicacao... Por favor, aguarde.
echo Um navegador sera aberto automaticamente em alguns segundos.
echo.
echo IMPORTANTE: NAO FECHE esta janela enquanto estiver usando a aplicacao!
echo             Para encerrar a aplicacao, feche esta janela.
echo.
echo Se o navegador nao abrir automaticamente, acesse:
echo http://localhost:8501
echo.

REM Inicia o executavel diretamente
"AnaliseProdutividadeManobristas.exe"

echo.
echo Aplicacao finalizada.
echo.
pause