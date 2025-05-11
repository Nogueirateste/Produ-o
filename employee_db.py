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