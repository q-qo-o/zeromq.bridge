from zeromq.bridge.impl.zmq_manager import ZmqManager
import carb
import omni.usd
from pxr import UsdGeom, Gf
import math
import traceback

class ZmqNavHelperInternalState:
    def __init__(self):
        self.mgr = ZmqManager.get_instance()
        self.logged_pub = False
        self.target_prim = None
        self.target_path = ""

    def clear(self):
        self.target_prim = None
        self.target_path = ""
        self.logged_pub = False

class ZmqNavHelper:
    @staticmethod
    def internal_state():
        return ZmqNavHelperInternalState()

    @staticmethod
    def compute(db) -> bool:
        state = db.per_instance_state
        try:
            # Inputs
            target_list = db.inputs.targetPrim
            if not target_list or len(target_list) == 0:
                state.clear()
                db.outputs.execOut = db.inputs.execIn
                return True
            
            target_path = str(target_list[0])
            
            # Cache prim
            if state.target_path != target_path or not state.target_prim or not state.target_prim.IsValid():
                stage = omni.usd.get_context().get_stage()
                if not stage:
                    return True
                
                prim = stage.GetPrimAtPath(target_path)
                if not prim or not prim.IsValid():
                    if state.target_path != target_path:
                        db.log_warning(f"ZmqNavHelper: Target prim {target_path} not found")
                    state.clear()
                    db.outputs.execOut = db.inputs.execIn
                    return True
                
                state.target_prim = prim
                state.target_path = target_path
            
            # Get Transform
            xform = omni.usd.get_world_transform_matrix(state.target_prim)
            translation = xform.ExtractTranslation()
            x, y, z = translation[0], translation[1], translation[2]
            
            # Use stage up-axis to align to ENU (East-North-Up)
            stage = omni.usd.get_context().get_stage()
            up_axis = UsdGeom.GetStageUpAxis(stage)
            
            if up_axis == 'Y':
                # World: Y-up. Assuming X=East, -Z=North, Y=Up
                x_enu = x
                y_enu = -z
                z_enu = y
            else:
                # World: Z-up. Assuming X=East, Y=North, Z=Up
                x_enu = x
                y_enu = y
                z_enu = z
                
            # Origin LLA
            lat0 = db.inputs.originLatitude
            lon0 = db.inputs.originLongitude
            alt0 = db.inputs.originAltitude
            
            # Convert to LLA
            lat, lon, alt = ZmqNavHelper.enu_to_lla(x_enu, y_enu, z_enu, lat0, lon0, alt0)
            
            # Prepare ZMQ data
            address = db.inputs.pubAddress
            if not address or address.strip() == "":
                address = state.mgr.get_global_pub_address()
                
            topic = db.inputs.topicName
            frame_id = db.inputs.frameId
            
            data = {
                "header": {
                    "frame_id": frame_id,
                    "stamp": 0.0 # Placeholder
                },
                "status": {
                    "status": 0,
                    "service": 1
                },
                "latitude": lat,
                "longitude": lon,
                "altitude": alt,
                "position_covariance": [0.0] * 9,
                "position_covariance_type": 0,
                "type": "gps"
            }
            
            # Publish
            state.mgr.publish_json(address, topic, data)
            
            if not state.logged_pub:
                db.log_info(f"ZMQ Nav data publishing started: topic={topic}, addr={address}")
                state.logged_pub = True
                
            db.outputs.execOut = db.inputs.execIn

        except Exception as e:
            db.log_error(f"Failed to publish ZMQ Nav data: {e}\n{traceback.format_exc()}")
            return False
            
        return True

    @staticmethod
    def enu_to_lla(x, y, z, lat0, lon0, alt0):
        # WGS84 Constants
        a = 6378137.0
        e2 = 0.00669437999014
        
        # Convert to radians
        lat0_rad = math.radians(lat0)
        lon0_rad = math.radians(lon0)
        
        # Radius of curvature in prime vertical
        N = a / math.sqrt(1 - e2 * math.sin(lat0_rad)**2)
        # Radius of curvature in meridian
        M = a * (1 - e2) / ((1 - e2 * math.sin(lat0_rad)**2)**1.5)
        
        # Delta lat/lon in radians
        d_lat = y / (M + alt0)
        # Avoid division by zero at poles, though N is large there. cos(lat) -> 0.
        cos_lat = math.cos(lat0_rad)
        if abs(cos_lat) < 1e-10:
             d_lon = 0
        else:
             d_lon = x / ((N + alt0) * cos_lat)
        
        # Result
        lat = math.degrees(lat0_rad + d_lat)
        lon = math.degrees(lon0_rad + d_lon)
        alt = alt0 + z
        
        return lat, lon, alt
