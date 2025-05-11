import os
import sys
import subprocess
import webbrowser
import time
import threading
import tempfile

def open_browser():
    # Aguarda 3 segundos para o servidor iniciar
    time.sleep(3)
    # Abre o navegador com a URL do servidor local
    webbrowser.open('http://localhost:8501')

# Conteúdo do app.py embutido como uma string
APP_CONTENT = '''
import streamlit as st
import pandas as pd
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from employee_db import EmployeeDatabase

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
    page_title="Análise de Produção de Manobristas",
    page_icon="🚗",
    layout="wide"
)

# Inicializar banco de dados
db = EmployeeDatabase()

# Configurar estados de sessão para abas
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = "Análise"

# Função para trocar abas
def change_tab(tab_name):
    st.session_state.current_tab = tab_name

# Barra lateral com seleção de abas
st.sidebar.title("Menu")
if st.sidebar.button("📊 Análise de Produção", use_container_width=True):
    change_tab("Análise")
if st.sidebar.button("👥 Gerenciar Funcionários", use_container_width=True):
    change_tab("Funcionários")
if st.sidebar.button("🚗 Análise de Veículos", use_container_width=True):
    change_tab("Veículos")

# Título principal
st.title("Análise de Produção de Manobristas")

# Function to process Excel file and extract driver data
def process_excel_file(uploaded_file):
    try:
        # Read Excel file
        # Se estiver executando como executável e o uploaded_file for um caminho de string
        if getattr(sys, 'frozen', False) and isinstance(uploaded_file, str) and os.path.exists(uploaded_file):
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        else:
            # Modo normal - uploaded_file é um objeto de upload do Streamlit
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        
        # Guardar o DataFrame completo para uso na análise de veículos
        df_completo = df.copy()
        
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
        
        # Extract relevant columns for aggregation (E=Status, H=Manobrista)
        try:
            status_col = 'Status' if 'Status' in df.columns else df.columns[4]
            manobrista_col = 'Manobrista' if 'Manobrista' in df.columns else df.columns[7]
            
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

# Conteúdo baseado na aba selecionada
if st.session_state.current_tab == "Análise":
    # Main interface for Analysis tab
    st.markdown("## Seleção de Arquivos")
    st.markdown("Selecione um ou dois arquivos Excel (.xls ou .xlsx) para análise.")

    # File upload widgets
    col1, col2 = st.columns(2)
    with col1:
        file1 = st.file_uploader("Selecione o primeiro arquivo Excel", 
                                type=["xls", "xlsx"], 
                                help="Formato aceito: Excel (.xls ou .xlsx)")

    with col2:
        file2 = st.file_uploader("Selecione o segundo arquivo Excel (opcional)", 
                                type=["xls", "xlsx"], 
                                help="Formato aceito: Excel (.xls ou .xlsx)")

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
                    
                    if result_df.empty:
                        st.warning("Nenhum dado de manobrista encontrado nos arquivos.")
                    else:
                        # Contador de filtros aplicados
                        filtros_aplicados = 0
                        
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
                        
                        # Display dashboard and metrics
                        st.markdown("## Dashboard - Análise de Produtividade")
                        
                        # Mensagem especial quando aplicados múltiplos filtros
                        if filtros_aplicados > 0:
                            st.success(f"Análise concluída com {filtros_aplicados} filtro(s) aplicado(s).")
                        
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
                                label="Em Saída (Expedição)",
                                value=f"{total_em_saida}"
                            )
                            
                        with col4:
                            st.metric(
                                label="Parqueados",
                                value=f"{total_parqueados}"
                            )
                        
                        # Segunda linha de métricas
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.metric(
                                label="Média de Veículos por Manobrista",
                                value=f"{media_por_manobrista:.1f}"
                            )
                        
                        with col2:
                            # Percentual em saída vs parqueados
                            if total_veiculos_movimentados > 0:
                                percentual_saida = (total_em_saida / total_veiculos_movimentados) * 100
                            else:
                                percentual_saida = 0
                                
                            st.metric(
                                label="% Em Saída (Expedição)",
                                value=f"{percentual_saida:.1f}%"
                            )
                        
                        # Dashboard com gráficos
                        st.markdown("### Visualização de Dados")
                        
                        # Preparar dados para gráficos - usar top 10 manobristas
                        top_data = result_df.head(10).copy() if len(result_df) >= 10 else result_df.copy()
                        
                        tab1, tab2, tab3 = st.tabs(["Ranking de Produtividade", "Distribuição por Tipo", "Comparação de Manobristas"])
                        
                        with tab1:
                            # Gráfico de barras para total de veículos por manobrista
                            fig = px.bar(
                                top_data,
                                x="MANOBRISTA",
                                y="TOTAL",
                                color="TOTAL",
                                color_continuous_scale="Viridis",
                                title="Top Manobristas por Total de Veículos Movimentados",
                                labels={"MANOBRISTA": "Manobrista", "TOTAL": "Total de Veículos"}
                            )
                            fig.update_layout(height=500)
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with tab2:
                            # Gráfico de pizza para distribuição EM SAIDA vs PARQUEADOS
                            fig2 = px.pie(
                                values=[total_em_saida, total_parqueados],
                                names=["Em Saída", "Parqueados"],
                                title="Distribuição de Veículos por Status",
                                color_discrete_sequence=px.colors.qualitative.Set2
                            )
                            fig2.update_traces(textposition='inside', textinfo='percent+label')
                            fig2.update_layout(height=500)
                            st.plotly_chart(fig2, use_container_width=True)
                        
                        with tab3:
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
                            st.plotly_chart(fig3, use_container_width=True)
                        
                        # Tabela de resultados
                        st.markdown("### Tabela de Resultados")
                        st.markdown(f"Total de manobristas: {total_manobristas}")
                        
                        # Format the table
                        st.dataframe(
                            result_df,
                            column_config={
                                "MATRICULA": st.column_config.TextColumn("MATRICULA"),
                                "MANOBRISTA": st.column_config.TextColumn("MANOBRISTA"),
                                "EM SAIDA": st.column_config.NumberColumn("EM SAIDA"),
                                "PARQUEADOS": st.column_config.NumberColumn("PARQUEADOS"),
                                "TOTAL": st.column_config.NumberColumn("TOTAL"),
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                        
                        # Detalhes de veículos por funcionário selecionado
                        st.markdown("### Detalhes de Veículos por Funcionário")
                        st.markdown("Selecione uma matrícula para ver os detalhes dos veículos movimentados por este funcionário.")
                        
                        # Lista de matrículas para seleção
                        matriculas = result_df['MATRICULA'].tolist()
                        nomes = result_df['MANOBRISTA'].tolist()
                        
                        # Criar lista de opções combinando matrícula e nome
                        opcoes_funcionarios = [f"{mat} - {nome}" for mat, nome in zip(matriculas, nomes) if mat]  # Filtrar matrículas vazias
                        if opcoes_funcionarios:
                            funcionario_selecionado = st.selectbox(
                                "Selecione um funcionário para ver detalhes:",
                                options=[""] + opcoes_funcionarios,
                                format_func=lambda x: x if x else "Selecione um funcionário..."
                            )
                            
                            # Se um funcionário foi selecionado
                            if funcionario_selecionado:
                                # Extrair matrícula da seleção
                                matricula_selecionada = funcionario_selecionado.split(' - ')[0]
                                
                                # Criar e mostrar dados detalhados
                                with st.expander("Detalhes dos veículos", expanded=True):
                                    # Preparar lista de veículos do funcionário selecionado
                                    veiculos_funcionario = []
                                    
                                    # Processar novamente os dados originais para extrair detalhes dos veículos
                                    for df in dataframes:
                                        if df is None:
                                            continue
                                            
                                        status_col = 'Status' if 'Status' in df.columns else df.columns[0]
                                        manobrista_col = 'Manobrista' if 'Manobrista' in df.columns else df.columns[1]
                                        
                                        # Filtrar por manobrista que contém a matrícula selecionada
                                        for _, row in df.iterrows():
                                            manobrista = row[manobrista_col]
                                            if matricula_selecionada in manobrista:
                                                status = row[status_col]
                                                
                                                # Determinar tipo de movimentação
                                                status_upper = status.upper()
                                                tipo_movimentacao = "Não Classificado"
                                                
                                                # Verificar se é saída
                                                is_saida = False
                                                for keyword in saida_keywords:
                                                    if keyword in status_upper:
                                                        is_saida = True
                                                        break
                                                
                                                if is_saida:
                                                    tipo_movimentacao = "Em Saída (Expedição)"
                                                elif 'PARQUEADO' in status_upper:
                                                    tipo_movimentacao = "Parqueado"
                                                
                                                # Adicionar à lista de veículos
                                                veiculos_funcionario.append({
                                                    "Status": status,
                                                    "Tipo de Movimentação": tipo_movimentacao
                                                })
                                    
                                    # Criar DataFrame com os veículos
                                    if veiculos_funcionario:
                                        df_veiculos = pd.DataFrame(veiculos_funcionario)
                                        
                                        # Mostrar contagem por tipo de movimentação
                                        st.subheader(f"Resumo de Veículos - {funcionario_selecionado}")
                                        
                                        # Contar tipos de movimentação
                                        contagem = df_veiculos['Tipo de Movimentação'].value_counts().reset_index()
                                        contagem.columns = ['Tipo de Movimentação', 'Quantidade']
                                        
                                        # Mostrar gráfico
                                        fig = px.bar(
                                            contagem,
                                            x='Tipo de Movimentação',
                                            y='Quantidade',
                                            color='Tipo de Movimentação',
                                            title=f"Distribuição de Veículos - {funcionario_selecionado}",
                                            labels={'Quantidade': 'Número de Veículos'}
                                        )
                                        st.plotly_chart(fig, use_container_width=True)
                                        
                                        # Mostrar tabela detalhada
                                        st.subheader("Lista de Veículos Movimentados")
                                        st.dataframe(
                                            df_veiculos,
                                            hide_index=False,
                                            use_container_width=True
                                        )
                                        
                                        # Download do relatório detalhado
                                        excel_buffer = BytesIO()
                                        df_veiculos.to_excel(excel_buffer, index=False)
                                        excel_data = excel_buffer.getvalue()
                                        
                                        st.download_button(
                                            label="Baixar Relatório Detalhado",
                                            data=excel_data,
                                            file_name=f"detalhes_veiculos_{matricula_selecionada}.xlsx",
                                            mime="application/vnd.ms-excel",
                                            use_container_width=True
                                        )
                                    else:
                                        st.info(f"Não foram encontrados detalhes de veículos para o funcionário {funcionario_selecionado}")
                        else:
                            st.info("Não há funcionários com matrícula para selecionar.")
                        
                        # Export options
                        st.markdown("## Exportar Resultados")
                        
                        # Excel export
                        excel_buffer = BytesIO()
                        result_df.to_excel(excel_buffer, index=False)
                        excel_data = excel_buffer.getvalue()
                        
                        st.download_button(
                            label="Baixar como Excel",
                            data=excel_data,
                            file_name="analise_produção_manobristas.xlsx",
                            mime="application/vnd.ms-excel",
                            use_container_width=True
                        )
                        
                        # CSV export
                        csv_data = result_df.to_csv(index=False).encode('utf-8')
                        
                        st.download_button(
                            label="Baixar como CSV",
                            data=csv_data,
                            file_name="analise_produção_manobristas.csv",
                            mime="text/csv",
                            use_container_width=True
                        )

    # Footer for Analysis tab
    st.markdown("---")
    st.markdown("### Informações")
    st.markdown("""
    - Esta ferramenta analisa arquivos Excel de movimentação de veículos.
    - Os dados são extraídos das colunas E (Status) e H (Manobrista).
    - O ranking é baseado no total de atividades registradas por manobrista.
    - A opção de filtro permite remover terceirizados da análise.
    - O filtro de funcionários cadastrados permite mostrar apenas quem está no sistema.
    - Resultados podem ser exportados em formato Excel ou CSV.
    """)

elif st.session_state.current_tab == "Funcionários":
    # Interface for Employee Management
    st.markdown("## Gerenciamento de Funcionários")
    st.markdown("Aqui você pode cadastrar, editar e remover funcionários do sistema.")
    
    # Tabs for different employee management functionalities
    employee_tab = st.radio(
        "Escolha uma opção:",
        ["Listar Funcionários", "Cadastrar Funcionário", "Editar/Remover Funcionário"],
        horizontal=True
    )
    
    if employee_tab == "Listar Funcionários":
        st.markdown("### Lista de Funcionários Cadastrados")
        
        # Get all employees
        employees_df = db.get_all_employees()
        
        if employees_df.empty:
            st.warning("Nenhum funcionário cadastrado no sistema.")
        else:
            # Show filter options
            mostrar_ativos = st.checkbox("Mostrar apenas funcionários ativos", value=True)
            
            if mostrar_ativos:
                filtered_df = employees_df[employees_df['ativo'] == True]
            else:
                filtered_df = employees_df
            
            # Display employee dataframe
            if filtered_df.empty:
                st.warning("Nenhum funcionário ativo cadastrado.")
            else:
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
                if st.button("Exportar Lista de Funcionários", use_container_width=True):
                    excel_buffer = BytesIO()
                    filtered_df.to_excel(excel_buffer, index=False)
                    excel_data = excel_buffer.getvalue()
                    
                    st.download_button(
                        label="Baixar como Excel",
                        data=excel_data,
                        file_name="lista_funcionarios.xlsx",
                        mime="application/vnd.ms-excel",
                        use_container_width=True
                    )
    
    elif employee_tab == "Cadastrar Funcionário":
        st.markdown("### Cadastrar Novo Funcionário")
        
        # Form to add new employee
        with st.form("add_employee_form"):
            matricula = st.text_input("Matrícula", help="Digite a matrícula/ID do funcionário")
            nome = st.text_input("Nome", help="Digite o nome completo do funcionário")
            
            tipo_options = ["interno", "chofer", "teclight", "outro"]
            tipo = st.selectbox("Tipo", tipo_options, help="Selecione o tipo de funcionário")
            
            ativo = st.checkbox("Ativo", value=True, help="Marque se o funcionário está ativo")
            
            submitted = st.form_submit_button("Cadastrar Funcionário", use_container_width=True)
            
            if submitted:
                if not matricula or not nome:
                    st.error("Matrícula e nome são campos obrigatórios.")
                else:
                    # Add employee to database
                    success, message = db.add_employee(matricula, nome, tipo, ativo)
                    
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
    
    elif employee_tab == "Editar/Remover Funcionário":
        st.markdown("### Editar ou Remover Funcionário")
        
        # Get all employees for selection
        employees_df = db.get_all_employees()
        
        if employees_df.empty:
            st.warning("Nenhum funcionário cadastrado no sistema.")
        else:
            # Search functionality
            search_term = st.text_input("Buscar funcionário (nome ou matrícula):")
            
            if search_term:
                filtered_df = db.search_employees(search_term)
                if filtered_df.empty:
                    st.warning(f"Nenhum funcionário encontrado com o termo '{search_term}'.")
                    display_df = employees_df
                else:
                    display_df = filtered_df
            else:
                display_df = employees_df
            
            # Select employee to edit
            matriculas = display_df['matricula'].tolist()
            nomes = display_df['nome'].tolist()
            
            # Create selection options
            options = [f"{mat} - {nome}" for mat, nome in zip(matriculas, nomes)]
            
            selected_employee = st.selectbox(
                "Selecione o funcionário para editar/remover:",
                options,
                format_func=lambda x: x
            )
            
            if selected_employee:
                # Extract matricula from selection
                selected_matricula = selected_employee.split(' - ')[0]
                
                # Get employee data
                employee = db.get_employee_by_matricula(selected_matricula)
                
                if employee is not None:
                    # Show edit form
                    with st.form("edit_employee_form"):
                        st.markdown(f"### Editando: {employee['nome']}")
                        
                        new_nome = st.text_input("Nome", value=employee['nome'])
                        
                        tipo_options = ["interno", "chofer", "teclight", "outro"]
                        current_tipo_index = tipo_options.index(employee['tipo']) if employee['tipo'] in tipo_options else 0
                        new_tipo = st.selectbox("Tipo", tipo_options, index=current_tipo_index)
                        
                        new_ativo = st.checkbox("Ativo", value=employee['ativo'])
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            update_btn = st.form_submit_button("Atualizar Dados", use_container_width=True)
                        
                        with col2:
                            delete_btn = st.form_submit_button("Remover Funcionário", use_container_width=True)
                        
                        if update_btn:
                            # Update employee
                            success, message = db.update_employee(
                                selected_matricula, 
                                nome=new_nome, 
                                tipo=new_tipo, 
                                ativo=new_ativo
                            )
                            
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
                        
                        if delete_btn:
                            # Show confirmation
                            if st.warning(f"Tem certeza que deseja remover {employee['nome']}?"):
                                # Delete employee
                                success, message = db.delete_employee(selected_matricula)
                                
                                if success:
                                    st.success(message)
                                else:
                                    st.error(message)
    
elif st.session_state.current_tab == "Veículos":
    # Interface for Vehicle Analysis
    st.markdown("## Análise de Veículos por Funcionário")
    st.markdown("Visualize os veículos movimentados por cada pessoa diretamente pelo nome.")
    
    # Verificar se algum arquivo foi carregado
    if 'processed_data' not in st.session_state or not st.session_state.processed_data:
        st.warning("Nenhum arquivo Excel carregado. Por favor, vá para a aba 'Análise' e carregue um arquivo Excel antes de usar esta funcionalidade.")
    else:
        # Obter os dados processados
        dataframes = st.session_state.dataframes
        result_df = st.session_state.processed_data
        saida_keywords = st.session_state.saida_keywords
        
        # Verificar se temos os dataframes completos para análise detalhada
        if 'dataframes_completos' not in st.session_state or not st.session_state.dataframes_completos:
            st.warning("Informações detalhadas dos veículos não estão disponíveis. Por favor, recarregue os arquivos na aba 'Análise'.")
        else:
            dataframes_completos = st.session_state.dataframes_completos
            
            # Extrair nomes dos manobristas da lista completa
            all_manobristas = []
            
            for df in dataframes:
                if df is None:
                    continue
                    
                manobrista_col = 'Manobrista' if 'Manobrista' in df.columns else df.columns[1]
                
                # Obter lista única de manobristas
                for _, row in df.iterrows():
                    manobrista = row[manobrista_col]
                    if isinstance(manobrista, str) and manobrista.strip():
                        # Limpar e formatar o nome
                        if '-' in manobrista:
                            # Formato com matrícula: "12345 - NOME"
                            nome_apenas = manobrista.split('-', 1)[1].strip()
                        else:
                            nome_apenas = manobrista.strip()
                        
                        if nome_apenas and nome_apenas not in all_manobristas:
                            all_manobristas.append(nome_apenas)
            
            # Ordenar alfabeticamente
            all_manobristas.sort()
            
            # Interface de seleção
            if all_manobristas:
                st.subheader("Selecione um funcionário para análise")
                
                # Opção de busca para facilitar encontrar um nome
                search_term = st.text_input("Buscar funcionário pelo nome:")
                
                filtered_manobristas = all_manobristas
                if search_term:
                    filtered_manobristas = [nome for nome in all_manobristas if search_term.upper() in nome.upper()]
                
                if not filtered_manobristas:
                    st.warning(f"Nenhum funcionário encontrado com o termo '{search_term}'.")
                else:
                    # Exibir lista de funcionários encontrados
                    funcionario_selecionado = st.selectbox(
                        "Selecione um funcionário:",
                        options=[""] + filtered_manobristas,
                        format_func=lambda x: x if x else "Selecione um funcionário..."
                    )
                    
                    # Se um funcionário foi selecionado
                    if funcionario_selecionado:
                        # Criar e mostrar dados detalhados
                        with st.expander("Detalhes dos veículos", expanded=True):
                            # Preparar lista de veículos do funcionário selecionado
                            veiculos_funcionario = []
                            
                            # Processar dados completos para extrair detalhes dos veículos
                            for df in dataframes_completos:
                                if df is None:
                                    continue
                                
                                # Verificar quais colunas estão disponíveis
                                colunas_necessarias = {
                                    'Chassi': 'Chassi',                  # Coluna A
                                    'Versão do modelo': 'Versão',        # Coluna C
                                    'Cor': 'Cor',                        # Coluna D
                                    'Status': 'Status',                  # Coluna E
                                    'Descrição': 'Descrição',            # Coluna F
                                    'Manobrista': 'Manobrista'           # Coluna H
                                }
                                
                                # Mapear nomes de colunas no DataFrame
                                colunas_mapeadas = {}
                                for nome_orig, nome_exib in colunas_necessarias.items():
                                    if nome_orig in df.columns:
                                        colunas_mapeadas[nome_orig] = nome_exib
                                    elif nome_orig == 'Chassi' and 0 in df.columns:
                                        colunas_mapeadas[0] = nome_exib
                                    elif nome_orig == 'Versão do modelo' and 2 in df.columns:
                                        colunas_mapeadas[2] = nome_exib
                                    elif nome_orig == 'Cor' and 3 in df.columns:
                                        colunas_mapeadas[3] = nome_exib
                                    elif nome_orig == 'Status' and 4 in df.columns:
                                        colunas_mapeadas[4] = nome_exib
                                    elif nome_orig == 'Descrição' and 5 in df.columns:
                                        colunas_mapeadas[5] = nome_exib
                                    elif nome_orig == 'Manobrista' and 7 in df.columns:
                                        colunas_mapeadas[7] = nome_exib
                                
                                # Identificar a coluna de manobrista
                                manobrista_col = 'Manobrista' if 'Manobrista' in df.columns else 7
                                
                                # Filtrar por nome do manobrista
                                for _, row in df.iterrows():
                                    manobrista = str(row[manobrista_col])
                                    
                                    # Verificar se o nome do manobrista contém o funcionário selecionado
                                    if funcionario_selecionado in manobrista:
                                        veiculo_info = {}
                                        
                                        # Adicionar as informações das colunas disponíveis
                                        for col_orig, col_exib in colunas_mapeadas.items():
                                            if col_orig in row.index:
                                                valor = row[col_orig]
                                                if pd.isna(valor):  # Verificar se é NaN
                                                    valor = ""
                                                veiculo_info[col_exib] = valor
                                        
                                        # Determinar tipo de movimentação
                                        if 'Status' in veiculo_info:
                                            status_upper = str(veiculo_info['Status']).upper()
                                            tipo_movimentacao = "Não Classificado"
                                            
                                            # Verificar se é saída
                                            is_saida = False
                                            for keyword in saida_keywords:
                                                if keyword in status_upper:
                                                    is_saida = True
                                                    break
                                            
                                            if is_saida:
                                                tipo_movimentacao = "Em Saída (Expedição)"
                                            elif 'PARQUEADO' in status_upper:
                                                tipo_movimentacao = "Parqueado"
                                            
                                            veiculo_info['Tipo de Movimentação'] = tipo_movimentacao
                                        
                                        # Adicionar à lista de veículos
                                        veiculos_funcionario.append(veiculo_info)
                            
                            # Criar DataFrame com os veículos
                            if veiculos_funcionario:
                                df_veiculos = pd.DataFrame(veiculos_funcionario)
                                
                                # Mostrar contagem por tipo de movimentação
                                st.subheader(f"Resumo de Veículos - {funcionario_selecionado}")
                                
                                # Contar tipos de movimentação se a coluna existe
                                if 'Tipo de Movimentação' in df_veiculos.columns:
                                    contagem = df_veiculos['Tipo de Movimentação'].value_counts().reset_index()
                                    contagem.columns = ['Tipo de Movimentação', 'Quantidade']
                                    
                                    # Mostrar gráfico
                                    fig = px.bar(
                                        contagem,
                                        x='Tipo de Movimentação',
                                        y='Quantidade',
                                        color='Tipo de Movimentação',
                                        title=f"Distribuição de Veículos - {funcionario_selecionado}",
                                        labels={'Quantidade': 'Número de Veículos'}
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                                
                                # Mostrar tabela detalhada
                                st.subheader("Lista de Veículos Movimentados")
                                
                                # Definir a ordem das colunas para exibição (priorizando as colunas solicitadas)
                                ordem_colunas = ['Chassi', 'Versão', 'Cor', 'Status', 'Descrição', 'Manobrista', 'Tipo de Movimentação']
                                colunas_exibir = [col for col in ordem_colunas if col in df_veiculos.columns]
                                
                                # Adicionar quaisquer outras colunas que possam existir
                                for col in df_veiculos.columns:
                                    if col not in colunas_exibir:
                                        colunas_exibir.append(col)
                                
                                # Exibir apenas as colunas disponíveis
                                st.dataframe(
                                    df_veiculos[colunas_exibir],
                                    hide_index=False,
                                    use_container_width=True
                                )
                                
                                # Download do relatório detalhado
                                excel_buffer = BytesIO()
                                df_veiculos.to_excel(excel_buffer, index=False)
                                excel_data = excel_buffer.getvalue()
                                
                                st.download_button(
                                    label="Baixar Relatório Detalhado",
                                    data=excel_data,
                                    file_name=f"detalhes_veiculos_{funcionario_selecionado}.xlsx",
                                    mime="application/vnd.ms-excel",
                                    use_container_width=True
                                )
                            else:
                                st.info(f"Não foram encontrados detalhes de veículos para o funcionário {funcionario_selecionado}")
            else:
                st.warning("Nenhum funcionário encontrado nos dados. Verifique se os arquivos Excel foram carregados corretamente.")
    
    # Tabs for different employee management functionalities
    employee_tab = st.radio(
        "Escolha uma opção:",
        ["Listar Funcionários", "Cadastrar Funcionário", "Editar/Remover Funcionário"],
        horizontal=True
    )
    
    if employee_tab == "Listar Funcionários":
        st.markdown("### Lista de Funcionários Cadastrados")
        
        # Get all employees
        employees_df = db.get_all_employees()
        
        if employees_df.empty:
            st.warning("Nenhum funcionário cadastrado no sistema.")
        else:
            # Show filter options
            mostrar_ativos = st.checkbox("Mostrar apenas funcionários ativos", value=True)
            
            if mostrar_ativos:
                filtered_df = employees_df[employees_df['ativo'] == True]
            else:
                filtered_df = employees_df
            
            # Display employee dataframe
            if filtered_df.empty:
                st.warning("Nenhum funcionário ativo cadastrado.")
            else:
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
                if st.button("Exportar Lista de Funcionários", use_container_width=True):
                    excel_buffer = BytesIO()
                    filtered_df.to_excel(excel_buffer, index=False)
                    excel_data = excel_buffer.getvalue()
                    
                    st.download_button(
                        label="Baixar como Excel",
                        data=excel_data,
                        file_name="lista_funcionarios.xlsx",
                        mime="application/vnd.ms-excel",
                        use_container_width=True
                    )
    
    elif employee_tab == "Cadastrar Funcionário":
        st.markdown("### Cadastrar Novo Funcionário")
        
        # Form to add new employee
        with st.form("add_employee_form"):
            matricula = st.text_input("Matrícula", help="Digite a matrícula/ID do funcionário")
            nome = st.text_input("Nome", help="Digite o nome completo do funcionário")
            
            tipo_options = ["interno", "chofer", "teclight", "outro"]
            tipo = st.selectbox("Tipo", tipo_options, help="Selecione o tipo de funcionário")
            
            ativo = st.checkbox("Ativo", value=True, help="Marque se o funcionário está ativo")
            
            submitted = st.form_submit_button("Cadastrar Funcionário", use_container_width=True)
            
            if submitted:
                if not matricula or not nome:
                    st.error("Matrícula e nome são campos obrigatórios.")
                else:
                    # Add employee to database
                    success, message = db.add_employee(matricula, nome, tipo, ativo)
                    
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
    
    elif employee_tab == "Editar/Remover Funcionário":
        st.markdown("### Editar ou Remover Funcionário")
        
        # Get all employees for selection
        employees_df = db.get_all_employees()
        
        if employees_df.empty:
            st.warning("Nenhum funcionário cadastrado no sistema.")
        else:
            # Search functionality
            search_term = st.text_input("Buscar funcionário (nome ou matrícula):")
            
            if search_term:
                filtered_df = db.search_employees(search_term)
                if filtered_df.empty:
                    st.warning(f"Nenhum funcionário encontrado com o termo '{search_term}'.")
                    display_df = employees_df
                else:
                    display_df = filtered_df
            else:
                display_df = employees_df
            
            # Select employee to edit
            matriculas = display_df['matricula'].tolist()
            nomes = display_df['nome'].tolist()
            
            # Create selection options
            options = [f"{mat} - {nome}" for mat, nome in zip(matriculas, nomes)]
            
            selected_employee = st.selectbox(
                "Selecione o funcionário para editar/remover:",
                options,
                format_func=lambda x: x
            )
            
            if selected_employee:
                # Extract matricula from selection
                selected_matricula = selected_employee.split(' - ')[0]
                
                # Get employee data
                employee = db.get_employee_by_matricula(selected_matricula)
                
                if employee is not None:
                    # Show edit form
                    with st.form("edit_employee_form"):
                        st.markdown(f"### Editando: {employee['nome']}")
                        
                        new_nome = st.text_input("Nome", value=employee['nome'])
                        
                        tipo_options = ["interno", "chofer", "teclight", "outro"]
                        current_tipo_index = tipo_options.index(employee['tipo']) if employee['tipo'] in tipo_options else 0
                        new_tipo = st.selectbox("Tipo", tipo_options, index=current_tipo_index)
                        
                        new_ativo = st.checkbox("Ativo", value=employee['ativo'])
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            update_btn = st.form_submit_button("Atualizar Dados", use_container_width=True)
                        
                        with col2:
                            delete_btn = st.form_submit_button("Remover Funcionário", use_container_width=True)
                        
                        if update_btn:
                            # Update employee
                            success, message = db.update_employee(
                                selected_matricula, 
                                nome=new_nome, 
                                tipo=new_tipo, 
                                ativo=new_ativo
                            )
                            
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
                        
                        if delete_btn:
                            # Show confirmation
                            if st.warning(f"Tem certeza que deseja remover {employee['nome']}?"):
                                # Delete employee
                                success, message = db.delete_employee(selected_matricula)
                                
                                if success:
                                    st.success(message)
                                else:
                                    st.error(message)
    
    elif employee_tab == "Análise de Veículos":
        st.markdown("### Análise de Veículos por Funcionário")
        st.markdown("Análise de veículos movimentados por funcionário, baseado nos dados carregados.")
        
        # Verificar se algum arquivo foi carregado
        if 'processed_data' not in st.session_state or not st.session_state.processed_data:
            st.warning("Nenhum arquivo Excel carregado. Por favor, vá para a aba 'Análise' e carregue um arquivo Excel antes de usar esta funcionalidade.")
        else:
            # Obter os dados processados
            dataframes = st.session_state.dataframes
            result_df = st.session_state.processed_data
            total_manobristas = len(result_df)
            saida_keywords = st.session_state.saida_keywords
            
            # Get all employees
            employees_df = db.get_all_employees()
            
            if employees_df.empty:
                st.warning("Nenhum funcionário cadastrado no sistema.")
            else:
                # Opções de filtro
                mostrar_ativos = st.checkbox("Mostrar apenas funcionários ativos", value=True)
                
                if mostrar_ativos:
                    filtered_df = employees_df[employees_df['ativo'] == True]
                else:
                    filtered_df = employees_df
                
                if filtered_df.empty:
                    st.warning("Nenhum funcionário ativo cadastrado.")
                else:
                    # Juntar matrículas e nomes
                    matriculas = filtered_df['matricula'].tolist()
                    nomes = filtered_df['nome'].tolist()
                    
                    # Criar lista de opções
                    opcoes_funcionarios = [f"{mat} - {nome}" for mat, nome in zip(matriculas, nomes)]
                    
                    funcionario_selecionado = st.selectbox(
                        "Selecione um funcionário para ver detalhes de veículos:",
                        options=[""] + opcoes_funcionarios,
                        format_func=lambda x: x if x else "Selecione um funcionário..."
                    )
                    
                    # Se um funcionário foi selecionado
                    if funcionario_selecionado:
                        # Extrair matrícula da seleção
                        matricula_selecionada = funcionario_selecionado.split(' - ')[0]
                        
                        # Criar e mostrar dados detalhados
                        with st.expander("Detalhes dos veículos", expanded=True):
                            # Preparar lista de veículos do funcionário selecionado
                            veiculos_funcionario = []
                            
                            # Processar novamente os dados originais para extrair detalhes dos veículos
                            for df in dataframes:
                                if df is None:
                                    continue
                                    
                                status_col = 'Status' if 'Status' in df.columns else df.columns[0]
                                manobrista_col = 'Manobrista' if 'Manobrista' in df.columns else df.columns[1]
                                
                                # Filtrar por manobrista que contém a matrícula selecionada
                                for _, row in df.iterrows():
                                    manobrista = row[manobrista_col]
                                    if matricula_selecionada in str(manobrista):
                                        status = row[status_col]
                                        
                                        # Determinar tipo de movimentação
                                        status_upper = str(status).upper()
                                        tipo_movimentacao = "Não Classificado"
                                        
                                        # Verificar se é saída
                                        is_saida = False
                                        for keyword in saida_keywords:
                                            if keyword in status_upper:
                                                is_saida = True
                                                break
                                        
                                        if is_saida:
                                            tipo_movimentacao = "Em Saída (Expedição)"
                                        elif 'PARQUEADO' in status_upper:
                                            tipo_movimentacao = "Parqueado"
                                        
                                        # Adicionar à lista de veículos
                                        veiculos_funcionario.append({
                                            "Status": status,
                                            "Tipo de Movimentação": tipo_movimentacao
                                        })
                            
                            # Criar DataFrame com os veículos
                            if veiculos_funcionario:
                                df_veiculos = pd.DataFrame(veiculos_funcionario)
                                
                                # Mostrar contagem por tipo de movimentação
                                st.subheader(f"Resumo de Veículos - {funcionario_selecionado}")
                                
                                # Contar tipos de movimentação
                                contagem = df_veiculos['Tipo de Movimentação'].value_counts().reset_index()
                                contagem.columns = ['Tipo de Movimentação', 'Quantidade']
                                
                                # Mostrar gráfico
                                fig = px.bar(
                                    contagem,
                                    x='Tipo de Movimentação',
                                    y='Quantidade',
                                    color='Tipo de Movimentação',
                                    title=f"Distribuição de Veículos - {funcionario_selecionado}",
                                    labels={'Quantidade': 'Número de Veículos'}
                                )
                                st.plotly_chart(fig, use_container_width=True)
                                
                                # Mostrar tabela detalhada
                                st.subheader("Lista de Veículos Movimentados")
                                st.dataframe(
                                    df_veiculos,
                                    hide_index=False,
                                    use_container_width=True
                                )
                                
                                # Download do relatório detalhado
                                excel_buffer = BytesIO()
                                df_veiculos.to_excel(excel_buffer, index=False)
                                excel_data = excel_buffer.getvalue()
                                
                                st.download_button(
                                    label="Baixar Relatório Detalhado",
                                    data=excel_data,
                                    file_name=f"detalhes_veiculos_{matricula_selecionada}.xlsx",
                                    mime="application/vnd.ms-excel",
                                    use_container_width=True
                                )
                            else:
                                st.info(f"Não foram encontrados detalhes de veículos para o funcionário {funcionario_selecionado}")

    # Footer for Employee Management tab
    st.markdown("---")
    st.markdown("### Informações")
    st.markdown("""
    - O cadastro de funcionários permite filtrar a análise de produtividade.
    - Apenas funcionários ativos serão considerados nos filtros.
    - A matrícula deve corresponder exatamente à matrícula que aparece nos relatórios Excel.
    - O campo 'Tipo' ajuda a identificar funcionários internos, chofer, teclight, etc.
    """)
'''

EMPLOYEE_DB_CONTENT = '''
import os
import pandas as pd
import csv

class EmployeeDatabase:
    """Classe para gerenciar o banco de dados de funcionários."""
    
    def __init__(self, db_file='funcionarios.csv'):
        """Inicializa o banco de dados de funcionários."""
        # Caminho para o arquivo de banco de dados
        self.db_file = db_file
        
        # Criar o arquivo se não existir
        if not os.path.exists(db_file):
            self._create_empty_db()
    
    def _create_empty_db(self):
        """Cria um banco de dados vazio com as colunas necessárias."""
        with open(self.db_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['matricula', 'nome', 'tipo', 'ativo'])
    
    def get_all_employees(self):
        """Retorna todos os funcionários do banco de dados."""
        try:
            df = pd.read_csv(self.db_file, encoding='utf-8')
            return df
        except Exception as e:
            print(f"Erro ao ler banco de dados: {e}")
            return pd.DataFrame(columns=['matricula', 'nome', 'tipo', 'ativo'])
    
    def get_active_employees(self):
        """Retorna apenas os funcionários ativos."""
        df = self.get_all_employees()
        return df[df['ativo'] == True]
    
    def add_employee(self, matricula, nome, tipo='interno', ativo=True):
        """Adiciona um novo funcionário ao banco de dados.
        
        Args:
            matricula (str): Matrícula/ID do funcionário
            nome (str): Nome completo do funcionário
            tipo (str): Tipo do funcionário (interno, chofer, teclight, etc)
            ativo (bool): Se o funcionário está ativo
        """
        # Verificar se a matrícula já existe
        df = self.get_all_employees()
        if not df.empty and matricula in df['matricula'].values:
            return False, "Matrícula já cadastrada"
        
        # Adicionar novo funcionário
        new_row = pd.DataFrame({
            'matricula': [matricula],
            'nome': [nome],
            'tipo': [tipo],
            'ativo': [ativo]
        })
        
        # Concatenar com o DF existente e salvar
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(self.db_file, index=False, encoding='utf-8')
        return True, "Funcionário cadastrado com sucesso"
    
    def update_employee(self, matricula, nome=None, tipo=None, ativo=None):
        """Atualiza os dados de um funcionário existente."""
        df = self.get_all_employees()
        
        # Verificar se a matrícula existe
        if df.empty or matricula not in df['matricula'].values:
            return False, "Matrícula não encontrada"
        
        # Atualizar os campos fornecidos
        idx = df[df['matricula'] == matricula].index[0]
        if nome is not None:
            df.loc[idx, 'nome'] = nome
        if tipo is not None:
            df.loc[idx, 'tipo'] = tipo
        if ativo is not None:
            df.loc[idx, 'ativo'] = ativo
        
        # Salvar alterações
        df.to_csv(self.db_file, index=False, encoding='utf-8')
        return True, "Dados atualizados com sucesso"
    
    def delete_employee(self, matricula):
        """Remove um funcionário do banco de dados."""
        df = self.get_all_employees()
        
        # Verificar se a matrícula existe
        if df.empty or matricula not in df['matricula'].values:
            return False, "Matrícula não encontrada"
        
        # Remover o funcionário
        df = df[df['matricula'] != matricula]
        df.to_csv(self.db_file, index=False, encoding='utf-8')
        return True, "Funcionário removido com sucesso"
    
    def get_employee_by_matricula(self, matricula):
        """Busca um funcionário pela matrícula."""
        df = self.get_all_employees()
        
        if df.empty or matricula not in df['matricula'].values:
            return None
        
        return df[df['matricula'] == matricula].iloc[0]
    
    def search_employees(self, query):
        """Pesquisa funcionários por nome ou matrícula."""
        df = self.get_all_employees()
        
        if df.empty:
            return df
        
        # Converter query para minúsculo para busca case-insensitive
        query = str(query).lower()
        
        # Buscar correspondências no nome ou matrícula
        mask = (
            df['nome'].str.lower().str.contains(query) | 
            df['matricula'].str.lower().str.contains(query)
        )
        
        return df[mask]

    def extract_matricula_from_name(self, employee_name):
        """Extrai a matrícula de um nome composto (ex: '12345 - NOME SOBRENOME')."""
        if employee_name and isinstance(employee_name, str) and ' - ' in employee_name:
            parts = employee_name.split(' - ', 1)
            return parts[0].strip()
        return None
    
    def is_registered_employee(self, employee_name):
        """Verifica se um funcionário está registrado no banco de dados.
        
        Args:
            employee_name (str): Nome completo do funcionário como aparece no Excel
                                 (ex: '12345 - NOME SOBRENOME')
        
        Returns:
            bool: True se o funcionário estiver registrado, False caso contrário
        """
        if not employee_name or not isinstance(employee_name, str):
            return False
            
        # Extrair matrícula do nome
        matricula = self.extract_matricula_from_name(employee_name)
        if not matricula:
            return False
            
        # Verificar se a matrícula está no banco de dados
        employee = self.get_employee_by_matricula(matricula)
        return employee is not None and employee['ativo']
'''

def write_temp_file(content, filename):
    # Cria um arquivo temporário real com o conteúdo fornecido
    if getattr(sys, 'frozen', False):
        # Se executando como executável, escreve na pasta do executável
        file_path = os.path.join(os.path.dirname(sys.executable), filename)
    else:
        # Caso contrário, escreve no diretório atual
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return file_path

def run_streamlit_app():
    # Define o diretório de trabalho
    if getattr(sys, 'frozen', False):
        # Executando como executável
        script_dir = os.path.dirname(sys.executable)
        os.chdir(script_dir)
    else:
        # Executando normalmente
        script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Cria os arquivos necessários
    app_path = write_temp_file(APP_CONTENT, "app.py")
    employee_db_path = write_temp_file(EMPLOYEE_DB_CONTENT, "employee_db.py")
    
    # Verifica se o arquivo funcionarios.csv existe, se não, cria
    if not os.path.exists("funcionarios.csv"):
        with open("funcionarios.csv", 'w', newline='', encoding='utf-8') as f:
            f.write("matricula,nome,tipo,ativo\n")
    
    # Cria diretório .streamlit se não existir
    streamlit_dir = ".streamlit"
    if not os.path.exists(streamlit_dir):
        os.makedirs(streamlit_dir)
    
    # Cria config.toml se não existir
    config_file = os.path.join(streamlit_dir, "config.toml")
    if not os.path.exists(config_file):
        with open(config_file, "w") as f:
            f.write("[server]\n")
            f.write("headless = true\n")
            f.write("address = \"0.0.0.0\"\n")
            f.write("port = 8501\n")
    
    # Inicia um thread para abrir o navegador após alguns segundos
    threading.Thread(target=open_browser).start()
    
    # Configura o comando para iniciar o Streamlit diretamente
    cmd = [
        sys.executable, "-m", "streamlit", "run", 
        app_path,
        "--server.headless=true",
        "--server.address=0.0.0.0",
        "--server.port=8501"
    ]
    
    # Executa o Streamlit como um processo
    try:
        print("Iniciando a aplicação de Análise de Produção de Manobristas...")
        print("Um navegador será aberto automaticamente em alguns segundos.")
        print("Se o navegador não abrir, acesse manualmente: http://localhost:8501")
        subprocess.run(cmd)
    except Exception as e:
        print(f"Erro ao iniciar a aplicação: {e}")
        input("Pressione Enter para sair...")

if __name__ == "__main__":
    run_streamlit_app()