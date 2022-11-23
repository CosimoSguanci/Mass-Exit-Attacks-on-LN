
import os
from blockchain_parser.blockchain import Blockchain
import json

blocks_json_array = []

# To get the blocks ordered by height, you need to provide the path of the
# `index` directory (LevelDB index) being maintained by bitcoind. It contains
# .ldb files and is present inside the `blocks` directory.
blockchain = Blockchain(os.path.expanduser('.bitcoin/blocks'))
for block in blockchain.get_ordered_blocks(os.path.expanduser('.bitcoin/blocks/index'), start=498084, end=763821):
    print("height=%d block=%s len=%d" % (block.height, block.hash, block.n_transactions))
    b = {}
    b["height"] = block.height
    b["n_transactions"] = block.n_transactions
    header = block.header
    b["timestamp"] = header.timestamp.timestamp()
    blocks_json_array.append(b)

with open('blocks.json', 'w') as outfile:
    json.dump(blocks_json_array, outfile)