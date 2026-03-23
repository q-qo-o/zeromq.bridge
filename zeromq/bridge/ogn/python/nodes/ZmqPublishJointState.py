# zeromq/bridge/ogn/python/nodes/ZmqPublishJointState.py
from zeromq.bridge.impl.zmq_manager import ZmqManager
import carb

class ZmqPublishJointStateInternalState:
    def __init__(self):
        self.mgr = ZmqManager.get_instance()
        self.logged_pub = False

class ZmqPublishJointState:
    @staticmethod
    def internal_state():
        return ZmqPublishJointStateInternalState()

    @staticmethod
    def compute(db) -> bool:
        state = db.per_instance_state
        try:
            # Topic name
            topic = db.inputs.topicName
            # Use provided address, or fall back to global address if empty
            address = db.inputs.pubAddress
            if not address or address.strip() == "":
                address = state.mgr.get_global_pub_address()
            
            # Prepare data
            data = {
                "name": [str(n) for n in db.inputs.jointNames],
                "position": list(db.inputs.jointPositions),
                "velocity": list(db.inputs.jointVelocities)
            }
            
            # Publish
            state.mgr.publish_json(address, topic, data)
            
            if not state.logged_pub:
                db.log_info(f"ZMQ joint state publishing started: addr={address}, topic={topic}")
                state.logged_pub = True

            # Exec out
            db.outputs.execOut = db.inputs.execIn
            
        except Exception as e:
            db.log_error(f"Failed to publish ZMQ joint state for topic '{topic}' at address '{address}': {e}")
            state.logged_pub = False
            return False
        return True
