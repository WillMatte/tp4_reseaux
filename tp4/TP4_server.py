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

import glosocket
import gloutils


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
        self._logged_users = {}
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

    def _create_account(
        self, client_soc: socket.socket, payload: gloutils.AuthPayload
    ) -> gloutils.GloMessage:
        """
        Crée un compte à partir des données du payload.

        Si les identifiants sont valides, créee le dossier de l'utilisateur,
        associe le socket au nouvel l'utilisateur et retourne un succès,
        sinon retourne un message d'erreur.
        """
        print("Creating account!")
        return gloutils.GloMessage()

    def _login(
        self, client_soc: socket.socket, payload: gloutils.AuthPayload
    ) -> gloutils.GloMessage:
        """
        Vérifie que les données fournies correspondent à un compte existant.

        Si les identifiants sont valides, associe le socket à l'utilisateur et
        retourne un succès, sinon retourne un message d'erreur.
        """
        return gloutils.GloMessage()

    def _logout(self, client_soc: socket.socket) -> None:
        """Déconnecte un utilisateur."""

    def _get_email_list(self, client_soc: socket.socket) -> gloutils.GloMessage:
        """
        Récupère la liste des courriels de l'utilisateur associé au socket.
        Les éléments de la liste sont construits à l'aide du gabarit
        SUBJECT_DISPLAY et sont ordonnés du plus récent au plus ancien.

        Une absence de courriel n'est pas une erreur, mais une liste vide.
        """
        return gloutils.GloMessage()

    def _get_email(
        self, client_soc: socket.socket, payload: gloutils.EmailChoicePayload
    ) -> gloutils.GloMessage:
        """
        Récupère le contenu de l'email dans le dossier de l'utilisateur associé
        au socket.
        """
        return gloutils.GloMessage()

    def _get_stats(self, client_soc: socket.socket) -> gloutils.GloMessage:
        """
        Récupère le nombre de courriels et la taille du dossier et des fichiers
        de l'utilisateur associé au socket.
        """
        return gloutils.GloMessage()

    def _send_email(self, payload: gloutils.EmailContentPayload) -> gloutils.GloMessage:
        """
        Détermine si l'envoi est interne ou externe et:
        - Si l'envoi est interne, écris le message tel quel dans le dossier
        du destinataire.
        - Si le destinataire n'existe pas, place le message dans le dossier
        SERVER_LOST_DIR et considère l'envoi comme un échec.
        - Si le destinataire est externe, considère l'envoi comme un échec.

        Retourne un messange indiquant le succès ou l'échec de l'opération.
        """
        return gloutils.GloMessage()

    def run(self):
        """Point d'entrée du serveur."""
        waiters: list[socket.socket] = []
        while True:
            # Select readable sockets
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
                        self._logout(waiter)
                        continue

                match json.loads(data):
                    case {"header": gloutils.Headers.AUTH_LOGIN}:
                        self._login(waiter, data)
                    case {"header": gloutils.Headers.AUTH_REGISTER}:
                        self._create_account(waiter, data)
                #Handle sockets
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
