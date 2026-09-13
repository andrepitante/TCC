# TCC
Projeto TCC Univesp

# Predição de Risco de Incêndios em Rodovias com Redes Neurais

Projeto desenvolvido como Trabalho de Conclusão de Curso (TCC) com o objetivo de estimar o risco de ocorrência de incêndios às margens de rodovias do Estado de São Paulo utilizando dados históricos de incêndios, informações meteorológicas e uma Rede Neural Artificial do tipo MLP (*Multilayer Perceptron*).

O sistema utiliza o histórico para aprender relações entre condições meteorológicas e ocorrências de incêndios. Após o treinamento, o modelo pode receber dados meteorológicos de um determinado horário e gerar um **score de risco para as próximas 4 horas** em cada segmento rodoviário analisado.

> O valor produzido pela rede é tratado como um **score de risco**, e não como uma probabilidade absoluta de ocorrência de incêndio.

---

## Rodovias analisadas

O projeto atualmente trabalha com cinco rodovias do Estado de São Paulo:

- SP-021
- SP-280
- SP-300
- SP-330
- SP-348

As rodovias são divididas logicamente em segmentos de aproximadamente **5 km**, totalizando **332 segmentos** utilizados pelo modelo.

---

## Visão geral

O processamento segue, de forma simplificada, o seguinte fluxo:

```text
Histórico de incêndios
        +
Dados meteorológicos
        +
Geometria das rodovias
        ↓
Tratamento e associação geográfica
        ↓
Segmentos rodoviários de 5 km
        ↓
Construção das variáveis meteorológicas
        ↓
Dataset histórico
        ↓
Treinamento da MLP
        ↓
Modelo treinado
        ↓
Dados meteorológicos
        ↓
Score de risco por segmento
        ↓
Mapa interativo
```

O horizonte adotado é de **4 horas**. Para cada horário de referência, o sistema estima o risco de ocorrência de incêndio no mesmo segmento durante as quatro horas seguintes.

---

## Dados utilizados

O projeto combina três grupos principais de dados.

### Incêndios

Registros históricos de ocorrências de incêndios em rodovias, contendo informações como data, horário, rodovia, quilometragem e localização geográfica.

### Meteorologia

Dados meteorológicos horários provenientes de estações distribuídas pelo Estado de São Paulo e regiões próximas.

Para cada segmento rodoviário, o sistema procura as estações meteorológicas disponíveis e utiliza a estação válida mais próxima para cada variável, respeitando uma distância máxima definida durante o desenvolvimento.

### Rodovias

As geometrias das rodovias são utilizadas para o tratamento espacial e para a representação dos segmentos analisados.

---

## Variáveis utilizadas pela MLP

O modelo utiliza **17 variáveis de entrada**:

| Variável | Descrição |
|---|---|
| `temperatura_atual` | Temperatura no horário de referência |
| `umidade_atual` | Umidade relativa no horário de referência |
| `precipitacao_atual` | Precipitação no horário de referência |
| `vento_atual` | Velocidade do vento |
| `rajada_atual` | Velocidade da rajada |
| `temperatura_media_24h` | Temperatura média das últimas 24 horas |
| `temperatura_max_24h` | Temperatura máxima das últimas 24 horas |
| `umidade_media_24h` | Umidade média das últimas 24 horas |
| `umidade_min_24h` | Menor umidade das últimas 24 horas |
| `vento_medio_24h` | Velocidade média do vento nas últimas 24 horas |
| `rajada_max_24h` | Maior rajada nas últimas 24 horas |
| `chuva_24h` | Precipitação acumulada nas últimas 24 horas |
| `horas_com_chuva_24h` | Quantidade de horas com chuva nas últimas 24 horas |
| `chuva_72h` | Precipitação acumulada nas últimas 72 horas |
| `horas_com_chuva_72h` | Quantidade de horas com chuva nas últimas 72 horas |
| `chuva_168h` | Precipitação acumulada nos últimos 7 dias |
| `horas_sem_chuva_ate_168h` | Quantidade de horas desde a última chuva, limitada a 168 horas |

Essas variáveis permitem que o modelo considere tanto a condição meteorológica atual quanto o comportamento recente do clima.

---

## Rede Neural

O modelo principal é uma rede neural MLP implementada com TensorFlow/Keras.

Arquitetura utilizada:

```text
17 entradas
    ↓
Dense 32 - ReLU
    ↓
Dropout 20%
    ↓
Dense 16 - ReLU
    ↓
Dense 8 - ReLU
    ↓
Dense 1 - Sigmoid
    ↓
Score de risco
```

O modelo possui aproximadamente **1.249 parâmetros treináveis**.

Também foi utilizada uma **Regressão Logística** como modelo de referência (*baseline*) para comparação.

---

## Dataset

O dataset final utilizado para modelagem possui aproximadamente **345 mil amostras**, compostas por situações com e sem ocorrência de incêndio.

Para evitar que informações futuras influenciem o treinamento, a divisão foi realizada temporalmente:

```text
2015–2023 → treinamento
2024      → validação
2025–2026 → teste
```

Foi utilizado ainda um intervalo de segurança de 4 horas entre os conjuntos para reduzir possíveis efeitos do horizonte de previsão.

---

## Resultado operacional

Após o treinamento, o modelo pode ser utilizado para calcular o risco dos **332 segmentos rodoviários** para um horário escolhido.

Exemplo:

```text
Horário de referência:
15/05/2025 14:00

Segmento:
SP330_SEG040

Score:
0.4439

Classificação:
MUITO ELEVADO

Horizonte:
próximas 4 horas
```

As faixas atualmente utilizadas são operacionais e podem ser ajustadas posteriormente conforme a avaliação do modelo.

```text
Score < 0.15          → BAIXO
0.15 ≤ Score < 0.25   → MODERADO
0.25 ≤ Score < 0.40   → ELEVADO
Score ≥ 0.40          → MUITO ELEVADO
```

---

## Visualização

Os resultados podem ser apresentados em um mapa interativo desenvolvido com **Folium/Leaflet**.

O mapa apresenta:

- segmentos rodoviários classificados por risco;
- escala de cores por faixa operacional;
- estações meteorológicas utilizadas pelo projeto;
- horário de referência;
- horizonte de previsão de 4 horas;
- informações detalhadas ao selecionar um segmento.

Os mapas gerados são arquivos HTML e podem ser abertos diretamente em um navegador.

---

## Estrutura do projeto

```text
TCC/
│
├── data/
│   ├── incendios/
│   ├── INMET/
│   └── rodovias/
│
├── import/
│   └── scripts de importação
│
├── sql/
│   └── consultas e criação das estruturas do banco
│
├── process/
│   └── processamento e preparação dos dados
│
├── mod_treinning/
│   ├── preparação do dataset
│   ├── baseline
│   └── treinamento da MLP
│
├── model/
│   ├── mlp_risco_incendio_v1.keras
│   ├── scaler_mlp_v1.pkl
│   └── mlp_risco_incendio_v1.json
│
├── real_time/
│   ├── preparar_meteorologia.py
│   ├── prever_todos_segmentos.py
│   └── gerar_mapa_folium.py
│
├── results/
│   ├── resultados CSV
│   ├── resultados JSON
│   └── mapas HTML
│
├── .env
├── .gitignore
└── README.md
```

---

## Tecnologias

O projeto utiliza principalmente:

- Python
- PostgreSQL
- PostGIS
- Pandas
- GeoPandas
- SQLAlchemy
- TensorFlow / Keras
- Scikit-learn
- Folium / Leaflet
- OpenStreetMap
- Esri World Topographic Map

---

## Execução da previsão

Com o ambiente Python ativado:

```powershell
python C:\TCC\real_time\prever_todos_segmentos.py
```

O programa solicita um horário de referência:

```text
Informe a hora de referência (AAAA-MM-DD HH:MM):
```

Exemplo:

```text
2025-05-15 14:00
```

O processo:

```text
1. verifica os dados meteorológicos necessários
2. prepara as últimas 168 horas
3. calcula as 17 variáveis
4. carrega o scaler
5. carrega a MLP treinada
6. calcula o score dos 332 segmentos
7. classifica as faixas de risco
8. exporta CSV e JSON
9. gera o mapa Folium
```

Os arquivos resultantes são armazenados em:

```text
C:\TCC\results\
```

---

## Objetivo do projeto

O sistema não pretende determinar com certeza onde ocorrerá um incêndio.

A proposta é utilizar dados históricos e meteorológicos para identificar **condições associadas a maior risco**, permitindo destacar segmentos rodoviários que possam merecer maior atenção durante as próximas horas.

Dessa forma, o modelo pode servir como ferramenta de apoio ao monitoramento e à tomada de decisão.

---

## Status

🚧 Projeto em desenvolvimento como Trabalho de Conclusão de Curso.

Atualmente estão implementados:

- tratamento dos históricos de incêndios;
- importação dos dados meteorológicos;
- tratamento geoespacial das rodovias;
- segmentação das rodovias;
- associação entre segmentos e estações meteorológicas;
- construção do dataset;
- treinamento da MLP;
- avaliação do modelo;
- previsão operacional para os 332 segmentos;
- exportação dos resultados;
- visualização interativa em mapa.

---


Trabalho de Conclusão de Curso – UNIVESP