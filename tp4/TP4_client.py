"""\
GLO-2000 Travail pratique 4 - Client 2025
Noms et numéros étudiants:
-
-
-
"""

import argparse
import getpass
import json
import socket
import sys

import glosocket
import gloutils



class Client:
    _username: str = ""
    _socket: socket.socket
    """Client pour le serveur mail @glo2000.ca 2025."""

    def __init__(self, destination: str) -> None:
        _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try: 
            host_ip = socket.gethostbyname(destination)
        except socket.gaierror: 
            print ("there was an error resolving the host", file=sys.stderr)
            sys.exit(1) 

        try:
            _socket.connect((host_ip, gloutils.APP_PORT))
        except socket.error:
            print("Une erreur est survenue lors de la connexion au serveur.", file=sys.stderr)
            exit(1)
        print(f"Connected to server {host_ip} with port {gloutils.APP_PORT}")


    def _register(self) -> None:
        username = input("Entrez un nom d'utilisateur: ")
        password = getpass.getpass("Entrez un mot de passe: ")

        payload: gloutils.AuthPayload = {
            "username": username,
            "password": password
        }

        print(payload)

        message: gloutils.GloMessage = {
            "header": gloutils.Headers.AUTH_REGISTER,
            payload: payload
        }

        glosocket.send_mesg(self._socket, message)

        """
        Demande un nom d'utilisateur et un mot de passe et les transmet au
        serveur avec l'entête `AUTH_REGISTER`.

        Si la création du compte s'est effectuée avec succès, l'attribut
        `_username` est mis à jour, sinon l'erreur est affichée.
        """

    def _login(self) -> None:
        """
        Demande un nom d'utilisateur et un mot de passe et les transmet au
        serveur avec l'entête `AUTH_LOGIN`.

        Si la connexion est effectuée avec succès, l'attribut `_username`
        est mis à jour, sinon l'erreur est affichée.
        """

    def _quit(self) -> None:
        """
        Préviens le serveur de la déconnexion avec l'entête `BYE` et ferme le
        socket du client.
        """

    def _read_email(self) -> None:
        """
        Demande au serveur la liste de ses courriels avec l'entête
        `INBOX_READING_REQUEST`.

        Affiche la liste des courriels puis transmet le choix de l'utilisateur
        avec l'entête `INBOX_READING_CHOICE`.

        Affiche le courriel à l'aide du gabarit `EMAIL_DISPLAY`.

        S'il n'y a pas de courriel à lire, l'utilisateur est averti avant de
        retourner au menu principal.
        """

    def _send_email(self) -> None:
        """
        Demande à l'utilisateur respectivement:
        - l'adresse email du destinataire,
        - le sujet du message,
        - le corps du message.

        La saisie du corps se termine par un point seul sur une ligne.

        Transmet ces informations avec l'entête `EMAIL_SENDING`.
        """

    def _check_stats(self) -> None:
        """
        Demande les statistiques au serveur avec l'entête `STATS_REQUEST`.

        Affiche les statistiques à l'aide du gabarit `STATS_DISPLAY`.
        """

    def _logout(self) -> None:
        """
        Préviens le serveur avec l'entête `AUTH_LOGOUT`.

        Met à jour l'attribut `_username`.
        """

    def run(self) -> None:
        should_quit = False

        while not should_quit:
            try:
                if not self._username:
                    print(gloutils.CLIENT_AUTH_CHOICE)
                    choice = input("Entrez votre choix [1-3]: ")
                    match (choice):
                        case "1":
                            self._register()
                        case "2":
                            self._login()
                        case "3":
                            should_quit = True
                        case _:
                            print("Choix invalide, veuillez réessayer.")
                    pass
                else:
                    print(gloutils.CLIENT_USE_CHOICES)
                    choice = input("Entrez votre choix [1-4]: ")
                    match (choice):
                        case "1":
                            self._read_email()
                        case "2":
                            self._send_email()
                        case "3":
                            self._check_stats()
                        case "4":
                            self._logout()
                        case _:
                            print("Choix invalide, veuillez réessayer.")
                    pass
            except EOFError:
                should_quit = True
            except glosocket.GLOSocketError:
                print("Connexion avec le serveur interrompue.")
                exit(1)
        self._quit()



# NE PAS ÉDITER PASSÉ CE POINT
# NE PAS ÉDITER PASSÉ CE POINT
# NE PAS ÉDITER PASSÉ CE POINT
# NE PAS ÉDITER PASSÉ CE POINT


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--destination",
        action="store",
        dest="dest",
        required=True,
        help="Adresse IP/URL du serveur.",
    )
    args = parser.parse_args(sys.argv[1:])
    client = Client(args.dest)
    client.run()
    return 0


if __name__ == "__main__":
    sys.exit(_main())
