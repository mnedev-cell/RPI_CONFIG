# RPI_CONFIG
## Download Config RPI
```shell
git clone https://github.com/mnedev-cell/RPI_CONFIG.git
```
## Create Config RPI
```shell
 sudo nano /home/pi/install_auto_config.py
```
## Programme principal
```shell
import requests
import json
import platform


# Fonction pour récupérer le nom d'hôte du Raspberry Pi
def get_rpi_hostname():
    return platform.node()


# Fonction pour récupérer le type de contrôle
def get_Type_CRTL():
    # Remplacez par la logique réelle pour obtenir le type de contrôle
    return "COU-XX"


# Appel à l'URL pour obtenir la configuration
def get_rpi_config():
    url = "https://ping.logitec.ma/YAPO_UPDATE/GET_RPI_CONFIG"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            config_data = response.json()
            return config_data
        else:
            print(f"Erreur : Impossible de récupérer les données, statut {response.status_code}")
            return None
    except Exception as e:
        print(f"Erreur : {e}")
        return None


# Génération du fichier config.py
def generate_config_file(config_data):
    if config_data:
        if config_data['TO_UPDATE_MAIN']:
            TO_UPDATE_MAIN = 1
        else:
            TO_UPDATE_MAIN = 0
        if config_data['To_UPDATE_CFG']:
            To_UPDATE_CFG = 1
        else:
            To_UPDATE_CFG = 0

        if config_data['st_etat_relais']['relais_1']:
            ENABLE_RELAIS = 1
        else:
            ENABLE_RELAIS = 0

        if config_data['st_etat_relais']['relais_1']:
            Port_relais = 1
        elif config_data['st_etat_relais']['relais_2']:
            Port_relais = 2
        else:
            Port_relais = None
        config = {
            "Position": get_rpi_hostname(),  # CRA-/COU
            "Status_VFD": config_data['st_etat_lcd']['lcd_1'],
            # True => Pour activer le VFD, False =>pour désactiver VFD
            "Port": config_data['st_etat_lcd']['PORT_USB'],  # Le numéro du Port Série utilisé
            "URL_webservice": config_data['web_service_url'],  # URL Yapo pour le webservice
            "URL_ping": config_data['web_ping_url'],  # URL Yapo pour le ping
            "Port_relais": Port_relais,  # Numéro BCM du GPIO utilisé pour le relais du Raspberry Pi
            "TypeCRTL": config_data['TypeCRTL'],  # Type de contrôle
            "Version": config_data['Version'],  # Version du programme
            "CheckForUpdates": TO_UPDATE_MAIN,  # Contrôle des mises à jour
            "ENABLE_SERVICE": To_UPDATE_CFG,  # Activation du service ping
            "ENABLE_RELAIS":  ENABLE_RELAIS, # Activation des relais,
            "MODE_PRG": config_data['Mode_PRG']  # Activation des relais
        }

        with open('config.py', 'w') as file:
            file.write("config = " + json.dumps(config, indent=4))
        print("Fichier config.py généré avec succès.")
    else:
        print("Erreur : Aucune donnée à écrire dans le fichier config.py.")

```
# Programme principal

```shell
    config_data = get_rpi_config()
    generate_config_file(config_data)
```
# Download main file
```shell
    wget https://upload.yapo.ovh/update/main.py
```
# AUTOSTART_TERMINAL
## Setup autostart
```shell
  sudo chmod +x  /home/pi/dir/autostart
```
```shell
 sudo nano /etc/xdg/lxsession/LXDE-pi/autostart
```
```shell
    @xset s noblank
    @xset s off
    @xset -dpms
    @lxterminal --command="/home/pi/dir/autostart"
```
