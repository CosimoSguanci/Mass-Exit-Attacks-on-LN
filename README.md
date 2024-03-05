# Mass Exit Attacks on the Lightning Network

This repository implements the simulations needed to carry out the analysis presented in the <b>"Mass Exit Attacks on the Lightning Network"</b> paper.

[ArXiv preprint](https://arxiv.org/abs/2208.01908) <br>
[IEEE ICBC 2023 poster](https://ieeexplore.ieee.org/document/10174926)

The repository is structured as follows.

```
root
|⎯ blocks
|⎯ max-cut
|⎯ mempool-during-congestion
|⎯ mempool-no-congestion
|⎯ mempool-simulator
|⎯ network simulation
```

`blocks` contains the script to extract the block data from a Bitcoin node, and the dataset used; <br>
`max-cut` contains the greedy heuristic used to compute the k-lopsided max-cut; <br>
`mempool-during-congestion`: mempool historical data in a period of high transaction congestion; <br>
`mempool-no-congestion`: mempool historical data in a period of typical transaction congestion. <br>

To simulate mass exit attacks, two sets of simulations have been developed:

<ul>
 <li><b>Mempool simulation</b>: only the Bitcoin mempool is simulated, as a queue of transactions with priority. Using historical data about mempool transactions and Bitcoin blocks, we estimate the confirmation time of Bitcoin transactions related to the attack (mainly LN justice transactions and channel force-closing transactions). Mempool simulations are implemented as Jupyter notebooks.</li>
 <li><b>Network simulation</b>: this simulation involves running an actual local Bitcoin blockchain and LN to simulate the attacks, and evaluate their outcome running software used in real-world scenarios (Bitcoin Core and LND). Network simulations are implemented as a Python script that makes use of Bitcoin Core and LND commands.</li>
</ul>

 
