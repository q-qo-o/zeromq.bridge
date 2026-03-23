from zeromq.bridge.impl.zmq_manager import ZmqManager
import carb
import omni.usd
from pxr import UsdGeom
import traceback

class ZmqAltimeterHelperInternalState:
    def __init__(self):
        self.mgr = ZmqManager.get_instance()
        self.logged_pub = False
        self.target_prim = None
        self.target_path = ""

    def clear(self):
        self.target_prim = None
        self.target_path = ""
        self.logged_pub = False

class ZmqAltimeterHelper:
    @staticmethod
    def internal_state():
        return ZmqAltimeterHelperInternalState()

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
                        db.log_warning(f"ZmqAltimeterHelper: Target prim {target_path} not found")
                    state.clear()
                    db.outputs.execOut = db.inputs.execIn
                    return True
                
                state.target_prim = prim
                state.target_path = target_path
            
            # Get Transform
            xform = omni.usd.get_world_transform_matrix(state.target_prim)
            translation = xform.ExtractTranslation()
            x, y, z = translation[0], translation[1], translation[2]
            
            # Use stage up-axis
            stage = omni.usd.get_context().get_stage()
            up_axis = UsdGeom.GetStageUpAxis(stage)
            
            current_z = z
            if up_axis == 'Y':
                current_z = y
                
            water_surface = db.inputs.waterSurfaceZ
            
            # Calculate Altitude: current_z - water_surface
            # If current_z < water_surface (below water), altitude < 0.
            # Requirement: If below surface, output 0.
            altitude = current_z - water_surface
            if altitude < 0:
                altitude = 0.0
                
            # Prepare ZMQ data (Float32 format)
            address = db.inputs.pubAddress
            if not address or address.strip() == "":
                address = state.mgr.get_global_pub_address()
                
            topic = db.inputs.topicName
            
            data = {
                "data": float(altitude)
            }
            
            # Publish
            state.mgr.publish_json(address, topic, data)
            
            if not state.logged_pub:
                db.log_info(f"ZMQ Altimeter data published: topic={topic}, addr={address}")
                state.logged_pub = True
                
            db.outputs.execOut = db.inputs.execIn

        except Exception as e:
            db.log_error(f"Failed to publish ZMQ Altimeter data: {e}\n{traceback.format_exc()}")
            return False
            
        return True
