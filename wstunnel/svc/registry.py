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
from wstunnel import winreg
import logging
import errno

__author__ = 'fabio'
logger = logging.getLogger(__name__)


def get_reg_values(key, root_key=winreg.HKEY_LOCAL_MACHINE):  # pragma: no cover
    """
    Given a key name, return a dictionary of its values.
    """
    key_handle = None
    count = 0
    result = {}
    try:
        logger.debug("Reading key {}".format(key))
        key_handle = winreg.OpenKey(root_key, key)
        while True:
            values = winreg.EnumValue(key_handle, count)
            logger.debug("Found {}".format(values))
            count += 1
            result.update({values[0]: values[1]})
    except WindowsError as error:
        if error.errno == errno.EINVAL:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Returning {} values".format(
                    len(result)))
            return result
        else:
            logger.error(error)
            raise error
    finally:
        if key_handle:
            logger.debug("Closing key handle for key {}".format(key))
            key_handle.Close()
