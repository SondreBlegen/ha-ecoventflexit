# Ecovent Flexit Fan Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

This Home Assistant custom component provides integration for Ecovent Flexit ventilation units, leveraging the `pyEcoventV2` Python library to communicate directly with the fan over your local network. It exposes your Flexit unit as a standard Home Assistant `fan` entity, allowing for control over power, speed, and a custom service for airflow modes.

**Please ensure you have `pyEcoventV2` installed in your Home Assistant environment if you are not using HACS, or if the automatic installation fails.** HACS should handle this automatically.

**Note:** This integration relies on the `pyEcoventV2` library. Compatibility is based on devices supported by that library (e.g., some Vents, Blauberg, Flexit models). Your specific `fan_id` and `password` are required for authentication.

## Features

- **Fan Entity:** Control your Ecovent Flexit unit's power (On/Off) and fan speed (Low, Medium, High).
- **Polling:** Periodically updates the fan's state (power, speed, airflow mode, and other attributes).
- **Custom Service:** `ecoventflexit.set_airflow` to change the airflow mode (e.g., `ventilation`, `heat_recovery`, `air_supply`).
- **Detailed Attributes:** Exposes additional information such as humidity, fan RPMs, firmware version, filter countdown, machine hours, and alarm status as entity attributes.

## Installation (HACS Recommended)

### 1. Add this Repository to HACS

1.  Open Home Assistant.
2.  Go to `HACS` -> `Integrations`.
3.  Click the three dots in the top right corner and select `Custom repositories`.
4.  In the `Add custom repository` field, paste the URL of this GitHub repository:
    `https://github.com/your_github_username/ha-ecoventflexit` (Replace `your_github_username` with your actual GitHub username).
5.  Select `Integration` as the Category.
6.  Click `ADD`.

### 2. Install the Integration

1.  Search for "Ecovent Flexit" in the HACS Integrations section.
2.  Click on the "Ecovent Flexit Fan" integration.
3.  Click `DOWNLOAD` and confirm.
4.  **Restart Home Assistant.** This is crucial for the new integration to be detected and for its dependencies (`pyEcoventV2`) to be installed.

### Manual Installation (Not Recommended for most users)

1.  Create the `ecoventflexit` folder inside your Home Assistant `custom_components` directory.
    ```bash
    <your Home Assistant config dir>/custom_components/ecoventflexit/
    ```
2.  Copy all the files from this repository's `custom_components/ecoventflexit/` folder into the newly created folder.
3.  Install the dependency:
    ```bash
    pip3 install pyEcoventV2
    ```
    (You might need to activate your Home Assistant virtual environment first, or run this command in the Home Assistant terminal add-on if you're using HassOS/Supervised).
4.  **Restart Home Assistant.**

## Configuration

The Ecovent Flexit integration is configured via the Home Assistant UI.

1.  Go to `Settings` -> `Devices & Services`.
2.  Click on the `ADD INTEGRATION` button (bottom right).
3.  Search for "Ecovent Flexit".
4.  You will be prompted to enter the following information:
    - **IP Address:** The static IP address of your Ecovent Flexit unit on your local network (e.g., `192.168.1.82`).
    - **Port:** The communication port (default: `4000`).
    - **Fan ID:** The unique ID of your Flexit unit (e.g., `002300424B465707`). This is often found on a sticker on the device or in its mobile app settings.
    - **Password:** The password for your Flexit unit (e.g., `11111111`).
    - **Name (Optional):** A friendly name for your fan entity (e.g., `Theodor ventilation`). If not provided, a default name will be used.
5.  Click `SUBMIT`.
6.  If the connection is successful, a new device and fan entity will be created (e.g., `fan.theodor_ventilation`).

## Usage

### Fan Entity

Once configured, you will have a standard Home Assistant `fan` entity.

- **Toggle:** Turn the fan On/Off.
- **Speed Control:** Set the speed to Low, Medium, or High via the UI controls or `fan.set_percentage` service.

### Custom Service: `ecoventflexit.set_airflow`

This service allows you to explicitly set the airflow mode of your Flexit unit.

1.  Go to `Developer Tools` -> `Services`.
2.  Select `ecoventflexit.set_airflow` from the dropdown.
3.  Fill in the service data:
    - **Entity ID:** The `entity_id` of your fan (e.g., `fan.theodor_ventilation`).
    - **Airflow Mode:** Choose one of the supported modes:
      - `ventilation`
      - `heat_recovery`
      - `air_supply`
      - `something` (This mode name comes directly from the library's protocol mapping and may correspond to a specific function on your device).

**Example Service Call:**

```yaml
service: ecoventflexit.set_airflow
data:
  entity_id: fan.theodor_ventilation
  airflow_mode: heat_recovery
Troubleshooting
"Cannot connect" error during setup:
Double-check the IP Address, Port, Fan ID, and Password are absolutely correct.
Ensure your Home Assistant instance can reach the fan's IP address on port 4000 (no firewall blocking).
Verify the fan is powered on and connected to your network.
Fan State / Speed shows None or incorrect values:
The pyEcoventV2 library might not be fully compatible with your exact Flexit model, even if it can connect. The library's params mapping might differ.
Check Home Assistant logs (Settings -> System -> Logs) for ecoventflexit or ecoventv2 related errors at INFO or ERROR level. Increase logging level to DEBUG for more detail:
code
Yaml
logger:
  default: info
  custom_components.ecoventflexit: debug
  ecoventv2: debug
HACS download problems:
Ensure HACS itself is properly installed and updated.
Clear your browser cache.
Restart Home Assistant after installation.
Development / Contributions
If you find issues or want to contribute, please open an issue or pull request on the GitHub repository: https://github.com/your_github_username/ha-ecoventflexit
Acknowledgements
This integration relies heavily on the excellent work of aglehmann and the pyEcoventV2 library:
pyEcoventV2 GitHub Repository: https://github.com/aglehmann/pyEcovent
```
