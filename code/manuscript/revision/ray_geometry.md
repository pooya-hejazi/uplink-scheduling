# Geometry of the held-out channels

Run the descriptive calculation from the project root with Python, NumPy and SciPy. Supply the original two scene directories.

    python Gate_4/revision/ray_geometry.py --o1 PATH_TO_O1_60 --asu PATH_TO_ASU_CAMPUS1

The script joins 640 channel blocks to the corresponding archived deterministic 10-dB records at 32 and 64 users. It checks each channel-file digest against the original manifest, verifies ray identifiers and path counts against the source, and checks that all four archived terms sum to each reported gap. No optimization, training or timing is performed.

Each row in ray_geometry.csv describes one block and size. User indices and evenly spaced tones match the original crops. Mean pair overlap is the mean squared normalized inner product across all distinct users and tones. Mean effective rank averages the exponential entropy of the normalized Gram eigenvalues across tones. At 0.10 W per user, mean partner-rate interdecile averages the 90th minus the 10th percentile of each user's linear-MMSE rate across possible partners, first within each tone and then over users and tones. Gap, tone conflict (T2), local enclosure and achieved-action slack (T4), and partner-rate spread are in bit/s/Hz.

For ray scenes, median path count describes source rays per user and n_los counts users with a source LOS flag. The source directly identifies the first ray on LOS links. Strongest and direct power fractions use the sum of the received powers of up to 25 rays per user, the same path cap as channel generation. The direction resultant is the norm of the received-power-weighted mean three-dimensional unit direction at the base station (one for aligned rays). Path count, power fractions and direction resultant are medians across the tile's users. Summaries quoted in the paper use medians across tiles; scene-wide LOS counts sum the counts within tiles. Guarded tile widths are approximately 1.20 m and 12 m, respectively, so the scene comparison combines differences in propagation geometry, carrier and spatial sampling.

For the Rice comparison, the per-frame early bound, later fixed-action rate proxy and elapsed time are in Gate_4/source_data/fig6_HUB.csv and fig6_LO.csv, with full denominators in fig6_capture_counts.csv. Gate_2/results/rice_replay_HUB.json and rice_replay_LO.json contain the mask, prefix diagnostics and abstention identifiers. The independent unit for clock comparisons is a recording. Each clock configuration contributes one.
