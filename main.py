import datetime
import json
import os
import platform
import queue
import re
import signal
import sys
import threading
import traceback
from time import sleep
import subprocess as sp
import requests
import serial
#from QRCodeReader import QRCodeReader
from qr_code_reader import QRCodeReader
from relay_controller.controller import RController
#from RelayController import RController
#from WebServiceClient import WServiceClient
from wservice_client import WServiceClient
from config import config
import logging

# Global variable to control the reading loop
continue_reading = True
# CONFIG.PY
SERVICE_NAME = 'ping_service'
ENABLE_SERVICE = config['ENABLE_SERVICE']  # Set to True to enable, False to disable
ENABLE_RELAIS = config['ENABLE_RELAIS']  # Set to True to enable, False to disable
lock = threading.Lock()

def end_read(signal, frame):
    global continue_reading
    with lock:
        continue_reading = False
    print("\nLecture TERMINEE")


# Custom logging setup for colored output
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


class VfdDisplay:
    def __init__(self, port="/dev/ttyUSB0", baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                 stopbits=serial.STOPBITS_ONE, timeout=1, enabled=True):
        self.enabled = enabled
        self.ser = None
        if self.enabled:
            try:
                self.ser = serial.Serial(port=port, baudrate=baudrate, bytesize=bytesize, parity=parity,
                                         stopbits=stopbits, timeout=timeout)
                if self.ser.is_open:
                    #print("Connexion série ouverte avec succès.")
                    logging.info("Serial connection opened successfully.")
                else:
                    # print("Erreur lors de l'ouverture de la connexion série.")
                    logging.error("Error opening serial connection.")
            except serial.SerialException as e:
                # print(f"Erreur lors de la création de la connexion série: {e}")
                logging.error(f"Serial connection error: {e}")
            sleep(2)

    def write_line(self, message, line=1, column=1):
        if self.enabled and self.ser:
            self.move_cursor(line, column)
            if line == 1:
                message = self.name_port(config["Position"]) + ": " + message
            self.ser.write(message.encode())

    def clear_screen(self):
        if self.enabled and self.ser:
            self.ser.write(b'\x0C')
            sleep(0.1)

    def move_cursor(self, line, column):
        if self.enabled and self.ser:
            cursor_move_cmd = [0x1F, 0x24, column, line]
            self.ser.write(bytes(cursor_move_cmd))

    def clear_line(self, line):
        if self.enabled and self.ser:
            self.move_cursor(line, 1)  # Move the cursor to the start of the line
            self.ser.write(b' ' * 20)  # Write 20 spaces to clear the line

    def close(self):
        if self.enabled and self.ser:
            self.ser.close()

    def name_port(self, port):
        self.port = port.split("-")
        return self.port[1].strip()

    # vfd = VfdDisplay(port=config["Port"], enabled=config["Status_VFD"])
    # vfd.clear_screen()
    # vfd.write_line("MACHINE ARRETEE", line=1, column=1)
    # vfd.write_line("ESSAYEZ + TARD", line=2, column=1)


# Capture SIGINT for cleanup when the script is aborted
signal.signal(signal.SIGINT, end_read)


def process_qr_code(qr_reader, ws_client, relay_controller, vfd_display):
    global LAST_LOCAL_DATE_TIME_PY
    sleep(0.1)
    vfd_display.clear_screen()
    vfd_display.write_line("VOTRE TICKET SVP", line=1, column=1)
    codebarre = qr_reader.Read()
    if codebarre is not None:
        codebarre = codebarre.replace("#", "*")
        response, status = validate_ticket(codebarre, ws_client)        
        handle_response(response, status, relay_controller, vfd_display)
      


def validate_ticket(codebarre, ws_client):
    sBadge_Ticket_Type = "B"
    return ws_client.MAJ_PASSAGE_TICKET(codebarre, mode_prg="N", user_agent=config["Position"],
                                        sBadge_Ticket_Type=sBadge_Ticket_Type, stypeCRTL=config["TypeCRTL"])


def handle_response(response, status, relay_controller, vfd_display):
    if response and status == "online":
        response_data = json.loads(response.text)
        #sMessage = response_data['sMessage']
        sMessage = response_data[0]['sERR_MESSAGE']
        #response_data['sMessage'] = sMessage
        if "OK" in sMessage:
            logging.info("sMessage: %s", sMessage)
            grant_access(relay_controller, response_data, vfd_display)
        else:
            logging.warning("sMessage: %s", sMessage)
            deny_access(response_data, vfd_display)
    else:
        deny_access_no_response(vfd_display)
        logging.error("sMessage: %s", status)


def grant_access(relay_controller, response_data, vfd_display):
    #vfd_display.write_line(response_data['sMessage'], line=1, column=1)
    logging.info("grant_access.")
    vfd_display.write_line(response_data[0]['sERR_MESSAGE'], line=1, column=1)
    vfd_display.write_line("VOUS POUVEZ ENTRER", line=2, column=1)
    if ENABLE_RELAIS and relay_controller:
        relay_controller.activate_relay()
        
    else:
        logging.info("Relay is disabled; message displayed instead.")

    # sleep(1.5)


def deny_access(response_data, vfd_display):
    vfd_display.clear_screen()
    mServeur = response_data[0]['sERR_MESSAGE']
    mLine = mServeur
    vfd_display.write_line("STOP", line=1, column=1)
    vfd_display.write_line(mLine[:21], line=2, column=1)
    sleep(2.5)


def deny_access_no_response(vfd_display):
    vfd_display.clear_screen()
    vfd_display.write_line("STOP!!", line=1, column=1)
    vfd_display.write_line("ALLEZ A LACCEUIL SVP", line=2, column=1)
    sleep(2.5)


def get_Current_Version():
    version = config['Version']
    return version


def extract_version_and_link(text):
    # Regular expression to match Version and Link
    pattern = r"Version=(?P<version>[0-9.]+);Link=(?P<link>https?://[^\s]+)"

    match = re.search(pattern, text)
    if match:
        version = match.group('version')
        link = match.group('link')
        return version, link
    else:
        return None, None


def check_program_update(sParam_KelProgramme):
    url = f"https://ping.logitec.ma/GetVersion/{sParam_KelProgramme}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses (4xx or 5xx)
        # Assuming the API returns JSON data
        # Extracting data
        # version, link = extract_version_and_link(response.text)
        return extract_version_and_link(response.text)

    except requests.exceptions.HTTPError as http_err:
        # print(f"HTTP error occurred: {http_err}")
        logging.error("Error checking program update: %s", http_err)
    except requests.exceptions.RequestException as e:
        logging.error("Error checking program update: %s", e)
    except Exception as err:
        # print(f"An error occurred: {err}")
        logging.error("Error checking program update: %s", err)

    return None, None


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


def download_file(url, filename):
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


def write_config_module(file_path, config_data):
    with open(file_path, 'w') as file:
        file.write("config = ")
        file.write(repr(config_data))  # Use repr to write the dict format


def Check_New_Version():
    global TIME_UPDATE_PY
    current_version = get_Current_Version()
    sKelProgramme = 'main.py'  # Replace with your actual program identifier
    filename = 'main.py'
    version, link = check_program_update(sKelProgramme)
    if not version is None and link is not None:
        # print(f"New Version: {version}")
        if version > current_version:
            # print("A new version is available!")
            logging.info("New Version: %s", version)
            # Save filename in the script's directory
            filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), filename)
            logging.info("Filepath: %s", filepath)
            status = download_file(link, filepath)  # Change filename as necessary
            if status == "OK":
                # print("Téléchargement Terminé ...")
                logging.info("Download complete.")
                chmod_file(filepath)
                requests.get("https://ping.logitec.ma/YAPO_UPDATE/UPDATE_RPI_CONFIG/UPDATE_MAIN/N")

                    # # Update additional files
                    # update_files = [
                    #     ("https://upload.yapo.ovh/update/config.py", "config.py"),
                    #     ("https://upload.yapo.ovh/update/VfdDisplay.py", "VfdDisplay.py"),
                    #     ("https://upload.yapo.ovh/update/RelayController.py", "RelayController.py"),
                    #     ("https://upload.yapo.ovh/update/ping_service.py", "ping_service.py"),
                    #     ("https://upload.yapo.ovh/update/WebServiceClient.py", "WebServiceClient.py"),
                    #     ("https://upload.yapo.ovh/update/QrCodeReader.py", "QrCodeReader.py"),
                    #     ("https://upload.yapo.ovh/update/UPDATE.py", "UPDATE.py"),
                    # ]
                    #
                    # for url, fname in update_files:
                    #     file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), fname)
                    #     download_file(url, file_path)

                # Restart the program
                logging.info("Restarting the program...")
                # os.execv(sys.executable, ['python'] + sys.argv)  # Restart without rebooting
                os.execl(sys.executable, sys.executable, *sys.argv)

                # Restart the system
                # if platform.system() == "Linux":
                #     print("The operating system is Linux.")
                #     time.sleep(5)
                #     os.system('sudo reboot')  # Restart
        else:
            # print("You are using the latest version.")
            logging.info("You are using the latest version: %s", current_version)
            TIME_UPDATE_PY = 1500
    else:
        # print("Mise à jour ? : Réponse Incorrecte ...")
        # print("Failed to check for updates.")
        logging.warning("Update check failed: Incorrect response.")

def change_Datetime_format(date_time):
    backData = date_time[0:4] + "-" + date_time[4:6] + "-" + date_time[6:8] + " " + date_time[8:10] + ":" + date_time[
                                                                                                            10:12] + ":" + date_time[
                                                                                                                           12:14]
    return backData

def Send_last_passage(last_passage):
    global continue_reading
    try:
        requests.packages.urllib3.disable_warnings()
        url_yapo_Send_last_passage =config["URL_ping"]+"/"+config["Position"]+"/"
        my_req = requests.get(url_yapo_Send_last_passage + last_passage, verify=False, timeout=5)  # Timeout
        if my_req.status_code != 200:
            print("Ping YAPO : ", "Echec, code : ", my_req.status_code)
        else:
            rep = my_req.text            
            if not rep.startswith("<html"):
                if my_req.text != "":
                    #print("Ping YAPO : ", my_req.text[:3], change_Datetime_format(my_req.text[3:]))
                    print("Ping YAPO: [", change_Datetime_format(last_passage), "] ")
                else:
                    print("Ping YAPO : ", my_req.text)  # OK : + Date et Heure du serveur YAPO
                # my_req.text = 'REBOOT'
                if my_req.text == 'REBOOT':
                    continue_reading = False
                    print("MACHINE REBOOT", "ESSAYEZ + TARD")
                    time.sleep(10)
                    os.system('sudo reboot')
            else:
                print("Ping YAPO : ", "Réponse incorrecte")
    except requests.exceptions.ConnectionError as errc:
        print("Ping YAPO : Error Connecting ", datetime.datetime.utcnow().strftime("%H:%M:%S"))
        logging.error(f"Connection error in Ping YAPO: {errc}")
    except requests.exceptions.Timeout as errt:
        logging.error(f"Timeout error in Ping YAPO: {errt}")
    except Exception as e:
        logging.error(f"Unexpected error in Ping YAPO: {e}")
        
def main_loop(qr_reader, ws_client, relay_controller, vfd_display):
    global continue_reading  # Use the global variable here
    global LAST_LOCAL_DATE_TIME_PY
    TIME_UPDATE_PY = 1500
    LAST_LOCAL_DATE_TIME_MAJ = datetime.datetime.now()
    LAST_LOCAL_DATE_TIME_PY = datetime.datetime.now()
    # Loop while continue_reading is True
    while continue_reading:
        try:
            sleep(0.1)
            if config["CheckUpdates"] == "Y" and (
                    datetime.datetime.now() - LAST_LOCAL_DATE_TIME_MAJ).total_seconds() >= TIME_UPDATE_PY:
                LAST_LOCAL_DATE_TIME_MAJ = datetime.datetime.now()
                # print("LAST LOCAL DATETIME UPDATE AT : ", LAST_LOCAL_DATE_TIME_MAJ.strftime("%H:%M:%S"))
                logging.info("LAST LOCAL DATETIME UPDATE AT: %s", LAST_LOCAL_DATE_TIME_MAJ.strftime("%H:%M:%S"))
                p_maj = threading.Thread(name='p_maj', target=Check_New_Version)
                p_maj.start()
                p_maj.join(timeout=5)
            
            if config["CheckPing"] == "Y" and (datetime.datetime.now() - LAST_LOCAL_DATE_TIME_PY).total_seconds() >= 10:
                LAST_LOCAL_DATE_TIME_PY = datetime.datetime.now()
                last_passage = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                pLast_pass = threading.Thread(name='pLast_pass', target=Send_last_passage, args=(last_passage,))
                pLast_pass.start()
                pLast_pass.join(timeout=5)
            process_qr_code(qr_reader, ws_client, relay_controller, vfd_display)

        except KeyboardInterrupt:
            logging.info("KeyboardInterrupt received, stopping...")
            continue_reading = False  # Set the flag to exit the loop
        except Exception as e:
            logging.error("An unexpected error occurred in main_loop: %s", e)
            continue_reading = False  # Optionally break on other exceptions
            # break  # Optionally break on other exceptions
            traceback.print_exc()

# Service Manager Integration
def check_service_status(service_name):
    """Check the status of a systemd service."""
    try:
        result = sp.run(['sudo', 'systemctl', 'status', service_name],
                        stdout=sp.PIPE, stderr=sp.PIPE, text=True)
        if 'Active: active' in result.stdout:
            print(f"{service_name} is running.")
        elif 'inactive' in result.stdout:
            print(f"{service_name} is not running.")
        else:
            print(f"Unknown status for {service_name}.")
    except Exception as e:
        print(f"Error checking service status: {e}")
        sys.exit(1)


def enable_service(service_name):
    """Enable and start the service."""
    try:
        sp.run(['sudo', 'systemctl', 'enable', service_name], check=True)
        sp.run(['sudo', 'systemctl', 'start', service_name], check=True)
        print(f"{service_name} has been enabled and started.")
    except Exception as e:
        print(f"Error enabling service: {e}")


def disable_service(service_name):
    """Disable and stop the service."""
    try:
        sp.run(['sudo', 'systemctl', 'disable', service_name], check=True)
        sp.run(['sudo', 'systemctl', 'stop', service_name], check=True)
        print(f"{service_name} has been disabled and stopped.")
    except Exception as e:
        print(f"Error disabling service: {e}")


def manage_service():
    """Checks the status and manages the ping_service based on CONFIG.PY."""
    logging.info("Checking and managing service status based on configuration...")

    # Check the current status of the service
    check_service_status(SERVICE_NAME)

    # Enable or disable the service based on the config
    if ENABLE_SERVICE:
        logging.info(f"Enabling and starting {SERVICE_NAME}...")
        enable_service(SERVICE_NAME)
    else:
        logging.info(f"Disabling and stopping {SERVICE_NAME}...")
        disable_service(SERVICE_NAME)


if __name__ == '__main__':
    # Service management at the start
    if ENABLE_SERVICE:
        manage_service()

    if ENABLE_RELAIS:
        port_relais = int(config["Port_relais"])
        relay_controller = RController(config["Port_relais"],port_relais )
        logging.info("RelayController initialized.")
        #relay_controller.activate_relay()
    else:
        relay_controller = None
        logging.info("RelayController is disabled.")

    # Initial setup code remains unchanged
    ws_client = WServiceClient(config["URL_webservice"])
    qr_reader = QRCodeReader(queue.Queue())
    vfd = VfdDisplay(port=config["Port"], enabled=config["Status_VFD"])

    # Initialisation
    vfd.clear_screen()
    vfd.write_line("Bonjour", line=1, column=1)
    vfd.write_line("Patientez SVP...", line=2, column=1)

    # Trigger the update check based on the new config option

    if config["CheckUpdates"]:
        p_maj = threading.Thread(name='p_maj', target=Check_New_Version)
        p_maj.start()
        p_maj.join(timeout=5)
        
    else:
        version = get_Current_Version()
        logging.info("You are using the latest version: %s", version)
        
    if config["CheckPing"]:
        last_passage = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        pLast_pass = threading.Thread(name='pLast_pass', target=Send_last_passage, args=(last_passage,)).start()
        
    try:
        main_loop(qr_reader, ws_client, relay_controller, vfd)
    except KeyboardInterrupt:
        logging.info("Program interrupted by user. Stopping QR code reader...")
        # qr_reader.stop()  # Signal the QR code reader to stop
    except Exception as e:
        # print("An exception occurred: ", e)
        logging.error("An exception occurred: %s", e)
        traceback.print_exc()
    finally:
        if vfd:
            vfd.close()
        logging.info("Exiting the program.")
        sys.exit()  # Ensure the program exits cleanly

# # Logging the program stop
logging.error("program stopped")
os.execl(sys.executable, sys.executable, *sys.argv)
