from zeromq.bridge.impl.zmq_manager import ZmqManager
import carb
import numpy as np

class ZmqSubscribeDoubleArrayInternalState:
    def __init__(self):
        self.mgr = ZmqManager.get_instance()
        self.last_val = []
        self.last_topic = ""
        self.subscription_requested = False
        self.last_timestamp = 0.0

class ZmqSubscribeDoubleArray:
    @staticmethod
    def internal_state():
        return ZmqSubscribeDoubleArrayInternalState()

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
                state.mgr.request_subscription(topic, "Float64MultiArray")
                state.last_topic = topic
                state.subscription_requested = True
            
            recv_topic, data, timestamp = state.mgr.receive_json(address, topic)
            
            if data and recv_topic == topic and timestamp > state.last_timestamp:
                state.last_timestamp = timestamp
                val = data.get("data", [])
                if isinstance(val, list):
                    state.last_val = val
                else:
                    state.last_val = []
                db.outputs.execOut = db.inputs.execIn
            
            db.outputs.data = state.last_val
            
        except Exception as e:
            carb.log_error(f"Failed to receive ZMQ double array: {e}")
            return False
            
        return True