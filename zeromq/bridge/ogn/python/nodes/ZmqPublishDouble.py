# zeromq/bridge/ogn/python/nodes/ZmqPublishDouble.py
from zeromq.bridge.impl.zmq_manager import ZmqManager
import carb

class ZmqPublishDoubleInternalState:
    def __init__(self):
        self.mgr = ZmqManager.get_instance()
        self.logged_pub = False

class ZmqPublishDouble:
    @staticmethod
    def internal_state():
        return ZmqPublishDoubleInternalState()

    @staticmethod
    def compute(db) -> bool:
        state = db.per_instance_state
        try:
            topic = db.inputs.topicName
            address = db.inputs.pubAddress
            if not address or address.strip() == "":
                address = state.mgr.get_global_pub_address()
            
            data = {"data": float(db.inputs.data)}
            
            state.mgr.publish_json(address, topic, data)
            
            if not state.logged_pub:
                db.log_info(f"ZMQ double publishing started: addr={address}, topic={topic}")
                state.logged_pub = True

            db.outputs.execOut = db.inputs.execIn
            
        except Exception as e:
            db.log_error(f"Failed to publish ZMQ double: {e}")
            return False
            
        return True
