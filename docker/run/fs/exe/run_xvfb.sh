
#!/bin/bash

set -e
# RESOLUTION=1920x1200x24
exec Xvfb -nolisten tcp "$DISPLAY" # -screen 0 $RESOLUTION
