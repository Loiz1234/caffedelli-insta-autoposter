"""
Descobre o location_id de Muzambinho (ou outro lugar) via Instagram Graph API.

Uso local:
    IG_ACCESS_TOKEN=EAAxxxx... IG_USER_ID=178xxx python scripts/find_location.py

Uso via GitHub Actions (workflow_dispatch "Find Location"):
    Gatilha manualmente no GitHub Actions UI em .github/workflows/find_location.yml

Saida: lista de paginas do Facebook que podem ser usadas como location_id.
Copia o ID da pagina mais relevante (normalmente "Muzambinho" categoria City)
e adiciona como Secret IG_LOCATION_ID no repositorio.
"""
import os
import sys
from ig_api import InstagramPoster

QUERY = os.environ.get("LOCATION_QUERY", "Muzambinho")


def main():
    token = os.environ.get("IG_ACCESS_TOKEN")
    user_id = os.environ.get("IG_USER_ID")
    if not token or not user_id:
        print("ERRO: Defina IG_USER_ID e IG_ACCESS_TOKEN no ambiente")
        return 1

    poster = InstagramPoster(user_id, token)
    print(f"Buscando paginas com termo '{QUERY}'...\n")
    results = poster.search_location(QUERY, limit=20)

    if not results:
        print("Nenhum resultado. Tente outro termo (ex: 'Muzambinho MG', 'Muzambinho Minas Gerais').")
        return 1

    print(f"{'ID':<22} {'Categoria':<25} Nome")
    print("-" * 100)
    for r in results:
        pid = r.get("id", "")
        cat = (r.get("category") or "-")[:24]
        name = r.get("name", "")
        print(f"{pid:<22} {cat:<25} {name}")

    print("\nCopie o ID mais adequado (geralmente categoria 'City' ou 'Local Business' em Muzambinho)")
    print("e adicione como Secret 'IG_LOCATION_ID' em:")
    print("https://github.com/Loiz1234/caffedelli-insta-autoposter/settings/secrets/actions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
