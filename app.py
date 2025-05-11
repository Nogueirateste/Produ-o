import streamlit as st
import pandas as pd
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import tempfile
import sqlite3
from io import BytesIO
from datetime import datetime
from employee_db import EmployeeDatabase
from user_auth import UserAuth

# Verificar se estamos executando como executável ou diretamente
# Isso é necessário para o PyInstaller encontrar os arquivos
if getattr(sys, 'frozen', False):
    # Estamos executando como executável
    # Definir caminhos relativos ao executável
    script_dir = os.path.dirname(sys.executable)
    os.chdir(script_dir)
else:
    # Estamos executando normalmente
    script_dir = os.path.dirname(os.path.abspath(__file__))

# Set page configuration
st.set_page_config(
    page_title="Sistema de Gestão de Manobristas",
    page_icon="🚗",
    layout="wide"
)

# Inicializar banco de dados
db = EmployeeDatabase()

# Inicializar sistema de autenticação
auth = UserAuth()

# Inicializar variáveis para armazenar os dados entre abas
if 'dataframes_completos' not in st.session_state:
    st.session_state.dataframes_completos = []
    
# Título principal será definido em cada seção, não aqui no início
    
if 'analyzed_data' not in st.session_state:
    st.session_state.analyzed_data = None
    
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = False
    
# Variáveis de autenticação
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    
if 'user_data' not in st.session_state:
    st.session_state.user_data = None
    
if 'show_login' not in st.session_state:
    st.session_state.show_login = True
    
if 'show_gerenciar_usuarios' not in st.session_state:
    st.session_state.show_gerenciar_usuarios = False

# Barra lateral com título e botões para navegação
st.sidebar.title("Menu")

# Variável de estado para controlar a aba ativa
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 0

# Funções para mudar a aba ativa
def set_tab_0():
    st.session_state.active_tab = 0
    # Resetar a flag de gerenciamento de usuários quando mudar de aba
    st.session_state.show_gerenciar_usuarios = False
    
def set_tab_1():
    st.session_state.active_tab = 1
    # Resetar a flag de gerenciamento de usuários quando mudar de aba
    st.session_state.show_gerenciar_usuarios = False
    
def set_tab_2():
    st.session_state.active_tab = 2
    # Resetar a flag de gerenciamento de usuários quando mudar de aba
    st.session_state.show_gerenciar_usuarios = False

# Botões no menu lateral para navegar entre as abas
if st.sidebar.button("📊 Análise de Produção", use_container_width=True, key="btn_analise"):
    set_tab_0()
    
if st.sidebar.button("👥 Gerenciar Funcionários", use_container_width=True, key="btn_funcionarios"):
    set_tab_1()
    
if st.sidebar.button("🚗 Análise de Veículos", use_container_width=True, key="btn_veiculos"):
    set_tab_2()

# Removido título principal global para evitar duplicação

# Function to process Excel file and extract driver data with caching
@st.cache_data(ttl=3600, show_spinner="Processando arquivo Excel...")
def process_excel_file(uploaded_file):
    try:
        # Cálculo de tamanho aproximado do arquivo para definir uso de chunks
        file_size_MB = 0
        if isinstance(uploaded_file, str) and os.path.exists(uploaded_file):
            file_size_MB = os.path.getsize(uploaded_file) / (1024 * 1024)
        else:
            # Para uploads do Streamlit, não podemos obter o tamanho diretamente
            # então assumimos que podem ser grandes e usamos chunks
            file_size_MB = 10  # Assumimos tamanho mínimo para chunks
        
        # Define se usamos chunks ou não baseado no tamanho do arquivo
        use_chunks = file_size_MB > 5  # Se for maior que 5MB, usamos chunks
        
        if use_chunks:
            # Processamento em chunks para arquivos grandes
            chunks = []
            chunk_size = 10000  # Número de linhas por chunk
            
            # Criar barra de progresso
            progress_bar = st.progress(0)
            progress_text = st.empty()
            progress_text.text("Iniciando processamento do arquivo...")
            
            # Ler em chunks
            if isinstance(uploaded_file, str) and os.path.exists(uploaded_file):
                # Modo executável - arquivo é um caminho
                xlsx = pd.ExcelFile(uploaded_file, engine='openpyxl')
                # Obtém o nome da primeira planilha
                sheet_name = xlsx.sheet_names[0]
                # Obtém o número total de linhas para calcular o progresso
                total_rows = xlsx.book[sheet_name].max_row
                
                # Lê em chunks
                for i in range(0, total_rows, chunk_size):
                    # Calcular o número de linhas para este chunk
                    end_row = min(i + chunk_size, total_rows)
                    # Ler o próximo chunk
                    chunk = pd.read_excel(xlsx, sheet_name=sheet_name, skiprows=i, nrows=end_row-i)
                    chunks.append(chunk)
                    # Atualiza a barra de progresso
                    progress = min(1.0, end_row / total_rows)
                    progress_bar.progress(progress)
                    progress_text.text(f"Processando... {int(progress * 100)}%")
                
                df = pd.concat(chunks, ignore_index=True)
            else:
                # Modo Streamlit - arquivo é um objeto de upload
                # No Streamlit, precisamos fazer de forma diferente, pois não podemos
                # ler diretamente em chunks de um objeto UploadedFile
                # Primeiro salvamos temporariamente
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                # Agora lemos do arquivo temporário em chunks
                xlsx = pd.ExcelFile(tmp_path, engine='openpyxl')
                sheet_name = xlsx.sheet_names[0]
                total_rows = xlsx.book[sheet_name].max_row
                
                for i in range(0, total_rows, chunk_size):
                    # Calcular o número de linhas para este chunk
                    end_row = min(i + chunk_size, total_rows)
                    # Ler o próximo chunk
                    chunk = pd.read_excel(xlsx, sheet_name=sheet_name, skiprows=i, nrows=end_row-i)
                    chunks.append(chunk)
                    # Atualiza a barra de progresso
                    progress = min(1.0, end_row / total_rows)
                    progress_bar.progress(progress)
                    progress_text.text(f"Processando... {int(progress * 100)}%")
                
                df = pd.concat(chunks, ignore_index=True)
                
                # Remover arquivo temporário
                os.unlink(tmp_path)
            
            # Limpar elementos de progresso
            progress_bar.empty()
            progress_text.empty()
        else:
            # Para arquivos pequenos, usamos o método normal
            if isinstance(uploaded_file, str) and os.path.exists(uploaded_file):
                df = pd.read_excel(uploaded_file, engine='openpyxl')
            else:
                # Modo normal - uploaded_file é um objeto de upload do Streamlit
                df = pd.read_excel(uploaded_file, engine='openpyxl')
        
        # Guardar o DataFrame completo para uso na análise de veículos
        df_completo = df.copy()
        
        # Mostrar informações sobre o arquivo carregado para diagnóstico
        st.write("### Informações de diagnóstico do arquivo:")
        st.write(f"Colunas encontradas: {list(df.columns)}")
        
        # Verificar e renomear colunas importantes se necessário
        colunas_esperadas = {
            'Chassi': 0,          # Coluna A
            'Versão do modelo': 2, # Coluna C
            'Cor': 3,             # Coluna D
            'Status': 4,          # Coluna E
            'Descrição': 5,       # Coluna F
            'Manobrista': 7       # Coluna H
        }
        
        # Renomear colunas conforme necessário
        for nome_coluna, indice in colunas_esperadas.items():
            if nome_coluna not in df.columns and len(df.columns) > indice:
                df.rename(columns={df.columns[indice]: nome_coluna}, inplace=True)
                df_completo.rename(columns={df_completo.columns[indice]: nome_coluna}, inplace=True)
                st.write(f"Renomeando coluna {indice} para '{nome_coluna}'")
        
        # Extract relevant columns for aggregation (E=Status, H=Manobrista)
        try:
            status_col = 'Status' if 'Status' in df.columns else df.columns[4]
            manobrista_col = 'Manobrista' if 'Manobrista' in df.columns else df.columns[7]
            
            # Mostrar valores únicos de status
            unique_statuses = df[status_col].dropna().unique()
            st.write(f"Valores únicos encontrados na coluna Status: {list(unique_statuses)}")
            
            # Clean data - remove rows with empty manobrista
            df_analise = df[[status_col, manobrista_col]].dropna(subset=[manobrista_col])
            
            # Convert manobrista entries to uppercase for consistency
            df_analise[manobrista_col] = df_analise[manobrista_col].str.upper()
            
            # Também garantir consistência em df_completo
            if manobrista_col in df_completo.columns:
                df_completo[manobrista_col] = df_completo[manobrista_col].fillna('').astype(str).str.upper()
            
            # Guardar o DataFrame completo na sessão para uso posterior
            if 'dataframes_completos' not in st.session_state:
                st.session_state.dataframes_completos = []
            
            st.session_state.dataframes_completos.append(df_completo)
            
            # Mostrar primeiras linhas após processamento
            st.write("Amostra das primeiras 5 linhas após processamento:")
            st.write(df_analise.head(5))
            
            return df_analise
        except Exception as e:
            st.error(f"Erro ao processar colunas: {str(e)}")
            st.error("Certifique-se de que o arquivo possui as colunas Status (E) e Manobrista (H)")
            return None
            
    except Exception as e:
        st.error(f"Erro ao processar arquivo: {str(e)}")
        return None

# Function to extract matricula from manobrista name
def extract_matricula(manobrista_name):
    # Assuming matricula is at the beginning of the name and follows a pattern
    # For example: "12345 - JOSE DA SILVA" should return "12345"
    if isinstance(manobrista_name, str) and '-' in manobrista_name:
        parts = manobrista_name.split('-', 1)
        return parts[0].strip()
    return ""

# Function to aggregate driver data
def aggregate_driver_data(dataframes):
    combined_data = {}
    
    for df in dataframes:
        if df is None:
            continue
            
        status_col = 'Status' if 'Status' in df.columns else df.columns[0]
        manobrista_col = 'Manobrista' if 'Manobrista' in df.columns else df.columns[1]
        
        # Group by manobrista and count statuses
        for _, row in df.iterrows():
            manobrista = row[manobrista_col]
            status = row[status_col]
            
            if manobrista not in combined_data:
                matricula = extract_matricula(manobrista)
                combined_data[manobrista] = {
                    'MATRICULA': matricula,
                    'MANOBRISTA': manobrista.split('-')[-1].strip() if '-' in manobrista else manobrista,
                    'EM SAIDA': 0,
                    'PARQUEADOS': 0,
                    'TOTAL': 0
                }
            
            # Update counts based on status
            status_upper = status.upper()
            
            # Verificação mais abrangente para "Em Saída (expedição)"
            is_saida = False
            saida_keywords = ['SAIDA', 'SAÍDA', 'EXPEDICAO', 'EXPEDIÇÃO', 'EXPEDIC', 'EXPEDIÇ']
            
            for keyword in saida_keywords:
                if keyword in status_upper:
                    is_saida = True
                    break
            
            # Se for uma saída
            if is_saida:
                combined_data[manobrista]['EM SAIDA'] += 1
            # Se for um parqueado
            elif 'PARQUEADO' in status_upper:
                combined_data[manobrista]['PARQUEADOS'] += 1
            
            combined_data[manobrista]['TOTAL'] += 1
    
    # Convert to DataFrame
    result_df = pd.DataFrame(combined_data.values())
    
    # Sort by total in descending order
    if not result_df.empty:
        result_df = result_df.sort_values('TOTAL', ascending=False)
    
    return result_df

# Função para mostrar a aba de Análise de Produção
def mostrar_aba_analise_producao():
    # Título principal da página
    st.title("Análise de Produção de Manobristas")
    st.markdown("### Ferramenta para análise de produtividade de manobristas baseada em arquivos Excel")
    st.markdown("## Seleção de Arquivos")
    st.markdown("Selecione um ou dois arquivos Excel (.xls ou .xlsx) para análise.")

    # File upload widgets
    col1, col2 = st.columns(2)
    with col1:
        file1 = st.file_uploader("Selecione o primeiro arquivo Excel", 
                                type=["xls", "xlsx"], 
                                help="Formato aceito: Excel (.xls ou .xlsx)",
                                key="file_upload_1")
        
        # Opção para usar arquivo de exemplo
        use_sample_file = st.checkbox("Usar arquivo de exemplo", value=False, 
                                     help="Marque esta opção para carregar o arquivo de exemplo incluído no sistema")
        
        if use_sample_file:
            file1 = "attached_assets/MovimentacaoVeiculos (19).xlsx"
            st.success("Arquivo de exemplo selecionado!")

    with col2:
        file2 = st.file_uploader("Selecione o segundo arquivo Excel (opcional)", 
                                type=["xls", "xlsx"], 
                                help="Formato aceito: Excel (.xls ou .xlsx)",
                                key="file_upload_2")

    # Filter options
    st.markdown("## Opções de Filtro")
    
    col1, col2 = st.columns(2)
    with col1:
        excluir_terceiros = st.checkbox("Excluir terceiros (teclight, etc.)", value=True,
                                    help="Marque para mostrar apenas funcionários do setor, incluindo chofer e excluindo outros terceirizados como teclight")
    
    with col2:
        apenas_cadastrados = st.checkbox("Mostrar apenas funcionários cadastrados", value=False,
                                        help="Marque para mostrar apenas os funcionários que estão cadastrados no sistema")

    # Process button
    process_btn = st.button("Processar Arquivos", use_container_width=True)

    # Check if we have already processed data that should be displayed
    show_results = False
    if 'result_df' in st.session_state and st.session_state.result_df is not None:
        # Mostrar dados já processados
        result_df = st.session_state.result_df
        show_results = True
        st.success("Exibindo dados processados anteriormente. Para processar novos arquivos, carregue-os e clique em 'Processar Arquivos'.")
    
    # Processing logic
    if process_btn:
        if not file1 and not file2:
            st.error("Selecione pelo menos um arquivo Excel para processar.")
        else:
            with st.spinner("Processando dados..."):
                # Process files
                df1 = process_excel_file(file1) if file1 else None
                df2 = process_excel_file(file2) if file2 else None
                
                dataframes = [df for df in [df1, df2] if df is not None]
                
                if not dataframes:
                    st.error("Não foi possível processar os arquivos selecionados.")
                else:
                    # Aggregate data
                    result_df = aggregate_driver_data(dataframes)
                    
                    # Salvar dados na sessão para uso em outras abas
                    st.session_state.dataframes = dataframes
                    
                    # Guardar o resultado na session_state para reuso
                    st.session_state.result_df = result_df
                    st.session_state.processed_files = True
                    
                    if result_df.empty:
                        st.warning("Nenhum dado de manobrista encontrado nos arquivos.")
                    else:
                        # Contador de filtros aplicados
                        filtros_aplicados = 0
                        
                        # Guardar variáveis para identificar status "em saída"
                        saida_keywords = ['em saida', 'em saída', 'saida', 'saída']
                        st.session_state.saida_keywords = saida_keywords
                        
                        # Filter out terceiros if option is checked
                        if excluir_terceiros:
                            # Palavras-chave que identificam funcionários terceirizados
                            # Removemos 'chofer' e 'choffer' conforme solicitado
                            terceiros_keywords = ['teclight', 'techlight', 'teclighit', 'pdi', 'ddr']
                            
                            # Criar função para verificar se é terceirizado
                            def is_terceiro(nome):
                                nome_lower = nome.lower()
                                for keyword in terceiros_keywords:
                                    if keyword in nome_lower:
                                        return True
                                return False
                            
                            # Filtrar o DataFrame para remover terceirizados
                            tamanho_antes = len(result_df)
                            filtered_df = result_df[~result_df['MANOBRISTA'].apply(is_terceiro)]
                            
                            # Mostrar mensagem informativa
                            if len(filtered_df) < tamanho_antes:
                                qtd_filtrados = tamanho_antes - len(filtered_df)
                                st.info(f"Foram filtrados {qtd_filtrados} manobristas terceirizados.")
                                filtros_aplicados += 1
                            
                            result_df = filtered_df
                        
                        # Filtrar apenas funcionários cadastrados
                        if apenas_cadastrados:
                            tamanho_antes = len(result_df)
                            
                            # Verificar cada manobrista no banco de dados
                            funcionarios_registrados = []
                            
                            for _, row in result_df.iterrows():
                                matricula = row['MATRICULA']
                                
                                # Verificar se a matrícula está no banco de dados
                                employee = db.get_employee_by_matricula(matricula)
                                if employee is not None and employee['ativo']:
                                    funcionarios_registrados.append(matricula)
                            
                            # Aplicar filtro
                            if funcionarios_registrados:
                                filtered_df = result_df[result_df['MATRICULA'].isin(funcionarios_registrados)]
                                
                                # Mostrar mensagem informativa
                                if len(filtered_df) < tamanho_antes:
                                    qtd_filtrados = tamanho_antes - len(filtered_df)
                                    st.info(f"Foram filtrados {qtd_filtrados} manobristas não cadastrados no sistema.")
                                    filtros_aplicados += 1
                                
                                result_df = filtered_df
                            else:
                                if len(result_df) > 0:
                                    st.warning("Nenhum dos manobristas está cadastrado no sistema. Não foi possível aplicar o filtro.")
                        
                        # Apenas guardamos os dados na sessão sem mostrar o dashboard imediatamente
                        # Armazenar informações de filtros aplicados
                        st.session_state.filtros_aplicados = filtros_aplicados
                        
                        # Mostrar mensagem de sucesso
                        st.success("Arquivos processados com sucesso! O dashboard será exibido abaixo.")
                        
                        # Salvar os dados para uso nas outras abas
                        st.session_state.analyzed_data = result_df
                        st.session_state.processed_files = True
                        
    # Exibir os resultados se houver dados processados (seja de uma execução anterior ou atual)
    if show_results or (process_btn and 'result_df' in locals() and not result_df.empty):
        # Display dashboard and metrics
        st.markdown("## Dashboard - Análise de Produtividade")
        
        # Se estamos mostrando dados processados anteriormente, recuperar as variáveis necessárias
        if show_results and not process_btn:
            result_df = st.session_state.result_df
            # Definir as variáveis necessárias que podem não estar definidas
            if 'filtros_aplicados' in st.session_state:
                filtros_aplicados = st.session_state.filtros_aplicados
            else:
                filtros_aplicados = 0
            if 'saida_keywords' not in st.session_state:
                st.session_state.saida_keywords = ['em saida', 'em saída', 'saida', 'saída']
                
        # Mensagem especial quando aplicados múltiplos filtros
        if 'filtros_aplicados' in st.session_state and st.session_state.filtros_aplicados > 0:
            st.success(f"Análise concluída com {st.session_state.filtros_aplicados} filtro(s) aplicado(s).")
        
        # Métricas gerais
        st.markdown("### Métricas Gerais")
        
        # Cálculo de métricas gerais
        total_manobristas = len(result_df)
        total_veiculos_movimentados = result_df['TOTAL'].sum()
        total_em_saida = result_df['EM SAIDA'].sum()
        total_parqueados = result_df['PARQUEADOS'].sum()
        
        # Métrica de produtividade média
        if total_manobristas > 0:
            media_por_manobrista = total_veiculos_movimentados / total_manobristas
        else:
            media_por_manobrista = 0
        
        # Display metrics in columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Total de Manobristas",
                value=f"{total_manobristas}"
            )
        
        with col2:
            st.metric(
                label="Total de Veículos",
                value=f"{total_veiculos_movimentados}"
            )
        
        with col3:
            st.metric(
                label="Em Saída",
                value=f"{total_em_saida}"
            )
        
        with col4:
            st.metric(
                label="Parqueados",
                value=f"{total_parqueados}"
            )
        
        # Mostrar média por manobrista
        st.metric(
            label="Média de Veículos por Manobrista",
            value=f"{media_por_manobrista:.2f}"
        )
        
        # Visualizações de dados
        st.markdown("### Visualizações")
        
        # Mostrar os top N manobristas por produtividade
        top_n = min(10, len(result_df))
        top_data = result_df.head(top_n)
        
        # Criar tabs para diferentes visualizações
        vis_tab1, vis_tab2, vis_tab3 = st.tabs(["Ranking", "Distribuição", "Detalhamento"])
        
        with vis_tab1:
            # Gráfico de barras para top manobristas
            fig1 = px.bar(
                top_data,
                x="MANOBRISTA",
                y="TOTAL",
                title=f"Top {top_n} Manobristas por Produtividade",
                color="TOTAL",
                color_continuous_scale=px.colors.sequential.Viridis
            )
            fig1.update_layout(height=500)
            st.plotly_chart(fig1, use_container_width=True, key="chart_ranking")
        
        with vis_tab2:
            # Gráfico de pizza para distribuição EM SAIDA vs PARQUEADOS
            fig2 = px.pie(
                values=[total_em_saida, total_parqueados],
                names=["Em Saída", "Parqueados"],
                title="Distribuição de Veículos por Status",
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig2.update_traces(textposition='inside', textinfo='percent+label')
            fig2.update_layout(height=500)
            st.plotly_chart(fig2, use_container_width=True, key="chart_pie")
        
        with vis_tab3:
            # Gráfico de barras empilhadas
            fig3 = px.bar(
                top_data,
                x="MANOBRISTA",
                y=["EM SAIDA", "PARQUEADOS"],
                title="Distribuição de Atividades por Manobrista",
                labels={"value": "Quantidade", "variable": "Tipo"},
                barmode="stack"
            )
            fig3.update_layout(height=500)
            st.plotly_chart(fig3, use_container_width=True, key="chart_stacked")
        
        # Tabela de resultados
        st.markdown("### Tabela de Resultados")
        st.markdown(f"Total de manobristas: {total_manobristas}")
        
        # Display results table with customized columns
        st.dataframe(
            result_df,
            column_config={
                "MATRICULA": st.column_config.TextColumn("Matrícula"),
                "MANOBRISTA": st.column_config.TextColumn("Nome"),
                "EM SAIDA": st.column_config.NumberColumn("Em Saída"),
                "PARQUEADOS": st.column_config.NumberColumn("Parqueados"),
                "TOTAL": st.column_config.NumberColumn("Total", format="%d 🚗")
            },
            height=400
        )
        
        # Export options
        st.markdown("### Exportar Resultados")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Exportar para Excel", key="dashboard_export_excel", use_container_width=True):
                # Create Excel file
                excel_buffer = BytesIO()
                result_df.to_excel(excel_buffer, index=False)
                excel_data = excel_buffer.getvalue()
                
                st.download_button(
                    label="Download Excel",
                    data=excel_data,
                    file_name="analise_manobristas.xlsx",
                    mime="application/vnd.ms-excel",
                    use_container_width=True,
                    key="dashboard_download_excel"
                )
        
        with col2:
            if st.button("Exportar para CSV", key="dashboard_export_csv", use_container_width=True):
                # Create CSV file
                csv_data = result_df.to_csv(index=False).encode('utf-8')
                
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name="analise_manobristas.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="dashboard_download_csv"
                )
    
    # Mostrar informações sobre como usar os dados
    st.markdown("""
    ## Próximos Passos
    - Você pode analisar os resultados acima para identificar os manobristas mais produtivos.
    - Acesse a aba "Análise de Veículos" para visualizar os detalhes dos veículos movimentados por cada manobrista.
    - A opção de filtro permite remover terceirizados da análise.
    - O filtro de funcionários cadastrados permite mostrar apenas quem está no sistema.
    - Resultados podem ser exportados em formato Excel ou CSV.
    """)

# Função para mostrar a aba de Gerenciamento de Funcionários
def mostrar_aba_gerenciar_funcionarios():
    # Interface for Employee Management
    st.title("Gerenciamento de Manobristas/Funcionários")
    st.markdown("Aqui você pode cadastrar, editar e remover manobristas e funcionários do sistema.")
    
    # Tabs for different employee management functionalities
    employee_tab = st.radio(
        "Escolha uma opção:",
        ["Listar Manobristas", "Cadastrar Manobrista", "Editar/Remover Manobrista"],
        horizontal=True,
        key="manobrista_management_tab"
    )
    
    if employee_tab == "Listar Manobristas":
        st.markdown("### Lista de Manobristas Cadastrados")
        
        # Get all employees
        employees_df = db.get_all_employees()
        
        if employees_df.empty:
            st.warning("Nenhum manobrista cadastrado no sistema.")
        else:
            # Show filter options
            col1, col2 = st.columns(2)
            with col1:
                mostrar_ativos = st.checkbox("Mostrar apenas manobristas ativos", value=True, key="mostrar_ativos_manobristas")
            
            with col2:
                filtrar_tipo = st.checkbox("Filtrar por tipo", value=False)
                if filtrar_tipo:
                    tipo_selecionado = st.selectbox("Selecione o tipo", 
                                                 ["todos", "interno", "chofer", "terceiro", "teclight", "outro"])
            
            # Aplicar filtros
            if mostrar_ativos:
                filtered_df = employees_df[employees_df['ativo'] == True]
            else:
                filtered_df = employees_df
            
            if filtrar_tipo and tipo_selecionado != "todos":
                filtered_df = filtered_df[filtered_df['tipo'] == tipo_selecionado]
            
            # Display employee dataframe
            if filtered_df.empty:
                st.warning("Nenhum manobrista encontrado com os filtros aplicados.")
            else:
                st.write(f"Total de manobristas: {len(filtered_df)}")
                st.dataframe(
                    filtered_df,
                    column_config={
                        "matricula": st.column_config.TextColumn("Matrícula"),
                        "nome": st.column_config.TextColumn("Nome"),
                        "tipo": st.column_config.TextColumn("Tipo"),
                        "ativo": st.column_config.CheckboxColumn("Ativo"),
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                # Export options
                if st.button("Exportar Lista de Manobristas", use_container_width=True, key="export_manobristas"):
                    excel_buffer = BytesIO()
                    filtered_df.to_excel(excel_buffer, index=False)
                    excel_data = excel_buffer.getvalue()
                    
                    st.download_button(
                        label="Download Excel",
                        data=excel_data,
                        file_name="manobristas.xlsx",
                        mime="application/vnd.ms-excel",
                        use_container_width=True
                    )
    
    elif employee_tab == "Cadastrar Manobrista":
        st.markdown("### Adicionar Novo Manobrista")
        
        # Form to add new employee
        with st.form("add_manobrista_form"):
            new_matricula = st.text_input("Matrícula/ID")
            new_nome = st.text_input("Nome Completo")
            new_tipo = st.selectbox("Tipo", ["interno", "chofer", "terceiro", "teclight", "outro"])
            new_ativo = st.checkbox("Ativo", value=True)
            
            # Submit button for the form
            submit_button = st.form_submit_button(label="Adicionar Manobrista")
            
            if submit_button:
                # Validate input
                if not new_matricula or not new_nome:
                    st.error("Por favor, preencha a matrícula e o nome do manobrista.")
                else:
                    # Add employee to database
                    success, message = db.add_employee(new_matricula, new_nome, new_tipo, new_ativo)
                    
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
    
    elif employee_tab == "Editar/Remover Manobrista":
        st.markdown("### Editar Manobrista Existente")
        
        # Get all employees
        all_employees = db.get_all_employees()
        
        if all_employees.empty:
            st.warning("Nenhum manobrista cadastrado no sistema.")
        else:
            # Create a list of options for the selectbox
            employee_options = []
            employee_map = {}
            
            for _, row in all_employees.iterrows():
                display_name = f"{row['matricula']} - {row['nome']}"
                employee_options.append(display_name)
                employee_map[display_name] = row.to_dict()
            
            # Selectbox for employee selection
            selected_employee = st.selectbox("Selecionar Manobrista", employee_options)
            
            if selected_employee:
                # Get the selected employee details
                employee = employee_map[selected_employee]
                selected_matricula = employee['matricula']
                
                # Form to edit employee
                with st.form("edit_manobrista_form"):
                    edit_nome = st.text_input("Nome Completo", value=employee['nome'])
                    edit_tipo = st.selectbox("Tipo", ["interno", "chofer", "terceiro", "teclight", "outro"], index=["interno", "chofer", "terceiro", "teclight", "outro"].index(employee['tipo']))
                    edit_ativo = st.checkbox("Ativo", value=employee['ativo'])
                    
                    # Form buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        update_btn = st.form_submit_button(label="Atualizar")
                    with col2:
                        delete_btn = st.form_submit_button(label="Remover", type="primary")
                    
                    if update_btn:
                        # Update employee
                        success, message = db.update_employee(
                            selected_matricula,
                            nome=edit_nome, 
                            tipo=edit_tipo, 
                            ativo=edit_ativo
                        )
                        
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    
                    if delete_btn:
                        # Show confirmation
                        st.warning(f"Tem certeza que deseja remover {employee['nome']}?")
                        
                        # Delete employee
                        success, message = db.delete_employee(selected_matricula)
                        
                        if success:
                            st.success(message)
                        else:
                            st.error(message)

# Função para mostrar a aba de Análise de Veículos
def mostrar_aba_analise_veiculos():
    # Interface for Vehicle Analysis
    st.title("Análise de Veículos por Funcionário")
    st.markdown("Visualize os veículos movimentados por cada manobrista nos arquivos analisados.")
    
    # Verificar se algum arquivo foi carregado
    if not st.session_state.processed_files:
        st.warning("Nenhum arquivo Excel carregado. Por favor, vá para a aba 'Análise de Produção' e carregue um arquivo Excel antes de usar esta funcionalidade.")
    else:
        # Obter os dados processados da session_state
        if 'dataframes' in st.session_state:
            dataframes = st.session_state.dataframes
        else:
            dataframes = []
            
        if 'analyzed_data' in st.session_state:
            result_df = st.session_state.analyzed_data
        elif 'result_df' in st.session_state:
            result_df = st.session_state.result_df
        else:
            result_df = None
            
        if 'saida_keywords' in st.session_state:
            saida_keywords = st.session_state.saida_keywords
        else:
            saida_keywords = ['em saida', 'em saída', 'saida', 'saída']
            st.session_state.saida_keywords = saida_keywords
        
        # Verificar se temos os dataframes completos para análise detalhada
        if 'dataframes_completos' not in st.session_state or not st.session_state.dataframes_completos:
            st.warning("Informações detalhadas dos veículos não estão disponíveis. Por favor, recarregue os arquivos na aba 'Análise de Produção'.")
        else:
            dataframes_completos = st.session_state.dataframes_completos
            
            # Extrair os nomes dos manobristas apenas dos resultados processados
            all_manobristas = []
            
            # Usar o dataframe de resultados para obter os nomes dos manobristas
            if result_df is not None and not result_df.empty:
                for _, row in result_df.iterrows():
                    nome = row['MANOBRISTA']
                    if nome and nome not in all_manobristas:
                        all_manobristas.append(nome)
            
            # Ordenar alfabeticamente
            all_manobristas.sort()
            
            # Interface de seleção
            if all_manobristas:
                st.subheader("Selecione um manobrista para análise detalhada de veículos")
                
                # Selecionar funcionário
                funcionario_selecionado = st.selectbox(
                    "Manobrista:",
                    all_manobristas
                )
                
                if funcionario_selecionado:
                    st.subheader(f"Análise de veículos para: {funcionario_selecionado}")
                    
                    # Extrair detalhes dos veículos movimentados por este funcionário
                    veiculos = []
                    
                    for df in dataframes_completos:
                        if 'Manobrista' in df.columns and 'Status' in df.columns:
                            # Filtrar linhas do funcionário selecionado
                            funcionario_rows = df[df['Manobrista'].str.contains(funcionario_selecionado, case=False, na=False)]
                            
                            for _, row in funcionario_rows.iterrows():
                                status = row['Status'].upper() if isinstance(row['Status'], str) else ''
                                chassi = row['Chassi'] if 'Chassi' in df.columns else ''
                                versao = row['Versão do modelo'] if 'Versão do modelo' in df.columns else ''
                                cor = row['Cor'] if 'Cor' in df.columns else ''
                                descricao = row['Descrição'] if 'Descrição' in df.columns else ''
                                
                                # Determinar se é saída ou parqueado
                                is_saida = False
                                for keyword in saida_keywords:
                                    if keyword.upper() in status:
                                        is_saida = True
                                        break
                                
                                tipo = "EM SAÍDA" if is_saida else "PARQUEADO"
                                
                                veiculos.append({
                                    'Chassi': chassi,
                                    'Versão': versao,
                                    'Cor': cor,
                                    'Descrição': descricao,
                                    'Status': status,
                                    'Tipo': tipo
                                })
                    
                    # Mostrar o total de veículos encontrados
                    if veiculos:
                        df_veiculos = pd.DataFrame(veiculos)
                        total_veiculos = len(df_veiculos)
                        st.markdown(f"**Total de veículos movimentados: {total_veiculos}**")
                        
                        # Contagem por tipo
                        saidas = df_veiculos[df_veiculos['Tipo'] == 'EM SAÍDA'].shape[0]
                        parqueados = df_veiculos[df_veiculos['Tipo'] == 'PARQUEADO'].shape[0]
                        
                        # Métricas
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Em Saída", saidas)
                        with col2:
                            st.metric("Parqueados", parqueados)
                        
                        # Visualização da distribuição de veículos por tipo
                        if total_veiculos > 0:
                            st.subheader("Distribuição de veículos")
                            fig = px.pie(
                                values=[saidas, parqueados],
                                names=["Em Saída", "Parqueados"],
                                title=f"Distribuição de veículos para {funcionario_selecionado}",
                                color_discrete_sequence=px.colors.qualitative.Set2
                            )
                            fig.update_traces(textposition='inside', textinfo='percent+label')
                            st.plotly_chart(fig, use_container_width=True, key=f"pie_{funcionario_selecionado}")
                        
                        # Detalhes dos veículos em uma tabela
                        st.subheader("Detalhes dos veículos")
                        
                        # Mostra a tabela de veículos
                        st.dataframe(
                            df_veiculos,
                            column_config={
                                "Chassi": st.column_config.TextColumn("Chassi"),
                                "Versão": st.column_config.TextColumn("Versão do Modelo"),
                                "Cor": st.column_config.TextColumn("Cor"),
                                "Descrição": st.column_config.TextColumn("Descrição"),
                                "Status": st.column_config.TextColumn("Status Original"),
                                "Tipo": st.column_config.TextColumn("Tipo")
                            },
                            hide_index=True
                        )
                        
                        # Opção para exportar detalhes
                        if st.button("Exportar Detalhes dos Veículos", key="export_vehicles", use_container_width=True):
                            # Create Excel file
                            excel_buffer = BytesIO()
                            df_veiculos.to_excel(excel_buffer, index=False)
                            excel_data = excel_buffer.getvalue()
                            
                            st.download_button(
                                label=f"Download Detalhes ({funcionario_selecionado})",
                                data=excel_data,
                                file_name=f"veiculos_{funcionario_selecionado}.xlsx",
                                mime="application/vnd.ms-excel",
                                use_container_width=True
                            )
                    else:
                        st.info(f"Não foram encontrados detalhes de veículos para o funcionário {funcionario_selecionado}")
            else:
                st.warning("Nenhum funcionário encontrado nos dados. Verifique se os arquivos Excel foram carregados corretamente.")

# Função para fazer login
def login():
    st.markdown("## Login")
    st.markdown("Entre com suas credenciais para acessar o sistema.")
    
    with st.form("login_form"):
        username = st.text_input("Usuário:")
        password = st.text_input("Senha:", type="password")
        submit = st.form_submit_button("Entrar")
        
        if submit:
            authenticated, user_data = auth.authenticate(username, password)
            
            if authenticated:
                st.session_state.logged_in = True
                st.session_state.user_data = user_data
                st.session_state.show_login = False
                st.success(f"Bem-vindo, {user_data['nome_completo']}!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos. Por favor, tente novamente.")

# Função para logout
def logout():
    st.session_state.logged_in = False
    st.session_state.user_data = None
    st.session_state.show_login = True
    st.rerun()

# Função para mostrar gerenciamento de usuários
def mostrar_gerenciar_usuarios():
    # Substitui o título de página ao invés de adicionar um subtítulo
    st.title("Gerenciamento de Usuários")
    st.markdown("Aqui você pode cadastrar, editar e remover usuários do sistema.")
    
    user_tab = st.radio(
        "Escolha uma opção:",
        ["Listar Usuários", "Cadastrar Usuário", "Editar/Remover Usuário"],
        horizontal=True,
        key="user_management_tab"
    )
    
    if user_tab == "Listar Usuários":
        st.markdown("### Lista de Usuários Cadastrados")
        
        # Get all users
        users_df = auth.get_all_users()
        
        if users_df.empty:
            st.warning("Nenhum usuário cadastrado no sistema.")
        else:
            # Show filter options
            mostrar_ativos = st.checkbox("Mostrar apenas usuários ativos", value=True, key="mostrar_usuarios_ativos")
            
            if mostrar_ativos:
                filtered_df = users_df[users_df['ativo'] == True]
            else:
                filtered_df = users_df
            
            # Não mostrar hash e salt na interface
            if not filtered_df.empty:
                filtered_df = filtered_df.drop(columns=['password_hash', 'salt'])
            
            # Display users dataframe
            if filtered_df.empty:
                st.warning("Nenhum usuário ativo cadastrado.")
            else:
                st.dataframe(
                    filtered_df,
                    column_config={
                        "username": st.column_config.TextColumn("Nome de Usuário"),
                        "nome_completo": st.column_config.TextColumn("Nome Completo"),
                        "nivel_acesso": st.column_config.TextColumn("Nível de Acesso"),
                        "ativo": st.column_config.CheckboxColumn("Ativo"),
                    },
                    hide_index=True,
                    use_container_width=True
                )
    
    elif user_tab == "Cadastrar Usuário":
        st.markdown("### Adicionar Novo Usuário")
        
        # Form to add new user
        with st.form("add_user_form"):
            new_username = st.text_input("Nome de Usuário")
            new_password = st.text_input("Senha", type="password")
            confirm_password = st.text_input("Confirmar Senha", type="password")
            new_nome = st.text_input("Nome Completo")
            new_nivel = st.selectbox("Nível de Acesso", ["operador", "supervisor", "admin"])
            new_ativo = st.checkbox("Ativo", value=True)
            
            # Submit button for the form
            submit_button = st.form_submit_button(label="Adicionar")
            
            if submit_button:
                # Validar input
                if not new_username or not new_password or not new_nome:
                    st.error("Por favor, preencha todos os campos obrigatórios.")
                elif new_password != confirm_password:
                    st.error("As senhas não conferem. Por favor, tente novamente.")
                else:
                    # Add user to system
                    success, message = auth.add_user(new_username, new_password, new_nome, new_nivel, new_ativo)
                    
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
    
    elif user_tab == "Editar/Remover Usuário":
        st.markdown("### Editar Usuário Existente")
        
        # Get all users
        all_users = auth.get_all_users()
        
        if all_users.empty:
            st.warning("Nenhum usuário cadastrado no sistema.")
        else:
            # Create a list of options for the selectbox
            user_options = []
            user_map = {}
            
            for _, row in all_users.iterrows():
                display_name = f"{row['username']} - {row['nome_completo']}"
                user_options.append(display_name)
                user_map[display_name] = row.to_dict()
            
            # Selectbox for user selection
            selected_user = st.selectbox("Selecionar Usuário", user_options)
            
            if selected_user:
                # Get the selected user details
                user = user_map[selected_user]
                selected_username = user['username']
                
                # Form to edit user
                with st.form("edit_user_form"):
                    edit_nome = st.text_input("Nome Completo", value=user['nome_completo'])
                    edit_nivel = st.selectbox("Nível de Acesso", ["operador", "supervisor", "admin"], index=["operador", "supervisor", "admin"].index(user['nivel_acesso']))
                    edit_ativo = st.checkbox("Ativo", value=user['ativo'])
                    
                    change_password = st.checkbox("Alterar Senha", value=False)
                    
                    if change_password:
                        new_password = st.text_input("Nova Senha", type="password")
                        confirm_password = st.text_input("Confirmar Nova Senha", type="password")
                    
                    # Form buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        update_btn = st.form_submit_button(label="Atualizar")
                    with col2:
                        delete_btn = st.form_submit_button(label="Remover", type="primary")
                    
                    if update_btn:
                        # Verificar se está tentando mudar a senha
                        password_to_change = None
                        if change_password:
                            if not new_password:
                                st.error("Por favor, digite a nova senha.")
                                return
                            elif new_password != confirm_password:
                                st.error("As senhas não conferem. Por favor, tente novamente.")
                                return
                            else:
                                password_to_change = new_password
                        
                        # Update user
                        success, message = auth.update_user(
                            selected_username,
                            nome_completo=edit_nome, 
                            nivel_acesso=edit_nivel, 
                            ativo=edit_ativo,
                            password=password_to_change
                        )
                        
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    
                    if delete_btn:
                        # Delete user
                        success, message = auth.delete_user(selected_username)
                        
                        if success:
                            st.success(message)
                        else:
                            st.error(message)

# Função para mostrar o conteúdo com base na aba ativa selecionada
def mostrar_conteudo():
    # Verificar login
    if not st.session_state.logged_in:
        login()
        return
    
    # Adicionar opção para gerenciar usuários no menu lateral se for admin
    if st.session_state.logged_in and st.session_state.user_data['nivel_acesso'] == 'admin':
        if st.sidebar.button("👤 Gerenciar Usuários", use_container_width=True, key="btn_usuarios"):
            st.session_state.show_gerenciar_usuarios = True
            st.rerun()
    
    # Adicionar botão de logout
    if st.sidebar.button("🚪 Sair", use_container_width=True, key="btn_logout"):
        logout()
    
    # Mostrar informações do usuário logado
    st.sidebar.markdown(f"**Usuário:** {st.session_state.user_data['nome_completo']}")
    st.sidebar.markdown(f"**Nível:** {st.session_state.user_data['nivel_acesso']}")
    
    # Verificar se deve mostrar a tela de gerenciamento de usuários
    if st.session_state.show_gerenciar_usuarios:
        if st.session_state.user_data['nivel_acesso'] == 'admin':
            mostrar_gerenciar_usuarios()
        else:
            st.warning("Você não tem permissão para acessar esta área.")
            st.session_state.show_gerenciar_usuarios = False
        return
    
    # Mostrar conteúdo normal baseado na aba ativa
    if st.session_state.active_tab == 0:
        mostrar_aba_analise_producao()
    elif st.session_state.active_tab == 1:
        mostrar_aba_gerenciar_funcionarios()
    else:
        mostrar_aba_analise_veiculos()

# Executar a função para mostrar o conteúdo com base na aba ativa
mostrar_conteudo()