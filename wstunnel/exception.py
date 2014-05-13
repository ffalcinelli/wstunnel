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


class ChainedException(Exception):
    """
    An exception which could be caused by another one
    """

    def __init__(self, message, *args, **kwargs):
        cause = kwargs.get("cause", None)
        if cause:
            message = "%s, caused by %s" % (message, repr(cause))

        super(ChainedException, self).__init__(message)


class EndpointNotAvailableException(ChainedException):
    """
    Exception raised when the endpoint is not available (most likely tunnel server side is down)
    """

    def __init__(self, message="Endpoint is not available", *args, **kwargs):
        super(EndpointNotAvailableException, self).__init__(message, *args, **kwargs)


class MappedServiceNotAvailableException(ChainedException):
    """
    Exception raised when the destination service is not available (most likely tunnel server side is up but the
    service is trying to remap does not respond)
    """

    def __init__(self, message="Mapped service is not available", *args, **kwargs):
        super(MappedServiceNotAvailableException, self).__init__(message, *args, **kwargs)
