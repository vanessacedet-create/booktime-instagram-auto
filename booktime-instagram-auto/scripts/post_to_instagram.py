"""
post_to_instagram.py

Script principal de publicação no Instagram via Graph API.

Como funciona:
1. Procura a próxima pasta dentro de `posts/` que NÃO esteja em `posts/published/`.
2. Lê a imagem e o arquivo caption.txt dessa pasta.
3. Monta a URL pública da imagem (raw.githubusercontent.com).
4. Chama POST /{ig-user-id}/media para criar o container.
5. Aguarda o container ficar pronto (status FINISHED).
6. Chama POST /{ig-user-id}/media_publish para publicar de fato.
7. Move a pasta para posts/published/ e commita a mudança.

Variáveis de ambiente esperadas:
- IG_ACCESS_TOKEN: token de longa duração (60 dias) da Graph API
- IG_BUSINESS_ACCOUNT_ID: ID da conta Instagram Business
- GITHUB_REPOSITORY: vem automaticamente do GitHub Actions (ex: user/repo)
- GITHUB_REF_NAME: branch atual, também automático (ex: main)
"""

import os
import sys
import time
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import requests

# ===== Configuração =====
GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

# Extensões de imagem aceitas pelo Instagram
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

# Tempo máximo de espera pelo processamento do container (em segundos)
MAX_WAIT_SECONDS = 60
POLL_INTERVAL_SECONDS = 5

# Caminhos
ROOT_DIR = Path(__file__).parent.parent
POSTS_DIR = ROOT_DIR / "posts"
PUBLISHED_DIR = POSTS_DIR / "published"


def get_env_or_die(var_name: str) -> str:
    """Pega variável de ambiente ou aborta com mensagem clara."""
    value = os.environ.get(var_name)
    if not value:
        print(f"❌ ERRO: variável de ambiente {var_name} não foi definida.")
        print(f"   Verifique se o secret {var_name} está configurado no GitHub.")
        sys.exit(1)
    return value


def find_next_pending_post() -> Optional[Path]:
    """
    Encontra a próxima pasta pendente em posts/.
    Retorna o caminho da pasta ou None se não houver nada pendente.

    Ordena alfabeticamente, então se você nomear as pastas com prefixo
    numérico ou data, a ordem fica previsível.
    Ex: posts/2026-05-11-livro-x/, posts/2026-05-12-livro-y/
    """
    if not POSTS_DIR.exists():
        return None

    candidates = sorted([
        p for p in POSTS_DIR.iterdir()
        if p.is_dir() and p.name != "published"
    ])

    return candidates[0] if candidates else None


def find_image_in_folder(folder: Path) -> Path:
    """Encontra o primeiro arquivo de imagem na pasta."""
    images = [
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    ]
    if not images:
        print(f"❌ ERRO: nenhuma imagem encontrada em {folder}")
        print(f"   Formatos aceitos: {', '.join(IMAGE_EXTENSIONS)}")
        sys.exit(1)
    if len(images) > 1:
        print(f"⚠️  Aviso: múltiplas imagens em {folder}, usando {images[0].name}")
    return images[0]


def read_caption(folder: Path) -> str:
    """Lê o conteúdo de caption.txt da pasta. Se não existir, usa string vazia."""
    caption_file = folder / "caption.txt"
    if not caption_file.exists():
        print(f"⚠️  Aviso: caption.txt não encontrado em {folder}, post irá sem legenda.")
        return ""
    return caption_file.read_text(encoding="utf-8").strip()


def build_image_url(image_path: Path) -> str:
    """
    Monta a URL pública da imagem via raw.githubusercontent.com.
    Formato: https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{caminho}
    """
    repo = get_env_or_die("GITHUB_REPOSITORY")  # ex: vanessacedet-create/booktime-instagram-auto
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    relative_path = image_path.relative_to(ROOT_DIR).as_posix()
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{relative_path}"


def create_media_container(ig_user_id: str, access_token: str, image_url: str, caption: str) -> str:
    """
    Cria o container de mídia (passo 1 da publicação).
    Retorna o creation_id do container.
    """
    url = f"{GRAPH_API_BASE}/{ig_user_id}/media"
    payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": access_token,
    }

    print(f"📤 Criando container de mídia...")
    print(f"   image_url: {image_url}")

    response = requests.post(url, data=payload, timeout=30)

    if response.status_code != 200:
        print(f"❌ ERRO ao criar container: HTTP {response.status_code}")
        print(f"   Resposta: {response.text}")
        sys.exit(1)

    data = response.json()
    creation_id = data.get("id")
    if not creation_id:
        print(f"❌ ERRO: resposta sem creation_id: {data}")
        sys.exit(1)

    print(f"✅ Container criado: {creation_id}")
    return creation_id


def wait_for_container_ready(creation_id: str, access_token: str) -> None:
    """
    Faz polling até o container ficar pronto.
    Status possíveis: EXPIRED, ERROR, FINISHED, IN_PROGRESS, PUBLISHED.
    """
    print(f"⏳ Aguardando processamento do container...")

    elapsed = 0
    while elapsed < MAX_WAIT_SECONDS:
        url = f"{GRAPH_API_BASE}/{creation_id}"
        params = {
            "fields": "status_code",
            "access_token": access_token,
        }
        response = requests.get(url, params=params, timeout=30)

        if response.status_code != 200:
            print(f"⚠️  Erro ao consultar status: HTTP {response.status_code} - {response.text}")
            time.sleep(POLL_INTERVAL_SECONDS)
            elapsed += POLL_INTERVAL_SECONDS
            continue

        status_code = response.json().get("status_code", "UNKNOWN")
        print(f"   Status: {status_code} ({elapsed}s)")

        if status_code == "FINISHED":
            print(f"✅ Container pronto para publicar.")
            return
        if status_code in ("ERROR", "EXPIRED"):
            print(f"❌ ERRO: container falhou com status {status_code}")
            sys.exit(1)

        time.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS

    print(f"❌ ERRO: container não ficou pronto em {MAX_WAIT_SECONDS}s.")
    sys.exit(1)


def publish_container(ig_user_id: str, access_token: str, creation_id: str) -> str:
    """
    Publica o container (passo final).
    Retorna o ID da mídia publicada.
    """
    url = f"{GRAPH_API_BASE}/{ig_user_id}/media_publish"
    payload = {
        "creation_id": creation_id,
        "access_token": access_token,
    }

    print(f"🚀 Publicando no Instagram...")
    response = requests.post(url, data=payload, timeout=30)

    if response.status_code != 200:
        print(f"❌ ERRO ao publicar: HTTP {response.status_code}")
        print(f"   Resposta: {response.text}")
        sys.exit(1)

    media_id = response.json().get("id")
    print(f"✅ Publicado! Media ID: {media_id}")
    return media_id


def move_to_published(folder: Path, media_id: str) -> None:
    """Move a pasta do post publicado para posts/published/."""
    PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)
    destination = PUBLISHED_DIR / folder.name

    # Se já existe destino com mesmo nome, adiciona sufixo
    if destination.exists():
        destination = PUBLISHED_DIR / f"{folder.name}-{media_id}"

    shutil.move(str(folder), str(destination))
    print(f"📁 Pasta movida para: {destination.relative_to(ROOT_DIR)}")

    # Grava o media_id num arquivo dentro da pasta arquivada
    (destination / "media_id.txt").write_text(media_id, encoding="utf-8")


def commit_and_push_changes(folder_name: str, media_id: str) -> None:
    """
    Commita o movimento da pasta e dá push.
    Roda apenas dentro do GitHub Actions.
    """
    if not os.environ.get("GITHUB_ACTIONS"):
        print(f"ℹ️  Não está no GitHub Actions, pulando commit/push.")
        return

    try:
        subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(
            ["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"],
            check=True,
        )
        subprocess.run(["git", "add", "posts/"], check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Publicado: {folder_name} (media_id: {media_id})"],
            check=True,
        )
        subprocess.run(["git", "push"], check=True)
        print(f"✅ Commit e push realizados.")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Erro no git: {e}")
        print(f"   A imagem foi publicada no Instagram, mas o repo não foi atualizado.")
        print(f"   Você pode mover a pasta manualmente pra posts/published/.")


def main():
    print("=" * 60)
    print("📸 Publicação no Instagram — BookTime")
    print("=" * 60)

    # 1. Carregar credenciais
    ig_user_id = get_env_or_die("IG_BUSINESS_ACCOUNT_ID")
    access_token = get_env_or_die("IG_ACCESS_TOKEN")

    # 2. Encontrar próximo post pendente
    folder = find_next_pending_post()
    if not folder:
        print("ℹ️  Nenhum post pendente em posts/. Nada a fazer.")
        return

    print(f"📂 Próximo post: {folder.name}")

    # 3. Pegar imagem e caption
    image_path = find_image_in_folder(folder)
    caption = read_caption(folder)
    image_url = build_image_url(image_path)

    print(f"🖼️  Imagem: {image_path.name}")
    print(f"📝 Caption ({len(caption)} caracteres): {caption[:80]}{'...' if len(caption) > 80 else ''}")

    # 4. Publicar
    creation_id = create_media_container(ig_user_id, access_token, image_url, caption)
    wait_for_container_ready(creation_id, access_token)
    media_id = publish_container(ig_user_id, access_token, creation_id)

    # 5. Arquivar
    move_to_published(folder, media_id)
    commit_and_push_changes(folder.name, media_id)

    print("=" * 60)
    print(f"🎉 Tudo certo! Confira em: https://www.instagram.com/p/{media_id}")
    print("=" * 60)


if __name__ == "__main__":
    main()
