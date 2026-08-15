# Au Gratin — automação de postagem

Publica automaticamente no Facebook e Instagram da Au Gratin, direto de mídia já tratada no Google Drive — usando o mesmo modelo de **cronograma curado com aprovação** do Bernardino/GM Hamburgueria: nada é escolhido "às cegas" na hora de postar.

## Fluxo

1. `scripts/generate_week_plan.py` monta o cronograma da semana (1 story/dia + 1 post semanal de sexta, que é OU um reel OU um carrossel — nunca os dois na mesma semana) e salva em `content/week_plans/<segunda-feira>.json` com `status: "pending_approval"`.
2. O cronograma aparece no painel (`painel_publicacoes.html`, aba Au Gratin) pra Rob revisar.
3. Depois de aprovado (`scripts/approve_week_plan.py content/week_plans/<data>.json`, ou pelo painel), o `status` vira `"approved"`.
4. Só então o `poller.py` (rodando via GitHub Actions) publica os posts do plano aprovado, nos horários da semana.

## Cronograma

- **Story**: segunda a sexta, 12h00 (buffet fechado no fim de semana) — 1 item (foto ou vídeo) de `Stories Iasmim`.
- **Post semanal**: sexta-feira, 11h00 — OU um carrossel de 5 fotos (`Fotos - Tratadas/2026/*`) OU um reel (`Vídeos tratados/*`), decidido no momento de gerar o cronograma da semana.

Ajuste dias/horários em `SCHEDULE` no topo de `scripts/poller.py`.

## Pools de conteúdo

- `content/augratin_stories_manifest.json` — 94 itens (fotos + vídeos), de `Stories Iasmim` (pasta plana, sem subpastas).
- `content/augratin_reels_manifest.json` — 21 vídeos, de 4 subpastas mensais (Fevereiro/Março/Maio/Junho 26). Pastas `usados`/`Usados` dentro de cada mês foram excluídas (já usado/arquivado).
- `content/augratin_feed_manifest.json` — 72 fotos (.heic, convertidas pra .jpg antes de postar), de Junho 26 (completo) e uma fatia recente de Maio 26.

Cada item tem `used`/`used_at` — quando o pool esgota, reseta sozinho e recomeça a rotação.

## Legendas

`scripts/make_caption.py` tem um conjunto pequeno de templates estáticos no tom informal/brincalhão característico do segmento, sem nenhum uso de travessão (—) — regra explícita do Rob, usar vírgulas ou frases separadas no lugar. O `FOOTER` com endereço/horário/delivery é um **placeholder** — não havia nenhuma informação de horário/delivery documentada na pasta do Drive da Au Gratin no momento da criação deste repositório; Rob precisa editar `FOOTER` em `scripts/make_caption.py` com o texto real antes do primeiro post ir ao ar.

A legenda é decidida uma única vez, na hora de gerar o cronograma (`generate_week_plan.py`), e gravada no próprio plano (`caption_text`) — nunca re-sorteada na hora de postar, pra garantir que o que o Rob aprovar seja exatamente o que sai.

## Segurança contra post duplicado

Aplicado desde o primeiro commit (aprendido com um incidente real no Bernardino):
- **Concurrency group** serializa execuções sobrepostas.
- **Trava de segurança**: se uma execução falhar parcialmente no meio de uma publicação, o slot é marcado como publicado mesmo assim (evita re-tentativa automática que duplicaria o que já saiu) e abre uma Issue urgente pedindo conferência manual. Nenhuma nova execução roda enquanto essa Issue estiver aberta.

## Configuração necessária

No GitHub (`Settings > Secrets and variables > Actions` deste repositório), adicionar:
- `RCLONE_CONFIG` — mesmo formato usado no Bernardino/TopTop/GM (acesso ao Google Drive).
- `FB_PAGE_ACCESS_TOKEN`
- `FB_PAGE_ID`
- `IG_BUSINESS_ID`

Nunca cole esses valores em uma conversa de chat — configure direto pelo GitHub (`gh secret set NOME --repo virandopaulista-droid/augratin-automacao`, digitado no seu terminal).

## Testar

Gerar um cronograma de teste e aprovar:

```
py -3 scripts/generate_week_plan.py
py -3 scripts/approve_week_plan.py content/week_plans/<data-da-segunda>.json
```

Rodar o poller em modo simulação (não publica de verdade, só valida o mount do Drive e a leitura do plano aprovado):

```
gh workflow run poller.yml --repo virandopaulista-droid/augratin-automacao -f live=false
```
