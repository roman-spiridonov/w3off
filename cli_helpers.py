import os
import sys


def supports_color():
    """
    Returns True if the running system's terminal supports color, and False
    otherwise.
    """
    plat = sys.platform
    supported_platform = plat != "Pocket PC" and (plat != "win32" or "ANSICON" in os.environ)
    # isatty is not always implemented, #6223.
    is_a_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    return supported_platform and is_a_tty


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


if not supports_color():
    bcolors.HEADER = ""
    bcolors.OKBLUE = ""
    bcolors.OKCYAN = ""
    bcolors.OKGREEN = ""
    bcolors.WARNING = ""
    bcolors.FAIL = ""
    bcolors.ENDC = ""
    bcolors.BOLD = ""
    bcolors.UNDERLINE = ""


# https://stackoverflow.com/questions/45169947/how-should-i-get-a-user-to-indicate-a-file-path-to-a-directory-in-a-command-line
def normalize_path(p):
    """Function to uniformly return a real, absolute filesystem path."""
    # ~/directory -> /home/user/directory
    p = os.path.expanduser(p)
    # A/.//B -> A/B
    p = os.path.normpath(p)
    # Resolve symbolic links
    p = os.path.realpath(p)
    # Ensure path is absolute
    p = os.path.abspath(p)
    return p
