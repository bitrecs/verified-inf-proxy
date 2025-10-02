import time
from fiber.logging_utils import get_logger
from fiber.chain import interface
from fiber.chain.fetch_nodes import get_nodes_for_netuid

logger = get_logger(__name__)

# def test_fiber():
#     st = time.perf_counter()
#     substrate = interface.get_substrate(subtensor_network="test")    
#     mg = metagraph.Metagraph(substrate=substrate, netuid=296)
#     mg.sync_nodes()
#     logger.info(f"Found nodes: {mg.nodes}")
#     for node in mg.nodes:
#         logger.info(f"Node {node} has ip {node.ip} and port {node.port} and stake {node.stake}")
#     et = time.perf_counter()
#     logger.info(f"Fetched nodes in {et-st} seconds")
#     assert len(mg.nodes) > 50   


def test_fiber2():
    substrate = interface.get_substrate(subtensor_network="test")        
    st = time.perf_counter()
    nodes = get_nodes_for_netuid(substrate=substrate, netuid=296)
    logger.info(f"Found nodes: {nodes}")

    head = substrate.get_block()
    logger.info(f'Fetched {len(nodes)} nodes from block {head} on network test:296')        
    block_number = head['header']['number']
    assert isinstance(block_number, int)    
    logger.info(f'Block number is {block_number}')
    
    for node in nodes:
        logger.info(f"Node {node} has ip {node.ip} and port {node.port} and stake {node.stake}")
        continue
    et = time.perf_counter()
    logger.info(f"Fetched nodes in {et-st} seconds")   
    assert len(nodes) > 50

    

   


    