# Entrega do teste técnico Onfly

## Objetivo

Corrigir o CLI que consolida reservas de hotel em JSON. O relatório conta todas as reservas e usa as confirmadas para calcular noites de quarto, valores em BRL, diária média, totais por mês de check-in e ranking de hotéis.

## Investigação e correções

A investigação começou pela leitura do enunciado, do fluxo do CLI, dos arquivos de configuração e dos cinco testes fornecidos. A execução do CLI original no CSV principal produziu `Reservas: 200 | Confirmadas: 153 | Noites: -1393 | Total BRL: 193218.53`. Os cinco testes originais falharam. A contagem direta no CSV encontrou 300 reservas, com 235 confirmações, 31 cancelamentos e 34 no-shows. A partir desses resultados, a investigação percorreu cada etapa da leitura até a serialização.

| Defeito | Causa raiz | Correção |
| --- | --- | --- |
| Leitura truncada | Um `break` encerrava a iteração após a 200ª linha de reserva. | `repositories/csv_reservation_repository.py` percorre o CSV até o fim. |
| Noites incorretas nas viradas de mês e ano | A subtração usava somente os números dos dias no mês. | `services/stay_calculator.py` subtrai as datas civis completas e multiplica a diferença em dias pela quantidade de quartos. |
| Valores incorretos em BRL | A conversão usava divisão com operandos convertidos para `float`. | `services/currency_converter.py` multiplica o valor pela taxa com `Decimal` do início ao fim. |
| No-shows faturados | A condição de faturamento aceitava qualquer status diferente de `CANCELLED`. | `services/status_policy.py` exige `CONFIRMED`. O relatório conta todos os status antes do filtro. |
| Ranking invertido | A chave de ordenação usava o valor monetário em ordem crescente. | `services/report_builder.py` ordena pelo valor exato decrescente e usa o ID crescente para desempatar. |

Em `report_builder.py`, a chave mensal vem da data ISO de check-in, o que preserva os quatro dígitos do ano. O cálculo da diária usa o total em BRL dividido pelo total de noites de quarto e retorna `0.00` quando não há noites. A formatação existente aplica `ROUND_HALF_UP` a duas casas na montagem do JSON, após as somas e a ordenação.

Entradas inválidas também precisam retornar código 2. Os repositórios agora tratam falhas de decodificação como erro de entrada. O repositório de câmbio e `services/row_parser.py` verificam se taxas e valores são finitos. O conversor identifica taxas ausentes para reservas faturáveis. Esses casos interrompem a execução com mensagem em stderr.

## Como validar

Execute na raiz do projeto, com Python 3.11 ou superior.

### Linux e macOS

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
pytest -q
PYTHONPATH=src python -m onfly_report --input data/reservas_hoteis.csv --rates data/taxas_cambio.csv --output output/report.json --top 5
PYTHONPATH=src python -m onfly_report --input data/exemplo-validacao.csv --rates data/taxas_cambio.csv --output output/exemplo.json
```

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m onfly_report --input data/reservas_hoteis.csv --rates data/taxas_cambio.csv --output output/report.json --top 5
.\.venv\Scripts\python.exe -m onfly_report --input data/exemplo-validacao.csv --rates data/taxas_cambio.csv --output output/exemplo.json
```

O CLI usa a biblioteca padrão. O arquivo `requirements-dev.txt` instala as ferramentas de desenvolvimento. Os JSONs são gerados localmente em `output/`.

## Resultados verificados

Em Linux, com Python **3.11.18** e pytest **8.3.4**, os cinco testes fornecidos falharam na versão original e **27 testes passaram** após a correção, incluindo os cinco originais. A suíte também passou em Python 3.12.14. Os testes adicionais usam CSVs temporários para verificar o limite de leitura, datas civis, status, câmbio, arredondamento, ranking, formato, códigos de saída e criação de diretórios.

Um cálculo independente baseado em frações exatas confirmou o resumo, todos os meses e o ranking dos dois relatórios. A amostra coincidiu integralmente com os valores esperados no enunciado. A validação confirmou o offset `-03:00` de `generated_at` nos dois arquivos.

| Campo | CSV principal | Amostra |
| --- | ---: | ---: |
| Reservas | 300 | 12 |
| Confirmadas | 235 | 9 |
| Canceladas | 31 | 2 |
| No-shows | 34 | 1 |
| Noites de quarto | 1.347 | 28 |
| Total em BRL | 396170.00 | 7566.00 |
| Diária média em BRL | 294.11 | 270.21 |

O SHA-256 do ZIP de origem é `33cf623a68b372c26fc077e63caf91c9c57d80afa59526d9672c1eb650923838`. Os hashes abaixo coincidiram com os dos arquivos extraídos do ZIP original.

```text
6e260d7a31421e6dbcfb57d4fd2446e74a90d6ca5c3577f1ac4491b16f15b3bb  data/exemplo-validacao.csv
cd371fc8610f3764fa3bc827ae9065c81b3f479a1dc800c504432ee0db999d39  data/reservas_hoteis.csv
62417b7dddf8eb94c95d244512687d958e83b765de053104930d3dfc03c8ea98  data/taxas_cambio.csv
8761c13118dd76ab999a1640d77e122eceb827ef40c941a53cdd2d8b34bf29bb  tests/helpers.py
9bf9369399ec97a969d9925e86a5cd81e8557b7bb49408047ba091cd26db138a  tests/test_currency.py
ed44b902819faf2b0f9370a97f76283574140e296dcd00c127f1c4389b97ca07  tests/test_nights.py
8e9ced57e65a44cffab85b65c94ac6a3682fb730387fc3492bf45dbc375249a7  tests/test_regression_report.py
bd095ccdb3a7c5eced3d3c290ed2c91ecffb47bb21d24ea9cea569c7e6d4f878  tests/test_status_rules.py
6faa26679668248f278049c08e6090cd5540294b760d4e718d2ae96e83b6fd72  tests/test_top_hotels.py
3ba59b989d0bfa4c29513bbb36626efd049733f95ad8bd4ec297a82941827f1e  README.md
```

## Uso de IA

O projeto partiu do código-base fornecido no desafio. A IA foi usada como apoio para interpretar o enunciado, corrigir os erros do CLI e ajustar a formatação do código alterado. Nesta versão, a IA também acrescentou testes, executou as validações e preparou a documentação.

A [declaração](uso-de-ia/declaracao.md) descreve a participação em cada etapa. O [registro da sessão](uso-de-ia/sessao.md) reúne o prompt, as interações e as evidências de validação. O [LogGPT fornecido](uso-de-ia/logGPT.md) e a [conversa compartilhada do Gemini](uso-de-ia/sessao-gemini.md) complementam esse registro. O histórico completo da etapa de preparação do prompt ainda precisa ser acrescentado.
