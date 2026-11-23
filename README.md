# EnergySim

Demonstração de desperdício de energia em computadores para apresentação de aproximadamente dois minutos. Abre diretamente no painel, sem cadastro ou configuração prévia.

## Executar

Use Python 3.12, a versão validada para o projeto. Abra o terminal na pasta que contém `app.py`.

```bash
python -m venv .venv
```

No Windows:

```powershell
.venv\Scripts\activate
```

No macOS ou Linux:

```bash
source .venv/bin/activate
```

Instale e execute:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Abra http://localhost:8501. O tema é carregado da pasta .streamlit, por isso execute na pasta do projeto. A interface não requer serviços externos, sensores ou conta. Faça a instalação das dependências antes do evento.

## Publicar no Streamlit Community Cloud

Se você recebeu o projeto em ZIP, extraia a pasta `EnergySim` e rode `git init -b main` nela para criar o repositório local.

1. No GitHub Desktop, adicione a pasta que contém `app.py` em **File → Add local repository**. Faça o primeiro commit se a pasta veio do ZIP. Com a branch `main` selecionada, use **Publish repository**.
2. Em [Streamlit Community Cloud](https://share.streamlit.io/), conecte sua conta do GitHub e selecione **Create app**. Escolha seu repositório e preencha **Branch** com `main` e **Main file path** com `app.py`.
3. Em **Advanced settings**, escolha **Python 3.12**. O Community Cloud instala as dependências de `requirements.txt` e carrega o tema de `.streamlit/config.toml`. O app usa dados simulados e dispensa configuração de segredos.
4. Clique em **Deploy** e abra o endereço `streamlit.app` gerado.

## Demonstração

1. Observe o medidor de energia e a faixa **Esperado x agora** de um PC intermediário executando navegador e documentos.
2. Clique em **1. Mostrar consumo extra**. O disco do medidor acelera, o marcador sai da faixa esperada, o alerta aparece e o gráfico desenha a temperatura subindo.
3. Clique em **2. Simular otimização**. A mesma tela compara potência, temperatura, percentual de redução, energia e custo mensal.
4. Role até **E em grande escala?**: informe a quantidade de computadores (padrão: 30) para ver a economia por ano. No cenário padrão, 30 computadores economizam R$ 6.998 e 7.776 kWh por ano.
5. **O que fazer no dia a dia** resume três ações: encerrar o que não está em uso, desativar a inicialização automática e acompanhar o consumo.
6. Use **Recomeçar** para uma nova apresentação. A tarifa configurada é mantida.

Os dois cliques não impõem duração mínima. O roteiro em docs/ROTEIRO_HACKATHON.md distribui a explicação em 120 segundos, dentro da faixa solicitada de 90 a 150 segundos. A duração ao vivo depende do apresentador.

## Valores e limites

Todos os indicadores são simulados. Nenhum processo real é encerrado e nenhum consumo real de hardware é medido. A utilização útil de CPU e GPU permanece fixa, isolando a parcela de 90 W adicionada pelo modelo. Essa parcela é um recurso didático, não uma estimativa de consumo de um programa específico.

A faixa esperada usa as faixas originais da tarefa e a margem de detecção de 15%. O cálculo de potência e a resposta térmica de primeira ordem reutilizam o motor original. Cada cenário avança 180 segundos simulados sem espera real. A temperatura exibida após a intervenção representa o final desse intervalo, não resfriamento instantâneo. O cenário escolhido permanece abaixo dos limiares de instabilidade e não apresenta falhas físicas.

O custo mensal considera potência constante por 8 horas diárias, durante 30 dias, com tarifa ilustrativa padrão de R$ 0,90/kWh. Altere a tarifa em **Premissas da simulação e tarifa**.

Fórmulas:

```text
energia mensal = potência em W / 1000 × 8 × 30
custo mensal = energia mensal × tarifa
redução percentual = (potência antes - potência depois) / potência antes × 100
economia mensal = custo antes - custo depois
```

No cenário padrão: 162,4 W antes, 72,4 W depois, redução de 55,4%, economia de 21,60 kWh e R$ 19,44 por mês. Esses números são calculados pelo modelo. A economia usa cenários com a mesma duração mensal, não o histórico acumulado durante os cliques.

## Recursos preservados

O botão **Explorar o modo completo** abre 19 etapas com três perfis de computador, atividades, recomendações, relatórios, teste de estresse e oito experimentos. O botão **Voltar à demonstração rápida** fica no fim de cada etapa.

Os cálculos e o comportamento legado não foram reescritos. As simulações antigas de instabilidade continuam apenas no modo educativo completo, com seus avisos originais. O novo comparativo usa um cálculo próprio e explícito entre dois estados da mesma tarefa. Não depende do percentual histórico do relatório legado.

## Estrutura alterada

* app.py: registro da demonstração como tela inicial e retorno pelo menu.
* ui/demo.py: medidor de energia, faixa esperado x agora, gráfico animado, comparação visual, projeção em grande escala e ações do dia a dia.
* ui/theme.css: identidade visual (azul-marinho e amarelo elétrico).
* core/demo.py: fluxo controlado que reutiliza Simulator, inject_waste e apply_decision.
* .streamlit/config.toml: tema claro e fontes (Bricolage Grotesque e Atkinson Hyperlegible).
* tests/: testes de fluxo, cálculos, persistência, tarifa e compatibilidade.
* docs/: análise inicial, roteiro de apresentação e documentação original.

## Verificação

```bash
python -m unittest discover -s tests -v
```

Os testes cobrem a detecção de consumo extra, a otimização, a tarifa, a projeção em grande escala, o reinício, a navegação e o funcionamento básico do simulador, do relatório e do teste de estresse.

## Interface

A tela principal usa a linguagem de uma instalação elétrica para tornar o consumo visível:

* **Medidor de energia:** o disco gira mais rápido quanto maior a potência, e o mostrador marca os kWh de 30 dias e o valor na conta de luz.
* **Esperado x agora:** uma faixa mostra o consumo esperado para a tarefa (67,7 a 82,2 W), a tolerância de 15% (até 94,5 W) e um marcador com a potência atual. Com o consumo extra, o marcador desliza para fora da faixa e o quadro destaca quantos watts passaram do esperado.
* **Gráfico ao longo do tempo:** a cada clique, o trecho novo de potência e temperatura é desenhado em animação, mostrando que a potência muda na hora e a temperatura sobe e desce aos poucos.
* **Números animados:** os valores contam até o novo resultado a cada etapa.

As animações rodam no navegador e respeitam a configuração de movimento reduzido do sistema. Os scripts ficam em `ui/demo.py` e não podem conter marcações HTML literais, pois o Streamlit os remove na sanitização; o teste `tests/test_scripts.py` verifica isso.

## Interface para apresentação em hackathon

A demonstração inicial apresenta indicadores resumidos e uma comparação visual de antes e depois. O código dos cálculos fica em `core/demo.py`.

O roteiro sugerido para apresentar o projeto à banca está em `docs/ROTEIRO_HACKATHON.md`.
