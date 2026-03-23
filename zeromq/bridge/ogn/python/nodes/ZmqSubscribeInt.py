# zeromq/bridge/ogn/python/nodes/ZmqSubscribeInt.py
from zeromq.bridge.impl.zmq_manager import ZmqManager
import carb

class ZmqSubscribeIntInternalState:
    def __init__(self):
        self.mgr = ZmqManager.get_instance()
        self.last_val = 0
        self.last_topic = ""
        self.subscription_requested = False
        self.last_timestamp = 0.0

class ZmqSubscribeInt:
    @staticmethod
    def internal_state():
        return ZmqSubscribeIntInternalState()

    @staticmethod
    def compute(db) -> bool:
        state = db.per_instance_state
        try:
            address = db.inputs.subAddress
            if not address or address.strip() == "":
                address = state.mgr.get_global_sub_address()
            
            # Force conversion to python string to avoid potential C++ binding/SSO issues
            topic = str(db.inputs.topicName)
            
            if topic != state.last_topic or not state.subscription_requested:
                state.mgr.request_subscription(topic, "Int32") # Default to Int32 for generic Int
                state.last_topic = topic
                state.subscription_requested = True
            
            recv_topic, data, timestamp = state.mgr.receive_json(address, topic)
            
            if data and recv_topic == topic and timestamp > state.last_timestamp:
                state.last_timestamp = timestamp
                state.last_val = int(data.get("data", 0))
                db.outputs.execOut = db.inputs.execIn
            
            db.outputs.data = state.last_val
            
        except Exception as e:
            db.log_error(f"Failed to receive ZMQ int: {e}")
            return False
            
        return True
