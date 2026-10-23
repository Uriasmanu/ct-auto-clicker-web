# Auto-Clicker Web: bot que abre um site e clica em botão quando disponível

**Linguagem:** Python 3.11+
**Tipo:** script de linha de comando (CLI), sem interface gráfica
**Plataforma alvo:** Windows 10/11 em PC fraco (2 GB de RAM, CPU dual-core)

## 1. Objetivo

Abrir um site, ler o conteúdo da página em intervalos regulares e clicar em um botão assim que ele estiver disponível (visível e habilitado). Depois do clique, registrar o resultado e encerrar ou continuar, conforme a configuração.

## 2. Stack

| Item | Escolha | Motivo |
|---|---|---|
| Linguagem | Python | Simples, leve, pouca configuração |
| Automação | Playwright (Chromium headless) | Lê o DOM já renderizado, tem espera embutida e é mais leve que Selenium |
| Configuração | `config.json` | Troca de site ou botão sem mexer no código |
| Log | `logging` da stdlib, em arquivo com rotação | Sem dependências extras |

Dependência externa única: `playwright`.

## 3. Requisitos funcionais

1. **RF1.** Carregar a URL configurada.
2. **RF2.** Verificar a cada N segundos se o botão existe, está visível e está habilitado. A localização é por seletor CSS, texto ou role.
3. **RF3.** Ler o texto de elementos indicados na configuração (ex.: status, estoque, preço) e registrar no log a cada checagem.
4. **RF4.** Se o botão estiver disponível, clicar nele.
5. **RF5.** Confirmar o sucesso do clique. Pode ser a mudança de URL, o aparecimento de um texto esperado ou o botão sumir.
6. **RF6.** Se o botão não estiver disponível, recarregar a página e tentar de novo.
7. **RF7.** Opções após o clique: `stop` (encerra) ou `continue` (segue monitorando).
8. **RF8.** Notificar em caso de sucesso (som local e mensagem no log). Notificação por Telegram ou e-mail é opcional.

## 4. Requisitos não funcionais (PC fraco)

- Navegador sempre em **headless**, com uma única aba e um único contexto.
- Bloquear carregamento de **imagens, fontes e mídia** via interceptação de rotas. Isso reduz RAM, CPU e banda.
- Intervalo mínimo de 5 s entre checagens, para não sobrecarregar a máquina nem o site.
- Argumentos do Chromium para reduzir consumo: `--disable-gpu`, `--disable-extensions`, `--no-sandbox`, `--disable-dev-shm-usage`.
- Meta de consumo: **menos de 300 MB de RAM** e CPU ociosa fora das checagens.
- Reiniciar o navegador a cada X checagens (ex.: 200) para evitar vazamento de memória.
- Tratar falhas de rede e timeouts sem derrubar o processo (retry com espera crescente).

## 5. Configuração (`config.json`)

```json
{
  "url": "https://exemplo.com/produto",
  "button": { "by": "text", "value": "Comprar" },
  "read_selectors": { "status": ".status", "preco": ".price" },
  "success_check": { "by": "text", "value": "Pedido confirmado" },
  "interval_seconds": 10,
  "after_click": "stop",
  "block_resources": ["image", "font", "media"],
  "restart_browser_every": 200,
  "headless": true
}
```

## 6. Fluxo

```
iniciar → abrir navegador → carregar URL
   ↓
loop:
   ler campos de read_selectors → logar
   botão visível e habilitado?
      sim → clicar → validar sucesso → notificar → (stop | continue)
      não → aguardar interval_seconds → recarregar página
```

## 7. Estrutura de arquivos

```
auto-clicker/
├── main.py          # ponto de entrada e loop principal
├── browser.py       # abre o navegador, bloqueia recursos, reinicia
├── checker.py       # localiza o botão, lê campos, clica
├── config.json
├── requirements.txt
└── logs/
```

## 8. Instalação e execução

```
pip install playwright
playwright install chromium
python main.py
```

## 9. Critérios de aceite

- Com o botão indisponível, o bot checa, loga os campos lidos e recarrega sem erro por pelo menos 1 hora.
- Quando o botão fica disponível, o clique acontece em até `interval_seconds` segundos.
- O uso de RAM se mantém abaixo de 300 MB durante a execução.
- Queda de internet não encerra o processo: ele retoma sozinho.

## 10. Fora de escopo

- Resolver CAPTCHA ou burlar proteção anti-bot.
- Login automático em contas de terceiros.
- Rodar vários sites em paralelo (pode vir numa v2).

## 11. Riscos

- Alguns sites proíbem automação nos termos de uso. Verificar antes de usar.
- Mudança de layout quebra o seletor, então a configuração precisa ser fácil de ajustar.
- Sites com detecção de bot podem bloquear o acesso.
