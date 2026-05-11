"""
post_to_instagram.py

Script principal de publicação no Instagram via Graph API.
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

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

MAX_WAIT_SECONDS = 60
POLL_INTERVAL_SECONDS = 5

ROOT_DIR = Path(__file__).parent.parent
POSTS_DIR = ROOT_DIR / "posts"
PUBLISHED_DIR = POSTS_DIR / "published"


def get_env_or_die(var_name: str) -> str:
    value = os.environ.get(var_name)
    if not value:
        print(f"❌ ERRO: variável de ambiente {var_name} não foi definida.")
        sys.exit(1)
    return value


def find_next_pending_post() -> Optional[Path]:
    if not POSTS_DIR.exists():
        return None
    candidates = sorted([
        p for p in POSTS_DIR.iterdir()
        if p.is_dir() and p.name != "published"
    ])
    return candidates[0] if candidates else None


def find_image_in_folder(folder: Path) -> Path:
    images = [
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    ]
    if not images:
        print(f"❌ ERRO: nenhuma imagem encontrada em {folder}")
        sys.exit(1)
    if len(images) > 1:
        print(f"⚠️  Múltiplas imagens em {folder}, usando {images[0].name}")
    return images[0]


def read_caption(folder: Path) -> str:
    caption_file = folder / "caption.txt"
    if not caption_file.exists():
        print(f"⚠️  caption.txt não encontrado, post irá sem legenda.")
        return ""
    return caption_file.read_text(encoding="utf-8").strip()


def build_image_url(image_path: Path) -> str:
    repo = get_env_or_die("GITHUB_REPOSITORY")
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    relative_path = image_path.relative_to(ROOT_DIR).as_posix()
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{relative_path}"


def create_media_container(ig_user_id, access_token, image_url, caption):
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
    creation_id = response.json().get("id")
    print(f"✅ Container criado: {creation_id}")
    return creation_id


def wait_for_container_ready(creation_id, access_token):
    print(f"⏳ Aguardando processamento...")
    elapsed = 0
    while elapsed < MAX_WAIT_SECONDS:
        url = f"{GRAPH_API_BASE}/{creation_id}"
        params = {"fields": "status_code", "access_token": access_token}
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            status_code = response.json().get("status_code", "UNKNOWN")
            print(f"   Status: {status_code} ({elapsed}s)")
            if status_code == "FINISHED":
                print(f"✅ Container pronto.")
                return
            if status_code in ("ERROR", "EXPIRED"):
                print(f"❌ ERRO: container falhou com status {status_code}")
                sys.exit(1)
        time.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS
    print(f"❌ ERRO: container não ficou pronto em {MAX_WAIT_SECONDS}s.")
    sys.exit(1)


def publish_container(ig_user_id, access_token, creation_id):
    url = f"{GRAPH_API_BASE}/{ig_user_id}/media_publish"
    payload = {"creation_id": creation_id, "access_token": access_token}
    print(f"🚀 Publicando no Instagram...")
    response = requests.post(url, data=payload, timeout=30)
    if response.status_code != 200:
        print(f"❌ ERRO ao publicar: HTTP {response.status_code}")
        print(f"   Resposta: {response.text}")
        sys.exit(1)
    media_id = response.json().get("id")
    print(f"✅ Publicado! Media ID: {media_id}")
    return media_id


def move_to_published(folder, media_id):
    PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)
    destination = PUBLISHED_DIR / folder.name
    if destination.exists():
        destination = PUBLISHED_DIR / f"{folder.name}-{media_id}"
    shutil.move(str(folder), str(destination))
    print(f"📁 Pasta movida para: {destination.relative_to(ROOT_DIR)}")
    (destination / "media_id.txt").write_text(media_id, encoding="utf-8")


def commit_and_push_changes(folder_name, media_id):
    if not os.environ.get("GITHUB_ACTIONS"):
        return
    try:
        subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", "posts/"], check=True)
        subprocess.run(["git", "commit", "-m", f"Publicado: {folder_name} (media_id: {media_id})"], check=True)
        subprocess.run(["git", "push"], check=True)
        print(f"✅ Commit e push realizados.")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Erro no git: {e}")


def main():
    print("=" * 60)
    print("📸 Publicação no Instagram — BookTime")
    print("=" * 60)

    ig_user_id = get_env_or_die("IG_BUSINESS_ACCOUNT_ID")
    access_token = get_env_or_die("IG_ACCESS_TOKEN")

    folder = find_next_pending_post()
    if not folder:
        print("ℹ️  Nenhum post pendente em posts/. Nada a fazer.")
        return

    print(f"📂 Próximo post: {folder.name}")
    image_path = find_image_in_folder(folder)
    caption = read_caption(folder)
    image_url = build_image_url(image_path)

    print(f"🖼️  Imagem: {image_path.name}")
    print(f"📝 Caption ({len(caption)} chars): {caption[:80]}{'...' if len(caption) > 80 else ''}")

    creation_id = create_media_container(ig_user_id, access_token, image_url, caption)
    wait_for_container_ready(creation_id, access_token)
    media_id = publish_container(ig_user_id, access_token, creation_id)

    move_to_published(folder, media_id)
    commit_and_push_changes(folder.name, media_id)

    print("=" * 60)
    print(f"🎉 Tudo certo!")
    print("=" * 60)


if __name__ == "__main__":
    main()
