# Auto-Clicker Web Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CLI em Python que abre um site, checa a cada N segundos se um botão está visível e habilitado, clica nele, confirma o sucesso e notifica.

**Architecture:** `main.py` orquestra o loop; `browser.py` encapsula o ciclo de vida do Chromium (headless, bloqueio de recursos, reinício); `checker.py` faz as operações na página (localizar, ler, clicar, confirmar). `config.py` valida o `config.json` e `notifier.py` isola o aviso de sucesso. Falhas de rede são capturadas no loop com backoff crescente.

**Tech Stack:** Python 3.11+, `playwright` (Chromium), `logging` da stdlib, `pytest` (só desenvolvimento).

**Spec:** `spec.md`

## Global Constraints

- Python 3.11+, Windows 10/11, PC com 2 GB de RAM e CPU dual-core.
- Única dependência de runtime: `playwright` (`pytest` só em dev).
- Chromium sempre headless, uma aba, um contexto.
- Bloquear `image`, `font`, `media` via `page.route` (lista vem de `block_resources`).
- Args do Chromium: `--disable-gpu`, `--disable-extensions`, `--no-sandbox`, `--disable-dev-shm-usage`.
- `interval_seconds` mínimo de 5.
- Reiniciar o navegador a cada `restart_browser_every` checagens (padrão 200).
- Meta: menos de 300 MB de RAM; falha de rede/timeout nunca derruba o processo.
- Log com `logging` em `logs/` com rotação (`RotatingFileHandler`).
- `after_click`: `stop` ou `continue`. Localização por `css`, `text` ou `role`.
- Fora de escopo: CAPTCHA, login automático, múltiplos sites em paralelo.
- Estrutura do spec (`main.py`, `browser.py`, `checker.py`, `config.json`, `requirements.txt`, `logs/`) acrescida de `config.py`, `notifier.py` e `tests/`.
- Sem commits automáticos: deixe tudo na working tree para revisão (regra do usuário). Onde um passo diria "commit", apenas confirme que os arquivos estão salvos.

## Review Focus

- `config.json` ausente, JSON inválido ou campo faltando: sair com mensagem clara, não com traceback.
- `interval_seconds` abaixo de 5, zero ou negativo: rejeitar na validação.
- Botão visível mas desabilitado: tratar como indisponível, sem clicar.
- Seletor de `read_selectors` que não existe na página: logar `N/A` e seguir, sem exceção.
- Clique que falha (elemento some entre a checagem e o clique, timeout): voltar ao loop sem encerrar.
- Ctrl+C: fechar o navegador e sair com código 0.

---

### Task 1: Setup e validação de configuração

**Files:**
- Create: `requirements.txt`, `requirements-dev.txt`, `config.json`, `config.py`, `tests/test_config.py`, `.gitignore` (inclui `logs/`, `__pycache__/`)

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) Locator: by: Literal["css","text","role"]; value: str`
  - `@dataclass(frozen=True) Config: url: str; button: Locator; read_selectors: dict[str, str]; success_check: Locator | None; interval_seconds: float; after_click: Literal["stop","continue"]; block_resources: tuple[str, ...]; restart_browser_every: int; headless: bool`
  - `class ConfigError(Exception)`
  - `load_config(path: str | Path) -> Config`

- [ ] **Step 1: Escrever os testes que falham** em `tests/test_config.py` (usando `tmp_path`):
  - `test_loads_spec_example`: o JSON do spec §5 carrega e `cfg.button == Locator("text","Comprar")`, `cfg.interval_seconds == 10`.
  - `test_missing_file_raises_config_error`
  - `test_invalid_json_raises_config_error`
  - `test_missing_url_raises_config_error`
  - `test_interval_below_5_raises_config_error` (valores 4.9, 0, -1)
  - `test_invalid_after_click_raises_config_error` (`"pause"`)
  - `test_invalid_locator_kind_raises_config_error` (`by: "xpath"`)
  - `test_defaults`: sem `block_resources`, `restart_browser_every`, `headless`, `after_click`, `success_check` → `("image","font","media")`, `200`, `True`, `"stop"`, `None`.
- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL (`ModuleNotFoundError: config`)

- [ ] **Step 3: Implementar `config.py`** conforme as Interfaces; toda falha de leitura/validação vira `ConfigError` com mensagem em português. `headless` sempre `True` por padrão; valor `False` é aceito só para depuração. Criar `config.json` com o exemplo do spec §5, `requirements.txt` (`playwright`) e `requirements-dev.txt` (`-r requirements.txt`, `pytest`).
- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS (8 testes)

### Task 2: Operações de página (`checker.py`)

**Files:**
- Create: `checker.py`, `tests/test_checker.py`, `tests/conftest.py`

**Interfaces:**
- Consumes: `Locator` de `config.py`.
- Produces:
  - `locate(page: Page, loc: Locator) -> playwright.sync_api.Locator` (`css`→`page.locator`, `text`→`page.get_by_text(exact=False)`, `role`→`page.get_by_role` com `value` no formato `"button:Comprar"`, ou só `"button"`; `.first` nos três casos)
  - `read_fields(page: Page, selectors: dict[str, str]) -> dict[str, str]` (ausente → `"N/A"`)
  - `is_button_available(page: Page, loc: Locator) -> bool` (existe, visível e habilitado; nunca lança)
  - `click_button(page: Page, loc: Locator, timeout_ms: int = 5000) -> bool` (`False` em falha)
  - `confirm_success(page: Page, check: Locator | None, old_url: str, button: Locator) -> bool`: `True` se `check` aparece, ou a URL mudou, ou o botão sumiu (RF5); com `check=None` vale URL mudada ou botão sumido.

- [ ] **Step 1: Escrever os testes que falham.** `conftest.py` fornece a fixture `page` (sessão: um Chromium headless; função: página nova). Usar `page.set_content(html)` com HTML inline:
  - `test_available_when_visible_and_enabled`
  - `test_unavailable_when_disabled` (`<button disabled>`)
  - `test_unavailable_when_hidden` (`style="display:none"`)
  - `test_unavailable_when_absent`
  - `test_locate_by_text_css_and_role` (os três acham o mesmo botão)
  - `test_read_fields_returns_text_and_na_for_missing` (`{"status": ".status", "x": ".nao-existe"}` → `{"status": "Em estoque", "x": "N/A"}`)
  - `test_click_button_triggers_handler` (onclick altera o DOM; asserção no DOM)
  - `test_click_button_returns_false_when_missing`
  - `test_confirm_success_by_text`, `test_confirm_success_by_button_gone`, `test_confirm_success_false_when_nothing_changed`
- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_checker.py -v`
Expected: FAIL (`ModuleNotFoundError: checker`)

- [ ] **Step 3: Implementar `checker.py`.** Capturar `playwright.sync_api.Error` e `TimeoutError` em `is_button_available`, `click_button` e `read_fields` para que nunca se propaguem como erro de lógica. Erros de rede de `page.goto` ficam com `browser.py`/`main.py`.
- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_checker.py -v`
Expected: PASS (11 testes). Pré-requisito: `playwright install chromium`.

### Task 3: Ciclo de vida do navegador (`browser.py`)

**Files:**
- Create: `browser.py`, `tests/test_browser.py`

**Interfaces:**
- Consumes: `Config` de `config.py`.
- Produces: `class BrowserSession` com
  - `__init__(self, cfg: Config)`
  - `start(self) -> Page` (lança Chromium com os args do Global Constraints, 1 contexto, 1 aba, registra a rota de bloqueio)
  - `goto(self) -> None` (`page.goto(cfg.url, wait_until="domcontentloaded", timeout=30000)`)
  - `reload(self) -> None` (`page.reload(wait_until="domcontentloaded", timeout=30000)`)
  - `restart(self) -> Page` (`close` + `start` + `goto`)
  - `close(self) -> None` (idempotente)
  - `page` (propriedade)
  - função pura `should_block(resource_type: str, blocked: tuple[str, ...]) -> bool`

- [ ] **Step 1: Escrever os testes que falham**
  - `test_should_block_matches_only_listed_types` (puro, `image`/`font`/`media` → `True`; `document`/`script` → `False`)
  - `test_start_opens_single_page_in_single_context`
  - `test_images_are_blocked`: servir HTML local com `<img>` via `http.server` em thread e checar via `page.on("requestfailed")` que a imagem falhou.
  - `test_restart_returns_working_page`
  - `test_close_is_idempotent`
- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_browser.py -v`
Expected: FAIL (`ModuleNotFoundError: browser`)

- [ ] **Step 3: Implementar `browser.py`.** A rota `**/*` chama `route.abort()` se `should_block(route.request.resource_type, ...)`, senão `route.continue_()`.
- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_browser.py -v`
Expected: PASS (5 testes)

### Task 4: Notificação de sucesso (`notifier.py`)

**Files:**
- Create: `notifier.py`, `tests/test_notifier.py`

**Interfaces:**
- Produces: `notify_success(message: str, beep=winsound.Beep) -> None` (loga `INFO` com `message` e toca o som; falha de som é logada em `WARNING`, nunca propagada; em plataforma sem `winsound`, só loga)

- [ ] **Step 1: Escrever os testes que falham**
  - `test_logs_message` (usar `caplog`)
  - `test_calls_beep` (passando `beep` falso)
  - `test_beep_failure_does_not_raise` (beep lança `RuntimeError`)
- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_notifier.py -v`
Expected: FAIL

- [ ] **Step 3: Implementar `notifier.py`.** Import de `winsound` dentro de `try/except ImportError`. Telegram/e-mail ficam fora (opcional no spec; YAGNI).
- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_notifier.py -v`
Expected: PASS (3 testes)

### Task 5: Loop principal e logging (`main.py`)

**Files:**
- Create: `main.py`, `tests/test_main.py`

**Interfaces:**
- Consumes: `load_config`, `ConfigError`, `BrowserSession`, funções de `checker`, `notify_success`.
- Produces:
  - `setup_logging(log_dir: Path = Path("logs")) -> None` (`RotatingFileHandler` em `logs/auto-clicker.log`, 1 MB × 3 backups, mais console)
  - `next_backoff(current: float, base: float = 5, cap: float = 300) -> float` (dobra até o teto; `current=0` → `base`)
  - `run_cycle(session: BrowserSession, cfg: Config) -> Literal["clicked","unavailable"]`: lê campos e loga, checa o botão, clica, confirma, notifica.
  - `main(argv: list[str] | None = None) -> int` (argumento opcional `--config`; padrão `config.json`)

- [ ] **Step 1: Escrever os testes que falham**
  - `test_next_backoff_doubles_and_caps` (`0→5→10→20 … →300→300`)
  - `test_main_returns_2_on_config_error` (arquivo inexistente; saída sem traceback)
  - `test_run_cycle_unavailable_when_button_disabled` (usa `BrowserSession` real e HTML servido localmente)
  - `test_run_cycle_clicks_and_confirms` (botão habilitado; clique muda o DOM para "Pedido confirmado" → `"clicked"`)
  - `test_loop_stops_after_click_when_after_click_stop` e `test_loop_continues_when_after_click_continue`: extrair o laço em `monitor(session, cfg, sleep=time.sleep, max_cycles: int | None = None)` para injetar `sleep` falso e limitar ciclos.
  - `test_loop_survives_network_error_and_backs_off`: `session.reload` falso lança `playwright.sync_api.Error` nas 2 primeiras vezes; asserção: nenhuma exceção sai e os `sleep` recebem `5, 10`.
  - `test_browser_restarts_every_n_cycles` (`restart_browser_every=3`, 7 ciclos → `restart` chamado 2×)
  - `test_keyboard_interrupt_closes_browser_and_returns_0`
- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_main.py -v`
Expected: FAIL

- [ ] **Step 3: Implementar `main.py`.** Ordem do ciclo conforme spec §6: ler campos → logar → botão disponível? sim: clicar, confirmar, notificar, e `stop` encerra / `continue` segue; não: `sleep(interval_seconds)` → `reload`. Erros de rede (`playwright.sync_api.Error`, `TimeoutError`) no `goto`/`reload` ativam `next_backoff` e reiniciam o contador ao primeiro ciclo bem-sucedido. Se o clique falhar, logar `WARNING` e seguir como indisponível. `restart_browser_every` conta checagens. `finally` sempre chama `session.close()`. Códigos de saída: 0 normal/Ctrl+C, 2 erro de configuração.
- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_main.py -v`
Expected: PASS

### Task 6: Verificação de aceite

**Files:**
- Create: `scripts/fake_site.py` (servidor local de apoio; fica fora do pacote do bot)

- [ ] **Step 1:** Implementar `scripts/fake_site.py`: `http.server` que serve uma página com `<div class="status">` e botão "Comprar" desabilitado, que passa a habilitado após `--after N` segundos; clicar leva a "Pedido confirmado".
- [ ] **Step 2:** Rodar suíte completa.

Run: `python -m pytest -v`
Expected: todos os testes passam.

- [ ] **Step 3:** Teste ponta a ponta. Em um terminal `python scripts/fake_site.py --after 30`; em outro, `python main.py` com `config.json` apontando para `http://localhost:8000`. Esperado: logs de checagem a cada `interval_seconds`, clique em até `interval_seconds` após os 30 s, mensagem de sucesso, som e encerramento (`after_click: stop`).
- [ ] **Step 4:** Queda de rede. Com o fake site rodando, parar o servidor por ~1 min e subir de novo. Esperado: logs de erro com backoff crescente, sem encerrar, retomada automática.
- [ ] **Step 5:** Memória. Com `--after 3600`, observar `chrome.exe`/`python.exe` no Gerenciador de Tarefas durante 10+ minutos (e passando por um reinício do navegador, usando `restart_browser_every: 5` temporariamente). Esperado: total abaixo de 300 MB.
- [ ] **Step 6:** Rodar 1 h sem erro com botão indisponível (critério do spec §9) e registrar o resultado.

---

## Self-Review

- **Cobertura:** RF1 (T3 `goto`), RF2 (T2 `is_button_available`/`locate`), RF3 (T2 `read_fields` + T5 log), RF4/RF5 (T2 + T5), RF6 (T5), RF7 (T1 + T5), RF8 (T4). RNFs: headless/bloqueio/args (T3), intervalo mínimo (T1), reinício (T5), retry crescente (T5). Aceite coberto na T6.
- **Desvio do spec:** arquivos extras `config.py` e `notifier.py` para permitir teste isolado; Telegram/e-mail ficam de fora por serem opcionais.
- **Consistência de tipos:** `Locator` e `Config` definidos na T1 e usados com os mesmos nomes nas T2–T5.
