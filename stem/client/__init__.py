# Copyright 2018, Damian Johnson and The Tor Project
# See LICENSE for licensing information

"""
Interaction with a Tor relay's ORPort. :class:`~stem.client.Relay` is
a wrapper for :class:`~stem.socket.RelaySocket`, much the same way as
:class:`~stem.control.Controller` provides higher level functions for
:class:`~stem.socket.ControlSocket`.

.. versionadded:: 1.7.0

::

  split - splits bytes into substrings

  Field - Packable and unpackable datatype.
    |- Size - Field of a static size.
    |- Address - Relay address.
    |- Certificate - Relay certificate.
    |
    |- pack - encodes content
    |- unpack - decodes content
    +- pop - decodes content with remainder

.. data:: AddrType (enum)

  Form an address takes.

  ===================== ===========
  AddressType           Description
  ===================== ===========
  **HOSTNAME**          relay hostname
  **IPv4**              IPv4 address
  **IPv6**              IPv6 address
  **ERROR_TRANSIENT**   temporarily error retrieving address
  **ERROR_PERMANENT**   permanent error retrieving address
  **UNKNOWN**           unrecognized address type
  ===================== ===========

.. data:: RelayCommand (enum)

  Command concerning streams and circuits we've established with a relay.
  Commands have two characteristics...

  * **forward/backward**: **forward** commands are issued from the orgin,
    whereas **backward** come from the relay

  * **stream/circuit**: **steam** commands concern an individual steam, whereas
    **circuit** concern the entire circuit we've established with a relay

  ===================== ===========
  RelayCommand          Description
  ===================== ===========
  **BEGIN**             begin a stream (**forward**, **stream**)
  **DATA**              transmit data (**forward/backward**, **stream**)
  **END**               end a stream (**forward/backward**, **stream**)
  **CONNECTED**         BEGIN reply (**backward**, **stream**)
  **SENDME**            ready to accept more cells (**forward/backward**, **stream/circuit**)
  **EXTEND**            extend the circuit through another relay (**forward**, **circuit**)
  **EXTENDED**          EXTEND reply (**backward**, **circuit**)
  **TRUNCATE**          remove last circuit hop (**forward**, **circuit**)
  **TRUNCATED**         TRUNCATE reply (**backward**, **circuit**)
  **DROP**              ignorable no-op (**forward/backward**, **circuit**)
  **RESOLVE**           request DNS resolution (**forward**, **stream**)
  **RESOLVED**          RESOLVE reply (**backward**, **stream**)
  **BEGIN_DIR**         request descriptor (**forward**, **steam**)
  **EXTEND2**           ntor EXTEND request (**forward**, **circuit**)
  **EXTENDED2**         EXTEND2 reply (**backward**, **circuit**)
  **UNKNOWN**           unrecognized command
  ===================== ===========

.. data:: CertType (enum)

  Relay certificate type.

  ===================== ===========
  CertType              Description
  ===================== ===========
  **LINK**              link key certificate certified by RSA1024 identity
  **IDENTITY**          RSA1024 Identity certificate
  **AUTHENTICATE**      RSA1024 AUTHENTICATE cell link certificate
  **UNKNOWN**           unrecognized certificate type
  ===================== ===========

.. data:: CloseReason (enum)

  Reason a relay is closed.

  ===================== ===========
  CloseReason           Description
  ===================== ===========
  **NONE**              no reason given
  **PROTOCOL**          tor protocol violation
  **INTERNAL**          internal error
  **REQUESTED**         client sent a TRUNCATE command
  **HIBERNATING**       relay suspended, trying to save bandwidth
  **RESOURCELIMIT**     out of memory, sockets, or circuit IDs
  **CONNECTFAILED**     unable to reach relay
  **OR_IDENTITY**       connected, but its OR identity was not as expected
  **OR_CONN_CLOSED**    connection that was carrying this circuit died
  **FINISHED**          circuit has expired for being dirty or old
  **TIMEOUT**           circuit construction took too long
  **DESTROYED**         circuit was destroyed without a client TRUNCATE
  **NOSUCHSERVICE**     request was for an unknown hidden service
  **UNKNOWN**           unrecognized reason
  ===================== ===========
"""

import io
import struct

import stem.util.connection
import stem.util.enum

from stem.util import _hash_attr

ZERO = '\x00'

__all__ = [
  'cell',
]

AddrType = stem.util.enum.UppercaseEnum(
  'HOSTNAME',
  'IPv4',
  'IPv6',
  'ERROR_TRANSIENT',
  'ERROR_PERMANENT',
  'UNKNOWN',
)

RelayCommand = stem.util.enum.Enum(
  ('BEGIN', 'RELAY_BEGIN'),
  ('DATA', 'RELAY_DATA'),
  ('END', 'RELAY_END'),
  ('CONNECTED', 'RELAY_CONNECTED'),
  ('SENDME', 'RELAY_SENDME'),
  ('EXTEND', 'RELAY_EXTEND'),
  ('EXTENDED', 'RELAY_EXTENDED'),
  ('TRUNCATE', 'RELAY_TRUNCATE'),
  ('TRUNCATED', 'RELAY_TRUNCATED'),
  ('DROP', 'RELAY_DROP'),
  ('RESOLVE', 'RELAY_RESOLVE'),
  ('RESOLVED', 'RELAY_RESOLVED'),
  ('BEGIN_DIR', 'RELAY_BEGIN_DIR'),
  ('EXTEND2', 'RELAY_EXTEND2'),
  ('EXTENDED2', 'RELAY_EXTENDED2'),
  ('UNKNOWN', 'UNKNOWN'),
)

CertType = stem.util.enum.UppercaseEnum(
  'LINK',
  'IDENTITY',
  'AUTHENTICATE',
  'UNKNOWN',
)

CloseReason = stem.util.enum.UppercaseEnum(
  'NONE',
  'PROTOCOL',
  'INTERNAL',
  'REQUESTED',
  'HIBERNATING',
  'RESOURCELIMIT',
  'CONNECTFAILED',
  'OR_IDENTITY',
  'OR_CONN_CLOSED',
  'FINISHED',
  'TIMEOUT',
  'DESTROYED',
  'NOSUCHSERVICE',
  'UNKNOWN',
)


def split(content, size):
  """
  Simple split of bytes into two substrings.

  :param bytes content: string to split
  :param int size: index to split the string on

  :returns: two value tuple with the split bytes
  """

  return content[:size], content[size:]


class Field(object):
  """
  Packable and unpackable datatype.
  """

  def pack(self):
    """
    Encodes field into bytes.

    :returns: **bytes** that can be communicated over Tor's ORPort

    :raises: **ValueError** if incorrect type or size
    """

    raise NotImplementedError('Not yet available')

  @classmethod
  def unpack(cls, packed):
    """
    Decodes bytes into a field of this type.

    :param bytes packed: content to decode

    :returns: instance of this class

    :raises: **ValueError** if packed data is malformed
    """

    unpacked, remainder = cls.pop(packed)

    if remainder:
      raise ValueError('%s is the wrong size for a %s field' % (repr(packed), cls.__name__))

    return unpacked

  @staticmethod
  def pop(packed):
    """
    Decodes bytes as this field type, providing it and the remainder.

    :param bytes packed: content to decode

    :returns: tuple of the form (unpacked, remainder)

    :raises: **ValueError** if packed data is malformed
    """

    raise NotImplementedError('Not yet available')

  def __eq__(self, other):
    return hash(self) == hash(other) if isinstance(other, Field) else False

  def __ne__(self, other):
    return not self == other


class Size(Field):
  """
  Unsigned `struct.pack format
  <https://docs.python.org/2/library/struct.html#format-characters>` for
  network-order fields.

  ====================  ===========
  Pack                  Description
  ====================  ===========
  CHAR                  Unsigned char (1 byte)
  SHORT                 Unsigned short (2 bytes)
  LONG                  Unsigned long (4 bytes)
  LONG_LONG             Unsigned long long (8 bytes)
  ====================  ===========
  """

  def __init__(self, name, size, pack_format):
    self.name = name
    self.size = size
    self.format = pack_format

  @staticmethod
  def pop(packed):
    raise NotImplementedError("Use our constant's unpack() and pop() instead")

  def pack(self, content):
    if not isinstance(content, int):
      raise ValueError('Size.pack encodes an integer, but was a %s' % type(content).__name__)

    packed = struct.pack(self.format, content)

    if self.size != len(packed):
      raise ValueError('%s is the wrong size for a %s field' % (repr(packed), self.name))

    return packed

  def unpack(self, packed):
    if self.size != len(packed):
      raise ValueError('%s is the wrong size for a %s field' % (repr(packed), self.name))

    return struct.unpack(self.format, packed)[0]

  def pop(self, packed):
    return self.unpack(packed[:self.size]), packed[self.size:]


class Address(Field):
  """
  Relay address.

  :var stem.client.AddrType type: address type
  :var int type_int: integer value of the address type
  :var unicode value: address value
  :var bytes value_bin: encoded address value
  """

  TYPE_FOR_INT = {
    0: AddrType.HOSTNAME,
    4: AddrType.IPv4,
    6: AddrType.IPv6,
    16: AddrType.ERROR_TRANSIENT,
    17: AddrType.ERROR_PERMANENT,
  }

  INT_FOR_TYPE = dict((v, k) for k, v in TYPE_FOR_INT.items())

  def __init__(self, addr_type, value):
    if isinstance(addr_type, int):
      self.type = Address.TYPE_FOR_INT.get(addr_type, AddrType.UNKNOWN)
      self.type_int = addr_type
    elif addr_type in AddrType:
      self.type = addr_type
      self.type_int = Address.INT_FOR_TYPE.get(addr_type, -1)
    else:
      raise ValueError('Invalid address type: %s' % addr_type)

    if self.type == AddrType.IPv4:
      if stem.util.connection.is_valid_ipv4_address(value):
        self.value = value
        self.value_bin = ''.join([Size.CHAR.pack(int(v)) for v in value.split('.')])
      else:
        if len(value) != 4:
          raise ValueError('Packed IPv4 addresses should be four bytes, but was: %s' % repr(value))

        self.value = '.'.join([str(Size.CHAR.unpack(value[i])) for i in range(4)])
        self.value_bin = value
    elif self.type == AddrType.IPv6:
      if stem.util.connection.is_valid_ipv6_address(value):
        self.value = stem.util.connection.expand_ipv6_address(value).lower()
        self.value_bin = ''.join([Size.SHORT.pack(int(v, 16)) for v in self.value.split(':')])
      else:
        if len(value) != 16:
          raise ValueError('Packed IPv6 addresses should be sixteen bytes, but was: %s' % repr(value))

        self.value = ':'.join(['%04x' % Size.SHORT.unpack(value[i * 2:(i + 1) * 2]) for i in range(8)])
        self.value_bin = value
    else:
      # The spec doesn't really tell us what form to expect errors to be. For
      # now just leaving the value unset so we can fill it in later when we
      # know what would be most useful.

      self.value = None
      self.value_bin = value

  def pack(self):
    cell = io.BytesIO()
    cell.write(Size.CHAR.pack(self.type_int))
    cell.write(Size.CHAR.pack(len(self.value_bin)))
    cell.write(self.value_bin)
    return cell.getvalue()

  @staticmethod
  def pop(content):
    if not content:
      raise ValueError('Payload empty where an address was expected')
    elif len(content) < 2:
      raise ValueError('Insuffient data for address headers')

    addr_type, content = Size.CHAR.pop(content)
    addr_length, content = Size.CHAR.pop(content)

    if len(content) < addr_length:
      raise ValueError('Address specified a payload of %i bytes, but only had %i' % (addr_length, len(content)))

    addr_value, content = split(content, addr_length)

    return Address(addr_type, addr_value), content

  def __hash__(self):
    return _hash_attr(self, 'type_int', 'value_bin')


class Certificate(Field):
  """
  Relay certificate as defined in tor-spec section 4.2.

  :var stem.client.CertType type: certificate type
  :var int type_int: integer value of the certificate type
  :var bytes value: certificate value
  """

  TYPE_FOR_INT = {
    1: CertType.LINK,
    2: CertType.IDENTITY,
    3: CertType.AUTHENTICATE,
  }

  INT_FOR_TYPE = dict((v, k) for k, v in TYPE_FOR_INT.items())

  def __init__(self, cert_type, value):
    if isinstance(cert_type, int):
      self.type = Certificate.TYPE_FOR_INT.get(cert_type, CertType.UNKNOWN)
      self.type_int = cert_type
    elif cert_type in CertType:
      self.type = cert_type
      self.type_int = Certificate.INT_FOR_TYPE.get(cert_type, -1)
    else:
      raise ValueError('Invalid certificate type: %s' % cert_type)

    self.value = value

  def pack(self):
    cell = io.BytesIO()
    cell.write(Size.CHAR.pack(self.type_int))
    cell.write(Size.SHORT.pack(len(self.value)))
    cell.write(self.value)
    return cell.getvalue()

  @staticmethod
  def pop(content):
    cert_type, content = Size.CHAR.pop(content)
    cert_size, content = Size.SHORT.pop(content)

    if cert_size > len(content):
      raise ValueError('CERTS cell should have a certificate with %i bytes, but only had %i remaining' % (cert_size, len(content)))

    cert_bytes, content = split(content, cert_size)
    return Certificate(cert_type, cert_bytes), content

  def __hash__(self):
    return _hash_attr(self, 'type_int', 'value')


setattr(Size, 'CHAR', Size('CHAR', 1, '!B'))
setattr(Size, 'SHORT', Size('SHORT', 2, '!H'))
setattr(Size, 'LONG', Size('LONG', 4, '!L'))
setattr(Size, 'LONG_LONG', Size('LONG_LONG', 8, '!Q'))
