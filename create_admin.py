from user_auth import UserAuth

# Criar instância do sistema de autenticação
auth = UserAuth()

# Adicionar usuário admin
success, message = auth.add_user(
    username="admin", 
    password="admin123", 
    nome_completo="Administrador",
    nivel_acesso="admin"
)

print(message)