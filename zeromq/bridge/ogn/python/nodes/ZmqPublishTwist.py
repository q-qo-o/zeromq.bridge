# zeromq/bridge/ogn/python/nodes/ZmqPublishTwist.py
from zeromq.bridge.impl.zmq_manager import ZmqManager
import carb

class ZmqPublishTwistInternalState:
    def __init__(self):
        self.mgr = ZmqManager.get_instance()

class ZmqPublishTwist:
    @staticmethod
    def internal_state():
        return ZmqPublishTwistInternalState()

    @staticmethod
    def compute(db) -> bool:
        state = db.per_instance_state
        try:
            topic = db.inputs.topicName
            # Use provided address, or fall back to global address if empty
            address = db.inputs.pubAddress
            if not address or address.strip() == "":
                address = state.mgr.get_global_pub_address()
            
            # Prepare data
            data = {
                "linear": list(db.inputs.linearVelocity),
                "angular": list(db.inputs.angularVelocity)
            }
            
            # Publish
            state.mgr.publish_json(address, topic, data)
            
            # Exec out
            db.outputs.execOut = db.inputs.execIn
            
        except Exception as e:
            db.log_error(f"Failed to publish ZMQ twist: {e}")
            return False
        return True
