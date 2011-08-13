# (c) 2011 Canonical Ltd.
# Author: Martin Pitt <martin.pitt@ubuntu.com>
# License: GPL v2 or later

import logging, subprocess

from jockey.oslib import OSLib
from jockey.handlers import KernelModuleHandler

# dummy stub for xgettext
def _(x): return x

class Nouveau3DHandler(KernelModuleHandler):
    '''Handler for experimental Nouveau 3D support'''

    def __init__(self, ui):
        KernelModuleHandler.__init__(self, ui, 'nouveau', 
            name=_('Experimental 3D support for NVIDIA cards'),
            description=_('This driver provides a highly experimental 3D acceleration for NVIDIA graphics cards, as a free alternative to the proprietary driver.\n\n'
                          'You need to restart your desktop session after installation.')
	    )
        self.package = 'libgl1-mesa-dri-experimental'

    def id(self):
        '''Return an unique identifier of the handler.'''

        return 'xorg:' + self.module

    def available(self):
        r = KernelModuleHandler.available(self)
        if r is not None:
            return r
        return self.module_loaded(self.module)
