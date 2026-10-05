"""
OB55 Parser for Free Fire
Parses OB55 protocol responses
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from src.utils.logging import get_logger
from src.utils.helpers import generate_id, get_timestamp

logger = get_logger(__name__)


@dataclass
class ParsedResponse:
    """Parsed OB55 response"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[int] = None
    timestamp: float = field(default_factory=get_timestamp)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "error_code": self.error_code,
            "timestamp": self.timestamp
        }


class OB55Parser:
    """OB55 protocol response parser"""

    def __init__(self):
        # OB55 message types
        self.MESSAGE_TYPES = {
            1: "AUTH_REQUEST",
            2: "AUTH_RESPONSE",
            3: "LOGIN_REQUEST",
            4: "LOGIN_RESPONSE",
            5: "ACCOUNT_INFO_REQUEST",
            6: "ACCOUNT_INFO_RESPONSE",
            7: "ERROR_RESPONSE",
            8: "PING",
            9: "PONG",
            10: "KEEPALIVE"
        }
        
        # OB55 error codes
        self.ERROR_CODES = {
            0: "SUCCESS",
            1: "UNKNOWN_ERROR",
            2: "INVALID_REQUEST",
            3: "AUTHENTICATION_FAILED",
            4: "ACCOUNT_NOT_FOUND",
            5: "ACCOUNT_BANNED",
            6: "RATE_LIMITED",
            7: "SERVER_ERROR",
            8: "TIMEOUT",
            9: "MAINTENANCE",
            10: "INVALID_TOKEN"
        }

    def parse_response(self, response: bytes) -> ParsedResponse:
        """Parse OB55 response"""
        try:
            # Check if response is empty
            if not response or len(response) < 8:
                return ParsedResponse(
                    success=False,
                    error="Empty response",
                    error_code=2
                )
            
            # Read message header
            message_type = struct.unpack('>I', response[0:4])[0]
            message_length = struct.unpack('>I', response[4:8])[0]
            
            # Check message length
            if len(response) < 8 + message_length:
                return ParsedResponse(
                    success=False,
                    error="Incomplete message",
                    error_code=2
                )
            
            # Extract message body
            message_body = response[8:8+message_length]
            
            # Parse based on message type
            if message_type == 2:  # AUTH_RESPONSE
                return self._parse_auth_response(message_body)
            elif message_type == 4:  # LOGIN_RESPONSE
                return self._parse_login_response(message_body)
            elif message_type == 6:  # ACCOUNT_INFO_RESPONSE
                return self._parse_account_info_response(message_body)
            elif message_type == 7:  # ERROR_RESPONSE
                return self._parse_error_response(message_body)
            elif message_type == 9:  # PONG
                return ParsedResponse(success=True, data={"type": "PONG"})
            else:
                return ParsedResponse(
                    success=False,
                    error=f"Unknown message type: {message_type}",
                    error_code=2
                )
                
        except Exception as e:
            logger.error(f"Failed to parse OB55 response: {e}")
            return ParsedResponse(
                success=False,
                error=str(e),
                error_code=1
            )

    def _parse_auth_response(self, body: bytes) -> ParsedResponse:
        """Parse authentication response"""
        try:
            # OB55 auth response format:
            # - 4 bytes: status code
            # - 4 bytes: token length
            # - N bytes: token
            # - 4 bytes: expiry timestamp
            
            if len(body) < 12:
                return ParsedResponse(
                    success=False,
                    error="Incomplete auth response",
                    error_code=2
                )
            
            status_code = struct.unpack('>I', body[0:4])[0]
            token_length = struct.unpack('>I', body[4:8])[0]
            
            if len(body) < 12 + token_length:
                return ParsedResponse(
                    success=False,
                    error="Incomplete token",
                    error_code=2
                )
            
            token = body[8:8+token_length].decode('utf-8')
            expiry = struct.unpack('>I', body[8+token_length:12+token_length])[0]
            
            if status_code == 0:
                return ParsedResponse(
                    success=True,
                    data={
                        "token": token,
                        "expiry": expiry,
                        "type": "AUTH_RESPONSE"
                    }
                )
            else:
                return ParsedResponse(
                    success=False,
                    error=self.ERROR_CODES.get(status_code, "UNKNOWN_ERROR"),
                    error_code=status_code
                )
                
        except Exception as e:
            logger.error(f"Failed to parse auth response: {e}")
            return ParsedResponse(
                success=False,
                error=str(e),
                error_code=1
            )

    def _parse_login_response(self, body: bytes) -> ParsedResponse:
        """Parse login response"""
        try:
            # OB55 login response format:
            # - 4 bytes: status code
            # - 4 bytes: account ID length
            # - N bytes: account ID
            # - 4 bytes: token length
            # - M bytes: token
            # - 4 bytes: expiry timestamp
            
            if len(body) < 16:
                return ParsedResponse(
                    success=False,
                    error="Incomplete login response",
                    error_code=2
                )
            
            offset = 0
            status_code = struct.unpack('>I', body[offset:offset+4])[0]
            offset += 4
            
            account_id_length = struct.unpack('>I', body[offset:offset+4])[0]
            offset += 4
            
            account_id = body[offset:offset+account_id_length].decode('utf-8')
            offset += account_id_length
            
            token_length = struct.unpack('>I', body[offset:offset+4])[0]
            offset += 4
            
            token = body[offset:offset+token_length].decode('utf-8')
            offset += token_length
            
            expiry = struct.unpack('>I', body[offset:offset+4])[0]
            
            if status_code == 0:
                return ParsedResponse(
                    success=True,
                    data={
                        "account_id": account_id,
                        "token": token,
                        "expiry": expiry,
                        "type": "LOGIN_RESPONSE"
                    }
                )
            else:
                return ParsedResponse(
                    success=False,
                    error=self.ERROR_CODES.get(status_code, "UNKNOWN_ERROR"),
                    error_code=status_code
                )
                
        except Exception as e:
            logger.error(f"Failed to parse login response: {e}")
            return ParsedResponse(
                success=False,
                error=str(e),
                error_code=1
            )

    def _parse_account_info_response(self, body: bytes) -> ParsedResponse:
        """Parse account info response"""
        try:
            # OB55 account info response format:
            # - 4 bytes: status code
            # - JSON data (variable length)
            
            if len(body) < 4:
                return ParsedResponse(
                    success=False,
                    error="Incomplete account info response",
                    error_code=2
                )
            
            status_code = struct.unpack('>I', body[0:4])[0]
            json_data = body[4:].decode('utf-8')
            
            if status_code == 0:
                try:
                    data = json.loads(json_data)
                    return ParsedResponse(
                        success=True,
                        data={
                            **data,
                            "type": "ACCOUNT_INFO_RESPONSE"
                        }
                    )
                except json.JSONDecodeError:
                    return ParsedResponse(
                        success=True,
                        data={
                            "raw_data": json_data,
                            "type": "ACCOUNT_INFO_RESPONSE"
                        }
                    )
            else:
                return ParsedResponse(
                    success=False,
                    error=self.ERROR_CODES.get(status_code, "UNKNOWN_ERROR"),
                    error_code=status_code
                )
                
        except Exception as e:
            logger.error(f"Failed to parse account info response: {e}")
            return ParsedResponse(
                success=False,
                error=str(e),
                error_code=1
            )

    def _parse_error_response(self, body: bytes) -> ParsedResponse:
        """Parse error response"""
        try:
            # OB55 error response format:
            # - 4 bytes: error code
            # - JSON error details (variable length)
            
            if len(body) < 4:
                return ParsedResponse(
                    success=False,
                    error="Incomplete error response",
                    error_code=1
                )
            
            error_code = struct.unpack('>I', body[0:4])[0]
            error_details = body[4:].decode('utf-8')
            
            try:
                details = json.loads(error_details)
                error_message = details.get("message", "Unknown error")
            except json.JSONDecodeError:
                error_message = error_details
            
            return ParsedResponse(
                success=False,
                error=error_message,
                error_code=error_code
            )
                
        except Exception as e:
            logger.error(f"Failed to parse error response: {e}")
            return ParsedResponse(
                success=False,
                error=str(e),
                error_code=1
            )

    def parse_json_response(self, json_data: Dict[str, Any]) -> ParsedResponse:
        """Parse JSON response (for HTTP API)"""
        try:
            if json_data.get("success", False):
                return ParsedResponse(
                    success=True,
                    data=json_data.get("data", {}),
                    timestamp=json_data.get("timestamp", get_timestamp())
                )
            else:
                return ParsedResponse(
                    success=False,
                    error=json_data.get("error", "Unknown error"),
                    error_code=json_data.get("error_code", 1)
                )
        except Exception as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return ParsedResponse(
                success=False,
                error=str(e),
                error_code=1
            )

    def parse_account_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse account data from JSON"""
        try:
            # Extract account information
            account_info = data.get("account", {})
            
            return {
                "account_id": account_info.get("account_id", ""),
                "nickname": account_info.get("nickname", "Unknown"),
                "level": account_info.get("level", 0),
                "diamonds": account_info.get("diamonds", 0),
                "coins": account_info.get("coins", 0),
                "region": account_info.get("region", "global"),
                "is_banned": account_info.get("is_banned", False),
                "ban_reason": account_info.get("ban_reason"),
                "ban_expiry": account_info.get("ban_expiry"),
                "last_login": account_info.get("last_login"),
                "creation_date": account_info.get("creation_date"),
                "is_guest": account_info.get("is_guest", True),
                "device_id": account_info.get("device_id"),
                "session_id": account_info.get("session_id"),
                "session_expiry": account_info.get("session_expiry"),
                "ip_address": account_info.get("ip_address"),
                "user_agent": account_info.get("user_agent")
            }
        except Exception as e:
            logger.error(f"Failed to parse account data: {e}")
            return {}

    def build_auth_request(self, device_id: str, timestamp: int) -> bytes:
        """Build OB55 authentication request"""
        try:
            # OB55 auth request format:
            # - 4 bytes: message type (1 for AUTH_REQUEST)
            # - 4 bytes: message length
            # - 4 bytes: device ID length
            # - N bytes: device ID
            # - 4 bytes: timestamp
            # - 32 bytes: signature (placeholder)
            
            device_id_bytes = device_id.encode('utf-8')
            message_type = struct.pack('>I', 1)
            device_id_length = struct.pack('>I', len(device_id_bytes))
            timestamp_bytes = struct.pack('>I', timestamp)
            signature = b'\x00' * 32  # Placeholder for signature
            
            message_body = device_id_length + device_id_bytes + timestamp_bytes + signature
            message_length = struct.pack('>I', len(message_body))
            
            return message_type + message_length + message_body
            
        except Exception as e:
            logger.error(f"Failed to build auth request: {e}")
            return b''

    def build_login_request(self, account_id: str, token: str, timestamp: int) -> bytes:
        """Build OB55 login request"""
        try:
            # OB55 login request format:
            # - 4 bytes: message type (3 for LOGIN_REQUEST)
            # - 4 bytes: message length
            # - 4 bytes: account ID length
            # - N bytes: account ID
            # - 4 bytes: token length
            # - M bytes: token
            # - 4 bytes: timestamp
            # - 32 bytes: signature (placeholder)
            
            account_id_bytes = account_id.encode('utf-8')
            token_bytes = token.encode('utf-8')
            
            message_type = struct.pack('>I', 3)
            account_id_length = struct.pack('>I', len(account_id_bytes))
            token_length = struct.pack('>I', len(token_bytes))
            timestamp_bytes = struct.pack('>I', timestamp)
            signature = b'\x00' * 32  # Placeholder for signature
            
            message_body = (account_id_length + account_id_bytes + 
                          token_length + token_bytes + 
                          timestamp_bytes + signature)
            message_length = struct.pack('>I', len(message_body))
            
            return message_type + message_length + message_body
            
        except Exception as e:
            logger.error(f"Failed to build login request: {e}")
            return b''

    def build_account_info_request(self, account_id: str, token: str, timestamp: int) -> bytes:
        """Build OB55 account info request"""
        try:
            # OB55 account info request format:
            # - 4 bytes: message type (5 for ACCOUNT_INFO_REQUEST)
            # - 4 bytes: message length
            # - 4 bytes: account ID length
            # - N bytes: account ID
            # - 4 bytes: token length
            # - M bytes: token
            # - 4 bytes: timestamp
            # - 32 bytes: signature (placeholder)
            
            account_id_bytes = account_id.encode('utf-8')
            token_bytes = token.encode('utf-8')
            
            message_type = struct.pack('>I', 5)
            account_id_length = struct.pack('>I', len(account_id_bytes))
            token_length = struct.pack('>I', len(token_bytes))
            timestamp_bytes = struct.pack('>I', timestamp)
            signature = b'\x00' * 32  # Placeholder for signature
            
            message_body = (account_id_length + account_id_bytes + 
                          token_length + token_bytes + 
                          timestamp_bytes + signature)
            message_length = struct.pack('>I', len(message_body))
            
            return message_type + message_length + message_body
            
        except Exception as e:
            logger.error(f"Failed to build account info request: {e}")
            return b''
