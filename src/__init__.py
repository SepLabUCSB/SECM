### Fixing relative imports for backwards compatibility with
### unpickling old data files
### See: https://stackoverflow.com/questions/13398462/unpickling-python-objects-with-a-changed-module-path

from .modules import * # Ensures that all the modules have been loaded in their new locations *first*.
from . import modules  # imports src/modules
from .analysis import *
from . import analysis
from .gui import *
from . import gui
import sys
sys.modules['modules'] = modules  # creates a modules entry in sys.modules
sys.modules['analysis'] = analysis
sys.modules['gui'] = gui