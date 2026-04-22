"""
Main runner — chamado pelo GitHub Actions a cada 15 minutos.
Le schedule.json, identifica posts que chegaram no horario, publica via Instagram Graph API.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ig_api import InstagramPoster, IGError

ROOT = Path(__file__).resolve().parent.parent
SCHEDULE_FILE = ROOT / "schedule.json"

# Janela de tolerancia — so posta se atraso <= 4h
# GitHub Actions cron pode atrasar ate 15-60 min em horarios de pico (SLA do GitHub).
# 4h da margem segura sem arriscar postar em horario inadequado (ver SAFE_END_HOUR).
TOLERANCE_HOURS = 4

# Horario seguro — nao posta entre 23h e 07h locais (BR)
# Protecao extra caso cron atrase muito — nao publica de madrugada.
SAFE_START_HOUR = 7   # nao posta antes
SAFE_END_HOUR = 23    # nao posta depois
TZ_BR = timezone(timedelta(hours=-3))


def log(msg):
    ts = datetime.now(TZ_BR).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def load_schedule():
    with open(SCHEDULE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_schedule(schedule):
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)


def build_public_url(relative_path: str) -> str:
    """Monta URL publica raw.githubusercontent.com para o arquivo."""
    repo = os.environ.get("GITHUB_REPOSITORY", "Loiz1234/caffedelli-insta-autoposter")
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    # Instagram precisa URL-encode de caracteres especiais
    import urllib.parse
    safe_path = urllib.parse.quote(relative_path, safe="/")
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{safe_path}"


def is_safe_hour(now: datetime) -> bool:
    h = now.hour
    return SAFE_START_HOUR <= h < SAFE_END_HOUR


def should_post(entry, now: datetime) -> bool:
    if entry.get("status") != "PRONTO_PARA_POSTAR":
        return False
    scheduled = datetime.fromisoformat(entry["data_agendada"])
    if scheduled > now:
        return False
    # Janela de tolerancia
    if (now - scheduled) > timedelta(hours=TOLERANCE_HOURS):
        # Muito atrasado — marca como pulado
        entry["status"] = "PULADO_ATRASO"
        entry["erro"] = f"Fora da janela de tolerancia de {TOLERANCE_HOURS}h"
        return False
    return True


def post_entry(poster: InstagramPoster, entry) -> dict:
    tipo = entry.get("tipo", "ESTATICO")
    legenda = entry.get("legenda", "")
    arquivos = entry["arquivos"]
    urls = [build_public_url(f) for f in arquivos]

    log(f"Publicando {entry['post_id']} ({tipo}) — {len(urls)} arquivo(s)")

    if tipo == "REEL":
        # Primeiro arquivo = video
        return poster.post_reel(urls[0], caption=legenda)
    elif tipo == "CARROSSEL":
        return poster.post_carousel(urls, caption=legenda)
    elif tipo == "ESTATICO":
        return poster.post_single_image(urls[0], caption=legenda)
    else:
        raise IGError(f"Tipo de post desconhecido: {tipo}")


def main():
    user_id = os.environ.get("IG_USER_ID")
    token = os.environ.get("IG_ACCESS_TOKEN")
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"

    now = datetime.now(TZ_BR)
    log(f"Tick — now={now.isoformat()}")

    if not is_safe_hour(now):
        log(f"Fora do horario seguro ({SAFE_START_HOUR}h-{SAFE_END_HOUR}h). Pulando.")
        return 0

    schedule = load_schedule()
    pending = [e for e in schedule if should_post(e, now)]

    if not pending:
        log("Nenhum post pendente no momento.")
        save_schedule(schedule)  # salva caso tenha marcado PULADO_ATRASO
        return 0

    log(f"{len(pending)} post(s) para publicar")

    if dry_run:
        log("DRY_RUN ativo — nao publicando de verdade")
        for e in pending:
            log(f"  -> iria publicar {e['post_id']} ({e['tipo']})")
        return 0

    if not user_id or not token:
        log("ERRO: IG_USER_ID ou IG_ACCESS_TOKEN nao definidos nos Secrets")
        return 2

    poster = InstagramPoster(user_id, token)
    any_error = False

    for entry in pending:
        entry["ultima_tentativa"] = now.isoformat()
        try:
            result = post_entry(poster, entry)
            entry["status"] = "POSTADO"
            entry["postado_em"] = datetime.now(TZ_BR).isoformat()
            entry["url_post"] = result.get("permalink") or f"ig://media/{result.get('id')}"
            entry["media_id"] = result.get("id")
            entry["erro"] = None
            log(f"  OK {entry['post_id']} -> {entry['url_post']}")
        except Exception as e:
            entry["status"] = "FALHOU"
            entry["erro"] = str(e)[:500]
            any_error = True
            log(f"  FALHA {entry['post_id']}: {e}")

    save_schedule(schedule)
    return 1 if any_error else 0


if __name__ == "__main__":
    sys.exit(main())
