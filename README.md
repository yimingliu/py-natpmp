## Introduction
py-natpmp is a NAT-PMP (Network Address Translation Port Mapping Protocol) library and testing client in Python. The client allows you to set up dynamic port mappings on NAT-PMP compatible routers. Thus this is a means for dynamic NAT traversal with routers that talk NAT-PMP. In practical terms, this is basically limited to the newer Apple AirPort base stations and the AirPort Express, which have support for this protocol.

In any case, this library puts a thin layer of Python abstraction over the NAT-PMP protocol, version 0, as specified by the NAT-PMP draft standard.

## Library
The library provides a set of high-level and low-level functions to interact via the NAT-PMP protocol. The functions map_port and get_public_address provide the two high-level functions offered by NAT-PMP. Responses are stored as Python objects.

## Client
To use the client, grab it and the above library. Make sure you have the library in the same directory as the client script or otherwise on your Python instance’s sys.path. Invoke the client on the command-line (Terminal.app) as python natpmp-client.py [-u] [-l lifetime] [-g gateway_addr] public_port private_port.

For example:

- `python natpmp-client.py -u -l 1800 60009 60009`
    Create a mapping for the public UDP port 60009 to the private UDP port 60009 for 1,800 seconds (30 minutes)
- `python natpmp-client.py 60010 60010`
    Create a mapping for the public TCP port 60010 to the private TCP port 60010
- `python natpmp-client.py -g 10.0.1.1 60011 60022`
    Explicitly instruct the gateway router 10.0.1.1 to create the TCP mapping from 60010 to 60022

Remember to turn off your firewall for those ports that you map.

## Caveats
This is an incomplete implementation of the specification.  When the router reboots, all dynamic mappings are lost.  The specification provides for notification packets to be sent by the router to each client when this happens.  There is no support in this library and client to monitor for such notifications, nor does it implement a daemon process to do so.  The specification recommends queuing requests – that is, all NAT-PMP interactions should happen serially.  This simple library does not queue requests – if you abuse it with multithreading, it will send those requests in parallel and possibly overwhelm the router.

The library will attempt to auto-detect your NAT gateway. This is done via a popen to netstat on BSDs/Darwin and ip on Linux. This is likely to fail miserably, depending on how standard the output is. In the library, a keyword argument is provided to override the default and specify your own gateway address. In the client, use the -g switch to manually specify your gateway.

## License & Disclaimer
In abstract, this little package is licensed under the new BSD license.  I keep copyright on the code, but let you use it to do whatever you want, including putting it into your own software.  Do not hold me responsible if things blow up -- you're the one downloading random code from the Internet.

### In legalese

Copyright: 2008-2023 Yiming Liu, all rights reserved.

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
