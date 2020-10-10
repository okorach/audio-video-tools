
import sys
import mediatools.media_config as mediaconf

try:
    mediaconf.load()
except FileNotFoundError as e:
    print(str(e))
    sys.exit(3)
