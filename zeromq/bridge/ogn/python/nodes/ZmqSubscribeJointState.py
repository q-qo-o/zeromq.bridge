# zeromq/bridge/ogn/python/nodes/ZmqSubscribeJointState.py
from zeromq.bridge.impl.zmq_manager import ZmqManager
import omni.graph.core as og

try:
    import omni.timeline
except ImportError:
    pass
import time

class ZmqSubscribeJointStateInternalState:
    def __init__(self):
        self.mgr = ZmqManager.get_instance()
        self.last_data = {
            "name": [],
            "position": [],
            "velocity": [],
            "effort": []
        }
        self.last_topic = ""
        self.subscription_requested = False
        self.last_timestamp = 0.0

class ZmqSubscribeJointState:
    @staticmethod
    def internal_state():
        return ZmqSubscribeJointStateInternalState()

    @staticmethod
    def compute(db) -> bool:
        state = db.per_instance_state
        try:
            address = db.inputs.subAddress
            if not address or address.strip() == "":
                address = state.mgr.get_global_sub_address()
            
            topic = str(db.inputs.topicName)
            
            if topic != state.last_topic or not state.subscription_requested:
                state.mgr.request_subscription(topic, "JointState")
                state.last_topic = topic
                state.subscription_requested = True
            
            recv_topic, data, timestamp = state.mgr.receive_json(address, topic)
            
            if recv_topic == topic and data and timestamp > state.last_timestamp:
                state.last_timestamp = timestamp
                state.last_data = data
                db.outputs.execOut = db.inputs.execIn
            
            db.outputs.jointNames = state.last_data.get("name", [])
            db.outputs.positionCommand = state.last_data.get("position", [])
            db.outputs.velocityCommand = state.last_data.get("velocity", [])
            db.outputs.effortCommand = state.last_data.get("effort", [])
            db.outputs.timestamp = state.last_timestamp
            
        except Exception as e:
            db.log_error(f"Failed to receive ZMQ joint state: {e}")
            return False
        return True
