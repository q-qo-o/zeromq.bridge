# zeromq/bridge/ogn/python/nodes/ZmqPublishJointState.py
from zeromq.bridge.impl.zmq_manager import ZmqManager
import omni.graph.core as og
import carb
try:
    from omni.isaac.dynamic_control import _dynamic_control
except ImportError:
    pass

class ZmqPublishJointStateInternalState:
    def __init__(self):
        self.mgr = ZmqManager.get_instance()
        self.logged_pub = False
        try:
            self.dc = _dynamic_control.acquire_dynamic_control_interface()
        except:
            self.dc = None
        self.art_handle = None
        self.last_target_path = ""

class ZmqPublishJointState:
    @staticmethod
    def internal_state():
        return ZmqPublishJointStateInternalState()

    @staticmethod
    def compute(db) -> bool:
        state = db.per_instance_state
        try:
            # Topic name
            topic = str(db.inputs.topicName)
            # Use provided address, or fall back to global address if empty
            address = db.inputs.pubAddress
            if not address or address.strip() == "":
                address = state.mgr.get_global_pub_address()
            
            # Read target prim
            target_prims = db.inputs.targetPrim
            if not target_prims or len(target_prims) == 0:
                carb.log_warn("ZmqPublishJointState: No Target Prim provided.")
                return False
                
            prim_path = target_prims[0]
            if hasattr(prim_path, "pathString"):
                prim_path = prim_path.pathString
            else:
                prim_path = str(prim_path)

            if state.dc is None:
                carb.log_error("Dynamic Control interface not available.")
                return False

            if prim_path != state.last_target_path or state.art_handle == _dynamic_control.INVALID_HANDLE or state.art_handle is None:
                state.art_handle = state.dc.get_articulation(prim_path)
                state.last_target_path = prim_path

            if state.art_handle == _dynamic_control.INVALID_HANDLE:
                carb.log_warn(f"ZmqPublishJointState: Invalid articulation prim at {prim_path}")
                return False
                
            # Read states from DC
            dof_count = state.dc.get_articulation_dof_count(state.art_handle)
            dof_states = state.dc.get_articulation_dof_states(state.art_handle, _dynamic_control.STATE_ALL)
            
            names = []
            positions = []
            velocities = []
            efforts = []
            
            if dof_count > 0 and dof_states is not None:
                for i in range(dof_count):
                    dof = state.dc.get_articulation_dof(state.art_handle, i)
                    names.append(state.dc.get_dof_name(dof))
                
                # dof_states is a structured array containing pos, vel, effort
                for s in dof_states:
                    positions.append(float(s["pos"]))
                    velocities.append(float(s["vel"]))
                    efforts.append(float(s["effort"]))

            # Prepare data
            data = {
                "name": names,
                "position": positions,
                "velocity": velocities,
                "effort": efforts,
                "timestamp": float(db.inputs.timestamp)
            }
            
            # Publish
            state.mgr.publish_json(address, topic, data)
            
            if not state.logged_pub:
                db.log_info(f"ZMQ joint state publishing started: addr={address}, topic={topic}")
                state.logged_pub = True

            # Exec out
            db.outputs.execOut = db.inputs.execIn
            
        except Exception as e:
            db.log_error(f"Failed to publish ZMQ joint state for topic '{topic}': {e}")
            state.logged_pub = False
            return False
        return True
