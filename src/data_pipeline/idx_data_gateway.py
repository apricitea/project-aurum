"""
Project Aurum - IDX Data Gateway
Real-time market data ingestion from Indonesian Stock Exchange
"""

import asyncio
import json
import logging
import socket
import struct
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
import pytz

import aioredis
from kafka import KafkaProducer
from kafka.errors import KafkaError


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Jakarta timezone
JAKARTA_TZ = pytz.timezone('Asia/Jakarta')
UTC_TZ = pytz.UTC


@dataclass
class TradeMessage:
    """IDX Trade Message Structure"""
    timestamp: datetime
    symbol: str
    price: float
    volume: int
    side: str  # 'BUY' or 'SELL'
    trade_id: str
    session_type: str = 'REGULAR'
    exchange: str = 'IDX'
    currency: str = 'IDR'

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class QuoteMessage:
    """IDX Quote Message Structure"""
    timestamp: datetime
    symbol: str
    bid_price: float
    ask_price: float
    bid_size: int
    ask_size: int
    mid_price: Optional[float] = None
    spread: Optional[float] = None
    exchange: str = 'IDX'
    currency: str = 'IDR'

    def __post_init__(self):
        """Calculate derived fields"""
        if self.bid_price > 0 and self.ask_price > 0:
            self.mid_price = (self.bid_price + self.ask_price) / 2
            self.spread = self.ask_price - self.bid_price

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class OrderBookMessage:
    """IDX Order Book Message Structure"""
    timestamp: datetime
    symbol: str
    side: str  # 'BID' or 'ASK'
    levels: List[Dict[str, float]]  # [{'price': float, 'size': int}, ...]
    exchange: str = 'IDX'

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class IDXMessageParser:
    """Parser for IDX binary message format"""

    # Message type constants
    MSG_TYPE_TRADE = 0x01
    MSG_TYPE_QUOTE = 0x02
    MSG_TYPE_ORDER_BOOK = 0x03
    MSG_TYPE_HEARTBEAT = 0x04
    MSG_TYPE_MARKET_STATUS = 0x05

    # Trade conditions
    TRADE_CONDITIONS = {
        0x00: 'NORMAL',
        0x01: 'CASH',
        0x02: 'CROSS',
        0x03: 'OPENING',
        0x04: 'CLOSING'
    }

    @staticmethod
    def parse_message(raw_data: bytes) -> Optional[Dict]:
        """Parse IDX binary message"""
        try:
            if len(raw_data) < 4:
                return None

            # Message header: Type(1) + Length(2) + Sequence(4)
            msg_type = struct.unpack('B', raw_data[0:1])[0]
            msg_length = struct.unpack('>H', raw_data[1:3])[0]
            sequence = struct.unpack('>I', raw_data[3:7])[0]

            if len(raw_data) < msg_length:
                logger.warning(f"Incomplete message: expected {msg_length}, got {len(raw_data)}")
                return None

            message_data = raw_data[7:msg_length]

            if msg_type == IDXMessageParser.MSG_TYPE_TRADE:
                return IDXMessageParser._parse_trade_message(message_data, sequence)
            elif msg_type == IDXMessageParser.MSG_TYPE_QUOTE:
                return IDXMessageParser._parse_quote_message(message_data, sequence)
            elif msg_type == IDXMessageParser.MSG_TYPE_ORDER_BOOK:
                return IDXMessageParser._parse_order_book_message(message_data, sequence)
            elif msg_type == IDXMessageParser.MSG_TYPE_HEARTBEAT:
                return {'type': 'heartbeat', 'sequence': sequence}
            else:
                logger.warning(f"Unknown message type: {msg_type}")
                return None

        except struct.error as e:
            logger.error(f"Failed to parse message: {e}")
            return None

    @staticmethod
    def _parse_trade_message(data: bytes, sequence: int) -> Dict:
        """Parse trade message format"""
        # IDX Trade Message Format:
        # Timestamp(8) + Symbol(8) + Price(8) + Volume(8) + Side(1) + Condition(1)
        timestamp_ns, symbol_bytes, price_raw, volume, side, condition = struct.unpack('>Q8sQQBB', data[:34])

        # Convert timestamp from nanoseconds to datetime
        timestamp = datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=UTC_TZ)

        # Decode symbol and strip null bytes
        symbol = symbol_bytes.decode('ascii').rstrip('\x00')

        # Convert price from fixed-point representation (multiply by 100 for IDR)
        price = price_raw / 100.0

        # Determine trade side
        trade_side = 'BUY' if side == 1 else 'SELL'

        # Get trade condition
        trade_condition = IDXMessageParser.TRADE_CONDITIONS.get(condition, 'UNKNOWN')

        trade = TradeMessage(
            timestamp=timestamp,
            symbol=symbol,
            price=price,
            volume=volume,
            side=trade_side,
            trade_id=f"{sequence}_{timestamp_ns}",
            session_type='REGULAR' if 9 <= timestamp.hour < 16 else 'AFTER_HOURS'
        )

        return {
            'type': 'trade',
            'sequence': sequence,
            'data': trade,
            'condition': trade_condition
        }

    @staticmethod
    def _parse_quote_message(data: bytes, sequence: int) -> Dict:
        """Parse quote message format"""
        # IDX Quote Message Format:
        # Timestamp(8) + Symbol(8) + BidPrice(8) + AskPrice(8) + BidSize(8) + AskSize(8)
        timestamp_ns, symbol_bytes, bid_price_raw, ask_price_raw, bid_size, ask_size = struct.unpack('>Q8sQQQQ', data[:48])

        timestamp = datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=UTC_TZ)
        symbol = symbol_bytes.decode('ascii').rstrip('\x00')
        bid_price = bid_price_raw / 100.0
        ask_price = ask_price_raw / 100.0

        quote = QuoteMessage(
            timestamp=timestamp,
            symbol=symbol,
            bid_price=bid_price,
            ask_price=ask_price,
            bid_size=bid_size,
            ask_size=ask_size
        )

        return {
            'type': 'quote',
            'sequence': sequence,
            'data': quote
        }

    @staticmethod
    def _parse_order_book_message(data: bytes, sequence: int) -> Dict:
        """Parse order book message format"""
        # IDX Order Book Message Format:
        # Timestamp(8) + Symbol(8) + Side(1) + Levels(1) + [Price(8) + Size(8)] * Levels
        timestamp_ns, symbol_bytes, side, num_levels = struct.unpack('>Q8sBB', data[:18])

        timestamp = datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=UTC_TZ)
        symbol = symbol_bytes.decode('ascii').rstrip('\x00')
        side_str = 'BID' if side == 0 else 'ASK'

        levels = []
        offset = 18
        for i in range(min(num_levels, 10)):  # Limit to 10 levels
            if offset + 16 <= len(data):
                price_raw, size = struct.unpack('>QQ', data[offset:offset+16])
                levels.append({
                    'price': price_raw / 100.0,
                    'size': size
                })
                offset += 16

        order_book = OrderBookMessage(
            timestamp=timestamp,
            symbol=symbol,
            side=side_str,
            levels=levels
        )

        return {
            'type': 'order_book',
            'sequence': sequence,
            'data': order_book
        }


class IDXDataGateway:
    """Main data gateway for IDX market data feed"""

    def __init__(self, config: Dict):
        self.config = config
        self.running = False
        self.socket = None
        self.kafka_producer = None
        self.redis_client = None
        self.message_count = 0
        self.error_count = 0
        self.last_heartbeat = None
        self.connection_retry_count = 0
        self.max_retries = config.get('max_retries', 5)

        # Callbacks for different message types
        self.callbacks: Dict[str, List[Callable]] = {
            'trade': [],
            'quote': [],
            'order_book': [],
            'heartbeat': [],
            'error': []
        }

        # Statistics
        self.stats = {
            'messages_processed': 0,
            'trades_processed': 0,
            'quotes_processed': 0,
            'errors': 0,
            'last_message_time': None,
            'connection_uptime': None
        }

    async def initialize(self):
        """Initialize connections"""
        try:
            # Initialize Kafka producer
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=self.config['kafka']['bootstrap_servers'],
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                retries=3,
                batch_size=16384,
                linger_ms=10,
                compression_type='snappy'
            )

            # Initialize Redis client
            self.redis_client = await aioredis.from_url(
                self.config['redis']['url'],
                encoding="utf-8",
                decode_responses=True
            )

            logger.info("IDX Data Gateway initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize gateway: {e}")
            raise

    async def connect_to_idx(self):
        """Connect to IDX Market Data Feed"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(30)  # 30 second timeout

            host = self.config['idx_feed']['host']
            port = self.config['idx_feed']['port']

            logger.info(f"Connecting to IDX feed at {host}:{port}")
            self.socket.connect((host, port))

            # Send authentication if required
            if 'username' in self.config['idx_feed']:
                await self._authenticate()

            self.connection_retry_count = 0
            self.stats['connection_uptime'] = datetime.now(UTC_TZ)
            logger.info("Connected to IDX Market Data Feed")

        except Exception as e:
            self.connection_retry_count += 1
            logger.error(f"Failed to connect to IDX feed (attempt {self.connection_retry_count}): {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            raise

    async def _authenticate(self):
        """Send authentication message to IDX feed"""
        username = self.config['idx_feed']['username']
        password = self.config['idx_feed']['password']

        # Create authentication message (format depends on IDX specification)
        auth_msg = struct.pack('>B32s32s', 0xFF, username.encode('ascii')[:32].ljust(32, b'\x00'),
                              password.encode('ascii')[:32].ljust(32, b'\x00'))

        self.socket.send(auth_msg)

        # Wait for authentication response
        response = self.socket.recv(1024)
        if response[0] != 0x00:  # Assuming 0x00 indicates success
            raise Exception("Authentication failed")

        logger.info("Authentication successful")

    def register_callback(self, message_type: str, callback: Callable):
        """Register callback for specific message type"""
        if message_type in self.callbacks:
            self.callbacks[message_type].append(callback)
        else:
            raise ValueError(f"Unknown message type: {message_type}")

    async def _trigger_callbacks(self, message_type: str, data: Any):
        """Trigger all callbacks for a message type"""
        for callback in self.callbacks[message_type]:
            try:
                await callback(data)
            except Exception as e:
                logger.error(f"Callback error for {message_type}: {e}")

    async def _send_to_kafka(self, topic: str, key: str, message: Dict):
        """Send message to Kafka topic"""
        try:
            future = self.kafka_producer.send(topic, key=key, value=message)
            # Don't wait for the result to maintain low latency
            return future
        except KafkaError as e:
            logger.error(f"Failed to send message to Kafka: {e}")
            self.error_count += 1

    async def _cache_latest_data(self, symbol: str, data_type: str, data: Dict):
        """Cache latest data in Redis"""
        try:
            key = f"latest:{data_type}:{symbol}"
            await self.redis_client.setex(key, 60, json.dumps(data, default=str))
        except Exception as e:
            logger.error(f"Failed to cache data in Redis: {e}")

    async def _process_trade_message(self, parsed_message: Dict):
        """Process trade message"""
        trade_data = parsed_message['data']
        symbol = trade_data.symbol

        # Send to Kafka
        await self._send_to_kafka('raw_trades', symbol, trade_data.to_dict())

        # Cache latest trade
        await self._cache_latest_data(symbol, 'trade', trade_data.to_dict())

        # Update statistics
        self.stats['trades_processed'] += 1

        # Trigger callbacks
        await self._trigger_callbacks('trade', trade_data)

        # Log high-value trades
        trade_value = trade_data.price * trade_data.volume
        if trade_value > 1_000_000_000:  # 1 billion IDR
            logger.info(f"Large trade: {symbol} {trade_data.volume:,} @ {trade_data.price:,.2f} = {trade_value:,.0f} IDR")

    async def _process_quote_message(self, parsed_message: Dict):
        """Process quote message"""
        quote_data = parsed_message['data']
        symbol = quote_data.symbol

        # Send to Kafka
        await self._send_to_kafka('raw_quotes', symbol, quote_data.to_dict())

        # Cache latest quote
        await self._cache_latest_data(symbol, 'quote', quote_data.to_dict())

        # Update statistics
        self.stats['quotes_processed'] += 1

        # Trigger callbacks
        await self._trigger_callbacks('quote', quote_data)

    async def _process_order_book_message(self, parsed_message: Dict):
        """Process order book message"""
        order_book_data = parsed_message['data']
        symbol = order_book_data.symbol

        # Send to Kafka
        await self._send_to_kafka('raw_order_book', symbol, order_book_data.to_dict())

        # Cache order book
        await self._cache_latest_data(symbol, f'order_book_{order_book_data.side.lower()}', order_book_data.to_dict())

        # Trigger callbacks
        await self._trigger_callbacks('order_book', order_book_data)

    async def _process_heartbeat(self, parsed_message: Dict):
        """Process heartbeat message"""
        self.last_heartbeat = datetime.now(UTC_TZ)
        await self._trigger_callbacks('heartbeat', parsed_message)

    async def _handle_connection_error(self, error: Exception):
        """Handle connection errors and attempt reconnection"""
        logger.error(f"Connection error: {error}")
        self.error_count += 1

        await self._trigger_callbacks('error', error)

        if self.socket:
            self.socket.close()
            self.socket = None

        if self.connection_retry_count < self.max_retries:
            retry_delay = min(2 ** self.connection_retry_count, 60)  # Exponential backoff, max 60 seconds
            logger.info(f"Retrying connection in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)

            try:
                await self.connect_to_idx()
            except Exception as e:
                logger.error(f"Reconnection failed: {e}")
        else:
            logger.error(f"Max retries ({self.max_retries}) exceeded. Stopping.")
            self.running = False

    async def start_streaming(self):
        """Start the main data streaming loop"""
        self.running = True
        buffer = b''

        logger.info("Starting IDX data streaming...")

        while self.running:
            try:
                if not self.socket:
                    await self.connect_to_idx()

                # Receive data with timeout
                self.socket.settimeout(5.0)
                data = self.socket.recv(4096)

                if not data:
                    raise ConnectionError("Connection closed by server")

                buffer += data

                # Process complete messages
                while len(buffer) >= 4:
                    # Check if we have enough data for the message length
                    if len(buffer) >= 3:
                        msg_length = struct.unpack('>H', buffer[1:3])[0]

                        if len(buffer) >= msg_length:
                            # Extract complete message
                            message_data = buffer[:msg_length]
                            buffer = buffer[msg_length:]

                            # Parse and process message
                            parsed_message = IDXMessageParser.parse_message(message_data)

                            if parsed_message:
                                await self._route_message(parsed_message)
                                self.message_count += 1
                                self.stats['messages_processed'] += 1
                                self.stats['last_message_time'] = datetime.now(UTC_TZ)
                        else:
                            # Wait for more data
                            break
                    else:
                        # Wait for more data
                        break

                # Log statistics periodically
                if self.message_count % 10000 == 0:
                    logger.info(f"Processed {self.message_count:,} messages, {self.error_count} errors")

            except socket.timeout:
                # Check for heartbeat
                if self.last_heartbeat:
                    time_since_heartbeat = (datetime.now(UTC_TZ) - self.last_heartbeat).total_seconds()
                    if time_since_heartbeat > 30:  # 30 seconds without heartbeat
                        logger.warning("No heartbeat received in 30 seconds")
                continue

            except Exception as e:
                await self._handle_connection_error(e)

    async def _route_message(self, parsed_message: Dict):
        """Route parsed message to appropriate handler"""
        message_type = parsed_message['type']

        if message_type == 'trade':
            await self._process_trade_message(parsed_message)
        elif message_type == 'quote':
            await self._process_quote_message(parsed_message)
        elif message_type == 'order_book':
            await self._process_order_book_message(parsed_message)
        elif message_type == 'heartbeat':
            await self._process_heartbeat(parsed_message)
        else:
            logger.warning(f"Unknown message type: {message_type}")

    def get_statistics(self) -> Dict:
        """Get current statistics"""
        stats = self.stats.copy()
        stats['connection_retry_count'] = self.connection_retry_count
        stats['total_message_count'] = self.message_count
        stats['total_error_count'] = self.error_count
        stats['is_connected'] = self.socket is not None

        if self.stats['connection_uptime']:
            uptime = datetime.now(UTC_TZ) - self.stats['connection_uptime']
            stats['uptime_seconds'] = uptime.total_seconds()

        return stats

    async def stop(self):
        """Stop the data gateway"""
        logger.info("Stopping IDX Data Gateway...")
        self.running = False

        if self.socket:
            self.socket.close()

        if self.kafka_producer:
            self.kafka_producer.close()

        if self.redis_client:
            await self.redis_client.close()

        logger.info("IDX Data Gateway stopped")


# Example usage and configuration
if __name__ == "__main__":
    config = {
        'idx_feed': {
            'host': 'feed.idx.co.id',  # Replace with actual IDX feed host
            'port': 9999,
            'username': 'your_username',
            'password': 'your_password'
        },
        'kafka': {
            'bootstrap_servers': ['localhost:9092']
        },
        'redis': {
            'url': 'redis://localhost:6379/0'
        },
        'max_retries': 5
    }

    async def trade_callback(trade: TradeMessage):
        """Example trade callback"""
        print(f"Trade: {trade.symbol} {trade.volume} @ {trade.price}")

    async def quote_callback(quote: QuoteMessage):
        """Example quote callback"""
        if quote.spread and quote.spread > 100:  # Wide spreads
            print(f"Wide spread: {quote.symbol} {quote.bid_price}-{quote.ask_price} (spread: {quote.spread})")

    async def main():
        gateway = IDXDataGateway(config)

        # Register callbacks
        gateway.register_callback('trade', trade_callback)
        gateway.register_callback('quote', quote_callback)

        try:
            await gateway.initialize()
            await gateway.start_streaming()
        except KeyboardInterrupt:
            logger.info("Shutdown requested by user")
        finally:
            await gateway.stop()

    # Run the gateway
    asyncio.run(main())