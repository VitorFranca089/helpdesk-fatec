# TriaDesk

Help desk de TI da faculdade com triagem automática. O aluno descreve o problema, o **Laya** (um modelo de decisão que roda localmente) classifica o chamado e o sistema encaminha para a fila do setor certo, com uma prioridade calculada.

Trabalho acadêmico de ADS. O enunciado pede um sistema que use um modelo de decisão estilo **JEV (TypeSafe AI)**, com perguntas do tipo **Choice**, **Score** ou **Noul**. Usamos o [Laya](https://github.com/NandhaKishorM/laya), alternativa open source (Apache 2.0) que oferece os mesmos três tipos de pergunta.

## O problema

Os chamados de TI chegam todos pelo mesmo canal e misturados: Wi-Fi lento, senha esquecida, software faltando no laboratório, erro no portal na véspera de uma entrega. Alguém precisa ler cada um para decidir quem atende e o que é mais urgente. O TriaDesk faz essa primeira leitura sozinho e manda para revisão humana só os casos em que o modelo não tem certeza.

## Como funciona

Para cada chamado, o backend envia ao Laya o texto do aluno e três perguntas, respondidas numa única passada do modelo:

| Pergunta | Tipo | Resposta usada |
|---|---|---|
| Qual setor deve atender? | **Choice** (5 setores) | setor escolhido e a confiança nele |
| Qual a urgência para o aluno? | **Score** (baixa, média, alta) | nível esperado, de 0 a 2 |
| O aluno menciona prazo, entrega ou prova? | **Noul** (sim/não) | probabilidade de "sim", de 0 a 1 |

Com essas respostas, as regras de [backend/app/triagem.py](backend/app/triagem.py) decidem o destino:

1. **Encaminhamento:** a fila é o setor escolhido pelo Choice.
2. **Revisão humana:** se a confiança no setor for menor que `LIMIAR_CONFIANCA` (padrão 0,60), o chamado vai para a fila `revisao_humana`, onde uma pessoa escolhe o setor.
3. **Prioridade:** `pontos = round(urgência × 40 + P(prazo) × 20)`, de 0 a 100. Com 60 ou mais é **alta**, com 30 ou mais é **média**, abaixo disso é **baixa**.
4. **Ordem da fila:** mais pontos primeiro; no empate, o chamado mais antigo.

Setores: Rede / Wi-Fi, Sistema Acadêmico, Laboratório, Conta / Senha e Outros.

## Como rodar

Tudo roda em containers: só é preciso ter o Docker com o Compose. Nada do projeto é instalado na máquina.

```bash
docker compose up --build
```

| O quê | Endereço |
|---|---|
| Frontend | http://localhost:8700 |
| API | http://localhost:8701/api |
| Documentação da API (Swagger) | http://localhost:8701/docs |

A **primeira subida baixa o modelo** multilíngue do Laya do Hugging Face. Isso leva alguns minutos e precisa de internet só nessa vez: depois o modelo fica em cache no volume `modelos`. Enquanto ele carrega, `GET /api/health` responde 503 e o frontend só sobe quando o backend fica saudável, ou seja, com o Laya pronto.

### Comandos do dia a dia

| `make` (Linux ou WSL) | `docker compose` (qualquer sistema) | O que faz |
|---|---|---|
| `make up` | `docker compose up -d --build` | builda e sobe tudo em segundo plano |
| `make ps` | `docker compose ps` | mostra os containers e se estão saudáveis |
| `make logs` | `docker compose logs -f backend` | acompanha os logs do backend |
| `make test` | `docker compose run --rm --no-deps backend pytest` | roda os testes das regras de triagem |
| `make smoke` | `docker compose exec backend python scripts/smoke_test.py` | envia os 4 chamados de teste para a API no ar |
| `make eval` | `docker compose exec backend python scripts/avaliar_perguntas.py` | compara as variantes das perguntas nos chamados rotulados |
| `make shell` | `docker compose exec backend bash` | abre um terminal no backend |
| `make db` | `docker compose exec backend python -m sqlite3 /data/triadesk.db` | abre o shell do SQLite |
| `make reset-db` | (ver o `Makefile`) | apaga todos os chamados, sem derrubar os containers |
| `make stop` | `docker compose stop` | para os containers sem removê-los |
| `make down` | `docker compose down` | remove os containers; os volumes ficam |
| `make clean` | `docker compose down -v` | remove também os volumes: **apaga os chamados e o modelo baixado** |

O `Makefile` só funciona no **Linux ou no WSL**, porque precisa do GNU make e de um shell POSIX. No Windows fora do WSL, use os comandos `docker compose` da segunda coluna. `make` sozinho lista os alvos, e `reset-db` e `clean` pedem confirmação antes de apagar.

O código do backend entra no container por bind mount e o Uvicorn roda com `--reload`: ao salvar um arquivo, o backend reinicia sozinho e recarrega o modelo do cache em alguns segundos. O frontend é buildado e servido pelo nginx, então mudanças nele pedem `make up` para rebuildar.

### Portas

| Serviço | Porta no host | Porta no container |
|---|---|---|
| frontend (nginx) | **8700** | 80 |
| backend (FastAPI) | **8701** | 8000 |

As duas ficam presas ao `127.0.0.1`, então não aparecem para a rede local. Foram escolhidas para não colidir com outros projetos desta máquina, que já usam 8000, 5173, 3000, 5000, 5432, 5433, 6379 e 7700. Também ficam longe de portas comuns em desenvolvimento, como 8080, 8001, 4173 e 5555.

Para trocar, crie um `.env` a partir do `.env.example` e mude `FRONTEND_PORT` ou `BACKEND_PORT`, depois rode `make up`. O endereço da API no frontend (`VITE_API_URL`) e o CORS do backend acompanham a troca sozinhos.

### Containers e volumes

| Serviço | Imagem | Volumes |
|---|---|---|
| `backend` | `python:3.12-slim` + PyTorch 2.14.0 CPU-only | `./backend` (código), `dados` (SQLite em `/data`), `modelos` (cache do Hugging Face em `/models`) |
| `frontend` | build em `node:22-alpine`, servido por `nginx:1.28-alpine` | nenhum |

O PyTorch é instalado pelo índice da CPU antes do `laya`, para a imagem não puxar o CUDA. O SQLite é um arquivo, então não tem container próprio: ele fica no volume `dados` do backend.

## Arquitetura

- **Frontend:** React + Vite + TypeScript, com três telas (abrir chamado, fila de atendimento e detalhe), que conversa com a API por HTTP no endereço de `VITE_API_URL`.
- **Backend:** FastAPI recebe o chamado, consulta o Laya, aplica as regras de triagem e grava o resultado.
- **Modelo de decisão:** o Laya 0.4.0 (checkpoint `multilingual`) roda dentro do processo do backend, em CPU, com um único `Router` carregado no startup.
- **Banco:** SQLite em arquivo, guardado num volume para os dados sobreviverem aos restarts.

```
backend/
  app/
    main.py           FastAPI, lifespan (carrega o Laya em segundo plano), CORS, erros em português
    config.py         variáveis de ambiente
    database.py       engine, sessão e Base do SQLAlchemy
    models.py         tabela chamados
    schemas.py        entrada e saída da API (Pydantic)
    laya_service.py   Router do Laya e as três perguntas
    triagem.py        regras de negócio (funções puras)
    routers/chamados.py
  tests/test_triagem.py   regras testadas com respostas do Laya mockadas
  scripts/smoke_test.py   envia os 4 chamados de teste com o sistema no ar
frontend/
  src/
    api.ts            cliente da API
    App.tsx           rotas e status do modelo
    pages/            AbrirChamado, Fila, DetalheChamado
    components/       cards do resultado, gráfico de setores, JSON recolhível
```

## API

Todas as rotas têm o prefixo `/api`. A documentação interativa fica em `/docs`.

| Método | Rota | O que faz |
|---|---|---|
| GET | `/health` | situação da API e do modelo (503 enquanto o Laya carrega) |
| GET | `/setores` | setores com nome amigável e descrição |
| POST | `/chamados` | `{aluno?, descricao}`: consulta o Laya, aplica as regras, grava e devolve o chamado |
| GET | `/chamados` | fila ordenada; filtros opcionais `?fila=` e `?status=` |
| GET | `/chamados/{id}` | detalhe, com o que foi enviado ao Laya e a resposta bruta |
| PATCH | `/chamados/{id}` | muda o `status` ou a `fila` (para a revisão humana) |
| GET | `/estatisticas` | contagem por fila, prioridade e status, e o tempo médio do Laya |

Erros voltam em português: 422 para descrição inválida (de 10 a 2000 caracteres), 404 para chamado inexistente e 503 enquanto o modelo não carregou.

## Configuração

No `.env` (opcional, a partir do `.env.example`):

| Variável | Padrão | Para quê |
|---|---|---|
| `FRONTEND_PORT` | `8700` | porta do frontend no host |
| `BACKEND_PORT` | `8701` | porta da API no host |
| `LIMIAR_CONFIANCA` | `0.60` | abaixo disso, o chamado vai para revisão humana |
| `LAYA_THREADS` | `4` | limita as threads do PyTorch na CPU |

O `compose.yaml` monta o resto a partir delas:

| Variável | Valor no Compose | Para quê |
|---|---|---|
| `DATABASE_URL` | `sqlite:////data/triadesk.db` | arquivo do SQLite, dentro do volume `dados` |
| `HF_HOME` | `/models` | cache do modelo, dentro do volume `modelos` |
| `CORS_ORIGENS` | `http://localhost:8700,http://127.0.0.1:8700` | origens liberadas no CORS |
| `VITE_API_URL` | `http://localhost:8701` | raiz do backend (sem `/api`), gravada no JS no build do frontend |

## Testes

- `backend/tests/test_triagem.py` testa as quatro regras com respostas do Laya mockadas (prioridade alta, média e baixa, revisão humana, limiar e ordenação), sem carregar o modelo.
- `backend/scripts/smoke_test.py`, com o sistema no ar, envia os quatro chamados abaixo para `POST /api/chamados` e imprime setor, urgência, prioridade e tempo.
- `backend/scripts/avaliar_perguntas.py` compara variantes das perguntas sobre 48 chamados rotulados (veja [Ajuste das perguntas](#ajuste-das-perguntas)).

| # | Mensagem | Esperado |
|---|---|---|
| 1 | Não consigo enviar a atividade no portal do aluno, dá erro ao anexar o PDF e o prazo acaba hoje às 23h59. | Sistema Acadêmico, urgência alta, cita prazo |
| 2 | O Wi-Fi do bloco B fica lento à noite, dá pra usar mas demora pra carregar as páginas. | Rede / Wi-Fi, urgência baixa ou média |
| 3 | O computador 12 do laboratório 3 não tem o VS Code instalado e a aula prática é amanhã. | Laboratório, urgência média ou alta |
| 4 | Esqueci a senha do e-mail institucional e o link de recuperação não chega. | Conta / Senha |

### Resultados

Smoke test de 08/10/2026, com o Laya 0.4.0 (checkpoint `multilingual`) em CPU, `LAYA_THREADS=4` e limiar de 0,60. Rodou duas vezes: com as perguntas do início do projeto e com as perguntas ajustadas (veja [Ajuste das perguntas](#ajuste-das-perguntas)). Os números estão como o modelo respondeu, sem regra no código para corrigir caso nenhum.

| # | Esperado | Perguntas iniciais | Perguntas ajustadas (em uso) |
|---|---|---|---|
| 1 | Sistema Acadêmico, urgência alta, cita prazo | Sistema Acadêmico (85%), urgência 1,14, prazo 43%: **média, 54 pts** ✘ | Sistema Acadêmico (85%), urgência 1,47, prazo 74%: **alta, 74 pts** ✔ |
| 2 | Rede / Wi-Fi, urgência baixa ou média | Rede / Wi-Fi (98%), urgência 1,19, prazo 2%: média, 48 pts ✔ | Rede / Wi-Fi (98%), urgência 1,50, prazo 13%: **alta, 62 pts** ✘ |
| 3 | Laboratório, urgência média ou alta | Laboratório (100%), urgência 1,46, prazo 27%: alta, 64 pts ✔ | Laboratório (100%), urgência 1,77, prazo 87%: alta, 88 pts ✔ |
| 4 | Conta / Senha | Conta / Senha (90%), urgência 1,36, prazo 3%: média, 55 pts ✔ | Conta / Senha (90%), urgência 1,14, prazo 1%: média, 46 pts ✔ |

O que aconteceu:

- **Setor (Choice):** acertou os 4 casos nas duas versões, com confiança entre 85% e 100%. Nenhum foi para revisão humana.
- **Caso 1, o mais urgente:** com as perguntas iniciais ficou com prioridade média, atrás dos casos 3 e 4. O Score deu 79% para urgência média, e o Noul deu só 43% para "cita prazo", mesmo com "o prazo acaba hoje às 23h59". Com as perguntas ajustadas, passou para alta.
- **Caso 2 virou um falso "alta":** "dá pra usar, mas demora" deveria ser média, e a urgência ficou em 1,50, bem na fronteira. É o efeito colateral do ajuste, descrito abaixo.
- **Tempo:** com as perguntas iniciais, de 431 a 850 ms por chamado na API (média de 578 ms; a primeira chamada é a mais lenta). Isso fica acima da faixa de 190 a 460 ms em CPU citada abaixo, nesta máquina (WSL2, 4 threads), mas ainda é adequado para um help desk. As perguntas ajustadas acrescentam 27 tokens de entrada (de 336 para 363), e no mesmo processo a mediana passou de 959 para 988 ms, cerca de 3% a mais. Essa medição foi feita com a máquina mais carregada, por isso os números absolutos são maiores.

## Ajuste das perguntas

Com as perguntas iniciais, a urgência praticamente não distinguia os chamados: em chamados rotulados como de urgência baixa, média e alta, a média do Score ficou em 1,22, 1,21 e 1,26. Na fila, um Wi-Fi lento ficava no mesmo patamar de "o PC quebrou e a aula é hoje". Para melhorar isso **sem forçar resultado no código**, só reescrevemos o texto das perguntas e medimos cada versão.

**Como foi feito:**

1. **Chamados rotulados à mão:** [backend/scripts/chamados_rotulados.json](backend/scripts/chamados_rotulados.json) tem 48 chamados, cada um com o setor, a urgência (0, 1 ou 2) e se cita prazo. São **32 de desenvolvimento**, incluindo os 4 do smoke test e 4 exemplos reais digitados na interface, e **16 de validação**, escritos antes da segunda rodada e não usados para escolher a variante.
2. **Variantes:** [backend/scripts/avaliar_perguntas.py](backend/scripts/avaliar_perguntas.py) roda cada variante das perguntas sobre os chamados, aplica as mesmas regras de triagem do sistema e compara com os rótulos. Para rodar: `make eval`. Ele carrega uma segunda cópia do modelo e leva alguns minutos.
3. **Critério de escolha, fixado antes de rodar:** a maior "ordem da fila" no conjunto de desenvolvimento (fração dos pares de chamados com prioridades esperadas diferentes que ficam na ordem certa), com desempate pelo acerto de setor.

**Resultados** (desenvolvimento / validação; a 1ª rodada só usou o conjunto de desenvolvimento):

| Variante | Setor | Prioridade certa | Ordem da fila | Urgência média nos rótulos baixa / média / alta |
|---|---|---|---|---|
| original (perguntas iniciais) | 81% / 69% | 22% / 38% | 67% / 54% | 1,22 / 1,21 / 1,26 |
| **misto_original (em uso)** | **81% / 69%** | **62% / 62%** | **78% / 75%** | **1,09 / 1,32 / 1,69** |
| pt_descritiva | 78% / 81% | 62% / 62% | 78% / 75% | 1,09 / 1,32 / 1,69 |
| misto_en (setor em inglês) | 91% / 75% | 62% / 62% | 78% / 75% | 1,09 / 1,32 / 1,69 |
| pt_descritiva_v2 | 75% / 62% | 59% / 62% | 78% / 74% | 1,16 / 1,36 / 1,66 |
| en_descritiva (tudo em inglês) | 91% / — | 25% / — | 74% / — | 1,07 / 1,11 / 1,28 |
| pt_5_niveis (urgência em 5 níveis) | 78% / — | 38% / — | 78% / — | 0,91 / 1,04 / 1,28 |
| en_5_niveis | 91% / — | 38% / — | 76% / — | 0,64 / 0,74 / 0,84 |

**O que mudou nas perguntas em uso** ([backend/app/laya_service.py](backend/app/laya_service.py)):

- **Setor:** ficou igual ao inicial. As descrições mais longas que testamos não acertaram mais no total e mandavam "e-mail institucional" para Rede / Wi-Fi.
- **Urgência:** a instrução passou a citar o campo do estado entre crases ("Qual é a urgência do problema descrito em `` `mensagem` ``?"), como fazem os presets do próprio Laya. Os níveis ficaram concretos: "baixa: dúvida, sugestão ou problema que pode esperar alguns dias", "média: atrapalha, mas há alternativa ou o prazo não é hoje" e "alta: impede agora uma aula, prova ou entrega de hoje".
- **Cita prazo:** a pergunta inclui aula, prova e entrega "hoje ou amanhã", e o Noul ganhou a descrição das duas respostas ("não cita prazo, data nem horário" e "cita prazo, data ou horário próximo").

**O que aprendemos:**

- **Cada pergunta é respondida de forma independente.** Trocar a pergunta de setor não muda nenhuma resposta de urgência ou de prazo. Por isso dá para escolher a melhor versão de cada uma.
- **Perguntas em inglês acertaram mais o setor no desenvolvimento** (91%), mas não na validação (75%). Ficamos com o português, porque a diferença é de poucos chamados e o projeto é todo em português.
- **A escala de 5 níveis não ajudou:** a urgência ficou ainda mais concentrada no meio.

**Limitações que continuam:**

- **Falsos "alta":** alguns chamados de urgência baixa ou média sobem para alta. A média dos chamados de urgência baixa ficou em 1,09, quando o ideal seria perto de 0. É o caso 2 do smoke test e também de "minha nota não apareceu no portal". O ajuste trocou chamados urgentes ficando para trás por alguns chamados comuns subindo demais.
- **Setor de "PC quebrado":** o chamado "Um pc quebrou, preciamos com urgência desse pc para podermos prosseguir a aula ainda hoje!" vai para Rede / Wi-Fi com 96% de confiança, alta o bastante para não cair na revisão humana. Chamados sobre "e-mail institucional" também tendem a ir para Rede / Wi-Fi.
- **O Noul reage à palavra "horário":** "qual é o horário de atendimento do suporte?" teve 70% em "cita prazo".
- **O nome do aluno entra no estado e mexe na resposta:** o mesmo texto com e sem nome teve confianças diferentes no setor.
- **Amostra pequena:** 48 chamados, rotulados por nós. Os números indicam a direção, não são uma medida definitiva.

A melhoria seguinte é a que o próprio Laya recomenda: juntar chamados reais rotulados e **calibrar** as temperaturas (`fit_temperatures`) ou fazer **fine-tuning** do checkpoint. O conjunto rotulado e o script de avaliação deste projeto já servem de ponto de partida para isso.

## Por que o Laya e não o JEV

- **Custo:** o JEV é uma API paga (cerca de US$ 0,042 por 1M de tokens) e exige cartão de crédito. O Laya é gratuito e auto-hospedado; o custo passa a ser só o hardware e a energia da máquina local.
- **Velocidade:** medições independentes colocam o JEV em cerca de 236 a 276 ms (p50). O Laya, com o modelo pré-carregado, fica em cerca de 33 ms numa GPU T4 e de 190 a 460 ms em CPU, o que é adequado para um help desk.
- **Privacidade:** no JEV, o texto do chamado sai para a API da TypeSafe. No Laya, os dados não saem da máquina.
- **Compatibilidade:** o Laya implementa o mesmo protocolo `POST /v1/systemone` do JEV, então migrar para o JEV no futuro seria basicamente trocar a URL.
- **Limitações:** o JEV leva vantagem com muitas opções (mais de cerca de 20 por pergunta), mas o TriaDesk usa só 5. A primeira execução precisa baixar o modelo, e as probabilidades do Laya vêm superconfiantes de fábrica, o que justifica o limiar de revisão humana e é uma boa melhoria futura (calibração ou fine-tuning com chamados reais).

## Decisões de implementação

- **Idioma fixo em português:** toda chamada ao Laya vai com `lang="pt"`. Sem isso, o Laya detecta o idioma pelo texto, e uma frase curta poderia ser lida como inglês e ir para o checkpoint inglês. Com `max_loaded=1`, isso descarregaria o modelo multilíngue e baixaria outro.
- **Carregamento em segundo plano:** o modelo carrega numa thread iniciada no startup, então a API sobe na hora e responde 503 até o Laya ficar pronto. O healthcheck do Docker só aprova o backend quando o modelo está carregado.
- **Sugestão do modelo preservada:** o campo `setor` guarda sempre o que o Laya sugeriu. Na revisão humana muda só a `fila`, e assim dá para comparar a sugestão do modelo com a decisão da pessoa.
