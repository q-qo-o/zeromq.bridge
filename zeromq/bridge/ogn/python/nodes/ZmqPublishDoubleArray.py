from zeromq.bridge.impl.zmq_manager import ZmqManager
import carb

class ZmqPublishDoubleArrayInternalState:
    def __init__(self):
        self.mgr = ZmqManager.get_instance()
        self.logged_pub = False

class ZmqPublishDoubleArray:
    @staticmethod
    def internal_state():
        return ZmqPublishDoubleArrayInternalState()

    @staticmethod
    def compute(db) -> bool:
        state = db.per_instance_state
        try:
            topic = db.inputs.topicName
            address = db.inputs.pubAddress
            if not address or address.strip() == "":
                address = state.mgr.get_global_pub_address()
            
            raw_data = db.inputs.data
            if hasattr(raw_data, "tolist"):
                data_list = raw_data.tolist()
            else:
                data_list = list(raw_data)
                
            payload = {"data": data_list}
            
            state.mgr.publish_json(address, topic, payload)
            
            if not state.logged_pub:
                carb.log_info(f"ZMQ double array publishing started: addr={address}, topic={topic}")
                state.logged_pub = True

            db.outputs.execOut = db.inputs.execIn
            
        except Exception as e:
            carb.log_error(f"Failed to publish ZMQ double array: {e}")
            return False
            
        return True