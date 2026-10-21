# Bounty Ops — skill pack para agentes que ganham dinheiro com bounty

Três skills que transformam "achei um bounty na internet" em "dinheiro
verificado no ledger", com as decisões ruins bloqueadas antes de custarem
tempo.

Formato aberto `agentskills.io` — instalável em Hermes, Claude Code, Codex,
Cursor, OpenClaw e qualquer runtime compatível.

---

## O problema que este pack resolve

Agentes de bounty falham de formas previsíveis, e quase sempre por erro de
processo, não por falta de capability:

1. **Trabalham bounty sem Expected Value.** Uma bounty de US$42 disputada por
   4 solvers rende US$8 — menos que uma hora de qualquer outra coisa. O
   agente só descobre isso depois de gastar duas horas.
2. **Descobrem o "no test suite means no payout" tarde demais.** A plataforma
   exige um teste de regressão novo. Repo sem suíte de testes = payout
   impossível, não importa quão bom é o fix.
3. **Perdem tentativas em erro de plumbing.** Branch que colide com
   diretório, push que pendura em prompt invisível, `gh pr create` que abre PR
   do branch errado. Cada um custa a tentativa inteira.
4. **Reportam valor postado como se fosse receita.** Bounty submetida não
   pagou nada. Confundir os dois números é como pipeline de agente vira
   ficção — e é exatamente o que impede o dono de decidir se vale continuar
   investindo.

Este pack attacka os quatro, em ordem: qualifica antes de agir, executa sem
erro de plumbing, e reporta a verdade.

---

## As skills

### `bounty-qualifier` — decide o que vale a pena

Transforma uma feed de bounties numa shortlist com a aritmética à mostra.

```
EV = (net_reward × win_probability) − effort_cost
win_probability ≈ 1 / (1 + competitors)
```

Filtros configuráveis: reward mínimo, EV mínimo, teto de esforço, piso de
valor/hora, e o filtro que mais importa — **repositório sem suíte de testes é
descartado**, porque não dá para provar o fix.

O que ele ensina e o script não pode esconder:
- **Bounty contestada é corrida, não fila.** "First passing submission wins"
  significa que ser segundo vale zero. Velocidade vence qualidade no payout;
  qualidade protege o win rate. São coisas diferentes.
- **Normalmente você tem uma tentativa.** Retry só depois de *verdict de
  verificação falho*, e só uma vez. Sua primeira tentativa descuidada queima o
  retry.
- **Registro ≠ elegibilidade.** Endereço de payout salvo não é transferência.
  Um board honesto ainda pode ser um péssimo investimento se a rota de saque
  não está confirmada.
- **Largura vs profundidade.** Breadth (muitos bounties baratos) escala linear
  e só funciona se submissão for barata. Depth (poucos, caros) tem EV alto
  mas depende de ganhar contests. A maioria deve começar em breadth para
  construir win rate.

### `bounty-solver` — executa sem perder tentativa

O workflow completo, do detalhe do bounty ao claim, com as armadilhas que só
aparecem na prática:

- A rota de **patch** (`POST /submissions/patch`) é preferível à de PR —
  elimina toda a superfície de falha de fork/branch/push.
- Se a plataforma exige PR: branch que colide com diretório é **rejeitado no
  push** ("directory file conflict"). `gh pr create` contra repo upstream
  precisa de `--repo` e `--head` explícitos. `gh repo create` não faz push.
  `git push` pendura em prompt invisível se o credential helper não estiver
  ligado ao CLI.
- **O teste de regressão é obrigatório e tem que falhar antes do fix.**
- **A suíte existente tem que continuar passando.** PR que quebra CI vale zero.
- Read the rubric antes: se não é satisfazível por mudança de código, pule.
- Nunca submeter duas vezes com descuido — a retry é seu único seguro.

### `revenue-ledger` — reportar a verdade

Quatro números, e só um é receita:

| Número | O que é | É receita? |
|---|---|---|
| Posted value | soma de tudo que você tentou | Não |
| Expected value | estimativa ponderada | Não |
| Pending | submetido, não verificado | Não |
| **Realized** | **concedido e pago** | **Sim** |

Regras contábeis: só `awarded` conta; a taxa da plataforma é descontada; uma
entrada por bounty (retry atualiza, não duplica); perdas nunca são deletadas;
o total é sempre derivado das entradas, nunca digitado.

O relatório sai com win rate sobre **decididas** (não sobre tentativas —
tentativa em voo não é derrota), receita por tentativa e por vitória.

---

## Instalação

**Hermes (ou qualquer runtime compatível com agentskills.io):**

```bash
# a partir do repositório
hermes skills tap add <owner>/bounty-ops
hermes skills install bounty-ops/bounty-qualifier
hermes skills install bounty-ops/bounty-solver
hermes skills install bounty-ops/revenue-ledger
```

**Claude Code / Codex / Cursor / Aider:**

```bash
npx skills add <owner>/bounty-ops
```

**Sem instalação, do zero:** copie `skills/<nome>/` para o diretório de
skills do seu runtime. Cada skill é um `SKILL.md` + scripts, sem dependências
externas — só Python 3 stdlib.

---

## Requisitos

- Python 3.8+ (stdlib apenas — nada para instalar)
- Para o `bounty-solver`: `gh` autenticado, e um cliente GitHub com escopo
  `repo`. A conta que abre o PR tem que ser a mesma logada na plataforma de
  bounty, senão o payout não sai.
- Nenhuma skill submete trabalho, gasta dinheiro ou toca conta sem
  aprovação explícita.

---

## Testes

```bash
python test_pack.py
```

44 testes cobrindo: normalização de feeds com nomes de campo diferentes, a
aritmética de EV, cada gate de desqualificação, e a contabilidade do ledger
(payout de 80%, retry sem duplicar, total recalculado, escrita atômica).

---

## Licença

MIT. Os scripts podem ser usados livremente.

---

## Preço

**Grátis** para uso pessoal e para instalar nas suas próprias máquinas.
**US$29** para uso comercial (consultoria, operação de agentes para
clientes, produto embutido) — inclui direito de redistribuir dentro da sua
operação e atualizações por 12 meses.

**Compre agora:** https://buy.stripe.com/fZucMXgKEaPf6V5bx9efC01

Checkout Stripe (US$29, compra única, cartão ou Pix). Após o pagamento, envie
o e-mail usado na compra e eu envio o acesso ao pack + atualizações por
12 meses. Repositorio publico, entao a versao gratuita continua disponivel
para uso pessoal — o que voce compra e a licenca comercial e o suporte.

Servico de operacao de agentes (R$ 490/mes):
https://buy.stripe.com/9B6cMXeCw5uV6V50SvefC02

---

## Por que este pack existe

Toda a orientação aqui veio de rodar o pipeline de verdade numa máquina real:
fork → branch → commit → push → PR → close, com três bugs que só apareceram
no caminho. As armadilhas estão documentadas porque alguém já pagau por elas.
