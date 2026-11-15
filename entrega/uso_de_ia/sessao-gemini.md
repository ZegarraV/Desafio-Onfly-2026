# Guia do Desafio Técnico Onfly — Google Gemini

Transcrição das duas perguntas e das duas respostas visíveis no [compartilhamento enviado](https://share.gemini.google/zqlcxBu86z9C). A página identifica o modo como **Pesquisa detalhada** e não informa a versão exata do modelo. A conversa mostra um anexo chamado `README (2).md`, indisponível para download no compartilhamento.

## Usuário

Leia o Readme do desafio Tecnico e me ajude a entender melhor os requisitos pedidos e sobre a entrega como envia-la

## Gemini

O desafio da Onfly exige que você atue como um investigador de código: o objetivo principal não é criar o projeto do zero, mas encontrar e corrigir defeitos de lógica e matemática em um CLI Python já construído, garantindo que a saída seja exata e os testes voltem a passar. Aqui estão os pontos de atenção mais críticos sobre os requisitos e as regras de negócio:

- **Filtro de Faturamento:** Apenas reservas com status `CONFIRMED` geram valores financeiros e noites. Status como `CANCELLED` e `NO_SHOW` entram na contagem total de reservas e na quebra por status, mas devem ser ignorados nos cálculos de dinheiro e ocupação.
- **Cálculo de Noites:** A fórmula é a diferença simples de dias entre o check-out e check-in multiplicada pela quantidade de quartos, sem incluir o dia de saída no cálculo.
- **Precisão Financeira:** A regra de ouro aqui é usar exclusivamente a classe `Decimal` do Python para operações de dinheiro (nunca `float`). O arredondamento (duas casas decimais, modelo half-up) só deve acontecer no momento final de serializar o JSON.
- **Câmbio:** Todos os valores base (`amount`) devem ser multiplicados pela taxa cambial (`rate_to_brl`) utilizando a tabela CSV de taxas fornecida.
- **Ordenação Estrita:** Fique atento à ordenação do relatório final: a chave `by_month` deve seguir ordem crescente, e a lista `top_hotels` precisa ser decrescente pelo maior valor financeiro (com desempate pelo ID do hotel em ordem crescente).
- **Imutabilidade:** O contrato da linha de comando (argumentos) e o formato exato do JSON final são sagrados. Você também está terminantemente proibido de alterar os testes que vieram no repositório; seu trabalho é consertar a aplicação para que esses testes passem.

Sobre o empacotamento e envio da entrega:

- O projeto finalizado deve ser submetido em um repositório público no seu GitHub (ZegarraV), e o link será compartilhado com o time da Onfly via formulário.
- Na raiz do projeto, você deve estruturar a pasta `entrega/` contendo o arquivo `README-ENTREGA.md`. Este documento é o seu relatório de investigação: aponte os defeitos corrigidos, a causa raiz de cada um (uma frase curta para cada erro), como você conduziu a investigação, o passo a passo para validar a solução e o log de sucesso do `pytest`.
- **Regra de Transparência:** Como estamos conversando sobre o projeto agora, a sua entrega se enquadra no "Caminho com IA". Você obrigatoriamente precisará criar uma subpasta `entrega/uso-de-ia/` contendo a exportação completa das nossas sessões (em arquivos `.md`, `.txt` ou `.jsonl`), além de um arquivo `declaracao.md`. Nessa declaração, informe qual ferramenta e modelo usou (no caso, Google Gemini) e deixe claro o limite do que a IA fez e do que você codificou manualmente.

Você já rodou o `pytest -q` inicial ou já localizou qual arquivo dentro de `src/onfly_report/` faz a conversão de tipos flutuantes para começarmos a caçar os defeitos?

## Usuário

quais pontos devo prestar mais atenção?

## Gemini

Para garantir a aprovação na suíte de testes sem alterar o código original da avaliação, o seu foco investigativo no CLI deve priorizar as seguintes regras de negócio e tipagem:

- **Uso estrito de `Decimal`:** Variáveis do tipo `float` causam imprecisão em operações financeiras. Todo o cálculo e a multiplicação pela taxa de câmbio devem usar `Decimal`. O arredondamento (duas casas decimais, usando o método half-up) deve acontecer exclusivamente no momento final da serialização para JSON.
- **Isolamento de status para faturamento:** Apenas reservas `CONFIRMED` entram no cálculo de valores (`total_amount_brl`), soma de noites (`total_room_nights`), na diária média, no agrupamento `by_month` e no ranking `top_hotels`. Os status `CANCELLED` e `NO_SHOW` contam unicamente no totalizador geral e em suas respectivas contagens.
- **Fórmula de ocupação e divisão por zero:** O total de noites não é apenas a diferença de dias; exige multiplicar a diferença (excluindo a data de saída) pela quantidade de quartos (`rooms`). Além disso, ao calcular o `average_nightly_rate_brl`, se a divisão envolver zero noites, o sistema não pode quebrar; deve retornar a string `"0.00"`.
- **Formatação rigorosa do JSON:** O valor financeiro exportado no output final não pode ser um tipo numérico. Ele deve ser uma string com exatas duas casas decimais e sem separador de milhares (ex: `"1234.50"`).
- **Critério de desempate na ordenação:** O ranking `top_hotels` exige ordenação primária decrescente pelo valor financeiro, mas você precisa garantir um critério secundário de desempate que ordene de forma crescente pelo `hotel_id`.
- **Imutabilidade das pontas:** Você tem liberdade total para refatorar e consertar os arquivos internos em `src/onfly_report/`, mas é estritamente proibido alterar os argumentos do comando CLI, o formato final do JSON, a base de dados em `data/` ou os testes em `tests/`.
