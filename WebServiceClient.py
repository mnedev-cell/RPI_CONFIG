import requests
from urllib.parse import urlparse
import logging
import os


class WServiceClient:
    """Classe responsable de la communication avec le service web."""

    def __init__(self, url):
        self.url = url

    def send_data(self, data):
        """Envoie des données au service web et retourne la réponse."""
        print(f"Envoi de la requête à {self.url} avec les données {data}")
        try:
            print("Url WS: ", self.url)
            response = requests.post(self.url, json=data, timeout=5)
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"Une erreur HTTP s'est produite : {http_err}")
            return None
        except requests.exceptions.ConnectionError as conn_err:
            logging.error(f"Erreur de connexion : {conn_err}")
            return None
        except requests.exceptions.Timeout as timeout_err:
            logging.error(f"Erreur de délai d'attente : {timeout_err}")
            return None
        except requests.exceptions.RequestException as err:
            logging.error(f"Une erreur s'est produite : {err}")
            return None
        else:
            try:
                return response.json()
            except ValueError:
                logging.error("Erreur : La réponse n'était pas un JSON valide.")
                return None

    def ping(self, ping_url):
        """Ping le serveur spécifié et retourne True s'il est en ligne, False sinon."""
        try:
            response = os.system("ping -c 1 " + ping_url)
            if response == 0:
                return True
            else:
                return False
        except requests.exceptions.RequestException:
            return False

    def extract_ip(self):
        try:
            # utilisation de urlparse pour décomposer l'URL
            parsed_url = urlparse(self.url)
            domain = parsed_url.netloc.split(":")[0]  # enlève le numéro de port si existant
            # vérifie si le domaine semble être une adresse IP
            parts = domain.split('.')
            if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
                print(domain)
                return domain
            else:
                raise ValueError("The domain in the URL does not appear to be an IP address")

        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def ping_get(self, ping):
        try:
            response = requests.get(ping)
            response.raise_for_status()  # Génère une exception HTTP si le statut n'est pas 200

        except requests.exceptions.HTTPError as errh:
            print("Erreur HTTP:", errh)
            return False
        except requests.exceptions.ConnectionError as errc:
            print("Erreur de connexion:", errc)
            return False
        except requests.exceptions.Timeout as errt:
            print("Timeout:", errt)
            return False
        except requests.exceptions.RequestException as err:
            print("Erreur:", err)
            return False
        else:
            return True

    def MAJ_PASSAGE_TICKET(self, cb, timeout=3, mode_prg="T",
                           user_agent="default_user_agent", sBadge_Ticket_Type="BILLET", stypeCRTL="SAL"):
        headers = {'User-Agent': user_agent, 'Content-Type': 'application/json', 'Accept': 'application/json'}

        try:
            # Determine mode
            mode_exp = "T"
            # Build request URL
            httprequrl = f"{self.url}/{cb}/TODAY/{user_agent}/{mode_exp}/{sBadge_Ticket_Type}/{stypeCRTL}"
            # Make HTTP GET request
            response = requests.get(httprequrl, headers=headers, verify=False, timeout=timeout)
            if response.status_code != 200:
                print(f"Request URL: {httprequrl}")
                return "", "pas200"

            return response, "online"

        except requests.Timeout as e:

            logging.error(f"Timeout error in MAJ_PASSAGE_TICKET: {e}")

            return "", "timeout"

        except requests.ConnectionError as e:

            logging.error(f"Connection error in MAJ_PASSAGE_TICKET: {e}")

            return "", "connection_error"

        except requests.HTTPError as e:

            logging.error(f"HTTP error in MAJ_PASSAGE_TICKET: {e}")

            return "", "http_error"

        except Exception as e:

            logging.error(f"Unexpected error in MAJ_PASSAGE_TICKET: {e}")

            return "", "exception"
