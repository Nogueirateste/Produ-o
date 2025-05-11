import os
import shutil
import subprocess
import glob
import tempfile
import sys

def upload_to_github(github_token, repo_url="https://github.com/Nogueirateste/Produ-o.git"):
    """Envia o código para o GitHub usando um token de acesso pessoal."""
    
    print("Preparando para enviar o código para GitHub...")
    
    # Extrair usuário e repo do URL
    parts = repo_url.split('/')
    repo_name = parts[-1].replace('.git', '')
    user_name = parts[-2]
    
    # Criar diretório temporário
    temp_dir = tempfile.mkdtemp()
    print(f"Criado diretório temporário: {temp_dir}")
    
    try:
        # Mudar para o diretório temporário
        os.chdir(temp_dir)
        
        # Inicializar Git
        subprocess.run(["git", "init"], check=True)
        subprocess.run(["git", "config", "--local", "user.name", "GitHub Actions"], check=True)
        subprocess.run(["git", "config", "--local", "user.email", "actions@github.com"], check=True)
        
        # Copiar todos os arquivos do projeto
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        print(f"Copiando arquivos de {script_dir}...")
        
        # Copiar arquivos Python
        for py_file in glob.glob(os.path.join(script_dir, "*.py")):
            shutil.copy2(py_file, temp_dir)
            print(f"Copiado: {os.path.basename(py_file)}")
        
        # Copiar arquivos CSV
        for csv_file in glob.glob(os.path.join(script_dir, "*.csv")):
            shutil.copy2(csv_file, temp_dir)
            print(f"Copiado: {os.path.basename(csv_file)}")
        
        # Copiar arquivos BAT
        for bat_file in glob.glob(os.path.join(script_dir, "*.bat")):
            shutil.copy2(bat_file, temp_dir)
            print(f"Copiado: {os.path.basename(bat_file)}")
        
        # Copiar arquivos TOML
        for toml_file in glob.glob(os.path.join(script_dir, "*.toml")):
            shutil.copy2(toml_file, temp_dir)
            print(f"Copiado: {os.path.basename(toml_file)}")
        
        # Criar diretório para assets
        assets_dir = os.path.join(temp_dir, "attached_assets")
        os.makedirs(assets_dir, exist_ok=True)
        
        # Copiar assets
        for asset_file in glob.glob(os.path.join(script_dir, "attached_assets", "*.*")):
            shutil.copy2(asset_file, assets_dir)
            print(f"Copiado asset: {os.path.basename(asset_file)}")
        
        # Adicionar todos os arquivos ao Git
        subprocess.run(["git", "add", "."], check=True)
        
        # Fazer commit
        subprocess.run(["git", "commit", "-m", "Upload automático do projeto de Análise de Produção de Manobristas"], check=True)
        
        # Configurar o remote
        repo_url_with_token = f"https://{github_token}@github.com/{user_name}/{repo_name}.git"
        subprocess.run(["git", "remote", "add", "origin", repo_url_with_token], check=True)
        
        # Fazer push
        subprocess.run(["git", "push", "-u", "origin", "master"], check=True)
        
        print("\nSucesso! O código foi enviado para o GitHub.")
        print(f"Repositório: https://github.com/{user_name}/{repo_name}")
        
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar comando Git: {e}")
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        # Limpar o token do histórico de comandos
        try:
            subprocess.run(["history", "-c"], shell=True, check=False)
        except:
            pass
        
        # Voltar para o diretório original
        os.chdir(script_dir)
        
        # Limpar diretório temporário
        try:
            shutil.rmtree(temp_dir)
            print(f"Diretório temporário removido: {temp_dir}")
        except:
            print(f"Não foi possível remover o diretório temporário: {temp_dir}")

if __name__ == "__main__":
    token = input("Digite seu token de acesso pessoal do GitHub: ")
    upload_to_github(token)