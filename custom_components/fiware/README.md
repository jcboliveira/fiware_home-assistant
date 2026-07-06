FIWARE Home Assistant Integration
===============================


Instalação (sem editar `configuration.yaml`)
-------------------------------------------

1. Copie a pasta `custom_components/fiware` para o diretório `config/custom_components/` da sua instalação do Home Assistant.
2. Reinicie o Home Assistant para carregar o novo componente.
3. Vá a Settings → Devices & Services → Add Integration e procure por "FIWARE". Configure `api_url`, `scan_interval` e (opcionalmente) `stations` / `exclude` via UI.

Ou, se preferir, ainda é possível usar `configuration.yaml` (não recomendado):

```yaml
fiware:
  api_url: https://broker.fiware.urbanplatform.portodigital.pt/v2/entities
  scan_interval: 60
  # opcional
  # stations: Station A,Station B
  # exclude: Station C
```

O que faz
---------

- Puxa entidades `AirQualityObserved` e `WeatherObserved` do FIWARE.
- Expõe sensores nativos no Home Assistant (PM2.5, PM10, NO2, O3, CO, AQI, temperatura, humidade, etc.).
- Filtra estações por nome (via `stations` ou `exclude`).

Notas
-----

- Observações com mais de 1 dia são ignoradas (como no script original).
- Não inclui configuração via UI (`config_flow`) por enquanto — posso adicionar se desejar.
