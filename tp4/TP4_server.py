"""\
GLO-2000 Travail pratique 4 - Serveur 2025
Noms et numéros étudiants:
-
-
-
"""

import hashlib
import hmac
import json
import os
import select
import socket
import sys
import re
import time
from datetime import datetime

import glosocket
import gloutils

from tp4utils import parse_packet, BadPacket

def create_packet(header: gloutils.Headers, payload=None) -> gloutils.GloMessage:
    return gloutils.GloMessage(
        header=header,
        payload=payload
    )

def create_error_packet(message: str) -> gloutils.GloMessage:
    return create_packet(gloutils.Headers.ERROR, gloutils.ErrorPayload(error_message=message))

def create_ok_packet() -> gloutils.GloMessage:
    return create_packet(gloutils.Headers.OK)


class Server:
    """Serveur mail @glo2000.ca 2025."""

    def __init__(self) -> None:
        """
        Prépare le socket du serveur `_server_socket`
        et le met en mode écoute.

        Prépare les attributs suivants:
        - `_client_socs` une liste des sockets clients.
        - `_logged_users` un dictionnaire associant chaque
            socket client à un nom d'utilisateur.

        S'assure que les dossiers de données du serveur existent.
        """
        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind(("127.0.0.1", gloutils.APP_PORT))
            self._server_socket.listen()
            print(f"Listening on port {gloutils.APP_PORT}")
        except socket.error:
            sys.exit(1)

        self._client_socs: list[socket.socket] = []
        self._logged_users: dict[socket.socket, str] = {}
        self._queued_packets: dict[socket.socket, list[gloutils.GloMessage]] = {} 
        self.validate_directories()


    def validate_directories(self) -> None:
        if not os.path.isdir(f"./{gloutils.SERVER_DATA_DIR}"):
            os.mkdir(f"./{gloutils.SERVER_DATA_DIR}")
        if not os.path.isdir(f"./{gloutils.SERVER_DATA_DIR}/{gloutils.SERVER_LOST_DIR}"):
            os.mkdir(f"./{gloutils.SERVER_DATA_DIR}/{gloutils.SERVER_LOST_DIR}")

    def cleanup(self) -> None:
        """Ferme toutes les connexions résiduelles."""
        for client_soc in self._client_socs:
            client_soc.close()
        self._server_socket.close()

    def _accept_client(self) -> None:
        """Accepte un nouveau client."""
        print("new client accepted")
        new_soc, _ = self._server_socket.accept()
        self._client_socs.append(new_soc)

    def _remove_client(self, client_soc: socket.socket) -> None:
        """Retire le client des structures de données et ferme sa connexion."""
        if client_soc in self._client_socs:
            print("removing from client_socs")
            self._client_socs.remove(client_soc)
        if client_soc in self._logged_users:
            print("removing from logged_users")
            self._logged_users.pop(client_soc)
        if client_soc in self._queued_packets:
            self._queued_packets.pop(client_soc)
        print("closing socket")
        client_soc.close()


    def _create_account(
        self, client_soc: socket.socket, payload: gloutils.AuthPayload
    ) -> gloutils.GloMessage:
        """
        Crée un compte à partir des données du payload.

        Si les identifiants sont valides, créee le dossier de l'utilisateur,
        associe le socket au nouvel l'utilisateur et retourne un succès,
        sinon retourne un message d'erreur.
        """
        print("Creating account")
        error = {}
        if not self._validate_username(payload['username']):
            error['username_error'] = \
                "Le nom d'utilisateur ne peut contenir que des  caractères alphanumériques, _, . ou -"
        if self._has_user_dir(payload['username']):
            error['username_error'] = \
                "Le nom d'utilisateur est déjà utilisé"
        if not self._validate_password_content(payload['password']):
            error['password_error'] = \
                "Le mot de passe doit avoir une taille supérieure ou égale à 10 caractères, " \
                "contenir au moins un chiffre, une minuscule et une majuscule."
        if error:
            joined = "; ".join(error.values())
            print(error)
            print("error in account creation")
            return create_error_packet(joined)

        username = payload['username'].lower()
        self._create_user_dir(username)
        self._hash_and_save_password(username, payload['password'])
        self._logged_users[client_soc] = username
        print("account creation successful")
        return create_ok_packet()

    @staticmethod
    def _validate_username(username:str) -> bool:
        pattern = re.compile(r'^[A-Za-z0-9_.-]+$')
        return bool(pattern.fullmatch(username))

    @staticmethod
    def _validate_password_content(password:str) -> bool:
        pattern = re.compile(r'^(?=.*[0-9])(?=.*[a-z])(?=.*[A-Z]).{10,}$')
        return bool(pattern.fullmatch(password))

    @staticmethod
    def _create_user_dir(username:str) -> None:
        os.mkdir(f"./{gloutils.SERVER_DATA_DIR}/{username}")

    def _has_user_dir(self, username: str) -> bool:
        if username is None:
            return False
        lower_username = username.lower()
        path = os.path.join(f"./{gloutils.SERVER_DATA_DIR}", lower_username)
        return os.path.isdir(path)


    def _list_user_emails(self, username: str) -> list[tuple[str, dict, float]]:
        """Return list of (path, payload, mtime) for every email file in user's folder, sorted newest first."""
        user_dir = f"./{gloutils.SERVER_DATA_DIR}/{username}"
        results: list[tuple[str, dict, float]] = []
        if not os.path.isdir(user_dir):
            return results
        for fname in os.listdir(user_dir):
            if fname == f"{gloutils.PASSWORD_FILENAME}.txt":
                continue
            full = os.path.join(user_dir, fname)
            if not os.path.isfile(full):
                continue
            try:
                with open(full, 'r', encoding='utf-8') as fh:
                    payload = json.load(fh)
                mtime = os.path.getmtime(full)
                results.append((full, payload, mtime))
            except (json.JSONDecodeError, OSError, ValueError):
                continue
        results.sort(key=lambda x: x[2], reverse=True)
        return results

    def _hash_and_save_password(self, username: str, password: str):
        password = self._hash_password(password)
        with open(f"./{gloutils.SERVER_DATA_DIR}/{username}/{gloutils.PASSWORD_FILENAME}.txt", "w") as file:
            file.write(password)

    @staticmethod
    def _hash_password(password: str):
        return hashlib.sha3_512(password.encode("utf-8")).hexdigest()

    def _login(
        self, client_soc: socket.socket, payload: gloutils.AuthPayload
    ) -> gloutils.GloMessage:
        """
        Vérifie que les données fournies correspondent à un compte existant.

        Si les identifiants sont valides, associe le socket à l'utilisateur et
        retourne un succès, sinon retourne un message d'erreur.
        """
        print("user loggin in")
        error = {}
        username = payload.get("username")
        if not self._has_user_dir(payload['username']):
            error['username_error'] = "Le nom d'utilisateur n'existe pas"
            print("login error")
            return create_error_packet(error['username_error'])
        username = username.lower()
        if not self._validate_password(username, payload['password']):
            error['password_error'] = "Mauvais mot de passe"
            print("login error")
            return create_error_packet(error['password_error'])
        self._logged_users[client_soc] = username
        print("login successful")
        return create_ok_packet()

    def _validate_password(self, username: str, password: str) -> bool:
        password = self._hash_password(password)
        with open(f"{gloutils.SERVER_DATA_DIR}/{username}/{gloutils.PASSWORD_FILENAME}.txt", "r") as file:
            stored_password = file.read().strip()
        return password == stored_password

    def _logout(self, client_soc: socket.socket) -> None:
        """Déconnecte un utilisateur."""
        if client_soc in self._logged_users:
            self._logged_users.pop(client_soc)
        return create_ok_packet()


    def _get_email_list(self, client_soc: socket.socket) -> gloutils.GloMessage:
        username = self._logged_users[client_soc]
        user_dir = f"./{gloutils.SERVER_DATA_DIR}/{username}"
        if not os.path.isdir(user_dir):
            payload = gloutils.EmailListPayload(email_list=[])
            return create_packet(gloutils.Headers.OK, payload)

        email_files = self._list_user_emails(username)

        email_files.sort(key=lambda x: x[2], reverse=True)

        email_list = []
        for i, (path, payload, mtime) in enumerate(email_files, start=1):
            email_list.append(gloutils.SUBJECT_DISPLAY.format(
                number=i,
                sender=payload.get('sender'),
                subject=payload.get('subject'),
                date=payload.get('date')
            ))

        payload = gloutils.EmailListPayload(email_list=email_list)
        return create_packet(gloutils.Headers.OK, payload)

        """
        Récupère la liste des courriels de l'utilisateur associé au socket.
        Les éléments de la liste sont construits à l'aide du gabarit
        SUBJECT_DISPLAY et sont ordonnés du plus récent au plus ancien.

        Une absence de courriel n'est pas une erreur, mais une liste vide.
        """

    def _get_email(
        self, client_soc: socket.socket, payload: gloutils.EmailChoicePayload
    ) -> gloutils.GloMessage:
        """
        Récupère le contenu de l'email dans le dossier de l'utilisateur associé
        au socket.
        """
        username = self._logged_users[client_soc]

        email_files = self._list_user_emails(username)

        email_files.sort(key=lambda x: x[2], reverse=True)

        choice = None
        try:
            choice = int(payload.get('choice'))
        except (TypeError, ValueError):
            return create_error_packet("Choix invalide.")

        if choice < 1 or choice > len(email_files):
            return create_error_packet("Choix invalide.")

        _, chosen_payload, _ = email_files[choice-1]
        return create_packet(gloutils.Headers.OK, gloutils.EmailContentPayload(
            sender=chosen_payload.get('sender'),
            destination=chosen_payload.get('destination'),
            subject=chosen_payload.get('subject'),
            date=chosen_payload.get('date'),
            content=chosen_payload.get('content')
        ))

    def _get_stats(self, client_soc: socket.socket) -> gloutils.GloMessage:
        """
        Récupère le nombre de courriels et la taille du dossier et des fichiers
        de l'utilisateur associé au socket.
        """
        username = self._logged_users[client_soc]
        user_dir = f"./{gloutils.SERVER_DATA_DIR}/{username}"
        if not os.path.isdir(user_dir):
            return create_packet(gloutils.Headers.OK, gloutils.StatsPayload(count=0, size=0))

        files = [f for f in os.listdir(user_dir) if f != f"{gloutils.PASSWORD_FILENAME}.txt"]
        count = 0
        size = 0
        for f in files:
            full = os.path.join(user_dir, f)
            if os.path.isfile(full):
                count += 1
                size += os.path.getsize(full)

        return create_packet(gloutils.Headers.OK, gloutils.StatsPayload(count=count, size=size))

    def _send_email(self, payload: gloutils.EmailContentPayload) -> gloutils.GloMessage:
        print(payload)
        destination = payload.get('destination')
        if not destination or '@' not in destination:
            return create_error_packet("Adresse destinataire invalide.")

        username, domain = destination.split('@', 1)
        if domain.lower() != gloutils.SERVER_DOMAIN:
            return create_error_packet("Destinataire externe non supporté.")
        
        username = username.lower()

        if self._has_user_dir(username):
            folder = f"./{gloutils.SERVER_DATA_DIR}/{username}"
            filename = f"{int(time.time()*1000)}.json"
            full = os.path.join(folder, filename)
            try:
                with open(full, 'w', encoding='utf-8') as fh:
                    json.dump(payload, fh)
            except (OSError, TypeError):
                return create_error_packet("Impossible d'écrire le message dans le dossier du destinataire.")
            return create_ok_packet()
        else:
            filename = f"{int(time.time()*1000)}.json"
            full = os.path.join(f"./{gloutils.SERVER_DATA_DIR}/{gloutils.SERVER_LOST_DIR}", filename)
            try:
                with open(full, 'w', encoding='utf-8') as fh:
                    json.dump(payload, fh)
            except (OSError, TypeError):
                return create_error_packet("Impossible d'enregistrer le message perdu.")
            return create_error_packet("Destinataire introuvable. Courriel placé dans le dossier LOST.")

        

        """
        Détermine si l'envoi est interne ou externe et:
        - Si l'envoi est interne, écris le message tel quel dans le dossier
        du destinataire.
        - Si le destinataire n'existe pas, place le message dans le dossier
        SERVER_LOST_DIR et considère l'envoi comme un échec.
        - Si le destinataire est externe, considère l'envoi comme un échec.

        Retourne un messange indiquant le succès ou l'échec de l'opération.
        """

    
    def _queue_packet(self, client: socket.socket, message: gloutils.GloMessage):
        glosocket.send_mesg(client, json.dumps(message))

    def _handle_packet(self, client: socket.socket, packet: str) -> None:
        authenticated_handlers = {
            gloutils.Headers.INBOX_READING_REQUEST: lambda client, _ : self._get_email_list(client),
            gloutils.Headers.INBOX_READING_CHOICE:  lambda client, packet : self._get_email(client, gloutils.EmailChoicePayload(packet.get("payload"))),
            gloutils.Headers.EMAIL_SENDING:          lambda client, packet : self._send_email(gloutils.EmailContentPayload(packet.get("payload"))),
            gloutils.Headers.STATS_REQUEST:         lambda client, _ : self._get_stats(client),
            gloutils.Headers.AUTH_LOGOUT:           lambda client, _ : self._logout(client),
        }

        anonymous_handlers = {
            gloutils.Headers.AUTH_REGISTER:         lambda client, packet : self._create_account(client, gloutils.AuthPayload(packet.get("payload"))),
            gloutils.Headers.AUTH_LOGIN:            lambda client, packet : self._login(client, gloutils.AuthPayload(packet.get("payload")))
        }

        try:
            parsed_packet = parse_packet(packet)
            header = parsed_packet.get("header")

            if header == gloutils.Headers.BYE:
                self._remove_client(client)
                return

            if client in self._logged_users:
                if header in authenticated_handlers:
                    self._queue_packet(client, authenticated_handlers[header](client, parsed_packet))
                elif header in anonymous_handlers:
                    self._queue_packet(client, create_error_packet("Utilisateur déjà authentifié"))
                else:
                    self._queue_packet(client, create_error_packet("Requête inconnue."))
            else:
                if header in anonymous_handlers:
                    self._queue_packet(client, anonymous_handlers[header](client, parsed_packet))
                elif header in authenticated_handlers:
                    self._queue_packet(client, create_error_packet("Utilisateur non authentifié."))
                else:
                    self._queue_packet(client, create_error_packet("Requête inconnue."))
        except (BadPacket, ValueError):
            self._queue_packet(client, create_error_packet("Packet invalide."))

    def run(self):
        """Point d'entrée du serveur."""

        authenticated_methods_handlers = {
            gloutils.Headers.INBOX_READING_REQUEST: self._get_email_list,
            gloutils.Headers.INBOX_READING_CHOICE: self._get_email,
            gloutils.Headers.AUTH_LOGOUT: self._logout,
            gloutils.Headers.STATS_REQUEST: self._get_stats
        }

        waiters: list[socket.socket] = []
        while True:
            result = select.select(self._client_socs + [self._server_socket], [], [])
            waiters.extend(result[0])
            for waiter in waiters:
                waiters.pop(0)
                if waiter is self._server_socket:
                    self._accept_client()

                else:
                    try:
                        data = glosocket.recv_mesg(waiter)
                    except glosocket.GLOSocketError:
                        self._remove_client(waiter)
                        continue

                    self._handle_packet(waiter, data)
                    pass


# NE PAS ÉDITER PASSÉ CE POINT
# NE PAS ÉDITER PASSÉ CE POINT
# NE PAS ÉDITER PASSÉ CE POINT
# NE PAS ÉDITER PASSÉ CE POINT


def _main() -> int:
    server = Server()
    try:
        server.run()
    except KeyboardInterrupt:
        server.cleanup()
    return 0


if __name__ == "__main__":
    sys.exit(_main())
