from PyInstaller.utils.hooks import collect_all

# Módulos específicos do Streamlit para coletar
hiddenimports = [
    'streamlit',
    'streamlit.web.cli',
    'streamlit.web.server',
    'streamlit.web.bootstrap',
    'streamlit.runtime',
    'streamlit.runtime.scriptrunner',
    'streamlit.runtime.caching',
    'streamlit.elements',
    'streamlit.state',
]

# Coletar todos os subpacotes e arquivos de dados do Streamlit
datas, binaries, hiddenimports_collected = collect_all('streamlit')
hiddenimports.extend(hiddenimports_collected)

# Não se esqueça de incluir outros pacotes essenciais
hiddenimports.extend([
    'pandas',
    'numpy',
    'openpyxl',
])