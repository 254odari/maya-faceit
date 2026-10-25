# osc_receiver.py
# Maya Faceit Plugin - OSC Receiver
# Converted from Blender to Maya Python 3.11

"""
OSC receiver for Faceit Maya plugin.
Handles OSC message reception, parsing, and queuing.
"""

import socket
import struct
import time
import threading
from typing import List, Optional, Tuple, Any

# ============================================================
# Global Queue
# ============================================================

osc_queue: List[tuple] = []
exit_event = threading.Event()


# ============================================================
# Queue Manager
# ============================================================

class QueueManager:
    """
    Parse and queue incoming OSC messages with current timestamp.
    """
    
    def queue_data(self, msg: bytes) -> None:
        """
        Parse and queue an OSC message.
        
        Args:
            msg: Raw OSC datagram
        """
        global osc_queue
        
        try:
            address, params = _parse_datagram(msg)
            osc_queue.append([self._get_timestamp(), address, params])
            
            # Limit queue size
            if len(osc_queue) > 10000:
                osc_queue.pop(0)
                
        except Exception as e:
            print(f"Error parsing OSC message: {str(e)}")
    
    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        return time.time()
    
    def reset(self) -> None:
        """Clear the OSC queue."""
        global osc_queue
        osc_queue.clear()


# ============================================================
# OSC Receiver
# ============================================================

class Receiver:
    """
    Handle opening and closing of UDP socket.
    Receive OSC messages and add to queue.
    """
    
    def __init__(self, queue_mgr: QueueManager):
        """
        Initialize the receiver.
        
        Args:
            queue_mgr: Queue manager instance
        """
        self.sock: Optional[socket.socket] = None
        self.queue_mgr: QueueManager = queue_mgr
        self.run_thread: Optional[threading.Thread] = None
        self.enabled: bool = False
        self._running: bool = False
    
    def run(self) -> None:
        """
        Receive messages continuously.
        """
        while self._running:
            if self.sock is None:
                time.sleep(0.1)
                continue
            
            try:
                # Set socket to non-blocking with timeout
                self.sock.settimeout(0.1)
                data, _address = self.sock.recvfrom(4096)
                
                if data:
                    try:
                        self.queue_mgr.queue_data(data)
                    except Exception as e:
                        print(f"Error processing message: {str(e)}")
                        
            except socket.timeout:
                # Timeout is expected, continue
                continue
            except OSError as e:
                if "WinError 10038" in str(e):
                    # Socket was closed
                    break
                print(f"Socket error: {str(e)}")
                continue
            except Exception as e:
                print(f"Unexpected error: {str(e)}")
                continue
    
    def start(self, address: str, port: int) -> None:
        """
        Open the socket and start the thread.
        
        Args:
            address: IP address to bind to
            port: Port to bind to
        """
        if self.enabled:
            print("Receiver already running")
            return
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((address, port))
            
            print(f"Start listening to OSC on port {port}")
            
            self._running = True
            exit_event.clear()
            
            self.run_thread = threading.Thread(target=self.run, daemon=True)
            self.run_thread.start()
            self.enabled = True
            
        except OSError as e:
            print(f"Failed to start receiver: {str(e)}")
            self.enabled = False
            raise
    
    def stop(self) -> None:
        """Close the socket and end the thread."""
        self.enabled = False
        self._running = False
        
        if self.sock is not None:
            try:
                self.sock.close()
                print("Stopped listening to OSC")
            except Exception as e:
                print(f"Error closing socket: {str(e)}")
            self.sock = None
        
        exit_event.set()
        
        if self.run_thread is not None and self.run_thread.is_alive():
            try:
                self.run_thread.join(timeout=1.0)
            except Exception as e:
                print(f"Error joining thread: {str(e)}")
            self.run_thread = None


# ============================================================
# OSC Parsing Utilities
# ============================================================

class ParseError(Exception):
    """Base exception for datagram parsing errors."""
    pass


class BuildError(Exception):
    """Base exception for datagram building errors."""
    pass


# Constants
IMMEDIATELY = 0

_INT_DGRAM_LEN = 4
_INT64_DGRAM_LEN = 8
_UINT64_DGRAM_LEN = 8
_FLOAT_DGRAM_LEN = 4
_DOUBLE_DGRAM_LEN = 8
_TIMETAG_DGRAM_LEN = 8
_STRING_DGRAM_PAD = 4
_BLOB_DGRAM_PAD = 4
_EMPTY_STR_DGRAM = b'\x00\x00\x00\x00'


def get_string(dgram: bytes, start_index: int) -> Tuple[str, int]:
    """
    Get a Python string from the datagram.
    
    Args:
        dgram: Datagram packet
        start_index: Index where the string starts
        
    Returns:
        Tuple of (string, new_end_index)
        
    Raises:
        ParseError: If datagram could not be parsed
    """
    if start_index < 0:
        raise ParseError('start_index < 0')
    
    offset = 0
    try:
        # Check for empty string
        if (len(dgram) > start_index + _STRING_DGRAM_PAD and
                dgram[start_index:start_index + _STRING_DGRAM_PAD] == _EMPTY_STR_DGRAM):
            return '', start_index + _STRING_DGRAM_PAD
        
        # Find null terminator
        while start_index + offset < len(dgram) and dgram[start_index + offset] != 0:
            offset += 1
        
        # Align to 4-byte boundary
        if offset % _STRING_DGRAM_PAD == 0:
            offset += _STRING_DGRAM_PAD
        else:
            offset += (-offset % _STRING_DGRAM_PAD)
        
        if offset > len(dgram[start_index:]):
            raise ParseError('Datagram is too short')
        
        data_str = dgram[start_index:start_index + offset]
        return data_str.replace(b'\x00', b'').decode('utf-8'), start_index + offset
        
    except IndexError as e:
        raise ParseError(f'Could not parse datagram: {e}')
    except TypeError as e:
        raise ParseError(f'Could not parse datagram: {e}')


def get_int(dgram: bytes, start_index: int) -> Tuple[int, int]:
    """
    Get a 32-bit big-endian two's complement integer from the datagram.
    
    Args:
        dgram: Datagram packet
        start_index: Index where the integer starts
        
    Returns:
        Tuple of (integer, new_end_index)
        
    Raises:
        ParseError: If datagram could not be parsed
    """
    try:
        if len(dgram[start_index:]) < _INT_DGRAM_LEN:
            raise ParseError('Datagram is too short')
        
        return (struct.unpack('>i', dgram[start_index:start_index + _INT_DGRAM_LEN])[0],
                start_index + _INT_DGRAM_LEN)
        
    except (struct.error, TypeError) as e:
        raise ParseError(f'Could not parse datagram: {e}')


def get_float(dgram: bytes, start_index: int) -> Tuple[float, int]:
    """
    Get a 32-bit big-endian IEEE 754 floating point number from the datagram.
    
    Args:
        dgram: Datagram packet
        start_index: Index where the float starts
        
    Returns:
        Tuple of (float, new_end_index)
        
    Raises:
        ParseError: If datagram could not be parsed
    """
    try:
        if len(dgram[start_index:]) < _FLOAT_DGRAM_LEN:
            # Pad if needed
            dgram = dgram + b'\x00' * (_FLOAT_DGRAM_LEN - len(dgram[start_index:]))
        
        return (struct.unpack('>f', dgram[start_index:start_index + _FLOAT_DGRAM_LEN])[0],
                start_index + _FLOAT_DGRAM_LEN)
        
    except (struct.error, TypeError) as e:
        raise ParseError(f'Could not parse datagram: {e}')


def _parse_datagram(dgram: bytes) -> Tuple[str, List[Any]]:
    """
    Parse an OSC datagram.
    
    Args:
        dgram: Raw OSC datagram
        
    Returns:
        Tuple of (address_pattern, parameters)
        
    Raises:
        ParseError: If datagram could not be parsed
    """
    _dgram = dgram
    _parameters = []
    
    try:
        # Get address pattern
        address_regexp, index = get_string(_dgram, 0)
        
        if not _dgram[index:]:
            return address_regexp, []
        
        # Get type tag string
        type_tag, index = get_string(_dgram, index)
        
        if type_tag.startswith(','):
            type_tag = type_tag[1:]
        
        params = []
        param_stack = [params]
        
        # Parse each parameter
        for param in type_tag:
            if param == "i":  # Integer
                val, index = get_int(_dgram, index)
                param_stack[-1].append(val)
            elif param == "f":  # Float
                val, index = get_float(_dgram, index)
                param_stack[-1].append(val)
            elif param == "s":  # String
                val, index = get_string(_dgram, index)
                param_stack[-1].append(val)
            elif param == "T":  # True
                param_stack[-1].append(True)
            elif param == "F":  # False
                param_stack[-1].append(False)
            elif param == "[":  # Array start
                array = []
                param_stack[-1].append(array)
                param_stack.append(array)
            elif param == "]":  # Array stop
                if len(param_stack) < 2:
                    raise ParseError(f'Unexpected closing bracket in type tag: {type_tag}')
                param_stack.pop()
            elif param == "b":  # Blob
                # Get blob length
                blob_len, index = get_int(_dgram, index)
                blob_data = _dgram[index:index + blob_len]
                index += (blob_len + (-blob_len % 4))
                param_stack[-1].append(blob_data)
            # Skip unknown types
            else:
                continue
        
        if len(param_stack) != 1:
            raise ParseError(f'Missing closing bracket in type tag: {type_tag}')
        
        _parameters = params
        return address_regexp, _parameters
        
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(f'Could not parse datagram: {e}')