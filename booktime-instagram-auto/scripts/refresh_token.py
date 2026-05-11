"""
refresh_token.py

Renova o token de longa duração (60 dias) da Graph API antes que expire.

O Facebook permite trocar um token de longa duração ainda válido por outro
de longa duração, resetando o prazo de 60 dias. Esse script deve rodar
mensalmente via GitHub Actions agendado.

Variáveis de ambiente esperadas:
- IG_ACCESS_TOKEN: token atual (ainda válido)
- APP_ID: ID do app no Meta for Developers
- APP_SECRET: secret do app no Meta for Developers
- GITHUB_TOKEN: vem automaticamente do Actions, usado pra atualizar o secret

Observação importante:
Atualizar secrets do GitHub via API requer permissão extra. Esse script faz
isso usando a REST API do GitHub. Veja README pra como configurar.
"""

import os
import sys
import requests
import base64
from nacl import encoding, public

GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def get_env_or_die(var_name: str) -> str:
    value = os.environ.get(var_name)
    if not value:
        print(f"❌ ERRO: variável de ambiente {var_name} não foi definida.")
        sys.exit(1)
    return value


def refresh_long_lived_token(app_id: str, app_secret: str, current_token: str) -> str:
    """
    Pede um novo token de longa duração ao Facebook.
    O novo token vale outros 60 dias a partir de agora.
    """
    url = f"{GRAPH_API_BASE}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": current_token,
    }

    print("📤 Solicitando novo token de longa duração...")
    response = requests.get(url, params=params, timeout=30)

    if response.status_code != 200:
        print(f"❌ ERRO: HTTP {response.status_code}")
        print(f"   Resposta: {response.text}")
        sys.exit(1)

    data = response.json()
    new_token = data.get("access_token")
    expires_in = data.get("expires_in", "desconhecido")

    if not new_token:
        print(f"❌ ERRO: resposta sem access_token: {data}")
        sys.exit(1)

    print(f"✅ Novo token obtido. Expira em ~{expires_in} segundos (~60 dias).")
    return new_token


def encrypt_secret(public_key: str, secret_value: str) -> str:
    """Criptografa o valor do secret usando a chave pública do repo (formato exigido pelo GitHub)."""
    pk = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(pk)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def update_github_secret(repo: str, secret_name: str, secret_value: str, github_token: str) -> None:
    """Atualiza um secret do repositório no GitHub via API REST."""
    print(f"🔐 Atualizando secret {secret_name} no GitHub...")

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # 1. Pegar a chave pública do repo
    key_url = f"https://api.github.com/repos/{repo}/actions/secrets/public-key"
    key_response = requests.get(key_url, headers=headers, timeout=30)

    if key_response.status_code != 200:
        print(f"❌ ERRO ao buscar chave pública: HTTP {key_response.status_code}")
        print(f"   Resposta: {key_response.text}")
        print(f"   Verifique se o GITHUB_TOKEN tem permissão de escrita em secrets.")
        sys.exit(1)

    key_data = key_response.json()
    public_key = key_data["key"]
    key_id = key_data["key_id"]

    # 2. Criptografar o novo valor
    encrypted_value = encrypt_secret(public_key, secret_value)

    # 3. Atualizar o secret
    update_url = f"https://api.github.com/repos/{repo}/actions/secrets/{secret_name}"
    payload = {
        "encrypted_value": encrypted_value,
        "key_id": key_id,
    }
    update_response = requests.put(update_url, headers=headers, json=payload, timeout=30)

    if update_response.status_code not in (201, 204):
        print(f"❌ ERRO ao atualizar secret: HTTP {update_response.status_code}")
        print(f"   Resposta: {update_response.text}")
        sys.exit(1)

    print(f"✅ Secret {secret_name} atualizado com sucesso.")


def main():
    print("=" * 60)
    print("🔄 Renovação do token de longa duração")
    print("=" * 60)

    current_token = get_env_or_die("IG_ACCESS_TOKEN")
    app_id = get_env_or_die("APP_ID")
    app_secret = get_env_or_die("APP_SECRET")
    github_token = get_env_or_die("GH_PAT_FOR_SECRETS")
    repo = get_env_or_die("GITHUB_REPOSITORY")

    new_token = refresh_long_lived_token(app_id, app_secret, current_token)
    update_github_secret(repo, "IG_ACCESS_TOKEN", new_token, github_token)

    print("=" * 60)
    print("🎉 Token renovado. Próxima renovação automática em ~30 dias.")
    print("=" * 60)


if __name__ == "__main__":
    main()
