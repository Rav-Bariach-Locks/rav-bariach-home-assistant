<p align="center">
  <img src="https://raw.githubusercontent.com/Rav-Bariach-Locks/rav-bariach-home-assistant/master/custom_components/rav-bariach/brand/logo.png" width="120" alt="RB Logo">
</p>

<h1 align="center">Rav Bariach Integration for Home Assistant</h1>

<p align="center">
  <a href="https://github.com/hacs/integration">
    <img src="https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge" alt="HACS Custom">
  </a>
  <img src="https://img.shields.io/badge/Home%20Assistant-Compatible-blue.svg?style=for-the-badge&logo=home-assistant" alt="Home Assistant">
  <img src="https://img.shields.io/badge/Cloud-Required-success.svg?style=for-the-badge&logo=icloud" alt="Cloud Dependent">
</p>

This custom integration allows you to control and monitor your **Rav Bariach Lock** systems directly from Home Assistant. Automate your home security and keep your peace of mind in one central dashboard.

---

## Features

*  **Smart Lock Control:** Securely lock or unlock your Rav Bariach doors with ease.
*  **Smart Relays:** Control additional RB modules and integrated features.
*  **Real-time Status:** Monitor door status, connectivity, and alarm states instantly.

---

##  Installation

### Method: HACS (Custom Repository)

[![](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Smart-RD&repository=rav-bariach-home-assistant&category=Integration)

1. Navigate to **HACS** in your Home Assistant sidebar.
2. Click the **three dots** (`⋮`) in the top-right corner and select **Custom repositories**.
3. **Repository URL:** `https://github.com/Rav-Bariach-Locks/rav-bariach-home-assistant`
4. **Category:** Select `Integration` and click **Add**.
5. Search for *"Rav Bariach"* in HACS, click **Download**.
6. 🔄 **Restart Home Assistant** to apply the changes.

---

##  Configuration

This integration is configured entirely via the Home Assistant UI (Config Flow). No YAML editing is required!

1. Go to ⚙️ **Settings** > **Devices & Services**.
2. Click **+ Add Integration** in the bottom right corner.
3. Search for **"Rav Bariach"**.
4. Enter your Rav Bariach Web Login credentials to authenticate.
5. Assign your new devices to your rooms and enjoy!

---

> [!WARNING]  
> **Cloud Dependency:** This integration requires your Rav Bariach system to be connected to the internet and cloud services to be active. It relies on the cloud API to communicate with your locks.

---

##  Support and Contribution

If you experience any issues or need help setting up your integration, please reach out to our support team:

*  **[Contact the Support Team](mailto:omer_y@rav-bariach.com,moran_g@rav-bariach.com,moti_l@rav-bariach.com)**