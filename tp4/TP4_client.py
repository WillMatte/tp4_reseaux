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

from typing import Union

class ErrorResponse(Exception):
    pass

class BadResponse(Exception):
    pass

class BadChoice(Exception):
    pass

def castString(str_val: str, type_val: type) -> type:
    try:
        message = json.loads(str_val)
        return message
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        raise BadResponse(f"Reponse invalide du serveur (Type attendu: {type_val}): {e}")

def getServerMessage(socket: socket.socket) -> gloutils.GloMessage:

    res = glosocket.recv_mesg(socket)

    message: gloutils.GloMessage = castString(res, gloutils.GloMessage)
    match message.get("header"):
        case gloutils.Headers.OK:
            return message
        case gloutils.Headers.ERROR:
            errorPayload = gloutils.ErrorPayload (message.get("payload"))
            errorMessage = errorPayload.get("error_message")
            if errorMessage != None:
                raise ErrorResponse(errorMessage)
            else:
                raise ErrorResponse("Erreur inconnue, veuillez réessayer.")
        case _ as e:
            raise BadResponse(f"Entête invalide de la part du serveur: {e}")

def getChoice(choicesNumber: int) -> int:
    choice = input(f"Entrez votre choix [1-{choicesNumber}]: ")
    try:
        number = int(choice)
        if number < 1 or number > choicesNumber:
            raise BadChoice(f"Invalid choice: {number}")
        return number
    except ValueError:
        raise BadChoice(f"Invalid choice: \"{choice}\"")

class Client:
    """Client pour le serveur mail @glo2000.ca 2025."""

    def __init__(self, destination: str) -> None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._username: str = ""
        try: 
            host_ip = socket.gethostbyname(destination)
        except socket.gaierror: 
            print("there was an error resolving the host", file=sys.stderr)
            sys.exit(1) 

        try:
            self._socket.connect((host_ip, gloutils.APP_PORT))
        except socket.error:
            print("Une erreur est survenue lors de la connexion au serveur.", file=sys.stderr)
            exit(1)
        print(f"Connected to server {host_ip} with port {gloutils.APP_PORT}")

    
    def _authenticate(self, header: Union[gloutils.Headers.AUTH_LOGIN, gloutils.Headers.AUTH_REGISTER]):
        username = input("Entrez un nom d'utilisateur: ")
        password = getpass.getpass("Entrez un mot de passe: ")

        message = gloutils.GloMessage(
            header=header,
            payload=gloutils.AuthPayload(
                username=username,
                password=password
         )
        )

        glosocket.send_mesg(self._socket, json.dumps(message))
        
        getServerMessage(self._socket)
        
        self._username = username

    def _register(self) -> None:
        self._authenticate(gloutils.Headers.AUTH_REGISTER)

    def _login(self) -> None:
        self._authenticate(gloutils.Headers.AUTH_LOGIN)

    def _quit(self) -> None:
        byeMessage = gloutils.GloMessage(
            header=gloutils.Headers.BYE
        ) 

        try:
            glosocket.send_mesg(self._socket, json.dumps(byeMessage))
            self._socket.close()
        except glosocket.GLOSocketError:
            print("Une erreur est survenue lors de la fermeture de la connexion avec le serveur.", file=sys.stderr)            


    def _read_email(self) -> None:
        readMailMessage = gloutils.GloMessage(
            header=gloutils.Headers.INBOX_READING_REQUEST
        )

        glosocket.send_mesg(self._socket, json.dumps(readMailMessage))
        message = getServerMessage(self._socket)
        mailRequestPayload = gloutils.EmailListPayload(message.get("payload"))

        emailList = mailRequestPayload.get("email_list")

        if emailList == None or emailList.__len__() == 0:
            print("Vous n'avez pas encore reçu de mail.")
            return


        for i, mailInfo in enumerate(mailRequestPayload.get("email_list")):
            print(f"#{i + 1} {mailInfo}")

        choice = getChoice(emailList.__len__())

        emailChoiceMessage = gloutils.GloMessage(
            header=gloutils.Headers.INBOX_READING_CHOICE,
            payload=gloutils.EmailChoicePayload(
                choice=choice
            )
        )

        glosocket.send_mesg(self._socket, json.dumps(emailChoiceMessage))
        message = getServerMessage(self._socket)
        email = gloutils.EmailContentPayload(message.get("payload"))

        print(gloutils.EMAIL_DISPLAY.format(
            # sender=email.get("sender"),÷
            to=email.get("destination"),
            subject=email.get("subject"),
            date=email.get("date"),
            body=email.get("content")
        ))

    def _send_email(self) -> None:
        email = input("Entrez l'adresse du destinataire: ")
        subject = input("Entrez le sujet: ")
        print("Entrez le contenu du courriel, terminez la saisie avec un'.'seul sur une ligne:")
        isWritingContent = True
        content = []
        while isWritingContent:
            line = input()
            if line == ".":
                isWritingContent = False
            else:
                content.append(line)

        content = "".join(content)

        message = gloutils.GloMessage(
            header=gloutils.Headers.EMAIL_SENDING,
            payload=gloutils.EmailContentPayload(
                # sender=self._username
                destination=email,
                subject=subject,
                content=content,
                date=gloutils.get_current_utc_time()
            )
        )

        glosocket.send_mesg(self._socket, json.dumps(message))

    def _check_stats(self) -> None:
        message = gloutils.GloMessage(
            header=gloutils.Headers.STATS_REQUEST
        )

        glosocket.send_mesg(self._socket, json.dumps(message))

        res = getServerMessage(self._socket)
        payload = gloutils.StatsPayload(res.get("payload"))

        print(gloutils.STATS_DISPLAY.format(
            count=payload.get("count"),
            size=payload.get("size")
        ))

    def _logout(self) -> None:
        message = gloutils.GloMessage(
            header=gloutils.Headers.AUTH_LOGOUT
        )

        glosocket.send_mesg(self._socket, json.dumps(message))

        getServerMessage(self._socket)

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
            except BadResponse as e:
                print(e, file=sys.stderr)
            except ErrorResponse as e:
                print(e, file=sys.stderr)
            except BadChoice as e:
                print(e, file=sys.stderr)
            except EOFError:
                should_quit = True
            except ValueError:
                print("Reponse invalide du serveur.")
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
