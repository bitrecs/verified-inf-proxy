import time
import logging
import traceback
import multiprocessing
from dotenv import load_dotenv
load_dotenv()
from typing import Dict, Any, Tuple
from fiber.chain import interface
from fiber.chain.metagraph import Metagraph

logger = logging.getLogger(__name__)


class MetagraphSyncManager:
    """Dedicated manager to keep metagraph data fresh without leaking threads."""
    def __init__(self, network: str, netuid: int, sync_interval: int = 600):
        self.network = network
        self.netuid = netuid
        self.sync_interval = sync_interval
        self._manager = multiprocessing.Manager()
        self._snapshot: Dict[str, Dict[str, Any]] = self._manager.dict()
        self._synced_at = self._manager.Value('f', None)
        self._stop_event = multiprocessing.Event()
        self._process: multiprocessing.Process | None = None

    def start(self) -> None:
        if self._process and self._process.is_alive():
            return
        self._stop_event.clear()
        self._process = multiprocessing.Process(
            target=self._run,
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
        return dict(self._snapshot), self._synced_at.value

    def _run(self) -> None:
        logger.info("MetagraphSyncManager process started")
        while not self._stop_event.is_set():
            substrate = None
            tmp_metagraph = None
            try:
                substrate = interface.get_substrate(subtensor_network=self.network)
                tmp_metagraph = Metagraph(
                    netuid=self.netuid,
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
                        
                self._snapshot.clear()
                self._snapshot.update(snapshot)
                self._synced_at.value = time.time()
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
            self._stop_event.wait(self.sync_interval)
        logger.info("MetagraphSyncManager process stopped")

