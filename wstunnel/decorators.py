# -*- coding: utf-8 -*-
# Copyright (C) 2013  Fabio Falcinelli
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
__author__ = 'fabio'


class enhance_log(object):
    """
    Enables the given logger before calling the function.
    """

    def __init__(self, logger, trace=False):
        self._logger = logger
        self._trace = trace

    def __call__(self, funct):
        def wrapper(*args, **kwargs):
            self._logger.disabled = False
            #self._logger.debug("Calling method {}".format(funct.__name__))
            result = funct(*args, **kwargs)
            #self._logger.debug("Exit from method {}".format(funct.__name__))
            return result

        return wrapper
