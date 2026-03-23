# zeromq/bridge/ogn/python/nodes/ZmqSubscribeTwist.py
from zeromq.bridge.impl.zmq_manager import ZmqManager
import carb

class ZmqSubscribeTwistInternalState:
    def __init__(self):
        self.mgr = ZmqManager.get_instance()
        self.last_data = {
            "linear": [0.0, 0.0, 0.0],
            "angular": [0.0, 0.0, 0.0]
        }
        self.last_topic = ""
        self.subscription_requested = False
        self.last_timestamp = 0.0

class ZmqSubscribeTwist:
    @staticmethod
    def internal_state():
        return ZmqSubscribeTwistInternalState()

    @staticmethod
    def compute(db) -> bool:
        state = db.per_instance_state
        try:
            # Use provided address, or fall back to global address if empty
            address = db.inputs.subAddress
            if not address or address.strip() == "":
                address = state.mgr.get_global_sub_address()
            
            # Force conversion to python string to avoid potential C++ binding/SSO issues
            topic = str(db.inputs.topicName)
            
            # Send subscription request to ROS2 bridge (if topic changed or not yet requested)
            if topic != state.last_topic or not state.subscription_requested:
                db.log_info(f"ZMQ twist subscription starting: addr={address}, topic={topic}")
                state.mgr.request_subscription(topic, "Twist")
                state.last_topic = topic
                state.subscription_requested = True
            
            # Non-blocking receive
            recv_topic, data, timestamp = state.mgr.receive_json(address, topic)
            
            if data and recv_topic == topic and timestamp > state.last_timestamp:
                state.last_timestamp = timestamp
                state.last_data = data
                db.outputs.execOut = db.inputs.execIn
                # Log success for debugging (optional: could be spammy if frequency is high)
                # db.log_info(f"Received ZMQ twist on '{topic}': {data}")

            db.outputs.linearVelocity = state.last_data.get("linear", [0.0, 0.0, 0.0])
            db.outputs.angularVelocity = state.last_data.get("angular", [0.0, 0.0, 0.0])
            
        except Exception as e:
            db.log_error(f"Failed to receive or parse ZMQ twist from topic '{topic}' at address '{address}': {e}")
            return False
        return True
