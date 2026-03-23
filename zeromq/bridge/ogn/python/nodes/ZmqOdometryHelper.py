from zeromq.bridge.impl.zmq_manager import ZmqManager
import carb
import traceback
import omni.usd
from omni.isaac.core.prims import RigidPrim
import numpy as np

class ZmqOdometryHelperInternalState:
    def __init__(self):
        self.mgr = ZmqManager.get_instance()
        self.logged_pub = False
        self.rigid_prim = None
        self.prim_path = ""

    def clear(self):
        self.rigid_prim = None
        self.prim_path = ""
        self.logged_pub = False

class ZmqOdometryHelper:
    @staticmethod
    def internal_state():
        return ZmqOdometryHelperInternalState()

    @staticmethod
    def compute(db) -> bool:
        state = db.per_instance_state
        try:
            # Inputs (Trigger)
            # if not db.inputs.execIn:
            #    return True

            # Get target prims
            targets = db.inputs.targetPrim
            if not targets or len(targets) == 0:
                state.clear()
                db.outputs.execOut = db.inputs.execIn
                return True
            
            target_path = str(targets[0])
            
            # Initialize or Update Rigid Prim
            if target_path != state.prim_path or state.rigid_prim is None:
                state.clear()
                state.prim_path = target_path
                
                try:
                    # Initialize RigidPrim wrapper
                    # Check if prim exists and is valid
                    stage = omni.usd.get_context().get_stage()
                    if stage:
                        prim = stage.GetPrimAtPath(target_path)
                        if prim and prim.IsValid():
                            # Note: RigidPrim works best with UsdPhysics applied, but can work with simple Xforms for pose
                            # For velocities, we ideally need physics.
                            state.rigid_prim = RigidPrim(prim_path=target_path, name="zmq_odom_tracked_prim")
                            # We don't necessarily need to initialize the physics view if we just read properties,
                            # but initializing ensures we hook into physics correctly.
                            state.rigid_prim.initialize()
                            db.log_info(f"Initialized RigidPrim for {target_path}")
                        else:
                            db.log_warning(f"Prim {target_path} not found or invalid")
                except Exception as exc:
                    db.log_error(f"Failed to initialize RigidPrim: {exc}")
                    state.clear()
                    return False

            if state.rigid_prim:
                # 1. Get Pose (World Frame)
                # position: np.array([x, y, z])
                # orientation: np.array([w, x, y, z]) (scalar-first quaternion in Isaac Core!)
                position, orientation = state.rigid_prim.get_world_pose()
                
                # 2. Get Velocity (World Frame)
                # linear_velocity: np.array([vx, vy, vz])
                # angular_velocity: np.array([wx, wy, wz])
                try:
                    lin_vel = state.rigid_prim.get_linear_velocity()
                    ang_vel = state.rigid_prim.get_angular_velocity()
                except Exception:
                    # Fallback if physics not running or not a rigid body
                     lin_vel = np.zeros(3)
                     ang_vel = np.zeros(3)

                # Metadata
                address = db.inputs.pubAddress
                if not address or address.strip() == "":
                    address = state.mgr.get_global_pub_address()
                
                topic = db.inputs.topicName
                frame_id = db.inputs.frameId
                child_frame_id = db.inputs.childFrameId
                
                # Construct Payload (ROS-like Odometry)
                # Note: ROS quaternions are [x, y, z, w], Isaac Core usually returns [w, x, y, z]
                # We need to map [w, x, y, z] -> [x, y, z, w] for standard ZMQ usage if clients expect ROS convention.
                # Let's assume ZMQ clients expect ROS geometry_msgs convention.
                
                q_w, q_x, q_y, q_z = orientation
                
                data = {
                    "header": {
                        "frame_id": frame_id,
                        "stamp": 0.0 # Placeholder
                    },
                    "child_frame_id": child_frame_id,
                    "pose": {
                        "pose": {
                            "position": {"x": float(position[0]), "y": float(position[1]), "z": float(position[2])},
                            "orientation": {"x": float(q_x), "y": float(q_y), "z": float(q_z), "w": float(q_w)}
                        },
                        # 6x6 covariance matrix flattened
                        "covariance": [0.0] * 36
                    },
                    "twist": {
                        "twist": {
                            "linear": {"x": float(lin_vel[0]), "y": float(lin_vel[1]), "z": float(lin_vel[2])},
                            "angular": {"x": float(ang_vel[0]), "y": float(ang_vel[1]), "z": float(ang_vel[2])}
                        },
                        "covariance": [0.0] * 36
                    },
                    "type": "odom"
                }

                # Publish
                state.mgr.publish_json(address, topic, data)
                
                if not state.logged_pub:
                    db.log_info(f"ZMQ Odometry published: topic={topic}, addr={address}")
                    state.logged_pub = True

            db.outputs.execOut = db.inputs.execIn

        except Exception as e:
            db.log_error(f"Failed to publish ZMQ Odometry: {e}\n{traceback.format_exc()}")
            return False

        return True
