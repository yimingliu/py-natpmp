#!/usr/bin/env python

"""NAT-PMP client library

Provides functions to interact with NAT-PMP gateways implementing version 0
of the NAT-PMP draft specification.

This version does not completely implement the draft standard.
* It does not provide functionality to listen for address change packets. 
* It does not have a proper request queuing system, meaning that
multiple requests may be issued in parallel, against spec recommendations.

For more information on NAT-PMP, see the NAT-PMP draft specification:

http://files.dns-sd.org/draft-cheshire-nat-pmp.txt

Requires Python 2.3 or later.
Tested on Python 2.5, 2.6 against Apple AirPort Express.

0.2.2 - changed gateway autodetect, per github issue #1.  thanks to jirib
0.2 - changed useException to use_exception, responseDataClass to response_data_class parameters in function calls for consistency
0.1 - repackaged via setuptools.  Fixed major bug in gateway detection.  Experimental gateway detection support for Windows 7.  Python 2.6 testing.
0.0.1.2 - NT autodetection code.  Thanks to roee shlomo for the gateway detection regex!
0.0.1.1 - Removed broken mutex code
0.0.1   - Initial release

"""

__version__ = "0.2"
__license__ = """Copyright (c) 2008-2010, Yiming Liu, All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.
* The names of the author and contributors may not be used to endorse or promote products
  derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 'AS IS'
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE."""

__author__ = "Yiming Liu <http://www.yimingliu.com/>"

import struct, socket, select, time, platform
import sys, os, re

NATPMP_PORT = 5351

NATPMP_RESERVED_VAL = 0

NATPMP_PROTOCOL_UDP = 1
NATPMP_PROTOCOL_TCP = 2

NATPMP_GATEWAY_NO_VALID_GATEWAY = -10
NATPMP_GATEWAY_NO_SUPPORT = -11
NATPMP_GATEWAY_CANNOT_FIND = -12

NATPMP_RESULT_SUCCESS = 0 # Success
NATPMP_RESULT_UNSUPPORTED_VERSION = 1 # Unsupported Version
NATPMP_RESULT_NOT_AUTHORIZED = 2 # Not Authorized/Refused/NATPMP turned off
NATPMP_RESULT_NETWORK_FAILURE = 3 # Network Failure
NATPMP_RESULT_OUT_OF_RESOURCES = 4 # can not create more mappings
NATPMP_RESULT_UNSUPPORTED_OPERATION = 5 # not a supported opcode
# all remaining results are fatal errors

NATPMP_ERROR_DICT = {
                NATPMP_RESULT_SUCCESS:"No error.",
                NATPMP_RESULT_UNSUPPORTED_VERSION:"The protocol version specified is unsupported.",
                NATPMP_RESULT_NOT_AUTHORIZED:"The operation was refused.  NAT-PMP may be turned off on gateway.",
                NATPMP_RESULT_NETWORK_FAILURE:"There was a network failure.  The gateway may not have an IP address.",# Network Failure
                NATPMP_RESULT_OUT_OF_RESOURCES:"The NAT-PMP gateway is out of resources and cannot create more mappings.", # can not create more mappings
                NATPMP_RESULT_UNSUPPORTED_OPERATION:"The NAT-PMP gateway does not support this operation", # not a supported opcode
                NATPMP_GATEWAY_NO_SUPPORT:'The gateway does not support NAT-PMP',
                NATPMP_GATEWAY_NO_VALID_GATEWAY:'No valid gateway address was specified.',
                NATPMP_GATEWAY_CANNOT_FIND:'Cannot automatically determine gateway address.  Must specify manually.'
              }


class NATPMPRequest(object):
    """Represents a basic NAT-PMP request.  This currently consists of the
       1-byte fields version and opcode.
       
       Other requests are derived from NATPMPRequest.
    """
    retry_increment = 0.250 # seconds

    def __init__(self, version, opcode):
        self.version = version
        self.opcode = opcode

    def toBytes(self):
        """Converts the request object to a byte string."""
        return struct.pack('!BB', self.version, self.opcode)

class PublicAddressRequest(NATPMPRequest):
    """Represents a NAT-PMP request to the local gateway for a public address.
       As per the specification, this is a generic request with the opcode = 0.
    """
    def __init__(self, version=0):
        NATPMPRequest.__init__(self, version, 0)

class PortMapRequest(NATPMPRequest):
    """Represents a NAT-PMP request to the local gateway for a port mapping.
       As per the specification, this request extends NATPMPRequest with
       the fields private_port, public_port, and lifetime.  The first two
       are 2-byte unsigned shorts, and the last is a 4-byte unsigned integer.
    """
    def __init__(self, protocol, private_port, public_port, lifetime=3600, version=0):
        NATPMPRequest.__init__(self, version, protocol)
        self.private_port = private_port
        self.public_port = public_port
        self.lifetime = lifetime

    def toBytes(self):
        s= NATPMPRequest.toBytes(self) + struct.pack('!HHHI', NATPMP_RESERVED_VAL, self.private_port, self.public_port, self.lifetime)  
        return s

class NATPMPResponse(object):
    """Represents a generic NAT-PMP response from the local gateway.  The
       generic response has fields for version, opcode, result, and secs
       since last epoch (last boot of the NAT gateway).  As per the
       specification, the opcode is offset by 128 from the opcode of
       the original request.
    """
    def __init__(self, version, opcode, result, sec_since_epoch):
        self.version = version
        self.opcode = opcode
        self.result = result
        self.sec_since_epoch = sec_since_epoch
        
    def __str__(self):
        return "NATPMPResponse(%d, %d, %d, $d)" % (self.version, self.opcode, self.result, self.sec_since_epoch)

class PublicAddressResponse(NATPMPResponse):
    """Represents a NAT-PMP response from the local gateway to a
       public-address request.  It has one additional 4-byte field
       containing the IP returned.
       
       The member variable ip contains the Python-friendly string form, while
       ip_int contains the same in the original 4-byte unsigned int.
    """
    def __init__(self, bytes):
        version, opcode, result, sec_since_epoch, self.ip_int = struct.unpack("!BBHII", bytes)
        NATPMPResponse.__init__(self, version, opcode, result, sec_since_epoch)
        self.ip = socket.inet_ntoa(bytes[8:8+4])
        #self.ip  = socket.inet_ntoa(self.ip_bytes)

    def __str__(self):
        return "PublicAddressResponse: version %d, opcode %d (%d), result %d, ssec %d, ip %s" % (self.version, self.opcode, self.result, self.sec_since_epoch, self.ip)

class PortMapResponse(NATPMPResponse):
    """Represents a NAT-PMP response from the local gateway to a
       public-address request.  The response contains the private port,
       public port, and the lifetime of the mapping in addition to typical
       NAT-PMP headers.  Note that the port mapping assigned is
       NOT NECESSARILY the port requested (see the specification
       for details).
    """
    def __init__(self, bytes):
        version, opcode, result, sec_since_epoch, self.private_port, self.public_port, self.lifetime = struct.unpack('!BBHIHHI', bytes)
        NATPMPResponse.__init__(self, version, opcode, result, sec_since_epoch)
    
    def __str__(self):
        return "PortMapResponse: version %d, opcode %d (%d), result %d, ssec %d, private_port %d, public port %d, lifetime %d" % (self.version, self.opcode, self.opcode, self.result, self.sec_since_epoch, self.private_port, self.public_port, self.lifetime)

class NATPMPError(Exception):
    """Generic exception state.  May be used to represent unknown errors."""
    pass

class NATPMPResultError(NATPMPError):
    """Used when a NAT gateway responds with an error-state response."""
    pass

class NATPMPNetworkError(NATPMPError):
    """Used when a network error occurred while communicating
       with the NAT gateway."""
    pass

class NATPMPUnsupportedError(NATPMPError):
    """Used when a NAT gateway does not support NAT-PMP."""
    pass


def get_gateway_addr():
    """A hack to obtain the current gateway automatically, since
       Python has no interface to sysctl().
       
       This may or may not be the gateway we should be contacting.
       It does not guarantee correct results.
       
       This function requires the presence of
       netstat on the path on POSIX and NT.
    """
    addr = ""
    shell_command = 'netstat -rn'
    if os.name == "posix":
        pattern = re.compile('(?:default|0\.0\.0\.0|::/0)\s+([\w\.:]+)\s+.*UG')
    elif os.name == "nt":
        if platform.version().startswith("6.1"):
            pattern = re.compile(".*?0.0.0.0[ ]+0.0.0.0[ ]+(.*?)[ ]+?.*?\n")
        else:
            pattern = re.compile(".*?Default Gateway:[ ]+(.*?)\n")
    system_out = os.popen(shell_command, 'r').read()
    if not system_out:
        raise NATPMPNetworkError(NATPMP_GATEWAY_CANNOT_FIND, error_str(NATPMP_GATEWAY_CANNOT_FIND))
    match = pattern.search(system_out)
    if not match:
        raise NATPMPNetworkError(NATPMP_GATEWAY_CANNOT_FIND, error_str(NATPMP_GATEWAY_CANNOT_FIND))
    addr = match.groups()[0].strip()
    return addr # TODO: use real auto-detection

def error_str(result_code):
    """Takes a numerical error code and returns a human-readable
       error string.
    """
    result = NATPMP_ERROR_DICT.get(result_code)
    if not result:
        result = "Unknown fatal error."
    return result

def get_gateway_socket(gateway):
    """Takes a gateway address string and returns a non-blocking UDP
       socket to communicate with its NAT-PMP implementation on
       NATPMP_PORT.
       
       e.g. addr = get_gateway_socket('10.0.1.1')
    """
    if not gateway:
        raise NATPMPNetworkError(NATPMP_GATEWAY_NO_VALID_GATEWAY, error_str(NATPMP_GATEWAY_NO_VALID_GATEWAY))
    response_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    response_socket.setblocking(0)
    response_socket.connect((gateway, NATPMP_PORT))
    return response_socket

def get_public_address(gateway_ip=None, retry=9):
    """A high-level function that returns the public interface IP of
       the current host by querying the NAT-PMP gateway.  IP is
       returned as string.
       
       Takes two possible keyword arguments:
            gateway_ip - the IP to the NAT-PMP compatible gateway.
                         Defaults to using auto-detection function
                         get_gateway_addr()
            retry - the number of times to retry the request if unsuccessful.
                    Defaults to 9 as per specification.
    """
    if gateway_ip == None:
        gateway_ip = get_gateway_addr()
    addr = None
    addr_request = PublicAddressRequest()
    addr_response = send_request_with_retry(gateway_ip, addr_request, response_data_class=PublicAddressResponse, retry=retry)
    if addr_response.result != 0:
        #sys.stderr.write("NAT-PMP error %d: %s\n" % (addr_response.result, error_str(addr_response.result)))
        #sys.stderr.flush()
        raise NATPMPResultError(addr_response.result, error_str(addr_response.result), addr_response)
    addr = addr_response.ip
    return addr

def map_tcp_port(public_port, private_port, lifetime=3600, gateway_ip=None, retry=9, use_exception=True):
    """A high-level wrapper to map_port() that requests a mapping
       for a public TCP port on the NAT to a private TCP port on this host.
       Returns the complete response on success.
       
            public_port - the public port of the mapping requested
            private_port - the private port of the mapping requested
            lifetime - the duration of the mapping in seconds.
                       Defaults to 3600, per specification.
            gateway_ip - the IP to the NAT-PMP compatible gateway.
                        Defaults to using auto-detection function
                        get_gateway_addr()
            retry - the number of times to retry the request if unsuccessful.
                    Defaults to 9 as per specification.
            use_exception - throw an exception if an error result is
                           received from the gateway.  Defaults to True.
    """
    return map_port(NATPMP_PROTOCOL_TCP, public_port, private_port, lifetime, gateway_ip=gateway_ip, retry=retry, use_exception=use_exception)

def map_udp_port(public_port, private_port, lifetime=3600, gateway_ip=None, retry=9, use_exception=True):
    """A high-level wrapper to map_port() that requests a mapping for
       a public UDP port on the NAT to a private UDP port on this host.
       Returns the complete response on success.
       
            public_port - the public port of the mapping requested
            private_port - the private port of the mapping requested
            lifetime - the duration of the mapping in seconds.
                       Defaults to 3600, per specification.
            gateway_ip - the IP to the NAT-PMP compatible gateway.
                         Defaults to using auto-detection function
                         get_gateway_addr()
            retry - the number of times to retry the request if unsuccessful.
                    Defaults to 9 as per specification.
            use_exception - throw an exception if an error result is
                            received from the gateway.  Defaults to True.
    """
    return map_port(NATPMP_PROTOCOL_UDP, public_port, private_port, lifetime, gateway_ip=gateway_ip, retry=retry, use_exception=use_exception)

def map_port(protocol, public_port, private_port, lifetime=3600, gateway_ip=None, retry=9, use_exception=True):
    """A function to map public_port to private_port of protocol.
       Returns the complete response on success.
       
            protocol - NATPMP_PROTOCOL_UDP or NATPMP_PROTOCOL_TCP
            public_port - the public port of the mapping requested
            private_port - the private port of the mapping requested
            lifetime - the duration of the mapping in seconds.
                       Defaults to 3600, per specification.
            gateway_ip - the IP to the NAT-PMP compatible gateway.
                         Defaults to using auto-detection function
                         get_gateway_addr()
            retry - the number of times to retry the request if unsuccessful.
                    Defaults to 9 as per specification.
            use_exception - throw an exception if an error result
                            is received from the gateway.  Defaults to True.
    """
    if protocol not in [NATPMP_PROTOCOL_UDP, NATPMP_PROTOCOL_TCP]:
        raise ValueError("Must be either NATPMP_PROTOCOL_UDP or NATPMP_PROTOCOL_TCP")
    if gateway_ip == None:
        gateway_ip = get_gateway_addr()
    response = None
    port_mapping_request = PortMapRequest(protocol, private_port, public_port, lifetime)
    port_mapping_response = send_request_with_retry(gateway_ip, port_mapping_request, response_data_class=PortMapResponse, retry=retry)
    if port_mapping_response.result != 0 and use_exception:
        raise NATPMPResultError(port_mapping_response.result, error_str(port_mapping_response.result), port_mapping_response)
    return port_mapping_response


def send_request(gateway_socket, request):
    gateway_socket.sendall(request.toBytes())

def read_response(gateway_socket, timeout, responseSize=16):
    data = ""
    source_addr = ("", "")
    rlist, wlist, xlist = select.select([gateway_socket], [], [], timeout)
    if rlist:
        resp_socket = rlist[0]
        data,source_addr = resp_socket.recvfrom(responseSize)
    return data,source_addr

def send_request_with_retry(gateway_ip, request, response_data_class=None, retry=9):
    gateway_socket = get_gateway_socket(gateway_ip)
    n = 1
    data = ""
    while n <= retry and not data:
        send_request(gateway_socket, request)
        data,source_addr = read_response(gateway_socket, n * request.retry_increment)
        if source_addr[0] != gateway_ip or source_addr[1] != NATPMP_PORT:
            data = "" # discard data if source mismatch, as per specification
        n += 1
    if n >= retry and not data:
        raise NATPMPUnsupportedError(NATPMP_GATEWAY_NO_SUPPORT, error_str(NATPMP_GATEWAY_NO_SUPPORT))
    if data and response_data_class:
        data = response_data_class(data)
    return data


if __name__ == "__main__":
    addr = get_public_address()
    map_resp = map_tcp_port(62001, 62001)
    print addr
    print map_resp.__dict__
