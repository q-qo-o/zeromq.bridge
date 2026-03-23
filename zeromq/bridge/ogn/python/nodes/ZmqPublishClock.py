# zeromq/bridge/ogn/python/nodes/ZmqPublishClock.py
from zeromq.bridge.impl.zmq_manager import ZmqManager
import math

class ZmqPublishClockInternalState:
    def __init__(self):
        self.mgr = ZmqManager.get_instance()
        self.logged_publish = False

class ZmqPublishClock:
    @staticmethod
    def internal_state():
        return ZmqPublishClockInternalState()

    @staticmethod
    def compute(db) -> bool:
        state = db.per_instance_state
        try:
            # Use provided address, or fall back to global address if empty
            address = db.inputs.pubAddress
            if not address or address.strip() == "":
                address = state.mgr.get_global_pub_address()
            
            topic = db.inputs.topicName
            time_s = db.inputs.timeStamp

            # Clock structure in ROS: sec, nsec
            sec = int(time_s)
            nanosec = int((time_s - sec) * 1e9)

            data = {"sec": sec, "nanosec": nanosec}

            state.mgr.publish_json(address, topic, data)
            if not state.logged_publish:
                db.log_info(f"ZMQ clock published: topic={topic}, addr={address}, sec={sec}, nanosec={nanosec}")
                state.logged_publish = True
            db.outputs.execOut = db.inputs.execIn

        except Exception as e:
            db.log_error(f"Failed to publish ZMQ clock: {e}")
            return False
        return True
