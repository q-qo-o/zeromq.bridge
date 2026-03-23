# zeromq/bridge/ogn/python/nodes/ZmqCameraHelper.py
from zeromq.bridge.impl.zmq_manager import ZmqManager
import numpy as np
import carb
import json
import traceback
import cv2
from omni.isaac.sensor import Camera

class ZmqCameraHelperInternalState:
    def __init__(self):
        self.mgr = ZmqManager.get_instance()
        self.logged_image_capture = False
        self.logged_image_publish = False
        self.logged_image_empty = False
        self.camera_sensor = None
        self.camera_path = ""
        self.resolution = [0, 0]
        self.frame_delay = 0

    def clear(self):
        """Clean up resources"""
        self.camera_sensor = None
        self.camera_path = ""
        self.resolution = [0, 0]
        self.logged_image_capture = False
        self.logged_image_publish = False
        self.logged_image_empty = False
        self.frame_delay = 0

class ZmqCameraHelper:
    @staticmethod
    def internal_state():
        return ZmqCameraHelperInternalState()

    @staticmethod
    def compute(db) -> bool:
        state = db.per_instance_state
        try:
            # Get camera targets
            camera_targets = db.inputs.cameraPrim
            if not camera_targets or len(camera_targets) == 0:
                state.clear()
                return True
            
            camera_path = str(camera_targets[0])
            resolution = db.inputs.resolution
            
            if resolution[0] <= 0 or resolution[1] <= 0:
                db.log_warning(f"Invalid resolution: {resolution}")
                state.clear()
                return True

            address = db.inputs.pubAddress
            if not address or address.strip() == "":
                address = state.mgr.get_global_pub_address()

            topic = db.inputs.topicName
            frame_id = db.inputs.frameId

            # 1. Initialize or Update Camera Sensor
            if camera_path != state.camera_path or resolution[0] != state.resolution[0] or resolution[1] != state.resolution[1] or state.camera_sensor is None:
                state.clear()
                state.camera_path = camera_path
                state.resolution = [resolution[0], resolution[1]]
                
                try:
                    # 使用 Isaac Sensor Camera 类，参考 BehaviorScript
                    state.camera_sensor = Camera(prim_path=camera_path, resolution=(resolution[0], resolution[1]))
                    state.camera_sensor.initialize()
                    state.frame_delay = 5
                    db.log_info(f"Initialized RGBA Camera sensor for {camera_path}")
                except Exception as exc:
                    db.log_error(f"Failed to initialize Camera sensor: {exc}")
                    state.clear()
                    return False

            # 2. Process data from the camera sensor
            img_data = state.camera_sensor.get_rgba()

            if img_data is not None and img_data.size > 0:
                state.frame_delay = 0
                if not state.logged_image_capture:
                    db.log_info(f"ZMQ RGBA image captured: size={img_data.shape}")
                    state.logged_image_capture = True
                
                state.logged_image_empty = False

                # 转换颜色空间：RGBA -> BGRA (OpenCV 标准格式，保留 Alpha)
                bgra_image = cv2.cvtColor(img_data, cv2.COLOR_RGBA2BGRA)

                # 使用 PNG 编码以保留 Alpha 通道（JPEG 不支持 Alpha）
                _, buffer = cv2.imencode('.png', bgra_image)
                data_bytes = buffer.tobytes()

                # Metadata
                h, w, c = img_data.shape
                metadata = {
                    "width": w, "height": h, "channels": c, 
                    "encoding": "png", "frame_id": frame_id, "type": "image"
                }

                # Publish
                state.mgr.publish_image(address, topic, data_bytes, metadata)
                if not state.logged_image_publish:
                    db.log_info(f"ZMQ RGBA image published: topic={topic}, addr={address}, encoding=png")
                    state.logged_image_publish = True
            else:
                if state.frame_delay > 0:
                    state.frame_delay -= 1
                elif not state.logged_image_empty:
                    db.log_warning(f"RGBA image is empty for {camera_path}")
                    state.logged_image_empty = True
                state.logged_image_capture = False

            db.outputs.execOut = db.inputs.execIn

        except Exception as e:
            db.log_error(f"Failed to publish ZMQ RGBA image: {e}\n{traceback.format_exc()}")
            return False

        return True
