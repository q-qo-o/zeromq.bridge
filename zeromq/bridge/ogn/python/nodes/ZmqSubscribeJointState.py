# zeromq/bridge/ogn/python/nodes/ZmqSubscribeJointState.py
from zeromq.bridge.impl.zmq_manager import ZmqManager
import omni.graph.core as og

class ZmqSubscribeJointStateInternalState:
    def __init__(self):
        self.mgr = ZmqManager.get_instance()
        self.last_data = {
            "name": [],
            "position": [],
            "velocity": []
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
            # Use provided address, or fall back to global address if empty
            address = db.inputs.subAddress
            if not address or address.strip() == "":
                address = state.mgr.get_global_sub_address()
            
            # Force conversion to python string to avoid potential C++ binding/SSO issues
            topic = str(db.inputs.topicName)
            
            # Send subscription request to ROS2 bridge (if topic changed or not yet requested)
            if topic != state.last_topic or not state.subscription_requested:
                state.mgr.request_subscription(topic, "JointState")
                state.last_topic = topic
                state.subscription_requested = True
            
            # Non-blocking receive
            recv_topic, data, timestamp = state.mgr.receive_json(address, topic)
            
            # Check if topic matches and is newer
            if recv_topic == topic and data and timestamp > state.last_timestamp:
                state.last_timestamp = timestamp
                state.last_data = data
                # Flag to signal receiving a new message
                db.outputs.execOut = db.inputs.execIn
                # db.log_info(f"Received ZMQ joint state on '{topic}': {len(data.get('name', []))} joints")
            
            # Update outputs with last known data
            db.outputs.jointNames = state.last_data.get("name", [])
            db.outputs.jointPositions = state.last_data.get("position", [])
            db.outputs.jointVelocities = state.last_data.get("velocity", [])
            
        except Exception as e:
            db.log_error(f"Failed to receive ZMQ joint state: {e}")
            return False
        return True
