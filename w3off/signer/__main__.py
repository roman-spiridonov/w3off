import os
import sys
from w3off.signer.w3signer import main

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main()
