import json
import pandas as pd

def main():

  f = open('max-cut/graph_removed_nodes.json') # open('5may2022-graph.json') # LND `describegraph` output taken on May 5, 2022
  data = json.load(f)
  f.close()

  publicKeys = [x['pub_key'] for x in data['nodes']]
  publicKeyToId = {}
  for i in range(len(publicKeys)):
    publicKeyToId[publicKeys[i]] = i

  n = len(data['nodes'])

  objects = []
  id = 0

  for v in range(n):
    objects.append({
      "id" : id,
      "pub_key" : publicKeys[v]
    })

    id += 1
  
  df = pd.DataFrame.from_records(objects)
  df.to_csv("max-cut/cloth/nodes_lnd_5may2022_nodes_removed.csv",index=False)

  print("[NODES] done!")

  objects = []
  id = 0
  channelId = 0

  for e in data['edges']:
    
    if e["node1_policy"] != None:
      objects.append({
        "id" : id,
        "channel_id" : channelId, 
        "counter_edge_id" : id+1,
        "from_node_id" : publicKeyToId[e["node1_pub"]],
        "to_node_id" : publicKeyToId[e["node2_pub"]],
        "balance" : int(int(e["capacity"]) * 1000 / 2),
        "fee_base" : int(e["node1_policy"]["fee_base_msat"]),
        "fee_proportional" : int(e["node1_policy"]["fee_rate_milli_msat"]),
        "min_htlc" : int(e["node1_policy"]["min_htlc"]),
        "timelock" : int(e["node1_policy"]["time_lock_delta"])
      })
    else: # if policy is NULL, the edge must be discarded?
      objects.append({
        "id" : id,
        "channel_id" : channelId, 
        "counter_edge_id" : id+1,
        "from_node_id" : publicKeyToId[e["node1_pub"]],
        "to_node_id" : publicKeyToId[e["node2_pub"]],
        "balance" : int(int(e["capacity"]) * 1000 / 2), # millisat?
        "fee_base" : 0,
        "fee_proportional" : 0,
        "min_htlc" : 0,
        "timelock" : 0
      }) 

    id += 1

    if e["node2_policy"] != None:
      objects.append({
        "id" : id,
        "channel_id" : channelId, 
        "counter_edge_id" : id-1,
        "from_node_id" : publicKeyToId[e["node2_pub"]],
        "to_node_id" : publicKeyToId[e["node1_pub"]],
        "balance" : int(int(e["capacity"]) * 1000 / 2), 
        "fee_base" : int(e["node2_policy"]["fee_base_msat"]),
        "fee_proportional" : int(e["node2_policy"]["fee_rate_milli_msat"]),
        "min_htlc" : int(e["node2_policy"]["min_htlc"]),
        "timelock" : int(e["node2_policy"]["time_lock_delta"])
      })
    else:
      objects.append({
        "id" : id,
        "channel_id" : channelId, 
        "counter_edge_id" : id-1,
        "from_node_id" : publicKeyToId[e["node2_pub"]],
        "to_node_id" : publicKeyToId[e["node1_pub"]],
        "balance" : int(int(e["capacity"]) * 1000 / 2), 
        "fee_base" : 0,
        "fee_proportional" : 0,
        "min_htlc" : 0,
        "timelock" : 0
      })

    id += 1
    channelId += 1

  df = pd.DataFrame.from_records(objects)
  df.to_csv("max-cut/cloth/edges_lnd_5may2022_nodes_removed.csv",index=False)

  print("[EDGES] done!")  

  objects = []
  id = 0

  for e in data['edges']:
    objects.append({
      "id" : id,
      "edge1_id" : id,
      "edge2_id" : id+1,
      "node1_id" : publicKeyToId[e["node1_pub"]],
      "node2_id" : publicKeyToId[e["node2_pub"]],
      "capacity" : int(e["capacity"]) * 1000 
    })

    id += 1

  df = pd.DataFrame.from_records(objects)
  df.to_csv("max-cut/cloth/channels_lnd_5may2022_nodes_removed.csv",index=False)

  print("[CHANNELS] done!")  

if __name__ == "__main__":
  main()