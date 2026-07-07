FIWARE Home Assistant Integration
=================================

Português / Português
---------------------

Este componente integra dados FIWARE no Home Assistant, importando entidades `AirQualityObserved` e `WeatherObserved` e criando sensores nativos para cada medição.

### O que faz

- Obtém dados FIWARE de qualidade do ar e de meteorologia.
- Expõe sensores nativos no Home Assistant para:
  - PM2.5, PM10, NO2, O3, CO
  - Índice de Qualidade do Ar (AQI)
  - Temperatura, Humidade, Velocidade do Vento, Precipitação, Índice UV
- Permite filtrar estações por nome com `stations` ou `exclude`.

### Instalação

1. Copie a pasta `custom_components/fiware` para `config/custom_components/` na sua instalação do Home Assistant.
2. Reinicie o Home Assistant.
3. Vá a Settings → Devices & Services → Add Integration e procure por `FIWARE`.
4. Configure `api_url`, `scan_interval` e, opcionalmente, `stations` / `exclude` pela interface gráfica (UI).

> Nota: esta integração pode ser configurada via YAML em `configuration.yaml`, em vez de utilizar a UI.

### Origem dos dados

- Os dados provêm do FIWARE broker de Porto Digital.
- Mais informações: https://www.portodigital.pt/

### Configuração YAML (opcional)

```yaml
fiware:
  api_url: https://broker.fiware.urbanplatform.portodigital.pt/v2/entities
  scan_interval: 60
  # stations: Station A,Station B
  # exclude: Station C
```

### Notas

- Observações com mais de 1 dia são ignoradas.
- O componente usa `scan_interval` para atualizar os dados.

### Ícone oficial / PR para `home-assistant/brands`

Se pretende que o Home Assistant mostre o ícone oficial na página de Integrações, é necessário submeter o logótipo ao repositório `home-assistant/brands`.

Passos rápidos (automático):

- Coloque um ficheiro SVG vetorial em `branding/fiware.svg`.
- Execute o script `pr_to_brands.sh` (Linux/macOS) ou `pr_to_brands.ps1` (PowerShell) a partir da raiz deste repositório. Estes scripts usam a CLI `gh` para fork/clone, criar branch, adicionar o ficheiro e abrir o PR.

Exemplo (bash):

```bash
chmod +x pr_to_brands.sh
./pr_to_brands.sh <YourGitHubUsername>
```

Exemplo (PowerShell):

```powershell
.\pr_to_brands.ps1 -GitHubUser YourGitHubUsername
```

Se preferir criar o PR manualmente, faça fork de `home-assistant/brands`, adicione `brands/fiware.svg` e abra um PR com o título "Add FIWARE brand icon".


English / English
-----------------

This integration adds FIWARE data to Home Assistant by polling `AirQualityObserved` and `WeatherObserved` entities and exposing native HA sensors.

### What it does

- Fetches FIWARE air quality and weather data.
- Creates native Home Assistant sensors for:
  - PM2.5, PM10, NO2, O3, CO
  - Air Quality Index (AQI)
  - Temperature, Humidity, Wind Speed, Precipitation, UV Index
- Supports station filtering with `stations` or `exclude`.

### Installation

1. Copy the `custom_components/fiware` folder into `config/custom_components/` in your Home Assistant installation.
2. Restart Home Assistant.
3. Go to Settings → Devices & Services → Add Integration and search for `FIWARE`.
4. Configure `api_url`, `scan_interval`, and optionally `stations` / `exclude` through the graphical UI.

> Note: you can also configure this integration via YAML in `configuration.yaml` instead of using the UI.

### Data source

- The data comes from Porto Digital's FIWARE broker.
- More info: https://www.portodigital.pt/

### YAML configuration (optional)

```yaml
fiware:
  api_url: https://broker.fiware.urbanplatform.portodigital.pt/v2/entities
  scan_interval: 60
  # stations: Station A,Station B
  # exclude: Station C
```

### Notes

- Observations older than 1 day are ignored.
- The integration uses `scan_interval` to refresh the data.
