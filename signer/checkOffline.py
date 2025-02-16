import socket
import requests


def checkOffline():
    return not (_checkActualConnection()) and not (_checkDNS())


def _checkActualConnection():
    try:
        requests.head("https://www.google.com", timeout=3)
        requests.head("http://example.com", timeout=3)
        requests.head("https://yandex.ru", timeout=3)
        return True  # Online
    except (requests.ConnectionError, requests.exceptions.ReadTimeout):
        return False  # Offline


def _checkDNS(host="8.8.8.8", port=53, timeout=1):
    """
    Host: 8.8.8.8 (google-public-dns-a.google.com)
    OpenPort: 53/tcp
    Service: domain (DNS/TCP)
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        return True  # Online
    except socket.error as ex:
        print(ex)
        return False  # Offline
    finally:
        sock.close()


if __name__ == "__main__":
    print("Both checks should return True to be considered offline: ")
    print(not _checkActualConnection())
    print(not _checkDNS())
