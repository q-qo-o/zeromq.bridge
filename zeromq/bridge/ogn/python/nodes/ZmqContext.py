# zeromq/bridge/ogn/python/nodes/ZmqContext.py
from zeromq.bridge.impl.zmq_manager import ZmqManager
import carb


class ZmqContextInternalState:
    mgr: ZmqManager
    is_initialized: bool

    def __init__(self):
        self.mgr = ZmqManager.get_instance()
        self.is_initialized = False


class ZmqContext:
    """
    ZmqContext node manages the global ZMQ context lifecycle.
    All data is transmitted through a single pair of addresses (PUB/SUB).
    Place this node at the start of your action graph to initialize ZMQ.
    Connect execOut to other ZMQ nodes to ensure proper ordering.
    """

    @staticmethod
    def internal_state():
        return ZmqContextInternalState()

    @staticmethod
    def compute(db) -> bool:
        state = db.per_instance_state

        try:
            # Get addresses from inputs
            pub_address = db.inputs.pubAddress
            sub_address = db.inputs.subAddress
            linger_ms = db.inputs.lingerMs

            context_changed = False

            # Initialize once; update addresses only if changed
            if state.is_initialized:
                current_pub = state.mgr.get_global_pub_address()
                current_sub = state.mgr.get_global_sub_address()
                next_pub = pub_address if pub_address else current_pub
                next_sub = sub_address if sub_address else current_sub

                if next_pub != current_pub or next_sub != current_sub:
                    state.mgr.set_global_addresses(pub_address, sub_address)
                    context_changed = True
            else:
                state.mgr.initialize(linger_ms=linger_ms, pub_address=pub_address, sub_address=sub_address)
                state.is_initialized = True
                context_changed = True

            # Output global addresses for reference
            db.outputs.outPubAddress = state.mgr.get_global_pub_address()
            db.outputs.outSubAddress = state.mgr.get_global_sub_address()

            # Signal that initialization is complete
            db.outputs.execOut = db.inputs.execIn

            if context_changed:
                carb.log_info(
                    f"ZmqContext updated - All data flows through PUB: {pub_address}, SUB: {sub_address}"
                )
            return True

        except Exception as e:
            carb.log_error(f"Failed to initialize ZmqContext: {e}")
            return False

    @staticmethod
    def on_connection_type_resolve(cls):
        # Called when the connection types are being resolved
        pass
