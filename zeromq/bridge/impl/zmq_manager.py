# zmq/bridge/impl/zmq_manager.py
import zmq
import json
import carb
import atexit

# Default ZMQ addresses
DEFAULT_PUB_ADDRESS = "tcp://*:25556"
DEFAULT_SUB_ADDRESS = "tcp://127.0.0.1:25557"

# Control topic for subscription requests
CONTROL_TOPIC = "__zmq_bridge_control__"

class ZmqManager:
    _instance = None

    def __init__(self):
        self.context = zmq.Context()
        self.publishers = {}
        self.subscribers = {}
        self._initialized = False
        
        # Global addresses configuration
        self.global_pub_address = DEFAULT_PUB_ADDRESS
        self.global_sub_address = DEFAULT_SUB_ADDRESS
        
        # Track subscription requests sent to ROS2
        self.subscription_requests = set()
        
        # Buffer for received messages: {address: {topic: (data, timestamp)}}
        self.message_buffer = {}
        
        # Register cleanup on exit
        atexit.register(self.shutdown)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ZmqManager()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance - use with caution"""
        if cls._instance is not None:
            cls._instance.shutdown()
            cls._instance = None

    def initialize(self, linger_ms=100, pub_address=None, sub_address=None):
        """Initialize the ZMQ context with proper settings
        
        Args:
            linger_ms: Socket linger time in milliseconds
            pub_address: Global publisher address (optional)
            sub_address: Global subscriber address (optional)
        """
        if self._initialized:
            return
        
        # Set global addresses if provided
        if pub_address and pub_address != self.global_pub_address:
            carb.log_info(f"Global PUB address changed: {self.global_pub_address} -> {pub_address}")
            self.global_pub_address = pub_address
        if sub_address and sub_address != self.global_sub_address:
            carb.log_info(f"Global SUB address changed: {self.global_sub_address} -> {sub_address}")
            self.global_sub_address = sub_address
            
        # Set context options for graceful shutdown
        self.context.setsockopt(zmq.LINGER, linger_ms)
        self._initialized = True
        carb.log_info(f"ZmqManager initialized - PUB: {self.global_pub_address}, SUB: {self.global_sub_address}")

    def set_global_addresses(self, pub_address, sub_address):
        """Update global ZMQ addresses at runtime
        
        Args:
            pub_address: Publisher address
            sub_address: Subscriber address
        """
        new_pub_address = pub_address if pub_address else DEFAULT_PUB_ADDRESS
        new_sub_address = sub_address if sub_address else DEFAULT_SUB_ADDRESS

        if new_pub_address != self.global_pub_address:
            carb.log_info(f"Global PUB address changed: {self.global_pub_address} -> {new_pub_address}")
        if new_sub_address != self.global_sub_address:
            carb.log_info(f"Global SUB address changed: {self.global_sub_address} -> {new_sub_address}")

        self.global_pub_address = new_pub_address
        self.global_sub_address = new_sub_address
        carb.log_info(f"Global addresses updated - PUB: {self.global_pub_address}, SUB: {self.global_sub_address}")

    def get_global_pub_address(self):
        """Get current global publisher address"""
        return self.global_pub_address

    def get_global_sub_address(self):
        """Get current global subscriber address"""
        return self.global_sub_address

    def clear(self):
        """Close all publishers and subscribers"""
        for pub in self.publishers.values():
            try:
                pub.close()
            except Exception as e:
                carb.log_warn(f"Error closing publisher: {e}")
        for sub in self.subscribers.values():
            try:
                sub.close()
            except Exception as e:
                carb.log_warn(f"Error closing subscriber: {e}")
        self.publishers = {}
        self.subscribers = {}
        carb.log_info("ZmqManager cleared all sockets")

    def shutdown(self):
        """Gracefully shutdown all resources"""
        self.clear()
        try:
            self.context.term()
        except Exception as e:
            carb.log_warn(f"Error terminating context: {e}")
        carb.log_info("ZmqManager shutdown complete")

    def get_publisher(self, address):
        # Use default address if empty or None
        if not address or address.strip() == "":
            address = DEFAULT_PUB_ADDRESS
            carb.log_warn(f"Empty publisher address provided, using default: {address}")
        
        if address not in self.publishers:
            try:
                pub = self.context.socket(zmq.PUB)
                # Enable address reuse and set socket options
                pub.setsockopt(zmq.LINGER, 100)
                # Don't set SO_REUSEADDR directly on zmq socket, it's handled by ZMQ
                pub.bind(address)
                self.publishers[address] = pub
                carb.log_info(f"Zmq Publisher bound to {address}")
            except zmq.ZMQError as e:
                carb.log_error(f"Failed to bind publisher to {address}: {e}")
                raise
        return self.publishers[address]

    def get_subscriber(self, address):
        # Use default address if empty or None
        if not address or address.strip() == "":
            address = DEFAULT_SUB_ADDRESS
            carb.log_warn(f"Empty subscriber address provided, using default: {address}")
        
        if address not in self.subscribers:
            try:
                sub = self.context.socket(zmq.SUB)
                sub.setsockopt(zmq.LINGER, 100)
                sub.connect(address)
                sub.setsockopt(zmq.SUBSCRIBE, b"") # Subscribe to all by default or manage topics?
                self.subscribers[address] = sub
                carb.log_info(f"Zmq Subscriber connected to {address}")
            except zmq.ZMQError as e:
                carb.log_error(f"Failed to connect subscriber to {address}: {e}")
                raise
        return self.subscribers[address]

    def publish_json(self, address, topic, data):
        pub = self.get_publisher(address)
        pub.send_multipart([topic.encode('utf-8'), json.dumps(data).encode('utf-8')])

    def publish_image(self, address, topic, image_data, metadata):
        """
        image_data: bytes or numpy array buffer
        metadata: dict with width, height, encoding, etc.
        """
        pub = self.get_publisher(address)
        pub.send_multipart([
            topic.encode('utf-8'),
            json.dumps(metadata).encode('utf-8'),
            image_data
        ])

    def _spin_socket(self, address):
        """Internal method to flush socket events into buffer"""
        sub = self.get_subscriber(address)
        try:
            # Read all available messages up to a limit to prevent starvation
            # But here we just poll(0) in a loop
            while sub.poll(0):
                parts = sub.recv_multipart()
                if len(parts) >= 2:
                    topic_b = parts[0]
                    data_b = parts[1]
                    topic = topic_b.decode('utf-8')
                    try:
                        data = json.loads(data_b.decode('utf-8'))
                        # Store in buffer
                        import time
                        if address not in self.message_buffer:
                            self.message_buffer[address] = {}
                        self.message_buffer[address][topic] = (data, time.time())
                    except json.JSONDecodeError:
                        pass
        except zmq.ZMQError:
            pass

    def receive_json(self, address, target_topic=None):
        # Always spin to update buffer from socket
        self._spin_socket(address)
        
        if not target_topic:
            return None, None, 0.0
            
        # Retrieve from buffer
        # Try exact match first
        if address in self.message_buffer:
            addr_buffer = self.message_buffer[address]
            if target_topic in addr_buffer:
                data, timestamp = addr_buffer[target_topic]
                return target_topic, data, timestamp
            
        return None, None, 0.0
            # For now, just log if it's not empty, to help debugging. 
            # Note: This might be spammy, so only enabling if needed or using carb.log_verbose
            # known_topics = list(addr_buffer.keys())
            # carb.log_verbose(f"ZmqManager: Requested '{target_topic}' not found. Available: {known_topics}")

        return None, None, 0.0
    # Convenience methods using global addresses
    
    def publish_json_global(self, topic, data):
        """Publish JSON data using the global publisher address"""
        return self.publish_json(self.global_pub_address, topic, data)

    def publish_image_global(self, topic, image_data, metadata):
        """Publish image using the global publisher address"""
        return self.publish_image(self.global_pub_address, topic, image_data, metadata)

    def receive_json_global(self, target_topic=None):
        """Receive JSON data using the global subscriber address"""
        return self.receive_json(self.global_sub_address, target_topic)
    
    # Subscription protocol for ROS2 bridge
    
    def request_subscription(self, topic_name, msg_type="generic"):
        """Send subscription request to ROS2 bridge
        
        Args:
            topic_name: ROS2 topic to subscribe to
            msg_type: Message type hint (e.g., 'Twist', 'JointState', 'generic')
        
        This sends a control message to ROS2 bridge requesting it to:
        1. Subscribe to the specified ROS2 topic
        2. Forward messages from that topic to ZMQ
        """
        request_key = f"{topic_name}:{msg_type}"
        
        # Only send once per topic
        if request_key in self.subscription_requests:
            return

        carb.log_info(f"New subscription topic requested: {topic_name} ({msg_type})")
        
        try:
            import time
            control_msg = {
                "action": "subscribe",
                "topic": topic_name,
                "msg_type": msg_type,
                "timestamp": time.time()
            }
            
            # Send on control topic
            self.publish_json(self.global_pub_address, CONTROL_TOPIC, control_msg)
            self.subscription_requests.add(request_key)
            
            carb.log_info(f"Subscription request sent: topic={topic_name}, type={msg_type}")
            
        except Exception as e:
            carb.log_error(f"Failed to send subscription request for {topic_name}: {e}")

    def unsubscribe_request(self, topic_name):
        """Send unsubscription request to ROS2 bridge
        
        Args:
            topic_name: ROS2 topic to unsubscribe from
        """
        try:
            import time
            control_msg = {
                "action": "unsubscribe",
                "topic": topic_name,
                "timestamp": time.time()
            }
            
            # Send on control topic
            self.publish_json(self.global_pub_address, CONTROL_TOPIC, control_msg)
            
            # Remove from tracking
            self.subscription_requests = {
                req for req in self.subscription_requests 
                if not req.startswith(f"{topic_name}:")
            }
            
            carb.log_info(f"Unsubscription request sent: topic={topic_name}")
            
        except Exception as e:
            carb.log_error(f"Failed to send unsubscription request for {topic_name}: {e}")
