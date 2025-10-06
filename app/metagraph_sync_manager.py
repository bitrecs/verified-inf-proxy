import time
import logging
import traceback
import multiprocessing
import gc  # Added for explicit cleanup
from dotenv import load_dotenv
load_dotenv()
from typing import Dict, Any, Tuple
from fiber.chain import interface
from fiber.chain.metagraph import Metagraph

logger = logging.getLogger(__name__)

class MetagraphSyncManager:
    """Dedicated manager to keep metagraph data fresh without leaking threads."""
    def __init__(self, network: str, netuid: int, sync_interval: int = 600, max_cycles_before_restart: int = 8):
        self.network = network
        self.netuid = netuid
        self.sync_interval = sync_interval
        self.max_cycles_before_restart = max_cycles_before_restart
        self._snapshot: Dict[str, Dict[str, Any]] = {}
        self._synced_at: float | None = None
        self._stop_event = multiprocessing.Event()
        self._process: multiprocessing.Process | None = None
        self._queue: multiprocessing.Queue = multiprocessing.Queue()

    def start(self) -> None:
        if self._process and self._process.is_alive():
            return
        self._stop_event.clear()
        self._process = multiprocessing.Process(
            target=self._run,
            args=(self._queue, self._stop_event, self.network, self.netuid, self.sync_interval, self.max_cycles_before_restart),
            name="MetagraphSyncManager",
            daemon=True
        )
        self._process.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._process and self._process.is_alive():
            self._process.join(timeout=20)
            if self._process.is_alive():
                self._process.terminate()

    def get_snapshot(self) -> Tuple[Dict[str, Dict[str, Any]], float | None]:
        # Non-blocking get from queue
        try:
            while True:
                snapshot, synced_at = self._queue.get_nowait()
                self._snapshot = snapshot
                self._synced_at = synced_at
        except Exception:
            pass
        return dict(self._snapshot), self._synced_at

    @staticmethod
    def _run(queue, stop_event, network, netuid, sync_interval, max_cycles_before_restart) -> None:
        logger.info("MetagraphSyncManager process started")
        cycle_count = 0
        while not stop_event.is_set():
            substrate = None
            tmp_metagraph = None
            try:
                substrate = interface.get_substrate(subtensor_network=network)
                tmp_metagraph = Metagraph(
                    netuid=netuid,
                    substrate=substrate,
                    load_old_nodes=False
                )
                tmp_metagraph.sync_nodes()
                snapshot: Dict[str, Dict[str, Any]] = {}
                for hotkey, node in tmp_metagraph.nodes.items():
                    axon = getattr(node, "axon_info", None)
                    snapshot[hotkey] = {
                        "uid": getattr(node, "uid", None),
                        "ip": getattr(axon, "ip", None),
                        "port": getattr(axon, "port", None),
                        "stake": float(getattr(node, "stake", 0)),
                        "last_update": getattr(node, "last_update", None),
                        "version": getattr(node, "version", None),
                    }
                queue.put((snapshot, time.time()))
                logger.info(f"Metagraph sync complete: {len(snapshot)} nodes")
            except Exception as e:
                logger.error(f"Metagraph sync failed: {e}")
                logger.error(traceback.format_exc())
            finally:
                if tmp_metagraph is not None:
                    try:
                        tmp_metagraph.shutdown()
                    except Exception as e:
                        logger.warning(f"Error shutting down metagraph: {e}")
                if substrate is not None:
                    try:
                        substrate.close()
                        logger.info("Metagraph substrate connection closed")
                    except Exception as e:
                        logger.warning(f"Error closing substrate: {e}")
            # Force cleanup to prevent memory leaks
            try:
                del tmp_metagraph
                del substrate
                gc.collect()
            except NameError:
                pass  # Variables may not be defined if exception occurred early
            cycle_count += 1
            if cycle_count >= max_cycles_before_restart:
                logger.info(f"MetagraphSyncManager restarting after {cycle_count} cycles to clear memory")
                break
            stop_event.wait(sync_interval)
        logger.info("MetagraphSyncManager process stopped")

