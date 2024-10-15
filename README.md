# RPI_CONFIG
## Download Config RPI
```shell
git clone https://github.com/mnedev-cell/RPI_CONFIG.git
```
## Create Config RPI
# Step 1: Create the Python Script

Assume the Python script you want to run is called auto_config_service.py. 
Save it to a directory, for example /home/pi/WORKDIR/auto_config_service.py.

```shell
 sudo nano /home/pi/install_auto_config.py
```
or
```shell
 sudo nano /home/pi/WORKDIR/auto_config_service.py
```

Add the following content to define the script:
## Programme principal
```shell
import os
import requests
import platform
import subprocess as sp
import json
import logging

class ColoredFormatter(logging.Formatter):
    COLORS = {
        'INFO': '\033[92m',  # Green
        'ERROR': '\033[91m',  # Red
        'WARNING': '\033[93m',  # Yellow/Orange
        'RESET': '\033[0m'  # Reset color
    }

    def format(self, record):
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        message = super().format(record)
        return f"{level_color}{message}{self.COLORS['RESET']}"


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
for handler in logging.root.handlers:
    handler.setFormatter(ColoredFormatter())

def get_rpi_hostname():
    return platform.node()

def GET_RPI_CONFIG(sRPI_NAME, sParam_Version):
    url = f"https://ping.logitec.ma/YAPO_UPDATE/GET_RPI_CONFIG/{sRPI_NAME}/{sParam_Version}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            config_data = response.json()
            return config_data
        else:
            print(f"Error: Unable to retrieve data, status {response.status_code}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def ensure_directory_exists(path):
    if path:
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"Directory created: {path}")
        else:
            print(f"Directory already exists: {path}")

def ensure_autostart_file(autostart_path, working_dir, script_path, main_file_url):
    if not os.path.exists(autostart_path):
        # Prepare the autostart content without using f-strings to avoid SyntaxError
        autostart_content = """#!/bin/bash
echo "Initial Start"
WORKDIR={working_dir}
MAINFILE=$WORKDIR/main.py
CONFIG_FILE=$WORKDIR/config.py
# Create WORKDIR if it doesn't exist
if [ ! -d "$WORKDIR" ]; then
  mkdir -p "$WORKDIR"
  echo "Created directory: $WORKDIR"
else
  echo "Directory $WORKDIR exists."
fi
cd {working_dir}
# Check if MAINFILE (main.py) exists, if not, download or create it
if [ ! -f "$MAINFILE" ]; then
  echo "Downloading or creating main.py"
  wget -O "$MAINFILE" "{main_file_url}" || {{

    echo "Could not download main.py, creating a default one."
    cat <<EOT >> "$MAINFILE"
# main.py - Auto-generated script
import os
import time

def main():
    print("Program started")

if __name__ == '__main__':
    main()
EOT
  }}
else
  echo "main.py already exists: $MAINFILE"
fi
while true
do
    sudo /usr/bin/python3 {script_path}
    sleep 1
done
$SHELL""".format(
    working_dir=working_dir,
    main_file_url=main_file_url,
    script_path=script_path
)

        with open(autostart_path, "w") as file:
            file.write(autostart_content)
        os.chmod(autostart_path, 0o755)
        print(f"Autostart script created: {autostart_path}")
    else:
        print(f"Autostart script already exists: {autostart_path}")

def ensure_config_file(config_file, config_file_url):
    # Check if the config.py file exists, if not, download it from the URL
    if not os.path.exists(config_file):
        print(f"Downloading config file from {config_file_url}")
        try:
            response = requests.get(config_file_url)
            if response.status_code == 200:
                with open(config_file, "w") as file:
                    file.write(response.text)
                print(f"Config file saved: {config_file}")
            else:
                print(f"Error: Unable to download config file, status {response.status_code}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print(f"Config file already exists: {config_file}")

def ensure_main_file(main_file_path, download_url):
    if not os.path.exists(main_file_path):
        try:
            response = requests.get(download_url)
            response.raise_for_status()
            with open(main_file_path, 'wb') as file:
                file.write(response.content)
            print(f"Main file downloaded from {download_url}")
        except Exception as e:
            print(f"Error downloading main.py: {e}")
    else:
        print(f"Main file already exists: {main_file_path}")

def download_file(url, filename):
    if not url == "" and filename != "":
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()  # Raise an error for bad responses

            # Write the content to a file
            with open(filename, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            logging.info("Downloaded file: %s", filename)
            return "OK"
        except requests.exceptions.HTTPError as http_err:
            # print(f"HTTP error occurred while downloading: {http_err}")
            logging.error("HTTP error while downloading: %s", http_err)
        except Exception as err:
            # print(f"An error occurred while downloading: {err}")
            logging.error("An error occurred while downloading: %s", err)
        return "NG"
    else:
        return "NG"

def chmod_file(file_path):
    cmd = f"sudo chmod o+rwx {file_path}"
    logging.info("Executing command: %s", cmd)
    if platform.system() == "Linux":
        try:
            qm_status, qm_result = sp.getstatusoutput(cmd)
            if qm_status == 0:
                # print("OK")
                logging.info("File permissions updated successfully.")
            else:
                logging.error("Failed to update permissions: %s", qm_result)
                # print("NG")
        except Exception as e:
            logging.error("Error updating file permissions: %s", e)

def setup_autostart_terminal(autostart_file_path):
    """
    Configure the LXDE-pi autostart file to disable screen blanking and run the autostart.sh script in LXTerminal.
    """
    autostart_file = "/etc/xdg/lxsession/LXDE-pi/autostart"
    try:
        # Check if the autostart file exists
        if os.path.exists(autostart_file):
            with open(autostart_file, "r") as file:
                lines = file.readlines()

            # Commands to disable screen blanking and run the autostart script
            new_lines = [
#                 "@xset s noblank\n",
#                 "@xset s off\n",
#                 "@xset -dpms\n",
                f"@lxterminal --command=\"{autostart_file_path}\"\n"
            ]
            read_cmd = f"sudo cat {autostart_file}"
            result = sp.getoutput(read_cmd)
            # Check if the new lines are already in the file
            if any(line in lines for line in new_lines):
                print("Autostart configuration already set.")
            else:
                # If the new lines are not already in the file, append them using sudo
                for line in new_lines:
                    append_cmd = f"echo '{line.strip()}' | sudo tee -a {autostart_file}"
                    sp.run(append_cmd, shell=True)
                    print(f"Added line to autostart: {line.strip()}")
                # Append the new lines to the autostart file
#                 with open(autostart_file, "a") as file:
#                     file.writelines(new_lines)
                print(f"Autostart configuration added to {autostart_file}.")
        else:
            print(f"Autostart file {autostart_file} does not exist.")
    
    except Exception as e:
        print(f"Error setting up autostart terminal: {e}")
        
def generate_config_file(config_data):
    if config_data.get('sOK_NG') == 'OK':
        autostart_file_path = config_data.get('autostart_file', '/home/pi/WORKDIR/autostart.sh')
        working_directory = config_data.get('WORKDIR', '/home/pi/WORKDIR')
        main_script_path = config_data.get('main_file', '/home/pi/WORKDIR/main.py')
        main_file_url = config_data.get('main_file_url', 'https://upload.yapo.ovh/update/main.py')
        config_file   = config_data.get('config_file', '/home/pi/WORKDIR/config.py')
        config_file_url = config_data.get('config_file_url', 'https://upload.yapo.ovh/update/config.py')
        autostart_file_url = config_data.get('autostart_file_url', 'https://upload.yapo.ovh/update/autostart.sh')
        # Automate the setup
        ensure_directory_exists(working_directory)
        ensure_autostart_file(
            autostart_file_path,
            working_directory,
            main_script_path,
            main_file_url
        )
        # Ensure config.py is present or download it
        ensure_config_file(config_file, config_file_url)
        # Ensure main.py is present or download it
        ensure_main_file(main_script_path,  main_file_url)
        
        UPDATE_AUTO_RUN = config_data.get('UPDATE_AUTO_RUN')
        print("Update AUTO_RUN: ",UPDATE_AUTO_RUN)
        if UPDATE_AUTO_RUN == "Y":
            # Download Config file
            #file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), fname)
            download_file(autostart_file_url, autostart_file_path)
            chmod_file(autostart_file_path)
            setup_autostart_terminal(autostart_file_path)
        else:
            setup_autostart_terminal(autostart_file_path)
            
        UPDATE_MAIN = config_data.get('UPDATE_MAIN')
        print("UPDATE MAIN: ",UPDATE_MAIN)
        if UPDATE_MAIN == "Y":
            # Download Config file
            #file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), fname)
            download_file(main_file_url, main_script_path)
        
        UPDATE_WS = config_data.get('UPDATE_WS')
        print("UPDATE WS: ",UPDATE_WS)
        if UPDATE_WS == "Y":
            ws_file_url = config_data.get('web_service_file_url')
            ws_file_path =os.path.join(working_directory, "WebServiceClient.py")
            print(ws_file_path)
            download_file(ws_file_url, ws_file_path)
        
        UPDATE_CFG = config_data.get('UPDATE_CFG')
        print("Update CFG: ",UPDATE_CFG)
        if UPDATE_CFG == "Y":
            # Download Config file
            #file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), fname)
            download_file(config_file_url, config_file)
        else:
            # Création Config.py
            config = {
                "Position": get_rpi_hostname(),  # CRA-/COU
                "Status_VFD": config_data['st_etat_lcd']['lcd_1'],
                # True => Pour activer le VFD, False =>pour désactiver VFD
                "Port": config_data['st_etat_lcd']['PORT_USB'],  # Le numéro du Port Série utilisé
                "URL_webservice": config_data['web_service_url'],  # URL Yapo pour le webservice
                "URL_ping": config_data['web_ping_url'],  # URL Yapo pour le ping
                "Port_relais": config_data['st_etat_relais']['Port_relais'],  # Numéro BCM du GPIO utilisé pour le relais du Raspberry Pi
                "TypeCRTL": config_data['TypeCRTL'],  # Type de contrôle
                "Version": config_data['Version'],  # Version du programme
                "CheckForUpdates": UPDATE_MAIN,  # Contrôle des mises à jour
                "ENABLE_SERVICE": 0,  # Activation du service ping
                "ENABLE_RELAIS":  1, # Activation des relais,
                "MODE_PRG": config_data['Mode_PRG']  # Activation des relais
            }

            with open(config_file, 'w') as file:
                file.write("config = " + json.dumps(config, indent=4))
            print(f"Config file generated successfully at: {config_file}")
            
    else:
        print("Configuration data indicates an error: sOK_NG is not 'OK'.")
```
# Main execution
```shell
sRPI_NAME = get_rpi_hostname()
sParam_Version = "24.10.11.0"
config_data = GET_RPI_CONFIG(sRPI_NAME, sParam_Version)

if config_data:
    print("Configuration Data Retrieved:", config_data)
    generate_config_file(config_data)
else:
    print("Failed to retrieve configuration data.")
```
#Step 2: Create the systemd Service File
Open a terminal and run:
```shell
sudo nano /etc/systemd/system/auto_config_service.service
```

# Download main file
```shell
    wget https://upload.yapo.ovh/update/main.py
```
# AUTOSTART_TERMINAL
```shell
  sudo nano  /home/pi/dir/autostart
```

## autostart file
```shell
 #!/bin/bash
 echo "Initial Start"
 echo "Reload"
 # shellcheck disable=SC2164
 cd  /home/pi/dir/
 while true
 	do
 	 sudo /usr/bin/python3 /home/pi/dir/main.py
 	 sleep 1
 	done
 $SHELL
```

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

