# Caffédelli — Agendador automático de Instagram

Sistema que publica automaticamente os posts do planejamento editorial da **@caffedelli** no Instagram, nos dias e horários corretos, via GitHub Actions + Instagram Graph API.

## 📊 Conteúdo atual
- **42 posts agendados** cobrindo 22/04/2026 → 18/07/2026
- **1 Reel**, **11 estáticos**, **30 carrosséis**
- Frequência: ter/qui/sáb (3×/semana) + posts extras em datas comemorativas (São João, Meio Ambiente, Namorados)
- Todo o conteúdo em `posts/` otimizado para Instagram (1080px, JPEG 87%)

## 🏗 Como funciona

```
GitHub Actions (cron */15 min)
    └─► python scripts/post_to_instagram.py
            ├─► Lê schedule.json
            ├─► Filtra posts com status=PRONTO_PARA_POSTAR e data_agendada <= agora
            ├─► Publica via IG Graph API
            │       ├─► Estático  → create container + publish
            │       ├─► Carrossel → N children + parent + publish
            │       └─► Reel     → video upload + wait + publish
            └─► Atualiza status=POSTADO + commit auto
```

**Horário seguro:** só publica entre 07h e 23h (Brasília). Evita posts em horários ruins se der bug de timezone.

**Janela de tolerância:** 1h. Se o Actions falhar por mais de 1h após o horário agendado, o post é marcado `PULADO_ATRASO` — não vai atrás retroativamente.

## 🔑 Secrets (configurar no GitHub)

Vá em **Settings → Secrets and variables → Actions → New repository secret** e adicione:

| Secret | Valor |
|---|---|
| `IG_USER_ID` | ID numérico da conta Business do Instagram (ex: `17841400000000000`) |
| `IG_ACCESS_TOKEN` | Token long-lived do Instagram Graph API (60 dias) |

### Como obter esses valores

**Pré-requisitos:**
1. Conta @caffedelli precisa ser **Business** ou **Creator** (não Pessoal)
2. Conectada a uma **Página do Facebook**
3. Criar um **App no Meta for Developers** (developers.facebook.com)

**Passo a passo:**

1. Acessa [developers.facebook.com/apps](https://developers.facebook.com/apps/) e cria um novo app tipo "Business"
2. No app, adiciona produto **"Instagram Graph API"**
3. Em **Tools → Graph API Explorer**:
   - Seleciona tua app
   - Adiciona permissões: `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`
   - Gera token de usuário
4. Em **Graph API Explorer**, faz GET `me/accounts` → copia o `access_token` da Página do Facebook
5. Com esse token, faz GET `{page-id}?fields=instagram_business_account` → pega o **IG_USER_ID**
6. Para token long-lived (60 dias), roda:
   ```
   https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id={APP_ID}&client_secret={APP_SECRET}&fb_exchange_token={SHORT_LIVED_TOKEN}
   ```

**⏰ ATENÇÃO:** O `IG_ACCESS_TOKEN` expira em 60 dias. Coloque um lembrete no calendário para renovar.

## 🧪 Testar manualmente

Na aba **Actions → Caffedelli Auto-Poster → Run workflow**, escolha `dry_run: true` para simular sem publicar.

Para testar local:
```bash
pip install -r requirements.txt
DRY_RUN=true python scripts/post_to_instagram.py
```

## 📅 Ver agendamento atual

Abra [schedule.json](schedule.json). Cada entrada tem:

```json
{
  "post_id": "CAFFEDELLI_DIA_01",
  "data_agendada": "2026-04-22T18:00:00-03:00",
  "tipo": "REEL",
  "status": "PRONTO_PARA_POSTAR",
  "arquivos": ["posts/DIA_01_REEL_MANIFESTO/dia01_reel_final.mp4"],
  "legenda": "...",
  "localizacao": "Muzambinho, MG",
  "postado_em": null,
  "url_post": null
}
```

Após cada postagem o `schedule.json` é commitado automaticamente com os campos `postado_em`, `url_post` e `media_id` preenchidos.

## 🚨 Status possíveis

| Status | Significado |
|---|---|
| `PRONTO_PARA_POSTAR` | Ainda não postou |
| `POSTADO` | Publicou com sucesso |
| `FALHOU` | Tentou mas deu erro (retry automático na próxima rodada) |
| `PULADO_ATRASO` | Horário passou há mais de 1h — não publica mais |

## 📂 Estrutura do projeto

```
.
├── .github/workflows/poster.yml   # cron do GitHub Actions
├── scripts/
│   ├── post_to_instagram.py       # main runner
│   ├── ig_api.py                  # wrapper Instagram Graph API
│   └── dry_run.py                 # teste local
├── posts/
│   ├── DIA_01_REEL_MANIFESTO/
│   ├── DIA_02_CARROSSEL_90PORCENTO/
│   └── ... (42 pastas)
├── schedule.json                  # fonte da verdade de tudo
├── requirements.txt
└── README.md
```
