# Verification of the Communications Engineering edition

| Item | Check |
|---|---|
| Article and Supplementary Information | 31 and 37 pages, respectively. The 177-word abstract, six figures, seven supplementary notes, sixteen numbered tables and 51 ordered references were checked. Supplementary Tables 13a and 13b distinguish the pilot and transmitted-data cohorts. |
| PDFs and submission ZIPs | The manuscript compiled from its upload ZIP. The supplement compiled separately from its TeX and eight figure assets. All 68 article and supplement pages matched the distributed PDFs in extracted text and raster pixels. The supplementary upload ZIP contains exactly one PDF. |
| Historical rate calculations | The edition checker verifies the original audit receipt and 2,176 fixed-filter evaluations. Seven methods share each of 1,536 known-channel cases. The common ceiling certifies 408, 395 and 426 zero-price decisions at 16, 32 and 64 users, respectively. |
| Receiver results | In both captures the same 1,488 test frames contributed 714,240 symbols per user. The checker recalculates each user's counts and EVM and reconciles the pooled bit errors to 5,084 and 3,182,737. Independent QR decoding of test frame 514 reproduced the per-user hard-error counts. Frame 2,000 was empty in both sources. |
| Cost and timing sensitivity | Reconstructed seven-method ledgers cover 1,024 size/topology combinations. The LO timing check reproduces the original restricted search and two wider searches using the same four calibration frames. |
| Source Data | The ZIP has 33 members. The figure and table blocks include the per-frame receiver ledger, per-user summaries, LO pilot timing curve and per-topology solver costs. The public release contains derived measurements and digests. |

The retained marked papers and response describe an earlier edition. Its verification and original PDF links remain available at [commit 98874b4](https://github.com/pooya-hejazi/uplink-scheduling/tree/98874b4e66491251c2e403de38c22e9ef3bfdf78).
