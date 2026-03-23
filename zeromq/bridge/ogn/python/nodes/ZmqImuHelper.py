# zeromq/bridge/ogn/python/nodes/ZmqImuHelper.py
from zeromq.bridge.impl.zmq_manager import ZmqManager
import carb
import traceback
import numpy as np
import omni.usd
from omni.isaac.sensor import IMUSensor

class ZmqImuHelperInternalState:
    def __init__(self):
        self.mgr = ZmqManager.get_instance()
        self.logged_pub = False
        self.imu_sensor = None
        self.imu_path = ""

    def clear(self):
        self.imu_sensor = None
        self.imu_path = ""
        self.logged_pub = False

class ZmqImuHelper:
    @staticmethod
    def internal_state():
        return ZmqImuHelperInternalState()

    @staticmethod
    def compute(db) -> bool:
        state = db.per_instance_state
        try:
            # Get imu targets
            imu_targets = db.inputs.imuPrim
            if not imu_targets or len(imu_targets) == 0:
                state.clear()
                return True
            
            imu_path = str(imu_targets[0])
            
            # Initialize or Update IMU Sensor
            if imu_path != state.imu_path or state.imu_sensor is None:
                state.clear()
                state.imu_path = imu_path
                
                try:
                    # 使用 Isaac Sensor IMUSensor
                    state.imu_sensor = IMUSensor(prim_path=imu_path)
                    state.imu_sensor.initialize()
                    db.log_info(f"Initialized IMU sensor for {imu_path}")
                except Exception as exc:
                    db.log_error(f"Failed to initialize IMU sensor: {exc}")
                    state.clear()
                    return False

            # Get reading from sensor
            reading = state.imu_sensor.get_current_frame()
            
            if reading is not None:
                # IMU typically provides linear_acceleration and angular_velocity
                # plus orientation if supported.
                accel = reading.get("lin_acc", [0.0, 0.0, 0.0])
                gyro = reading.get("ang_vel", [0.0, 0.0, 0.0])
                quat = reading.get("orientation", [1.0, 0.0, 0.0, 0.0])
                
                # Metadata
                address = db.inputs.pubAddress
                if not address or address.strip() == "":
                    address = state.mgr.get_global_pub_address()
                
                topic = db.inputs.topicName
                frame_id = db.inputs.frameId
                
                # Prepare data
                data = {
                    "header": {
                        "frame_id": frame_id,
                        "stamp": 0.0 # Placeholder for time
                    },
                    "orientation": {"x": float(quat[1]), "y": float(quat[2]), "z": float(quat[3]), "w": float(quat[0])},
                    "angular_velocity": {"x": float(gyro[0]), "y": float(gyro[1]), "z": float(gyro[2])},
                    "linear_acceleration": {"x": float(accel[0]), "y": float(accel[1]), "z": float(accel[2])},
                    "type": "imu"
                }

                # Publish
                state.mgr.publish_json(address, topic, data)
                
                if not state.logged_pub:
                    db.log_info(f"ZMQ IMU data published: topic={topic}, addr={address}")
                    state.logged_pub = True
            else:
                db.log_warning(f"IMU reading is None for {imu_path}")

            db.outputs.execOut = db.inputs.execIn

        except Exception as e:
            db.log_error(f"Failed to publish ZMQ IMU data: {e}\n{traceback.format_exc()}")
            return False

        return True
