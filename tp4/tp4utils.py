import hashlib
import hmac
import json
import os
import select
import socket
import sys
import re

import glosocket
import gloutils

class ErrorResponse(Exception):
    pass

class BadPacket(Exception):
    pass

class BadChoice(Exception):
    pass

def castString(str_val: str, type_val: type) -> type:
    try:
        message = json.loads(str_val)
        return message
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        raise BadPacket(f"Reponse invalide du serveur (Type attendu: {type_val}): {e}")

def parse_packet(packet: str) -> gloutils.GloMessage:
    return castString(packet, gloutils.GloMessage)
