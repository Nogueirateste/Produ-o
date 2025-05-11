import pandas as pd
import os
import hashlib
import secrets
import string

class UserAuth:
    """Sistema de autenticação de usuários com armazenamento em CSV."""
    
    def __init__(self, users_file='usuarios.csv'):
        """Inicializa o sistema de autenticação.
        
        Args:
            users_file (str): Caminho para o arquivo CSV de usuários
        """
        self.users_file = users_file
        self._check_users_file()
    
    def _check_users_file(self):
        """Verifica se o arquivo de usuários existe e o cria se necessário."""
        if not os.path.exists(self.users_file):
            self._create_empty_users_file()
            # Criar um usuário admin padrão na primeira execução
            self.add_user(
                username="admin", 
                password="admin123", 
                nome_completo="Administrador",
                nivel_acesso="admin"
            )
    
    def _create_empty_users_file(self):
        """Cria um arquivo de usuários vazio com as colunas necessárias."""
        df = pd.DataFrame(columns=['username', 'password_hash', 'salt', 'nome_completo', 'nivel_acesso', 'ativo'])
        df.to_csv(self.users_file, index=False)
        print("Arquivo de usuários criado com sucesso!")
    
    def _hash_password(self, password, salt=None):
        """Gera um hash seguro da senha com salt.
        
        Args:
            password (str): Senha do usuário
            salt (str, optional): Salt para o hash. Se None, gera um novo.
            
        Returns:
            tuple: (hash_senha, salt)
        """
        if salt is None:
            # Gerar um salt aleatório
            salt = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
        
        # Concatenar senha e salt antes de gerar o hash
        password_with_salt = password + salt
        # Gerar hash SHA-256
        password_hash = hashlib.sha256(password_with_salt.encode()).hexdigest()
        
        return password_hash, salt
    
    def get_all_users(self):
        """Retorna todos os usuários cadastrados.
        
        Returns:
            pandas.DataFrame: DataFrame com todos os usuários
        """
        try:
            return pd.read_csv(self.users_file)
        except Exception as e:
            print(f"Erro ao ler arquivo de usuários: {str(e)}")
            return pd.DataFrame(columns=['username', 'password_hash', 'salt', 'nome_completo', 'nivel_acesso', 'ativo'])
    
    def get_active_users(self):
        """Retorna apenas os usuários ativos.
        
        Returns:
            pandas.DataFrame: DataFrame com usuários ativos
        """
        users_df = self.get_all_users()
        return users_df[users_df['ativo'] == True]
    
    def add_user(self, username, password, nome_completo, nivel_acesso="operador", ativo=True):
        """Adiciona um novo usuário ao sistema.
        
        Args:
            username (str): Nome de usuário único
            password (str): Senha do usuário
            nome_completo (str): Nome completo do usuário
            nivel_acesso (str): Nível de acesso (admin, supervisor, operador)
            ativo (bool): Se o usuário está ativo no sistema
            
        Returns:
            tuple: (sucesso, mensagem)
        """
        # Validar nível de acesso
        if nivel_acesso not in ["admin", "supervisor", "operador"]:
            return False, "Nível de acesso inválido. Use 'admin', 'supervisor' ou 'operador'."
        
        # Verificar se o usuário já existe
        users_df = self.get_all_users()
        if username in users_df['username'].values:
            return False, f"Usuário '{username}' já existe no sistema."
        
        # Gerar hash da senha
        password_hash, salt = self._hash_password(password)
        
        # Adicionar o novo usuário
        new_user = {
            'username': username,
            'password_hash': password_hash,
            'salt': salt,
            'nome_completo': nome_completo,
            'nivel_acesso': nivel_acesso,
            'ativo': ativo
        }
        
        # Adicionar ao DataFrame e salvar
        new_row = pd.DataFrame([new_user])
        users_df = pd.concat([users_df, new_row], ignore_index=True)
        users_df.to_csv(self.users_file, index=False)
        
        return True, f"Usuário '{username}' adicionado com sucesso."
    
    def update_user(self, username, nome_completo=None, nivel_acesso=None, ativo=None, password=None):
        """Atualiza os dados de um usuário existente.
        
        Args:
            username (str): Nome de usuário a ser atualizado
            nome_completo (str, optional): Novo nome completo
            nivel_acesso (str, optional): Novo nível de acesso
            ativo (bool, optional): Novo status de ativo
            password (str, optional): Nova senha
            
        Returns:
            tuple: (sucesso, mensagem)
        """
        # Verificar se o usuário existe
        users_df = self.get_all_users()
        if username not in users_df['username'].values:
            return False, f"Usuário '{username}' não encontrado."
        
        # Obter o índice do usuário
        user_idx = users_df.index[users_df['username'] == username].tolist()[0]
        
        # Atualizar campos
        if nome_completo is not None:
            users_df.at[user_idx, 'nome_completo'] = nome_completo
            
        if nivel_acesso is not None:
            if nivel_acesso not in ["admin", "supervisor", "operador"]:
                return False, "Nível de acesso inválido. Use 'admin', 'supervisor' ou 'operador'."
            users_df.at[user_idx, 'nivel_acesso'] = nivel_acesso
            
        if ativo is not None:
            users_df.at[user_idx, 'ativo'] = ativo
            
        if password is not None:
            # Obter o salt existente
            salt = users_df.at[user_idx, 'salt']
            # Atualizar o hash da senha
            password_hash, _ = self._hash_password(password, salt)
            users_df.at[user_idx, 'password_hash'] = password_hash
        
        # Salvar as alterações
        users_df.to_csv(self.users_file, index=False)
        
        return True, f"Usuário '{username}' atualizado com sucesso."
    
    def delete_user(self, username):
        """Remove um usuário do sistema.
        
        Args:
            username (str): Nome de usuário a ser removido
            
        Returns:
            tuple: (sucesso, mensagem)
        """
        # Verificar se o usuário existe
        users_df = self.get_all_users()
        if username not in users_df['username'].values:
            return False, f"Usuário '{username}' não encontrado."
        
        # Verificar se é o último admin ativo
        if username != "admin":  # Admin original não pode ser excluído
            user_data = users_df[users_df['username'] == username].iloc[0]
            
            if user_data['nivel_acesso'] == "admin" and user_data['ativo']:
                # Conta quantos admins ativos temos
                active_admins = users_df[(users_df['nivel_acesso'] == "admin") & (users_df['ativo'])].shape[0]
                
                if active_admins <= 1:
                    return False, "Não é possível remover o último administrador ativo do sistema."
        
        # Remover o usuário
        users_df = users_df[users_df['username'] != username]
        users_df.to_csv(self.users_file, index=False)
        
        return True, f"Usuário '{username}' removido com sucesso."
    
    def authenticate(self, username, password):
        """Autentica um usuário com username e senha.
        
        Args:
            username (str): Nome de usuário
            password (str): Senha
            
        Returns:
            tuple: (autenticado, dados_usuario)
        """
        # Verificar se o usuário existe
        users_df = self.get_all_users()
        if username not in users_df['username'].values:
            return False, None
        
        # Obter os dados do usuário
        user_data = users_df[users_df['username'] == username].iloc[0].to_dict()
        
        # Verificar se o usuário está ativo
        if not user_data['ativo']:
            return False, None
        
        # Verificar a senha
        password_hash = user_data['password_hash']
        salt = user_data['salt']
        
        # Gerar hash da senha fornecida
        input_hash, _ = self._hash_password(password, salt)
        
        if input_hash == password_hash:
            # Autenticação bem-sucedida
            return True, user_data
        else:
            # Senha incorreta
            return False, None
    
    def get_user_by_username(self, username):
        """Busca um usuário pelo nome de usuário.
        
        Args:
            username (str): Nome de usuário a ser buscado
            
        Returns:
            dict or None: Dados do usuário ou None se não encontrado
        """
        users_df = self.get_all_users()
        if username in users_df['username'].values:
            return users_df[users_df['username'] == username].iloc[0].to_dict()
        return None